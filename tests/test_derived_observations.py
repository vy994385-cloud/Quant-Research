"""Tests for derived observations engine."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.analysis.derived_observations import (
    DerivedObservation,
    DerivedObservationsResult,
    EvidenceClassification,
    analyze_derived_observations,
    derive_revenue_cash_divergence,
    derive_segment_vs_overall_divergence,
    derive_management_financial_deterioration,
    derive_leverage_trajectory_signal,
    derive_working_capital_strain,
)
from src.data.company.financials import FinancialSnapshot, SegmentResult
from src.data.company.management import ManagementChange


_AS_OF = datetime(2024, 6, 15, tzinfo=timezone.utc)


def _snap(
    period_end: date,
    revenue: Decimal | None = None,
    net_profit: Decimal | None = None,
    operating_cash_flow: Decimal | None = None,
    total_debt: Decimal | None = None,
    shareholders_equity: Decimal | None = None,
    receivables: Decimal | None = None,
    inventory: Decimal | None = None,
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
        receivables=receivables,
        inventory=inventory,
        segments=segments,
    )


def _change(
    effective_date: date,
    change_type: str = "Resignation",
) -> ManagementChange:
    return ManagementChange(
        symbol="TEST",
        person_name="John Doe",
        role="CEO",
        change_type=change_type,
        effective_date=effective_date,
    )


# ---------------------------------------------------------------------------
# Revenue-cash divergence
# ---------------------------------------------------------------------------


class TestRevenueCashDivergence:
    def test_divergence_detected(self):
        snap1 = _snap(
            date(2023, 1, 1),
            revenue=Decimal("1000"),
            operating_cash_flow=Decimal("200"),
        )
        snap2 = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1200"),
            operating_cash_flow=Decimal("100"),
        )
        result = derive_revenue_cash_divergence([snap1, snap2], "TEST")
        assert result is not None
        assert result.evidence_classification == EvidenceClassification.OBSERVATION
        assert "revenue-cash flow divergence" in result.title.lower()

    def test_no_divergence(self):
        snap1 = _snap(
            date(2023, 1, 1),
            revenue=Decimal("1000"),
            operating_cash_flow=Decimal("200"),
        )
        snap2 = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1200"),
            operating_cash_flow=Decimal("300"),
        )
        result = derive_revenue_cash_divergence([snap1, snap2], "TEST")
        assert result is None

    def test_insufficient_data(self):
        snap = _snap(date(2024, 1, 1), revenue=Decimal("1000"))
        result = derive_revenue_cash_divergence([snap], "TEST")
        assert result is None


# ---------------------------------------------------------------------------
# Segment vs overall divergence
# ---------------------------------------------------------------------------


class TestSegmentDivergence:
    def test_divergence_detected(self):
        snap1 = _snap(
            date(2023, 1, 1),
            revenue=Decimal("1000"),
            segments=(
                SegmentResult(segment_name="A", revenue=Decimal("600")),
                SegmentResult(segment_name="B", revenue=Decimal("400")),
            ),
        )
        snap2 = _snap(
            date(2024, 1, 1),
            revenue=Decimal("900"),
            segments=(
                SegmentResult(segment_name="A", revenue=Decimal("700")),
                SegmentResult(segment_name="B", revenue=Decimal("200")),
            ),
        )
        result = derive_segment_vs_overall_divergence([snap1, snap2], "TEST")
        assert result is not None
        assert result.evidence_classification == EvidenceClassification.OBSERVATION
        assert "A" in result.description

    def test_no_divergence(self):
        snap1 = _snap(
            date(2023, 1, 1),
            revenue=Decimal("1000"),
            segments=(
                SegmentResult(segment_name="A", revenue=Decimal("500")),
            ),
        )
        snap2 = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1200"),
            segments=(
                SegmentResult(segment_name="A", revenue=Decimal("600")),
            ),
        )
        result = derive_segment_vs_overall_divergence([snap1, snap2], "TEST")
        assert result is None


# ---------------------------------------------------------------------------
# Management-financial deterioration
# ---------------------------------------------------------------------------


class TestManagementFinancialDeterioration:
    def test_deterioration_detected(self):
        changes = [
            _change(date(2024, 1, 1), change_type="Resignation"),
            _change(date(2024, 2, 1), change_type="Resignation"),
        ]
        snap1 = _snap(
            date(2023, 1, 1),
            revenue=Decimal("1000"),
            net_profit=Decimal("100"),
            operating_cash_flow=Decimal("200"),
        )
        snap2 = _snap(
            date(2024, 1, 1),
            revenue=Decimal("800"),
            net_profit=Decimal("50"),
            operating_cash_flow=Decimal("100"),
        )
        result = derive_management_financial_deterioration(
            changes, [snap1, snap2], "TEST"
        )
        assert result is not None
        assert result.evidence_classification == EvidenceClassification.INTERPRETATION

    def test_no_deterioration(self):
        changes = [_change(date(2024, 1, 1), change_type="Resignation")]
        snap1 = _snap(date(2023, 1, 1), revenue=Decimal("1000"))
        snap2 = _snap(date(2024, 1, 1), revenue=Decimal("1200"))
        result = derive_management_financial_deterioration(
            changes, [snap1, snap2], "TEST"
        )
        assert result is None


# ---------------------------------------------------------------------------
# Leverage trajectory
# ---------------------------------------------------------------------------


class TestLeverageTrajectory:
    def test_increasing_leverage(self):
        snap1 = _snap(
            date(2022, 1, 1),
            total_debt=Decimal("1000"),
            shareholders_equity=Decimal("1000"),
        )
        snap2 = _snap(
            date(2023, 1, 1),
            total_debt=Decimal("2000"),
            shareholders_equity=Decimal("1000"),
        )
        snap3 = _snap(
            date(2024, 1, 1),
            total_debt=Decimal("3000"),
            shareholders_equity=Decimal("1000"),
        )
        result = derive_leverage_trajectory_signal(
            [snap1, snap2, snap3], "TEST"
        )
        assert result is not None
        assert result.evidence_classification == EvidenceClassification.FACT
        assert "increasing leverage" in result.title.lower()

    def test_decreasing_leverage(self):
        snap1 = _snap(
            date(2022, 1, 1),
            total_debt=Decimal("300"),
            shareholders_equity=Decimal("1000"),
        )
        snap2 = _snap(
            date(2023, 1, 1),
            total_debt=Decimal("200"),
            shareholders_equity=Decimal("1000"),
        )
        snap3 = _snap(
            date(2024, 1, 1),
            total_debt=Decimal("100"),
            shareholders_equity=Decimal("1000"),
        )
        result = derive_leverage_trajectory_signal(
            [snap1, snap2, snap3], "TEST"
        )
        assert result is None


# ---------------------------------------------------------------------------
# Working capital strain
# ---------------------------------------------------------------------------


class TestWorkingCapitalStrain:
    def test_strain_detected(self):
        snap1 = _snap(
            date(2023, 1, 1),
            receivables=Decimal("100"),
            inventory=Decimal("100"),
        )
        snap2 = _snap(
            date(2024, 1, 1),
            receivables=Decimal("150"),
            inventory=Decimal("150"),
        )
        result = derive_working_capital_strain([snap1, snap2], "TEST")
        assert result is not None
        assert result.evidence_classification == EvidenceClassification.OBSERVATION

    def test_no_strain(self):
        snap1 = _snap(
            date(2023, 1, 1),
            receivables=Decimal("100"),
            inventory=Decimal("100"),
        )
        snap2 = _snap(
            date(2024, 1, 1),
            receivables=Decimal("110"),
            inventory=Decimal("110"),
        )
        result = derive_working_capital_strain([snap1, snap2], "TEST")
        assert result is None


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------


class TestFullAnalysis:
    def test_empty(self):
        result = analyze_derived_observations([], [], "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert result.observations == ()
        assert result.fact_count == 0
        assert result.observation_count == 0
        assert result.interpretation_count == 0

    def test_multiple_observations(self):
        snap1 = _snap(
            date(2022, 1, 1),
            revenue=Decimal("1000"),
            net_profit=Decimal("100"),
            operating_cash_flow=Decimal("200"),
            total_debt=Decimal("100"),
            shareholders_equity=Decimal("1000"),
            receivables=Decimal("50"),
            inventory=Decimal("50"),
        )
        snap2 = _snap(
            date(2023, 1, 1),
            revenue=Decimal("1100"),
            net_profit=Decimal("80"),
            operating_cash_flow=Decimal("150"),
            total_debt=Decimal("200"),
            shareholders_equity=Decimal("1000"),
            receivables=Decimal("60"),
            inventory=Decimal("60"),
        )
        snap3 = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1200"),
            net_profit=Decimal("60"),
            operating_cash_flow=Decimal("100"),
            total_debt=Decimal("300"),
            shareholders_equity=Decimal("1000"),
            receivables=Decimal("80"),
            inventory=Decimal("80"),
        )
        changes = [
            _change(date(2024, 1, 1), change_type="Resignation"),
            _change(date(2024, 2, 1), change_type="Resignation"),
        ]
        result = analyze_derived_observations(
            [snap1, snap2, snap3], changes, "TEST", _AS_OF
        )
        assert len(result.observations) >= 2
        assert result.fact_count + result.observation_count + result.interpretation_count == len(result.observations)

    def test_forbids_extra_fields(self):
        result = analyze_derived_observations([], [], "TEST", _AS_OF)
        assert result.symbol == "TEST"
