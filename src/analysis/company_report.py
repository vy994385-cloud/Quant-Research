from dataclasses import dataclass
from decimal import Decimal

from src.analysis.benchmarking import BenchmarkResult
from src.analysis.financial_anomalies import FinancialAnomaly
from src.analysis.financial_trends import FinancialTrend
from src.analysis.risk_signals import RiskSignal


@dataclass(frozen=True)
class CompanyResearchReport:
    symbol: str

    strengths: tuple[str, ...]
    risks: tuple[str, ...]
    unknowns: tuple[str, ...]

    anomalies: tuple[FinancialAnomaly, ...]
    trends: tuple[FinancialTrend, ...]
    benchmarks: tuple[BenchmarkResult, ...]
    risk_signals: tuple[RiskSignal, ...]

    confidence: Decimal


def build_company_report(
    *,
    symbol: str,
    anomalies: list[FinancialAnomaly],
    trends: list[FinancialTrend],
    benchmarks: list[BenchmarkResult],
    risk_signals: list[RiskSignal],
    available_data_points: int,
    expected_data_points: int,
) -> CompanyResearchReport:

    strengths: list[str] = []
    risks: list[str] = []
    unknowns: list[str] = []

    for trend in trends:

        if trend.metric in {
            "revenue",
            "net_profit",
            "operating_cash_flow",
            "free_cash_flow",
        } and trend.direction == "INCREASING":

            strengths.append(
                f"{trend.metric} is showing a persistent "
                "increasing trend."
            )

    for signal in risk_signals:
        risks.append(signal.title)

    if expected_data_points > 0:
        coverage = (
            Decimal(available_data_points)
            / Decimal(expected_data_points)
        )
    else:
        coverage = Decimal("0")

    coverage = min(
        max(coverage, Decimal("0")),
        Decimal("1"),
    )

    confidence = coverage

    if not risk_signals:
        unknowns.append(
            "No material risk signals were generated "
            "from the currently available analytical data."
        )

    if not benchmarks:
        unknowns.append(
            "Peer comparison is unavailable or incomplete."
        )

    if not trends:
        unknowns.append(
            "Historical trend analysis is unavailable "
            "because insufficient reporting periods were supplied."
        )

    return CompanyResearchReport(
        symbol=symbol,
        strengths=tuple(strengths),
        risks=tuple(risks),
        unknowns=tuple(unknowns),
        anomalies=tuple(anomalies),
        trends=tuple(trends),
        benchmarks=tuple(benchmarks),
        risk_signals=tuple(risk_signals),
        confidence=confidence,
    )
