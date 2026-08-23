"""
Point-in-time (PIT) enforcement regression tests.

Validates that analysis orchestrators correctly enforce
available_at boundaries for FinancialSnapshot inputs:

  1. available_at <= as_of  → accepted
  2. available_at > as_of   → rejected
  3. available_at missing   → rejected (not treated as safe)
  4. mixed snapshots        → only valid ones pass through
  5. exact boundary         → accepted at exact as_of
  6. backward compat        → tests with available_at still work
  7. no future leakage      → derived observations never see future data
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.analysis.business_intelligence import (
    analyze_business_intelligence,
)
from src.analysis.deep_fundamental import (
    analyze_deep_fundamentals,
)
from src.data.company.business_profile import BusinessProfile
from src.data.company.financials import FinancialSnapshot


def _make_snapshot(
    period_end: date,
    available_at: datetime | None = None,
    revenue: Decimal = Decimal("1000"),
    net_profit: Decimal = Decimal("100"),
) -> FinancialSnapshot:
    return FinancialSnapshot(
        symbol="TEST",
        period_end=period_end,
        available_at=available_at,
        revenue=revenue,
        net_profit=net_profit,
    )


def _utc(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# deep_fundamental orchestrator PIT enforcement
# ---------------------------------------------------------------------------


class TestDeepFundamentalPIT:
    """PIT enforcement in analyze_deep_fundamentals."""

    AS_OF = _utc(2024, 6, 15)

    def test_available_at_before_as_of_accepted(self):
        snap = _make_snapshot(
            date(2024, 3, 31),
            available_at=_utc(2024, 5, 1),
        )
        result = analyze_deep_fundamentals(
            [snap], "TEST", self.AS_OF
        )
        assert result.period_count == 1

    def test_available_at_after_as_of_rejected(self):
        snap = _make_snapshot(
            date(2024, 3, 31),
            available_at=_utc(2024, 7, 1),
        )
        result = analyze_deep_fundamentals(
            [snap], "TEST", self.AS_OF
        )
        assert result.period_count == 0
        assert any("PIT filter" in n for n in result.notes)

    def test_available_at_missing_rejected(self):
        snap = _make_snapshot(
            date(2024, 3, 31),
            available_at=None,
        )
        result = analyze_deep_fundamentals(
            [snap], "TEST", self.AS_OF
        )
        assert result.period_count == 0
        assert any("PIT filter" in n for n in result.notes)

    def test_mixed_snapshots_partial_rejection(self):
        accepted = _make_snapshot(
            date(2024, 3, 31),
            available_at=_utc(2024, 5, 1),
            revenue=Decimal("1000"),
        )
        future = _make_snapshot(
            date(2024, 6, 30),
            available_at=_utc(2024, 8, 1),
            revenue=Decimal("2000"),
        )
        no_avail = _make_snapshot(
            date(2024, 9, 30),
            available_at=None,
            revenue=Decimal("3000"),
        )
        result = analyze_deep_fundamentals(
            [accepted, future, no_avail], "TEST", self.AS_OF
        )
        assert result.period_count == 1
        assert result.first_period == "2024-03-31"

    def test_exact_boundary_accepted(self):
        snap = _make_snapshot(
            date(2024, 3, 31),
            available_at=self.AS_OF,
        )
        result = analyze_deep_fundamentals(
            [snap], "TEST", self.AS_OF
        )
        assert result.period_count == 1

    def test_one_second_after_boundary_rejected(self):
        snap = _make_snapshot(
            date(2024, 3, 31),
            available_at=self.AS_OF + timedelta(seconds=1),
        )
        result = analyze_deep_fundamentals(
            [snap], "TEST", self.AS_OF
        )
        assert result.period_count == 0

    def test_no_future_data_in_trajectories(self):
        past = _make_snapshot(
            date(2023, 3, 31),
            available_at=_utc(2023, 5, 1),
            revenue=Decimal("1000"),
        )
        future = _make_snapshot(
            date(2024, 3, 31),
            available_at=_utc(2024, 8, 1),
            revenue=Decimal("2000"),
        )
        result = analyze_deep_fundamentals(
            [past, future], "TEST", self.AS_OF
        )
        assert result.period_count == 1
        assert result.first_period == "2023-03-31"

    def test_pit_note_records_rejection_count(self):
        snaps = [
            _make_snapshot(date(2024, 1, 31), available_at=_utc(2024, 3, 1)),
            _make_snapshot(date(2024, 3, 31), available_at=None),
            _make_snapshot(date(2024, 6, 30), available_at=_utc(2024, 8, 1)),
        ]
        result = analyze_deep_fundamentals(snaps, "TEST", self.AS_OF)
        pit_notes = [n for n in result.notes if "PIT filter" in n]
        assert len(pit_notes) >= 1
        assert "2 snapshot(s) rejected" in pit_notes[0]


# ---------------------------------------------------------------------------
# business_intelligence orchestrator PIT enforcement
# ---------------------------------------------------------------------------


class TestBusinessIntelligencePIT:
    """PIT enforcement in analyze_business_intelligence."""

    AS_OF = _utc(2024, 6, 15)

    def test_available_at_before_as_of_accepted(self):
        profile = BusinessProfile(symbol="TEST", sector="Tech")
        snap = _make_snapshot(
            date(2024, 3, 31),
            available_at=_utc(2024, 5, 1),
        )
        result = analyze_business_intelligence(
            [snap], profile, [], [], "TEST", self.AS_OF
        )
        assert result.business_analysis is not None

    def test_available_at_after_as_of_rejected(self):
        profile = BusinessProfile(symbol="TEST", sector="Tech")
        snap = _make_snapshot(
            date(2024, 3, 31),
            available_at=_utc(2024, 7, 1),
        )
        result = analyze_business_intelligence(
            [snap], profile, [], [], "TEST", self.AS_OF
        )
        assert result.business_analysis is None
        assert any("PIT filter" in n for n in result.notes)

    def test_available_at_missing_rejected(self):
        profile = BusinessProfile(symbol="TEST", sector="Tech")
        snap = _make_snapshot(
            date(2024, 3, 31),
            available_at=None,
        )
        result = analyze_business_intelligence(
            [snap], profile, [], [], "TEST", self.AS_OF
        )
        assert result.business_analysis is None
        assert any("PIT filter" in n for n in result.notes)

    def test_exact_boundary_accepted(self):
        profile = BusinessProfile(symbol="TEST", sector="Tech")
        snap = _make_snapshot(
            date(2024, 3, 31),
            available_at=self.AS_OF,
        )
        result = analyze_business_intelligence(
            [snap], profile, [], [], "TEST", self.AS_OF
        )
        assert result.business_analysis is not None

    def test_management_changes_pit_filtered(self):
        profile = BusinessProfile(symbol="TEST", sector="Tech")
        snap = _make_snapshot(
            date(2024, 3, 31),
            available_at=_utc(2024, 5, 1),
        )
        from src.data.company.management import ManagementChange

        past_change = ManagementChange(
            symbol="TEST",
            person_name="Jane Doe",
            role="CFO",
            change_type="Appointment",
            effective_date=date(2024, 1, 15),
        )
        future_change = ManagementChange(
            symbol="TEST",
            person_name="John Smith",
            role="CEO",
            change_type="Appointment",
            effective_date=date(2024, 8, 1),
        )
        result = analyze_business_intelligence(
            [snap],
            profile,
            [],
            [past_change, future_change],
            "TEST",
            self.AS_OF,
        )
        assert result.management_analysis is not None
        assert result.management_analysis.change_count == 1

    def test_pit_note_records_both_rejections(self):
        profile = BusinessProfile(symbol="TEST", sector="Tech")
        snap_future = _make_snapshot(
            date(2024, 3, 31),
            available_at=_utc(2024, 8, 1),
        )
        from src.data.company.management import ManagementChange

        future_mgmt = ManagementChange(
            symbol="TEST",
            person_name="X",
            role="CEO",
            change_type="Appointment",
            effective_date=date(2024, 9, 1),
        )
        result = analyze_business_intelligence(
            [snap_future],
            profile,
            [],
            [future_mgmt],
            "TEST",
            self.AS_OF,
        )
        pit_notes = [n for n in result.notes if "PIT filter" in n]
        assert len(pit_notes) >= 2
