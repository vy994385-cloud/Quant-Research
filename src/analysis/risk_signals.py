from dataclasses import dataclass
from decimal import Decimal

from src.analysis.benchmarking import BenchmarkResult
from src.analysis.financial_anomalies import FinancialAnomaly
from src.analysis.financial_trends import FinancialTrend


@dataclass(frozen=True)
class RiskSignal:
    signal_id: str
    category: str
    severity: str
    confidence: Decimal
    title: str
    explanation: str
    supporting_metrics: tuple[str, ...]


def signals_from_anomalies(
    anomalies: list[FinancialAnomaly],
) -> list[RiskSignal]:

    signals: list[RiskSignal] = []

    for index, anomaly in enumerate(anomalies, start=1):

        signal_id = f"FIN_ANOMALY_{index:03d}"

        signals.append(
            RiskSignal(
                signal_id=signal_id,
                category="FINANCIAL",
                severity=anomaly.severity,
                confidence=Decimal("0.70"),
                title=(
                    f"Unusual {anomaly.metric} movement"
                ),
                explanation=anomaly.explanation,
                supporting_metrics=(
                    anomaly.metric,
                ),
            )
        )

    return signals


def signals_from_trends(
    trends: list[FinancialTrend],
) -> list[RiskSignal]:

    signals: list[RiskSignal] = []

    for trend in trends:

        if trend.direction != "INCREASING":
            continue

        if trend.metric not in {
            "receivables",
            "payables",
            "total_debt",
        }:
            continue

        if trend.average_change < Decimal("10"):
            continue

        signals.append(
            RiskSignal(
                signal_id=f"TREND_{trend.metric.upper()}",
                category="FINANCIAL_TREND",
                severity="LOW",
                confidence=Decimal("0.60"),
                title=(
                    f"Persistent increase in {trend.metric}"
                ),
                explanation=trend.explanation,
                supporting_metrics=(
                    trend.metric,
                ),
            )
        )

    return signals


def signals_from_benchmarks(
    benchmarks: list[BenchmarkResult],
) -> list[RiskSignal]:

    signals: list[RiskSignal] = []

    for benchmark in benchmarks:

        if benchmark.percentile < Decimal("90"):
            continue

        if benchmark.metric not in {
            "receivables",
            "payables",
            "total_debt",
        }:
            continue

        signals.append(
            RiskSignal(
                signal_id=(
                    f"PEER_{benchmark.metric.upper()}"
                ),
                category="PEER_CONTEXT",
                severity="MEDIUM",
                confidence=Decimal("0.65"),
                title=(
                    f"{benchmark.metric} is unusually high "
                    "relative to peers"
                ),
                explanation=(
                    f"The company's {benchmark.metric} is at the "
                    f"{benchmark.percentile}th percentile of "
                    "the supplied peer group."
                ),
                supporting_metrics=(
                    benchmark.metric,
                ),
            )
        )

    return signals


def combine_risk_signals(
    *,
    anomalies: list[FinancialAnomaly],
    trends: list[FinancialTrend],
    benchmarks: list[BenchmarkResult],
) -> list[RiskSignal]:

    signals: list[RiskSignal] = []

    signals.extend(
        signals_from_anomalies(anomalies)
    )

    signals.extend(
        signals_from_trends(trends)
    )

    signals.extend(
        signals_from_benchmarks(benchmarks)
    )

    return signals
