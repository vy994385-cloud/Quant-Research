"""Tests for fundamental observation model and builder."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.analysis.fundamental_observations import (
    FundamentalObservation,
    FundamentalObservationSet,
    ObservationDirection,
    ObservationSeverity,
    ObservationStatus,
    _determine_direction,
    _determine_severity,
    build_anomaly_observations,
    build_balance_sheet_observations,
    build_earnings_quality_observations,
    build_fundamental_observations,
    build_margin_observations,
    build_trajectory_observations,
)
from src.analysis.balance_sheet_quality import (
    BalanceSheetObservation,
)
from src.analysis.earnings_quality import (
    EarningsQualityObservation,
)
from src.analysis.financial_anomalies import FinancialAnomaly
from src.analysis.fundamental_trajectories import (
    MarginTrajectory,
    TrajectoryAnalysis,
)
from src.data.company.financials import FinancialSnapshot


def _snap(
    period: str,
    revenue: str | None = None,
    net_profit: str | None = None,
    symbol: str = "TEST",
) -> FinancialSnapshot:
    kwargs: dict = {"symbol": symbol, "period_end": date.fromisoformat(period)}
    if revenue is not None:
        kwargs["revenue"] = Decimal(revenue)
    if net_profit is not None:
        kwargs["net_profit"] = Decimal(net_profit)
    return FinancialSnapshot(**kwargs)


_AS_OF = datetime(2024, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Direction determination
# ---------------------------------------------------------------------------


class TestDetermineDirection:
    def test_positive_change(self):
        assert _determine_direction("100", "revenue") == "POSITIVE"

    def test_negative_change(self):
        assert _determine_direction("-50", "revenue") == "NEGATIVE"

    def test_zero_change(self):
        assert _determine_direction("0", "revenue") == "NEUTRAL"

    def test_none_change(self):
        assert _determine_direction(None, "revenue") == "NEUTRAL"

    def test_debt_negative_is_positive(self):
        assert _determine_direction("-100", "total_debt") == "POSITIVE"

    def test_debt_positive_is_negative(self):
        assert _determine_direction("100", "total_debt") == "NEGATIVE"

    def test_receivables_increase_is_negative(self):
        assert _determine_direction("50", "receivables") == "NEGATIVE"

    def test_invalid_string(self):
        assert _determine_direction("abc", "revenue") == "NEUTRAL"


# ---------------------------------------------------------------------------
# Severity determination
# ---------------------------------------------------------------------------


class TestDetermineSeverity:
    def test_persistent_is_high(self):
        assert _determine_severity("test", persistent=True) == "HIGH"

    def test_flagged_is_medium(self):
        assert _determine_severity("test", flagged=True) == "MEDIUM"

    def test_anomaly_type_is_medium(self):
        assert _determine_severity("accelerating_debt") == "MEDIUM"

    def test_default_is_low(self):
        assert _determine_severity("other_type") == "LOW"


# ---------------------------------------------------------------------------
# Trajectory observation building
# ---------------------------------------------------------------------------


class TestBuildTrajectoryObservations:
    def test_builds_observations(self):
        traj = TrajectoryAnalysis(
            metric="revenue",
            symbol="TEST",
            period_count=3,
            first_period="2021-03-31",
            last_period="2023-03-31",
            first_value="1000",
            last_value="1210",
            cagr="10.0",
            total_change="210",
            total_change_pct="21.0",
            direction="INCREASING",
            explanation="Revenue increased.",
        )
        snapshots = [_snap("2021-03-31", revenue="1000")]
        result = build_trajectory_observations(
            [traj], snapshots, "TEST", _AS_OF
        )
        assert len(result) == 1
        obs = result[0]
        assert obs.category == "trajectory"
        assert obs.metric == "revenue"
        assert obs.direction == "POSITIVE"
        assert obs.as_of == _AS_OF.isoformat()

    def test_empty_trajectories(self):
        result = build_trajectory_observations([], [], "TEST", _AS_OF)
        assert result == []


# ---------------------------------------------------------------------------
# Margin observation building
# ---------------------------------------------------------------------------


class TestBuildMarginObservations:
    def test_builds_margin_observations(self):
        mt = MarginTrajectory(
            margin_name="net_margin",
            symbol="TEST",
            period_count=2,
            first_period="2021-03-31",
            last_period="2022-03-31",
            first_value="10.0",
            last_value="12.0",
            total_change_pp="2.0",
            direction="EXPANDING",
            persistent=True,
            values=[],
            explanation="Margin expanded.",
        )
        result = build_margin_observations(
            [mt], [], "TEST", _AS_OF
        )
        assert len(result) == 1
        assert result[0].category == "margin_trajectory"
        assert result[0].direction == "POSITIVE"
        assert result[0].severity == "MEDIUM"

    def test_empty(self):
        result = build_margin_observations([], [], "TEST", _AS_OF)
        assert result == []


# ---------------------------------------------------------------------------
# Earnings quality observation building
# ---------------------------------------------------------------------------


class TestBuildEarningsQualityObservations:
    def test_builds_observations(self):
        eq = EarningsQualityObservation(
            observation_type="persistent_cash_profit_divergence",
            symbol="TEST",
            severity="MEDIUM",
            periods_covered=2,
            first_period="2021-03-31",
            last_period="2022-03-31",
            metric="net_profit vs operating_cash_flow",
            persistent=True,
            explanation="Divergence detected.",
        )
        result = build_earnings_quality_observations(
            [eq], [], "TEST", _AS_OF
        )
        assert len(result) == 1
        assert result[0].category == "earnings_quality"
        assert result[0].direction == "NEGATIVE"

    def test_empty(self):
        result = build_earnings_quality_observations([], [], "TEST", _AS_OF)
        assert result == []


# ---------------------------------------------------------------------------
# Balance-sheet observation building
# ---------------------------------------------------------------------------


class TestBuildBalanceSheetObservations:
    def test_builds_observations(self):
        bs = BalanceSheetObservation(
            observation_type="accelerating_debt",
            symbol="TEST",
            severity="MEDIUM",
            periods_covered=1,
            first_period="2021-03-31",
            last_period="2022-03-31",
            explanation="Debt accelerated.",
        )
        result = build_balance_sheet_observations(
            [bs], [], "TEST", _AS_OF
        )
        assert len(result) == 1
        assert result[0].category == "balance_sheet_quality"
        assert result[0].direction == "NEGATIVE"

    def test_empty(self):
        result = build_balance_sheet_observations([], [], "TEST", _AS_OF)
        assert result == []


# ---------------------------------------------------------------------------
# Anomaly observation building
# ---------------------------------------------------------------------------


class TestBuildAnomalyObservations:
    def test_builds_observations(self):
        anomaly = FinancialAnomaly(
            metric="receivables",
            current_change=Decimal("50"),
            comparison_change=Decimal("10"),
            severity="MEDIUM",
            explanation="Receivables growing faster than revenue.",
        )
        result = build_anomaly_observations(
            [anomaly], [], "TEST", _AS_OF
        )
        assert len(result) == 1
        assert result[0].category == "anomaly"
        assert result[0].severity == "MEDIUM"

    def test_empty(self):
        result = build_anomaly_observations([], [], "TEST", _AS_OF)
        assert result == []


# ---------------------------------------------------------------------------
# Full observation set building
# ---------------------------------------------------------------------------


class TestBuildFundamentalObservations:
    def test_builds_complete_set(self):
        traj = TrajectoryAnalysis(
            metric="revenue",
            symbol="TEST",
            period_count=2,
            first_period="2021-03-31",
            last_period="2022-03-31",
            first_value="1000",
            last_value="1100",
            total_change="100",
            total_change_pct="10.0",
            direction="INCREASING",
            explanation="Revenue increased.",
        )
        mt = MarginTrajectory(
            margin_name="net_margin",
            symbol="TEST",
            period_count=2,
            first_period="2021-03-31",
            last_period="2022-03-31",
            first_value="10.0",
            last_value="12.0",
            total_change_pp="2.0",
            direction="EXPANDING",
            values=[],
            explanation="Margin expanded.",
        )
        eq = EarningsQualityObservation(
            observation_type="persistent_cash_profit_divergence",
            symbol="TEST",
            severity="MEDIUM",
            periods_covered=2,
            first_period="2021-03-31",
            last_period="2022-03-31",
            metric="net_profit vs operating_cash_flow",
            persistent=True,
            explanation="Divergence.",
        )
        snapshots = [
            _snap("2021-03-31", revenue="1000"),
            _snap("2022-03-31", revenue="1100"),
        ]

        result = build_fundamental_observations(
            symbol="TEST",
            as_of=_AS_OF,
            snapshots=snapshots,
            trajectory_results={
                "trajectories": [traj],
                "margin_trajectories": [mt],
            },
            earnings_quality_results=[eq],
            balance_sheet_results=[],
            anomaly_results=[],
        )

        assert result.symbol == "TEST"
        assert result.total_count >= 2
        assert result.positive_count >= 1
        assert result.negative_count >= 1
        assert "trajectory" in result.coverage
        assert "margin_trajectory" in result.coverage
        assert "earnings_quality" in result.coverage

    def test_empty_results(self):
        result = build_fundamental_observations(
            symbol="TEST",
            as_of=_AS_OF,
            snapshots=[],
            trajectory_results={},
            earnings_quality_results=[],
            balance_sheet_results=[],
            anomaly_results=[],
        )
        assert result.total_count == 0
        assert len(result.notes) > 0
