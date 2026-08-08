from decimal import Decimal

from src.analysis.benchmarking import BenchmarkResult
from src.analysis.financial_anomalies import FinancialAnomaly
from src.analysis.financial_trends import FinancialTrend
from src.analysis.risk_signals import (
    combine_risk_signals,
    signals_from_anomalies,
    signals_from_benchmarks,
    signals_from_trends,
)


def test_anomaly_creates_risk_signal():

    anomaly = FinancialAnomaly(
        metric="receivables",
        current_change=Decimal("50"),
        comparison_change=Decimal("10"),
        severity="MEDIUM",
        explanation="Receivables increased faster than revenue.",
    )

    signals = signals_from_anomalies(
        [anomaly],
    )

    assert len(signals) == 1
    assert signals[0].category == "FINANCIAL"
    assert signals[0].severity == "MEDIUM"
    assert signals[0].confidence == Decimal("0.70")


def test_increasing_debt_creates_trend_signal():

    trend = FinancialTrend(
        metric="total_debt",
        direction="INCREASING",
        observations=3,
        average_change=Decimal("15"),
        explanation="Debt increased across reporting periods.",
    )

    signals = signals_from_trends(
        [trend],
    )

    assert len(signals) == 1
    assert signals[0].category == "FINANCIAL_TREND"


def test_small_trend_is_ignored():

    trend = FinancialTrend(
        metric="total_debt",
        direction="INCREASING",
        observations=3,
        average_change=Decimal("5"),
        explanation="Debt increased slightly.",
    )

    signals = signals_from_trends(
        [trend],
    )

    assert signals == []


def test_high_peer_percentile_creates_signal():

    benchmark = BenchmarkResult(
        metric="receivables",
        company_value=Decimal("300"),
        peer_median=Decimal("100"),
        percentile=Decimal("95"),
        relative_to_peers="ABOVE_PEER_MEDIAN",
    )

    signals = signals_from_benchmarks(
        [benchmark],
    )

    assert len(signals) == 1
    assert signals[0].category == "PEER_CONTEXT"
    assert signals[0].severity == "MEDIUM"


def test_normal_peer_position_is_ignored():

    benchmark = BenchmarkResult(
        metric="receivables",
        company_value=Decimal("110"),
        peer_median=Decimal("100"),
        percentile=Decimal("60"),
        relative_to_peers="ABOVE_PEER_MEDIAN",
    )

    signals = signals_from_benchmarks(
        [benchmark],
    )

    assert signals == []


def test_combines_all_signal_sources():

    anomaly = FinancialAnomaly(
        metric="receivables",
        current_change=Decimal("50"),
        comparison_change=Decimal("10"),
        severity="MEDIUM",
        explanation="Receivables increased faster than revenue.",
    )

    trend = FinancialTrend(
        metric="total_debt",
        direction="INCREASING",
        observations=3,
        average_change=Decimal("15"),
        explanation="Debt increased.",
    )

    benchmark = BenchmarkResult(
        metric="receivables",
        company_value=Decimal("300"),
        peer_median=Decimal("100"),
        percentile=Decimal("95"),
        relative_to_peers="ABOVE_PEER_MEDIAN",
    )

    signals = combine_risk_signals(
        anomalies=[anomaly],
        trends=[trend],
        benchmarks=[benchmark],
    )

    assert len(signals) == 3
