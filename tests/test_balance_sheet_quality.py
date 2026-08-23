"""Tests for balance-sheet quality analysis."""

from datetime import date
from decimal import Decimal

import pytest

from src.analysis.balance_sheet_quality import (
    BalanceSheetObservation,
    CashDebtChange,
    DebtGrowthComparison,
    EquityChange,
    LiquidityChange,
    WorkingCapitalChange,
    analyze_balance_sheet_quality,
    compare_debt_vs_revenue_growth,
    detect_sustained_negative_working_capital,
    track_cash_debt_ratio,
    track_equity_changes,
    track_liquidity,
    track_working_capital,
)
from src.data.company.financials import FinancialSnapshot


def _snap(
    period: str,
    revenue: str | None = None,
    total_debt: str | None = None,
    current_assets: str | None = None,
    current_liabilities: str | None = None,
    cash_and_equivalents: str | None = None,
    shareholders_equity: str | None = None,
    total_equity: str | None = None,
    symbol: str = "TEST",
) -> FinancialSnapshot:
    kwargs: dict = {"symbol": symbol, "period_end": date.fromisoformat(period)}
    for field_name, val in [
        ("revenue", revenue),
        ("total_debt", total_debt),
        ("current_assets", current_assets),
        ("current_liabilities", current_liabilities),
        ("cash_and_equivalents", cash_and_equivalents),
        ("shareholders_equity", shareholders_equity),
        ("total_equity", total_equity),
    ]:
        if val is not None:
            kwargs[field_name] = Decimal(val)
    return FinancialSnapshot(**kwargs)


# ---------------------------------------------------------------------------
# Debt vs revenue growth tests
# ---------------------------------------------------------------------------


class TestDebtVsRevenueGrowth:
    def test_detects_acceleration(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000", total_debt="500"),
            _snap("2022-03-31", revenue="1050", total_debt="700"),
        ]
        result = compare_debt_vs_revenue_growth(snapshots)
        assert len(result) == 1
        assert result[0].flagged is True
        assert Decimal(result[0].divergence_pp) > Decimal("20")

    def test_no_acceleration(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000", total_debt="500"),
            _snap("2022-03-31", revenue="1100", total_debt="520"),
        ]
        result = compare_debt_vs_revenue_growth(snapshots)
        assert len(result) == 1
        assert result[0].flagged is False

    def test_insufficient_data(self):
        result = compare_debt_vs_revenue_growth([])
        assert result == []


# ---------------------------------------------------------------------------
# Liquidity tests
# ---------------------------------------------------------------------------


class TestLiquidity:
    def test_detects_deterioration(self):
        snapshots = [
            _snap("2021-03-31", current_assets="600", current_liabilities="300"),
            _snap("2022-03-31", current_assets="400", current_liabilities="300"),
        ]
        result = track_liquidity(snapshots)
        assert len(result) == 1
        assert result[0].deteriorated is True
        assert Decimal(result[0].change) < Decimal("-0.5")

    def test_no_deterioration(self):
        snapshots = [
            _snap("2021-03-31", current_assets="600", current_liabilities="300"),
            _snap("2022-03-31", current_assets="650", current_liabilities="300"),
        ]
        result = track_liquidity(snapshots)
        assert len(result) == 1
        assert result[0].deteriorated is False

    def test_missing_data(self):
        snapshots = [
            _snap("2021-03-31", current_assets="600"),
            _snap("2022-03-31", current_assets="400"),
        ]
        result = track_liquidity(snapshots)
        assert result == []


# ---------------------------------------------------------------------------
# Working capital tests
# ---------------------------------------------------------------------------


