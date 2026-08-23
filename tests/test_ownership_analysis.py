"""Tests for ownership analysis engine."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.analysis.ownership_analysis import (
    OwnershipAnalysisResult,
    OwnershipDirection,
    OwnershipPeriod,
    OwnershipSignal,
    OwnershipSeverity,
    OwnershipTrend,
    analyze_ownership,
)
from src.data.company.ownership import OwnershipSnapshot


_AS_OF = datetime(2024, 6, 15, tzinfo=timezone.utc)


def _snap(
    period_end: date,
    promoter: Decimal | None = None,
    institutional: Decimal | None = None,
    public: Decimal | None = None,
    pledge: Decimal | None = None,
) -> OwnershipSnapshot:
    return OwnershipSnapshot(
        symbol="TEST",
        period_end=period_end,
        promoter_percentage=promoter,
        institutional_percentage=institutional,
        public_percentage=public,
        promoter_pledged_percentage=pledge,
    )


# ---------------------------------------------------------------------------
# Empty / insufficient data
# ---------------------------------------------------------------------------


class TestInsufficientData:
    def test_empty_snapshots(self):
        result = analyze_ownership([], "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert result.snapshot_count == 0
        assert len(result.periods) == 0
        assert len(result.notes) > 0

    def test_single_snapshot_no_trend(self):
        snap = _snap(date(2024, 1, 1), promoter=Decimal("51"))
        result = analyze_ownership([snap], "TEST", _AS_OF)
        assert result.snapshot_count == 1
        assert len(result.periods) == 1
        assert len(result.trends) == 0

    def test_pit_filter_future_date(self):
        snap = _snap(date(2024, 1, 1), promoter=Decimal("51"))
        future = datetime(2023, 1, 1, tzinfo=timezone.utc)
        result = analyze_ownership([snap], "TEST", future)
        assert result.snapshot_count == 0


# ---------------------------------------------------------------------------
# Period building
# ---------------------------------------------------------------------------


class TestPeriodBuilding:
    def test_basic_fields(self):
        snap = _snap(
            date(2024, 1, 1),
            promoter=Decimal("51.5"),
            institutional=Decimal("27.3"),
            public=Decimal("21.2"),
            pledge=Decimal("10.0"),
        )
        result = analyze_ownership([snap], "TEST", _AS_OF)
        period = result.periods[0]
        assert period.promoter_pct == "51.5"
        assert period.institutional_pct == "27.3"
        assert period.public_pct == "21.2"
        assert period.pledge_pct == "10.0"

    def test_concentration_ratio(self):
        snap = _snap(
            date(2024, 1, 1),
            promoter=Decimal("50"),
            institutional=Decimal("30"),
            public=Decimal("20"),
        )
        result = analyze_ownership([snap], "TEST", _AS_OF)
        period = result.periods[0]
        # 50 / (30 + 20) = 1.0
        assert period.concentration_ratio == "1.00"

    def test_coverage_pct(self):
        snap = _snap(
            date(2024, 1, 1),
            promoter=Decimal("50"),
            institutional=Decimal("30"),
            public=Decimal("20"),
        )
        result = analyze_ownership([snap], "TEST", _AS_OF)
        assert result.periods[0].coverage_pct == "100.00"

    def test_missing_fields(self):
        snap = _snap(date(2024, 1, 1))
        result = analyze_ownership([snap], "TEST", _AS_OF)
        period = result.periods[0]
        assert period.promoter_pct is None
        assert period.concentration_ratio is None


# ---------------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------------


class TestTrends:
    def test_increasing_promoter(self):
        snaps = [
            _snap(date(2024, 1, 1), promoter=Decimal("40")),
            _snap(date(2024, 6, 1), promoter=Decimal("50")),
        ]
        result = analyze_ownership(snaps, "TEST", _AS_OF)
        assert len(result.trends) >= 1
        trend = result.trends[0]
        assert trend.direction == OwnershipDirection.INCREASING.value
        assert trend.first_value == "40"
        assert trend.last_value == "50"

    def test_decreasing_institutional(self):
        snaps = [
            _snap(
                date(2024, 1, 1), institutional=Decimal("40")
            ),
            _snap(
                date(2024, 6, 1), institutional=Decimal("25")
            ),
        ]
        result = analyze_ownership(snaps, "TEST", _AS_OF)
        trend = result.trends[0]
        assert trend.direction == OwnershipDirection.DECREASING.value

    def test_stable_trend(self):
        snaps = [
            _snap(date(2024, 1, 1), promoter=Decimal("50")),
            _snap(date(2024, 6, 1), promoter=Decimal("50")),
        ]
        result = analyze_ownership(snaps, "TEST", _AS_OF)
        trend = result.trends[0]
        assert trend.direction == OwnershipDirection.STABLE.value


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------


class TestSignals:
    def test_low_promoter_signal(self):
        snap = _snap(
            date(2024, 1, 1),
            promoter=Decimal("20"),
            institutional=Decimal("40"),
            public=Decimal("40"),
        )
        result = analyze_ownership([snap], "TEST", _AS_OF)
        signal_types = [s.signal_type for s in result.signals]
        assert "LOW_PROMOTER" in signal_types

    def test_high_pledge_signal(self):
        snap = _snap(
            date(2024, 1, 1),
            promoter=Decimal("60"),
            pledge=Decimal("60"),
        )
        result = analyze_ownership([snap], "TEST", _AS_OF)
        signal_types = [s.signal_type for s in result.signals]
        assert "HIGH_PLEDGE" in signal_types

    def test_moderate_pledge_signal(self):
        snap = _snap(
            date(2024, 1, 1),
            promoter=Decimal("60"),
            pledge=Decimal("30"),
        )
        result = analyze_ownership([snap], "TEST", _AS_OF)
        signal_types = [s.signal_type for s in result.signals]
        assert "MODERATE_PLEDGE" in signal_types

    def test_high_institutional_signal(self):
        snap = _snap(
            date(2024, 1, 1),
            promoter=Decimal("20"),
            institutional=Decimal("75"),
            public=Decimal("5"),
        )
        result = analyze_ownership([snap], "TEST", _AS_OF)
        signal_types = [s.signal_type for s in result.signals]
        assert "HIGH_INSTITUTIONAL" in signal_types

    def test_promoter_shift_signal(self):
        snaps = [
            _snap(date(2024, 1, 1), promoter=Decimal("40")),
            _snap(date(2024, 6, 1), promoter=Decimal("50")),
        ]
        result = analyze_ownership(snaps, "TEST", _AS_OF)
        signal_types = [s.signal_type for s in result.signals]
        assert "PROMOTER_SHIFT" in signal_types

    def test_no_signal_for_stable_data(self):
        snaps = [
            _snap(
                date(2024, 1, 1),
                promoter=Decimal("51"),
                institutional=Decimal("27"),
                public=Decimal("22"),
                pledge=Decimal("5"),
            ),
            _snap(
                date(2024, 6, 1),
                promoter=Decimal("51"),
                institutional=Decimal("27"),
                public=Decimal("22"),
                pledge=Decimal("5"),
            ),
        ]
        result = analyze_ownership(snaps, "TEST", _AS_OF)
        assert len(result.signals) == 0


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------


class TestCoverage:
    def test_coverage_count(self):
        snaps = [
            _snap(date(2024, 1, 1), promoter=Decimal("50")),
            _snap(date(2024, 6, 1), promoter=Decimal("50")),
        ]
        result = analyze_ownership(snaps, "TEST", _AS_OF)
        assert result.coverage["period_count"] == 2
        assert result.coverage["promoter_percentage"] == 2
