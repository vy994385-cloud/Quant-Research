"""Tests for risk analysis engine."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.analysis.risk_analysis import (
    RiskAnalysisResult,
    RiskObservation,
    analyze_risks,
    _detect_financial_risks,
    _detect_sector_risks,
    _detect_concentration_risks,
    _detect_execution_risks,
)
from src.data.company.business_profile import BusinessProfile
from src.data.company.financials import FinancialSnapshot, SegmentResult
from src.data.company.management import ManagementChange


_AS_OF = datetime(2024, 6, 15, tzinfo=timezone.utc)


def _snap(
    period_end: date,
    total_debt: Decimal | None = None,
    shareholders_equity: Decimal | None = None,
    current_assets: Decimal | None = None,
    current_liabilities: Decimal | None = None,
    revenue: Decimal | None = None,
    net_profit: Decimal | None = None,
    operating_cash_flow: Decimal | None = None,
    segments: tuple[SegmentResult, ...] = (),
) -> FinancialSnapshot:
    return FinancialSnapshot(
        symbol="TEST",
        period_end=period_end,
        total_debt=total_debt,
        shareholders_equity=shareholders_equity,
        current_assets=current_assets,
        current_liabilities=current_liabilities,
        revenue=revenue,
        net_profit=net_profit,
        operating_cash_flow=operating_cash_flow,
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
# Sector risks
# ---------------------------------------------------------------------------


class TestSectorRisks:
    def test_no_profile(self):
        result = _detect_sector_risks(None, "TEST")
        assert result == ()

    def test_technology_sector(self):
        profile = BusinessProfile(symbol="TEST", sector="Technology")
        result = _detect_sector_risks(profile, "TEST")
        assert len(result) == 1
        assert result[0].risk_dimension == "TECHNOLOGY"

    def test_financial_sector(self):
        profile = BusinessProfile(symbol="TEST", sector="Financial Services")
        result = _detect_sector_risks(profile, "TEST")
        assert len(result) == 1
        assert result[0].risk_dimension == "REGULATORY"

    def test_energy_sector(self):
        profile = BusinessProfile(symbol="TEST", sector="Energy")
        result = _detect_sector_risks(profile, "TEST")
        assert len(result) == 1
        assert result[0].risk_dimension == "COMMODITY"

    def test_healthcare_sector(self):
        profile = BusinessProfile(symbol="TEST", sector="Healthcare")
        result = _detect_sector_risks(profile, "TEST")
        assert len(result) == 1
        assert result[0].risk_dimension == "REGULATORY"

    def test_other_sector(self):
        profile = BusinessProfile(symbol="TEST", sector="Consumer Goods")
        result = _detect_sector_risks(profile, "TEST")
        assert result == ()


# ---------------------------------------------------------------------------
# Financial risks
# ---------------------------------------------------------------------------


class TestFinancialRisks:
    def test_empty_snapshots(self):
        result = _detect_financial_risks([], "TEST")
        assert result == ()

    def test_high_leverage(self):
        snap = _snap(
            date(2024, 1, 1),
            total_debt=Decimal("3000"),
            shareholders_equity=Decimal("1000"),
        )
        result = _detect_financial_risks([snap], "TEST")
        assert len(result) == 1
        assert result[0].severity == "HIGH"
        assert result[0].risk_dimension == "FINANCIAL"

    def test_liquidity_risk(self):
        snap = _snap(
            date(2024, 1, 1),
            current_assets=Decimal("500"),
            current_liabilities=Decimal("1000"),
        )
        result = _detect_financial_risks([snap], "TEST")
        assert len(result) == 1
        assert result[0].severity == "HIGH"
        assert result[0].risk_id == "TEST_LIQUIDITY_RISK"

    def test_cash_divergence(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            net_profit=Decimal("100"),
            operating_cash_flow=Decimal("-50"),
        )
        result = _detect_financial_risks([snap], "TEST")
        assert len(result) == 1
        assert result[0].risk_id == "TEST_CASH_DIVERGENCE"


# ---------------------------------------------------------------------------
# Concentration risks
# ---------------------------------------------------------------------------


class TestConcentrationRisks:
    def test_empty_snapshots(self):
        result = _detect_concentration_risks([], "TEST")
        assert result == ()

    def test_no_segments(self):
        snap = _snap(date(2024, 1, 1), revenue=Decimal("1000"))
        result = _detect_concentration_risks([snap], "TEST")
        assert result == ()

    def test_high_concentration(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(
                SegmentResult(segment_name="Core", revenue=Decimal("900")),
                SegmentResult(segment_name="Other", revenue=Decimal("100")),
            ),
        )
        result = _detect_concentration_risks([snap], "TEST")
        assert len(result) == 1
        assert "Core" in result[0].title
        assert result[0].risk_dimension == "CONCENTRATION"

    def test_no_high_concentration(self):
        snap = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            segments=(
                SegmentResult(segment_name="A", revenue=Decimal("500")),
                SegmentResult(segment_name="B", revenue=Decimal("500")),
            ),
        )
        result = _detect_concentration_risks([snap], "TEST")
        assert result == ()


# ---------------------------------------------------------------------------
# Execution risks
# ---------------------------------------------------------------------------


class TestExecutionRisks:
    def test_few_changes(self):
        changes = [_change(date(2024, 1, 1))]
        result = _detect_execution_risks(changes, "TEST")
        assert result == ()

    def test_elevated_turnover(self):
        changes = [
            _change(date(2024, 1, 1), change_type="Resignation"),
            _change(date(2024, 2, 1), change_type="Resignation"),
            _change(date(2024, 3, 1), change_type="Resignation"),
        ]
        result = _detect_execution_risks(changes, "TEST")
        assert len(result) == 1
        assert result[0].risk_dimension == "EXECUTION"
        assert result[0].severity == "MEDIUM"


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------


class TestFullAnalysis:
    def test_empty(self):
        result = analyze_risks([], None, [], "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert result.observations == ()
        assert "sector_risks" in result.missing_analyses
        assert "financial_risks" in result.missing_analyses

    def test_with_profile_and_data(self):
        profile = BusinessProfile(symbol="TEST", sector="Technology")
        snap = _snap(
            date(2024, 1, 1),
            total_debt=Decimal("3000"),
            shareholders_equity=Decimal("1000"),
        )
        result = analyze_risks([snap], profile, [], "TEST", _AS_OF)
        assert len(result.observations) > 0
        assert "TECHNOLOGY" in result.dimension_counts
        assert "FINANCIAL" in result.dimension_counts
        assert result.severity_counts.get("HIGH", 0) >= 1

    def test_forbids_extra_fields(self):
        result = analyze_risks([], None, [], "TEST", _AS_OF)
        assert result.symbol == "TEST"
