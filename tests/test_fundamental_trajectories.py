"""Tests for fundamental trajectory analysis."""

from datetime import date
from decimal import Decimal

import pytest

from src.analysis.fundamental_trajectories import (
    TrajectoryAnalysis,
    _cagr,
    _pct_change,
    compute_all_leverage_trajectories,
    compute_all_margin_trajectories,
    compute_trajectory,
    analyze_trajectories,
    analyze_all_trajectories,
)
from src.data.company.financials import FinancialSnapshot


def _snap(
    period: str,
    revenue: str | None = None,
    net_profit: str | None = None,
    operating_profit: str | None = None,
    operating_cash_flow: str | None = None,
    free_cash_flow: str | None = None,
    total_debt: str | None = None,
    cash_and_equivalents: str | None = None,
    receivables: str | None = None,
    inventory: str | None = None,
    current_assets: str | None = None,
    current_liabilities: str | None = None,
    total_equity: str | None = None,
    shareholders_equity: str | None = None,
    symbol: str = "TEST",
) -> FinancialSnapshot:
    kwargs: dict = {"symbol": symbol, "period_end": date.fromisoformat(period)}
    for field_name, val in [
        ("revenue", revenue),
        ("net_profit", net_profit),
        ("operating_profit", operating_profit),
        ("operating_cash_flow", operating_cash_flow),
        ("free_cash_flow", free_cash_flow),
        ("total_debt", total_debt),
        ("cash_and_equivalents", cash_and_equivalents),
        ("receivables", receivables),
        ("inventory", inventory),
        ("current_assets", current_assets),
        ("current_liabilities", current_liabilities),
        ("total_equity", total_equity),
        ("shareholders_equity", shareholders_equity),
    ]:
        if val is not None:
            kwargs[field_name] = Decimal(val)
    return FinancialSnapshot(**kwargs)


# ---------------------------------------------------------------------------
# _pct_change tests
# ---------------------------------------------------------------------------


class TestPctChange:
    def test_basic(self):
        result = _pct_change(Decimal("100"), Decimal("120"))
        assert result == Decimal("20")

    def test_decrease(self):
        result = _pct_change(Decimal("100"), Decimal("80"))
        assert result == Decimal("-20")

    def test_zero_previous(self):
        assert _pct_change(Decimal("0"), Decimal("100")) is None

    def test_none_previous(self):
        assert _pct_change(None, Decimal("100")) is None

    def test_none_current(self):
        assert _pct_change(Decimal("100"), None) is None


# ---------------------------------------------------------------------------
# _cagr tests
# ---------------------------------------------------------------------------


class TestCAGR:
    def test_basic(self):
        # (120/100)^(1/2) - 1 = 9.54%
        result = _cagr(Decimal("100"), Decimal("120"), 2)
        assert result is not None
        assert abs(result - Decimal("9.54")) < Decimal("0.1")

    def test_single_period(self):
        result = _cagr(Decimal("100"), Decimal("120"), 1)
        assert result is not None
        assert result == Decimal("20")

    def test_zero_first(self):
        assert _cagr(Decimal("0"), Decimal("120"), 2) is None

    def test_negative_first(self):
        assert _cagr(Decimal("-100"), Decimal("120"), 2) is None

    def test_zero_periods(self):
        assert _cagr(Decimal("100"), Decimal("120"), 0) is None


# ---------------------------------------------------------------------------
# compute_trajectory tests
# ---------------------------------------------------------------------------


class TestComputeTrajectory:
    def test_basic_trajectory(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000"),
            _snap("2022-03-31", revenue="1100"),
            _snap("2023-03-31", revenue="1210"),
        ]
        result = compute_trajectory(snapshots, "revenue", "TEST")
        assert result is not None
        assert result.metric == "revenue"
        assert result.symbol == "TEST"
        assert result.period_count == 3
        assert result.first_value == "1000"
        assert result.last_value == "1210"
        assert result.direction == "INCREASING"
        assert result.cagr is not None
        assert len(result.growth_rates) == 2

    def test_insufficient_data(self):
        snapshots = [_snap("2021-03-31", revenue="1000")]
        result = compute_trajectory(snapshots, "revenue", "TEST")
        assert result is None

    def test_missing_metric(self):
        snapshots = [
            _snap("2021-03-31"),
            _snap("2022-03-31"),
        ]
        result = compute_trajectory(snapshots, "revenue", "TEST")
        assert result is None

    def test_decreasing_trajectory(self):
        snapshots = [
            _snap("2021-03-31", revenue="1200"),
            _snap("2022-03-31", revenue="1100"),
            _snap("2023-03-31", revenue="1000"),
        ]
        result = compute_trajectory(snapshots, "revenue", "TEST")
        assert result is not None
        assert result.direction == "DECREASING"

    def test_mixed_trajectory(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000"),
            _snap("2022-03-31", revenue="1200"),
            _snap("2023-03-31", revenue="1100"),
        ]
        result = compute_trajectory(snapshots, "revenue", "TEST")
        assert result is not None
        assert result.direction == "MIXED"


