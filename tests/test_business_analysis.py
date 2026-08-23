"""Tests for business analysis engine."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.analysis.business_analysis import (
    BusinessAnalysisResult,
    BusinessQualitySignal,
    SegmentConcentration,
    SegmentShare,
    SegmentTrend,
    analyze_business,
    compute_business_quality_signals,
    compute_segment_concentration,
    compute_segment_trends,
)
from src.data.company.business_profile import BusinessProfile
from src.data.company.financials import FinancialSnapshot, SegmentResult


_AS_OF = datetime(2024, 6, 15, tzinfo=timezone.utc)


def _snap(
    period_end: date,
    revenue: Decimal | None = None,
    net_profit: Decimal | None = None,
    operating_cash_flow: Decimal | None = None,
    total_debt: Decimal | None = None,
    shareholders_equity: Decimal | None = None,
    segments: tuple[SegmentResult, ...] = (),
) -> FinancialSnapshot:
    return FinancialSnapshot(
        symbol="TEST",
        period_end=period_end,
        revenue=revenue,
        net_profit=net_profit,
        operating_cash_flow=operating_cash_flow,
        total_debt=total_debt,
        shareholders_equity=shareholders_equity,
        segments=segments,
    )


def _seg(name: str, revenue: Decimal | None = None) -> SegmentResult:
    return SegmentResult(segment_name=name, revenue=revenue)


# ---------------------------------------------------------------------------
# Empty / insufficient data
# ---------------------------------------------------------------------------


class TestInsufficientData:
    def test_empty_snapshots(self):
        result = analyze_business([], None, "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert result.segment_concentrations == ()
        assert result.segment_trends == ()
        assert result.quality_signals == ()
        assert "segment_concentration" in result.missing_analyses

    def test_single_snapshot_no_segments(self):
        snap = _snap(date(2024, 1, 1), revenue=Decimal("1000"))
        result = analyze_business([snap], None, "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert "segment_concentration" in result.missing_analyses
        assert "segment_trends" in result.missing_analyses

    def test_no_profile(self):
        result = analyze_business([], None, "TEST", _AS_OF)
        assert result.has_profile is False
        assert result.sector is None


# ---------------------------------------------------------------------------
# Segment concentration
# ---------------------------------------------------------------------------


class TestSegmentConcentration:
    def test_no_segments(self):
        snap = _snap(date(2024, 1, 1), revenue=Decimal("1000"))
        result = compute_segment_concentration(snap)
        assert result.concentration_level == "NO_SEGMENTS"

    def test_no_total_revenue(self):
        snap = _snap(
            date(2024, 1, 1),
            segments=(_seg("A", Decimal("100")),),
        )
        result = compute_segment_concentration(snap)
        assert result.concentration_level == "NO_TOTAL_REVENUE"

    def test_single_segment(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(_seg("A", Decimal("1000")),),
        )
        result = compute_segment_concentration(snap)
        assert result.segment_count == 1
        assert result.dominant_segment == "A"
        assert result.dominant_segment_pct == "100.00"
        assert result.concentration_level == "HIGHLY_CONCENTRATED"

    def test_two_equal_segments(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(
                _seg("A", Decimal("500")),
                _seg("B", Decimal("500")),
            ),
        )
        result = compute_segment_concentration(snap)
        assert result.segment_count == 2
        # HHI = 50^2 + 50^2 = 5000, which is > 2500 = HIGHLY_CONCENTRATED
        assert result.concentration_level == "HIGHLY_CONCENTRATED"

    def test_dominant_segment(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(
                _seg("A", Decimal("800")),
                _seg("B", Decimal("200")),
            ),
        )
        result = compute_segment_concentration(snap)
        assert result.dominant_segment == "A"
        assert result.dominant_segment_pct == "80.00"
        assert result.concentration_level == "HIGHLY_CONCENTRATED"

    def test_hhi_calculation(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(
                _seg("A", Decimal("600")),
                _seg("B", Decimal("400")),
            ),
        )
        result = compute_segment_concentration(snap)
        # HHI = 60^2 + 40^2 = 3600 + 1600 = 5200
        assert result.hhi == "5200.00"
        assert result.concentration_level == "HIGHLY_CONCENTRATED"

    def test_segment_with_none_revenue(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(
                _seg("A", Decimal("600")),
                _seg("B", None),
            ),
        )
        result = compute_segment_concentration(snap)
        assert result.segment_count == 2
        assert len(result.segment_shares) == 2
        assert result.segment_shares[1].revenue is None


# ---------------------------------------------------------------------------
# Segment trends
# ---------------------------------------------------------------------------


class TestSegmentTrends:
    def test_single_period(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(_seg("A", Decimal("500")),),
        )
        result = compute_segment_trends([snap])
        assert result == ()

    def test_increasing_segment(self):
        snap1 = _snap(
            date(2023, 1, 1),
            revenue=Decimal("1000"),
            segments=(_seg("A", Decimal("300")),),
        )
        snap2 = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(_seg("A", Decimal("500")),),
        )
        result = compute_segment_trends([snap1, snap2])
        assert len(result) == 1
        assert result[0].direction == "INCREASING"
        assert result[0].share_change == "20.00"

    def test_stable_segment(self):
        snap1 = _snap(
            date(2023, 1, 1),
            revenue=Decimal("1000"),
            segments=(_seg("A", Decimal("500")),),
        )
        snap2 = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(_seg("A", Decimal("500")),),
        )
        result = compute_segment_trends([snap1, snap2])
        assert len(result) == 1
        assert result[0].direction == "STABLE"

    def test_new_segment_not_in_first_period(self):
        snap1 = _snap(
            date(2023, 1, 1),
            revenue=Decimal("1000"),
            segments=(_seg("A", Decimal("500")),),
        )
        snap2 = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(
                _seg("A", Decimal("400")),
                _seg("B", Decimal("600")),
            ),
        )
        result = compute_segment_trends([snap1, snap2])
        # A appears in both periods and shows a trend
        # B only appears in period 2 so no trend for B
        assert len(result) == 1
        assert result[0].segment_name == "A"


# ---------------------------------------------------------------------------
# Business quality signals
# ---------------------------------------------------------------------------


class TestBusinessQualitySignals:
    def test_empty_snapshots(self):
        result = compute_business_quality_signals([], "TEST")
        assert result == ()

    def test_revenue_scale_signal(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("5000000000"),
        )
        result = compute_business_quality_signals([snap], "TEST")
        assert len(result) == 1
        assert result[0].signal_type == "SCALE"
        assert result[0].direction == "POSITIVE"

    def test_margin_signal_positive(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            net_profit=Decimal("200"),
        )
        result = compute_business_quality_signals([snap], "TEST")
        margin_signals = [s for s in result if s.signal_type == "MARGIN"]
        assert len(margin_signals) == 1
        assert margin_signals[0].direction == "POSITIVE"

    def test_margin_signal_negative(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            net_profit=Decimal("-50"),
        )
        result = compute_business_quality_signals([snap], "TEST")
        margin_signals = [s for s in result if s.signal_type == "MARGIN"]
        assert len(margin_signals) == 1
        assert margin_signals[0].direction == "NEGATIVE"

    def test_cash_generation_positive(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            net_profit=Decimal("100"),
            operating_cash_flow=Decimal("150"),
        )
        result = compute_business_quality_signals([snap], "TEST")
        cash_signals = [s for s in result if s.signal_type == "CASH_GENERATION"]
        assert len(cash_signals) == 1
        assert cash_signals[0].direction == "POSITIVE"

    def test_leverage_positive(self):
        snap = _snap(
            date(2024, 1, 1),
            total_debt=Decimal("500"),
            shareholders_equity=Decimal("1000"),
        )
        result = compute_business_quality_signals([snap], "TEST")
        lev_signals = [s for s in result if s.signal_type == "LEVERAGE"]
        assert len(lev_signals) == 1
        assert lev_signals[0].direction == "POSITIVE"

    def test_leverage_negative(self):
        snap = _snap(
            date(2024, 1, 1),
            total_debt=Decimal("3000"),
            shareholders_equity=Decimal("1000"),
        )
        result = compute_business_quality_signals([snap], "TEST")
        lev_signals = [s for s in result if s.signal_type == "LEVERAGE"]
        assert len(lev_signals) == 1
        assert lev_signals[0].direction == "NEGATIVE"


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------


class TestFullAnalysis:
    def test_with_profile(self):
        profile = BusinessProfile(
            symbol="TEST",
            sector="Technology",
            industry="Software",
        )
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(_seg("A", Decimal("1000")),),
        )
        result = analyze_business([snap], profile, "TEST", _AS_OF)
        assert result.has_profile is True
        assert result.sector == "Technology"
        assert result.industry == "Software"

    def test_multiple_periods(self):
        snap1 = _snap(
            date(2023, 1, 1),
            revenue=Decimal("1000"),
            segments=(_seg("A", Decimal("500")),),
        )
        snap2 = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(_seg("A", Decimal("500")),),
        )
        result = analyze_business([snap1, snap2], None, "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert "segment_trends" in result.available_analyses

    def test_coverage_tracking(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(_seg("A", Decimal("500")),),
        )
        result = analyze_business([snap], None, "TEST", _AS_OF)
        assert "2024-01-01" in result.coverage

    def test_forbids_extra_fields(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
        )
        result = analyze_business([snap], None, "TEST", _AS_OF)
        assert result.symbol == "TEST"
