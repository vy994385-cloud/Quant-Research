"""Tests for earnings quality analysis."""

from datetime import date
from decimal import Decimal

import pytest

from src.analysis.earnings_quality import (
    CashProfitComparison,
    EarningsQualityObservation,
    GrowthDivergence,
    analyze_cash_profit_series,
    analyze_earnings_quality,
    compare_cash_profit,
    compare_growth_rates,
    detect_inventory_divergence,
    detect_persistent_cash_profit_divergence,
    detect_receivables_divergence,
)
from src.data.company.financials import FinancialSnapshot


def _snap(
    period: str,
    revenue: str | None = None,
    net_profit: str | None = None,
    operating_cash_flow: str | None = None,
    free_cash_flow: str | None = None,
    receivables: str | None = None,
    inventory: str | None = None,
    symbol: str = "TEST",
) -> FinancialSnapshot:
    kwargs: dict = {"symbol": symbol, "period_end": date.fromisoformat(period)}
    for field_name, val in [
        ("revenue", revenue),
        ("net_profit", net_profit),
        ("operating_cash_flow", operating_cash_flow),
        ("free_cash_flow", free_cash_flow),
        ("receivables", receivables),
        ("inventory", inventory),
    ]:
        if val is not None:
            kwargs[field_name] = Decimal(val)
    return FinancialSnapshot(**kwargs)


# ---------------------------------------------------------------------------
# Cash/profit comparison tests
# ---------------------------------------------------------------------------


class TestCashProfitComparison:
    def test_basic_comparison(self):
        snapshot = _snap(
            "2022-03-31",
            net_profit="100",
            operating_cash_flow="120",
            free_cash_flow="80",
        )
        result = compare_cash_profit(snapshot)
        assert result.period == "2022-03-31"
        assert result.ocf_to_profit_ratio is not None
        assert Decimal(result.ocf_to_profit_ratio) == Decimal("1.2")
        assert result.ocf_exceeds_profit is True
        assert result.fcf_exceeds_profit is False

    def test_missing_data(self):
        snapshot = _snap("2022-03-31")
        result = compare_cash_profit(snapshot)
        assert result.ocf_to_profit_ratio is None
        assert result.ocf_exceeds_profit is None

    def test_zero_profit(self):
        snapshot = _snap(
            "2022-03-31",
            net_profit="0",
            operating_cash_flow="100",
        )
        result = compare_cash_profit(snapshot)
        assert result.ocf_to_profit_ratio is None


# ---------------------------------------------------------------------------
# Persistent divergence tests
# ---------------------------------------------------------------------------


class TestPersistentDivergence:
    def test_detects_divergence(self):
        snapshots = [
            _snap(
                "2021-03-31",
                net_profit="100",
                operating_cash_flow="-50",
            ),
            _snap(
                "2022-03-31",
                net_profit="120",
                operating_cash_flow="-60",
            ),
        ]
        result = detect_persistent_cash_profit_divergence(snapshots)
        assert result is not None
        assert result.observation_type == "persistent_cash_profit_divergence"
        assert result.severity == "MEDIUM"
        assert result.periods_covered == 2
        assert result.persistent is True

    def test_no_divergence(self):
        snapshots = [
            _snap(
                "2021-03-31",
                net_profit="100",
                operating_cash_flow="120",
            ),
            _snap(
                "2022-03-31",
                net_profit="120",
                operating_cash_flow="140",
            ),
        ]
        result = detect_persistent_cash_profit_divergence(snapshots)
        assert result is None

    def test_high_severity_for_3plus_periods(self):
        snapshots = [
            _snap("2021-03-31", net_profit="100", operating_cash_flow="-50"),
            _snap("2022-03-31", net_profit="120", operating_cash_flow="-60"),
            _snap("2023-03-31", net_profit="140", operating_cash_flow="-70"),
        ]
        result = detect_persistent_cash_profit_divergence(snapshots)
        assert result is not None
        assert result.severity == "HIGH"
        assert result.periods_covered == 3

    def test_insufficient_data(self):
        snapshots = [_snap("2021-03-31", net_profit="100", operating_cash_flow="-50")]
        result = detect_persistent_cash_profit_divergence(snapshots)
        assert result is None


# ---------------------------------------------------------------------------
# Receivables divergence tests
# ---------------------------------------------------------------------------


class TestReceivablesDivergence:
    def test_detects_divergence(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000", receivables="100"),
            _snap("2022-03-31", revenue="1100", receivables="200"),
        ]
        result = detect_receivables_divergence(snapshots)
        assert result is not None
        assert result.observation_type == "receivables_growth_divergence"
        assert result.metric == "receivables"
        assert len(result.growth_divergences) == 1
        assert result.growth_divergences[0].flagged is True

    def test_no_divergence(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000", receivables="100"),
            _snap("2022-03-31", revenue="1200", receivables="120"),
        ]
        result = detect_receivables_divergence(snapshots)
        assert result is None

    def test_insufficient_data(self):
        snapshots = [_snap("2021-03-31", revenue="1000")]
        result = detect_receivables_divergence(snapshots)
        assert result is None


# ---------------------------------------------------------------------------
# Inventory divergence tests
# ---------------------------------------------------------------------------


class TestInventoryDivergence:
    def test_detects_divergence(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000", inventory="100"),
            _snap("2022-03-31", revenue="1100", inventory="250"),
        ]
        result = detect_inventory_divergence(snapshots)
        assert result is not None
        assert result.observation_type == "inventory_growth_divergence"

    def test_no_divergence(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000", inventory="100"),
            _snap("2022-03-31", revenue="1200", inventory="110"),
        ]
        result = detect_inventory_divergence(snapshots)
        assert result is None


# ---------------------------------------------------------------------------
# Full earnings quality analysis
# ---------------------------------------------------------------------------


class TestFullAnalysis:
    def test_returns_observations(self):
        snapshots = [
            _snap(
                "2021-03-31",
                revenue="1000",
                net_profit="100",
                operating_cash_flow="-50",
                receivables="100",
            ),
            _snap(
                "2022-03-31",
                revenue="1100",
                net_profit="120",
                operating_cash_flow="-60",
                receivables="250",
            ),
        ]
        result = analyze_earnings_quality(snapshots)
        assert len(result) >= 1
        types = {o.observation_type for o in result}
        assert "persistent_cash_profit_divergence" in types
        assert "receivables_growth_divergence" in types

    def test_empty_with_clean_data(self):
        snapshots = [
            _snap(
                "2021-03-31",
                revenue="1000",
                net_profit="100",
                operating_cash_flow="120",
                receivables="100",
            ),
            _snap(
                "2022-03-31",
                revenue="1200",
                net_profit="120",
                operating_cash_flow="144",
                receivables="120",
            ),
        ]
        result = analyze_earnings_quality(snapshots)
        assert result == []

    def test_insufficient_data(self):
        result = analyze_earnings_quality([])
        assert result == []


# ---------------------------------------------------------------------------
# Growth divergence comparison
# ---------------------------------------------------------------------------


class TestGrowthDivergence:
    def test_comparison_returns_divergences(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000", receivables="100"),
            _snap("2022-03-31", revenue="1100", receivables="200"),
            _snap("2023-03-31", revenue="1210", receivables="300"),
        ]
        result = compare_growth_rates(snapshots, "receivables")
        assert len(result) == 2
        assert all(isinstance(d, GrowthDivergence) for d in result)