# ---------------------------------------------------------------------------
# Margin trajectory tests
# ---------------------------------------------------------------------------


class TestMarginTrajectory:
    def test_expanding_margin(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000", net_profit="100"),
            _snap("2022-03-31", revenue="1100", net_profit="132"),
        ]
        result = compute_all_margin_trajectories(snapshots, "TEST")
        assert len(result) >= 1
        net_margin = [m for m in result if m.margin_name == "net_margin"]
        assert len(net_margin) == 1
        assert net_margin[0].direction == "EXPANDING"

    def test_contracting_margin(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000", net_profit="100"),
            _snap("2022-03-31", revenue="1100", net_profit="99"),
        ]
        result = compute_all_margin_trajectories(snapshots, "TEST")
        net_margin = [m for m in result if m.margin_name == "net_margin"]
        assert len(net_margin) == 1
        assert net_margin[0].direction == "CONTRACTING"

    def test_insufficient_data(self):
        snapshots = [_snap("2021-03-31", revenue="1000")]
        result = compute_all_margin_trajectories(snapshots, "TEST")
        assert result == []


# ---------------------------------------------------------------------------
# Leverage trajectory tests
# ---------------------------------------------------------------------------


class TestLeverageTrajectory:
    def test_increasing_leverage(self):
        snapshots = [
            _snap("2021-03-31", total_debt="500", revenue="1000"),
            _snap("2022-03-31", total_debt="700", revenue="1050"),
        ]
        result = compute_all_leverage_trajectories(snapshots, "TEST")
        assert len(result) >= 1
        debt_rev = [l for l in result if l.metric == "debt_to_revenue"]
        assert len(debt_rev) == 1
        assert debt_rev[0].direction == "INCREASING"

    def test_elevated_leverage(self):
        snapshots = [
            _snap("2021-03-31", total_debt="500", revenue="400"),
            _snap("2022-03-31", total_debt="700", revenue="400"),
        ]
        result = compute_all_leverage_trajectories(snapshots, "TEST")
        debt_rev = [l for l in result if l.metric == "debt_to_revenue"]
        assert len(debt_rev) == 1
        assert debt_rev[0].elevated is True


# ---------------------------------------------------------------------------
# analyze_trajectories tests
# ---------------------------------------------------------------------------


class TestAnalyzeTrajectories:
    def test_returns_multiple_trajectories(self):
        snapshots = [
            _snap(
                "2021-03-31",
                revenue="1000",
                net_profit="100",
                total_debt="500",
            ),
            _snap(
                "2022-03-31",
                revenue="1100",
                net_profit="120",
                total_debt="450",
            ),
            _snap(
                "2023-03-31",
                revenue="1210",
                net_profit="144",
                total_debt="400",
            ),
        ]
        result = analyze_trajectories(snapshots, "TEST")
        assert len(result) >= 2
        metrics = {t.metric for t in result}
        assert "revenue" in metrics
        assert "net_profit" in metrics

    def test_analyze_all_includes_margins_and_leverage(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000", net_profit="100", total_debt="500"),
            _snap("2022-03-31", revenue="1100", net_profit="120", total_debt="450"),
        ]
        result = analyze_all_trajectories(snapshots, "TEST")
        assert "trajectories" in result
        assert "margin_trajectories" in result
        assert "leverage_trajectories" in result


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_snapshots(self):
        result = analyze_trajectories([], "TEST")
        assert result == []

    def test_single_snapshot(self):
        result = analyze_trajectories(
            [_snap("2021-03-31", revenue="1000")], "TEST"
        )
        assert result == []

    def test_all_none_values(self):
        snapshots = [
            _snap("2021-03-31"),
            _snap("2022-03-31"),
        ]
        result = analyze_trajectories(snapshots, "TEST")
        assert result == []

    def test_symbol_preserved(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000", symbol="RELIANCE"),
            _snap("2022-03-31", revenue="1100", symbol="RELIANCE"),
        ]
        result = compute_trajectory(snapshots, "revenue", "RELIANCE")
        assert result is not None
        assert result.symbol == "RELIANCE"
