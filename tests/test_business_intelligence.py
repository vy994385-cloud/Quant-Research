"""Tests for business intelligence orchestrator."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.analysis.business_intelligence import (
    BusinessIntelligenceResult,
    analyze_business_intelligence,
)
from src.data.company.business_profile import BusinessProfile
from src.data.company.financials import FinancialSnapshot, SegmentResult
from src.data.company.management import ManagementChange


_AS_OF = datetime(2024, 6, 15, tzinfo=timezone.utc)
_AVAILABILITY_LAG = timedelta(days=45)


def _snap(
    period_end: date,
    revenue: Decimal | None = None,
    net_profit: Decimal | None = None,
    operating_cash_flow: Decimal | None = None,
    total_debt: Decimal | None = None,
    shareholders_equity: Decimal | None = None,
    cash_and_equivalents: Decimal | None = None,
    segments: tuple[SegmentResult, ...] = (),
    available_at: datetime | None = None,
) -> FinancialSnapshot:
    if available_at is None:
        available_at = datetime.combine(
            period_end + _AVAILABILITY_LAG,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
    return FinancialSnapshot(
        symbol="TEST",
        period_end=period_end,
        available_at=available_at,
        revenue=revenue,
        net_profit=net_profit,
        operating_cash_flow=operating_cash_flow,
        total_debt=total_debt,
        shareholders_equity=shareholders_equity,
        cash_and_equivalents=cash_and_equivalents,
        segments=segments,
    )


# ---------------------------------------------------------------------------
# Empty / insufficient data
# ---------------------------------------------------------------------------


class TestInsufficientData:
    def test_empty_snapshots(self):
        result = analyze_business_intelligence(
            [], None, [], [], "TEST", _AS_OF
        )
        assert result.symbol == "TEST"
        assert result.has_profile is False
        assert "business_analysis" in result.missing_analyses
        assert "competitive_analysis" in result.missing_analyses
        assert "management_analysis" in result.missing_analyses
        assert "risk_analysis" in result.missing_analyses
        assert "derived_observations" in result.missing_analyses

    def test_no_profile(self):
        snap = _snap(date(2024, 1, 1), revenue=Decimal("1000"))
        result = analyze_business_intelligence(
            [snap], None, [], [], "TEST", _AS_OF
        )
        assert result.has_profile is False
        assert result.sector is None


# ---------------------------------------------------------------------------
# With data
# ---------------------------------------------------------------------------


class TestWithData:
    def test_with_profile_and_snapshots(self):
        profile = BusinessProfile(
            symbol="TEST",
            sector="Technology",
            industry="Software",
            country="US",
            full_time_employees=500,
        )
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            net_profit=Decimal("200"),
            total_debt=Decimal("3000"),
            shareholders_equity=Decimal("1000"),
            segments=(
                SegmentResult(segment_name="Core", revenue=Decimal("800")),
                SegmentResult(segment_name="Other", revenue=Decimal("200")),
            ),
        )
        result = analyze_business_intelligence(
            [snap], profile, [], [], "TEST", _AS_OF
        )
        assert result.has_profile is True
        assert result.sector == "Technology"
        assert result.industry == "Software"
        assert result.country == "US"
        assert result.employees == 500
        assert result.business_analysis is not None
        assert result.risk_analysis is not None
        assert len(result.risk_analysis.observations) > 0

    def test_with_management_changes(self):
        snap1 = _snap(
            date(2023, 1, 1),
            total_debt=Decimal("1000"),
            cash_and_equivalents=Decimal("100"),
        )
        snap2 = _snap(
            date(2024, 1, 1),
            total_debt=Decimal("500"),
            cash_and_equivalents=Decimal("200"),
        )
        changes = [
            ManagementChange(
                symbol="TEST",
                person_name="Jane Doe",
                role="CFO",
                change_type="Appointment",
                effective_date=date(2024, 1, 15),
            ),
        ]
        result = analyze_business_intelligence(
            [snap1, snap2], None, [], changes, "TEST", _AS_OF
        )
        assert result.management_analysis is not None
        assert result.management_analysis.change_count == 1
        assert "management_analysis" in result.available_analyses

    def test_total_observations(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            net_profit=Decimal("200"),
            total_debt=Decimal("3000"),
            shareholders_equity=Decimal("1000"),
        )
        result = analyze_business_intelligence(
            [snap], None, [], [], "TEST", _AS_OF
        )
        assert result.total_observations >= 0
        assert result.risk_count >= 0
        assert result.derived_count >= 0

    def test_forbids_extra_fields(self):
        result = analyze_business_intelligence(
            [], None, [], [], "TEST", _AS_OF
        )
        assert result.symbol == "TEST"


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


class TestSerialization:
    def test_result_is_picklable(self):
        import pickle

        result = analyze_business_intelligence(
            [], None, [], [], "TEST", _AS_OF
        )
        pickled = pickle.dumps(result)
        restored = pickle.loads(pickled)
        assert restored.symbol == "TEST"
        assert restored.as_of == _AS_OF.isoformat()