class TestWorkingCapital:
    def test_basic_tracking(self):
        snapshots = [
            _snap("2021-03-31", current_assets="600", current_liabilities="300"),
            _snap("2022-03-31", current_assets="500", current_liabilities="300"),
        ]
        result = track_working_capital(snapshots)
        assert len(result) == 1
        assert Decimal(result[0].previous_value) == Decimal("300")
        assert Decimal(result[0].current_value) == Decimal("200")
        assert Decimal(result[0].change) == Decimal("-100")

    def test_sustained_negative(self):
        snapshots = [
            _snap("2021-03-31", current_assets="200", current_liabilities="300"),
            _snap("2022-03-31", current_assets="180", current_liabilities="300"),
            _snap("2023-03-31", current_assets="160", current_liabilities="300"),
        ]
        result = detect_sustained_negative_working_capital(snapshots)
        assert result is not None
        assert result.observation_type == "sustained_negative_working_capital"
        assert result.periods_covered == 3
        assert result.persistent is True

    def test_no_sustained_negative(self):
        snapshots = [
            _snap("2021-03-31", current_assets="600", current_liabilities="300"),
            _snap("2022-03-31", current_assets="500", current_liabilities="300"),
        ]
        result = detect_sustained_negative_working_capital(snapshots)
        assert result is None


# ---------------------------------------------------------------------------
# Cash/debt ratio tests
# ---------------------------------------------------------------------------


class TestCashDebtRatio:
    def test_weakening(self):
        snapshots = [
            _snap("2021-03-31", cash_and_equivalents="200", total_debt="500"),
            _snap("2022-03-31", cash_and_equivalents="100", total_debt="500"),
        ]
        result = track_cash_debt_ratio(snapshots)
        assert len(result) == 1
        assert result[0].weakened is True

    def test_stable(self):
        snapshots = [
            _snap("2021-03-31", cash_and_equivalents="200", total_debt="500"),
            _snap("2022-03-31", cash_and_equivalents="190", total_debt="500"),
        ]
        result = track_cash_debt_ratio(snapshots)
        assert len(result) == 1
        assert result[0].weakened is False


# ---------------------------------------------------------------------------
# Equity changes tests
# ---------------------------------------------------------------------------


class TestEquityChanges:
    def test_erosion(self):
        snapshots = [
            _snap("2021-03-31", shareholders_equity="1000"),
            _snap("2022-03-31", shareholders_equity="850"),
        ]
        result = track_equity_changes(snapshots)
        assert len(result) == 1
        assert result[0].eroded is True
        assert Decimal(result[0].change_pct) <= Decimal("-10")

    def test_no_erosion(self):
        snapshots = [
            _snap("2021-03-31", shareholders_equity="1000"),
            _snap("2022-03-31", shareholders_equity="1050"),
        ]
        result = track_equity_changes(snapshots)
        assert len(result) == 1
        assert result[0].eroded is False


# ---------------------------------------------------------------------------
# Full balance-sheet quality analysis
# ---------------------------------------------------------------------------


class TestFullAnalysis:
    def test_returns_observations(self):
        snapshots = [
            _snap(
                "2021-03-31",
                revenue="1000",
                total_debt="500",
                current_assets="600",
                current_liabilities="300",
                shareholders_equity="1000",
            ),
            _snap(
                "2022-03-31",
                revenue="1050",
                total_debt="700",
                current_assets="400",
                current_liabilities="300",
                shareholders_equity="850",
            ),
        ]
        result = analyze_balance_sheet_quality(snapshots)
        assert len(result) >= 1
        types = {o.observation_type for o in result}
        assert "accelerating_debt" in types
        assert "liquidity_deterioration" in types
        assert "equity_erosion" in types

    def test_empty_with_clean_data(self):
        snapshots = [
            _snap(
                "2021-03-31",
                revenue="1000",
                total_debt="500",
                current_assets="600",
                current_liabilities="300",
                shareholders_equity="1000",
            ),
            _snap(
                "2022-03-31",
                revenue="1100",
                total_debt="450",
                current_assets="650",
                current_liabilities="300",
                shareholders_equity="1050",
            ),
        ]
        result = analyze_balance_sheet_quality(snapshots)
        assert result == []

    def test_insufficient_data(self):
        result = analyze_balance_sheet_quality([])
        assert result == []

    def test_single_period(self):
        snapshots = [_snap("2021-03-31", revenue="1000")]
        result = analyze_balance_sheet_quality(snapshots)
        assert result == []
