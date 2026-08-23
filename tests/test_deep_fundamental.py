"""Tests for deep fundamental orchestrator."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.analysis.deep_fundamental import (
    DeepFundamentalResult,
    analyze_deep_fundamentals,
)
from src.data.company.financials import FinancialSnapshot


_AVAILABILITY_LAG = timedelta(days=45)


def _snap(
    period: str,
    revenue: str | None = None,
    net_profit: str | None = None,
    operating_profit: str | None = None,
    operating_cash_flow: str | None = None,
    free_cash_flow: str | None = None,
    total_assets: str | None = None,
    total_debt: str | None = None,
    cash_and_equivalents: str | None = None,
    receivables: str | None = None,
    inventory: str | None = None,
    current_assets: str | None = None,
    current_liabilities: str | None = None,
    shareholders_equity: str | None = None,
    symbol: str = "TEST",
    available_at: datetime | None = None,
) -> FinancialSnapshot:
    period_end = date.fromisoformat(period)
    if available_at is None:
        available_at = datetime.combine(
            period_end + _AVAILABILITY_LAG,
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
    kwargs: dict = {
        "symbol": symbol,
        "period_end": period_end,
        "available_at": available_at,
    }
    for field_name, val in [
        ("revenue", revenue),
        ("net_profit", net_profit),
        ("operating_profit", operating_profit),
        ("operating_cash_flow", operating_cash_flow),
        ("free_cash_flow", free_cash_flow),
        ("total_assets", total_assets),
        ("total_debt", total_debt),
        ("cash_and_equivalents", cash_and_equivalents),
        ("receivables", receivables),
        ("inventory", inventory),
        ("current_assets", current_assets),
        ("current_liabilities", current_liabilities),
        ("shareholders_equity", shareholders_equity),
    ]:
        if val is not None:
            kwargs[field_name] = Decimal(val)
    return FinancialSnapshot(**kwargs)


_AS_OF = datetime(2024, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Empty / insufficient data
# ---------------------------------------------------------------------------


class TestInsufficientData:
    def test_empty_snapshots(self):
        result = analyze_deep_fundamentals([], "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert result.period_count == 0
        assert "trajectories" in result.missing_analyses
        assert "earnings_quality" in result.missing_analyses
        assert "balance_sheet_quality" in result.missing_analyses
        assert "anomalies" in result.missing_analyses
        assert len(result.notes) > 0

    def test_single_snapshot(self):
        snapshots = [_snap("2021-03-31", revenue="1000")]
        result = analyze_deep_fundamentals(snapshots, "TEST", _AS_OF)
        assert result.period_count == 1
        assert "trajectories" in result.missing_analyses
        assert result.trajectories == ()
        assert result.observation_set is None


# ---------------------------------------------------------------------------
# Multi-period analysis
# ---------------------------------------------------------------------------


class TestMultiPeriodAnalysis:
    def test_basic_analysis(self):
        snapshots = [
            _snap(
                "2021-03-31",
                revenue="1000",
                net_profit="100",
                total_debt="500",
                current_assets="600",
                current_liabilities="300",
                shareholders_equity="800",
            ),
            _snap(
                "2022-03-31",
                revenue="1100",
                net_profit="120",
                total_debt="450",
                current_assets="650",
                current_liabilities="300",
                shareholders_equity="850",
            ),
            _snap(
                "2023-03-31",
                revenue="1210",
                net_profit="144",
                total_debt="400",
                current_assets="700",
                current_liabilities="300",
                shareholders_equity="900",
            ),
        ]
        result = analyze_deep_fundamentals(snapshots, "TEST", _AS_OF)

        assert result.symbol == "TEST"
        assert result.period_count == 3
        assert result.first_period == "2021-03-31"
        assert result.last_period == "2023-03-31"

        # Trajectories
        assert len(result.trajectories) > 0
        assert len(result.margin_trajectories) > 0
        assert len(result.leverage_trajectories) > 0

        # Available analyses
        assert "trajectories" in result.available_analyses
        assert "earnings_quality" in result.available_analyses
        assert "balance_sheet_quality" in result.available_analyses
        assert "anomalies" in result.available_analyses
        assert "financial_trends" in result.available_analyses

        # Observation set
        assert result.observation_set is not None
        assert result.observation_set.total_count > 0
        assert result.positive_count > 0 or result.negative_count > 0

    def test_anomaly_detection(self):
        snapshots = [
            _snap(
                "2021-03-31",
                revenue="1000",
                receivables="100",
                net_profit="100",
                operating_cash_flow="-50",
            ),
            _snap(
                "2022-03-31",
                revenue="1100",
                receivables="300",
                net_profit="120",
                operating_cash_flow="-60",
            ),
        ]
        result = analyze_deep_fundamentals(snapshots, "TEST", _AS_OF)

        # Should detect anomalies
        assert len(result.anomalies) > 0
        anomaly_metrics = {a.metric for a in result.anomalies}
        assert "receivables" in anomaly_metrics
        assert "profit_cfo_divergence" in anomaly_metrics

    def test_earnings_quality_signals(self):
        snapshots = [
            _snap(
                "2021-03-31",
                revenue="1000",
                net_profit="100",
                operating_cash_flow="-50",
            ),
            _snap(
                "2022-03-31",
                revenue="1100",
                net_profit="120",
                operating_cash_flow="-60",
            ),
        ]
        result = analyze_deep_fundamentals(snapshots, "TEST", _AS_OF)

        assert len(result.earnings_quality_observations) > 0
        types = {
            o.observation_type
            for o in result.earnings_quality_observations
        }
        assert "persistent_cash_profit_divergence" in types

    def test_balance_sheet_signals(self):
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
        result = analyze_deep_fundamentals(snapshots, "TEST", _AS_OF)

        assert len(result.balance_sheet_observations) > 0
        types = {
            o.observation_type
            for o in result.balance_sheet_observations
        }
        assert "accelerating_debt" in types

    def test_financial_trends(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000"),
            _snap("2022-03-31", revenue="1100"),
            _snap("2023-03-31", revenue="1210"),
        ]
        result = analyze_deep_fundamentals(snapshots, "TEST", _AS_OF)

        assert len(result.financial_trends) > 0


# ---------------------------------------------------------------------------
# DeepFundamentalResult properties
# ---------------------------------------------------------------------------


class TestDeepFundamentalResult:
    def test_has_observations(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000"),
            _snap("2022-03-31", revenue="1100"),
        ]
        result = analyze_deep_fundamentals(snapshots, "TEST", _AS_OF)
        # May or may not have observations depending on data
        assert isinstance(result.has_observations, bool)

    def test_property_counts(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000"),
            _snap("2022-03-31", revenue="1100"),
        ]
        result = analyze_deep_fundamentals(snapshots, "TEST", _AS_OF)
        assert result.positive_count >= 0
        assert result.negative_count >= 0
        assert result.neutral_count >= 0


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_input_same_output(self):
        snapshots = [
            _snap("2021-03-31", revenue="1000", net_profit="100"),
            _snap("2022-03-31", revenue="1100", net_profit="120"),
        ]
        r1 = analyze_deep_fundamentals(snapshots, "TEST", _AS_OF)
        r2 = analyze_deep_fundamentals(snapshots, "TEST", _AS_OF)

        assert r1.period_count == r2.period_count
        assert len(r1.trajectories) == len(r2.trajectories)
        assert len(r1.anomalies) == len(r2.anomalies)
        assert r1.observation_set is not None
        assert r2.observation_set is not None
        assert (
            r1.observation_set.total_count
            == r2.observation_set.total_count
        )
