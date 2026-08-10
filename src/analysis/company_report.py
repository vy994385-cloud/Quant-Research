from dataclasses import dataclass
from decimal import Decimal

from src.analysis.benchmarking import BenchmarkResult
from src.analysis.financial_anomalies import FinancialAnomaly
from src.analysis.financial_trends import FinancialTrend
from src.analysis.future_intelligence import (
    FutureTechnologyProfile,
    ai_participation_score,
    future_readiness_score,
    innovation_execution_score,
    technology_diversification_score,
)
from src.analysis.risk_signals import RiskSignal


@dataclass(frozen=True)
class CompanyResearchReport:
    """
    Unified descriptive company research report.

    This report combines financial, trend, benchmark, risk and
    optional future-technology intelligence.

    It does NOT:
    - predict stock returns
    - produce BUY/SELL instructions
    - execute trades
    """

    symbol: str

    strengths: tuple[str, ...]
    risks: tuple[str, ...]
    unknowns: tuple[str, ...]

    anomalies: tuple[FinancialAnomaly, ...]
    trends: tuple[FinancialTrend, ...]
    benchmarks: tuple[BenchmarkResult, ...]
    risk_signals: tuple[RiskSignal, ...]

    confidence: Decimal

    future_technology: FutureTechnologyProfile | None = None

    @property
    def has_future_intelligence(self) -> bool:
        return self.future_technology is not None

    @property
    def future_readiness(self) -> Decimal:
        """
        Descriptive future-readiness score.

        Returns the neutral baseline when no future-technology
        profile has been supplied.
        """

        if self.future_technology is None:
            return Decimal("50")

        return future_readiness_score(
            self.future_technology
        )

    @property
    def ai_participation(self) -> Decimal:
        """
        Descriptive AI participation score.

        A company with no explicit AI signals receives 0 because
        this metric measures AI participation specifically.
        """

        if self.future_technology is None:
            return Decimal("0")

        return ai_participation_score(
            self.future_technology
        )

    @property
    def innovation_execution(self) -> Decimal:
        """
        Descriptive innovation execution score.
        """

        if self.future_technology is None:
            return Decimal("50")

        return innovation_execution_score(
            self.future_technology
        )

    @property
    def technology_diversification(self) -> Decimal:
        """
        Descriptive technology-area breadth score.
        """

        if self.future_technology is None:
            return Decimal("0")

        return technology_diversification_score(
            self.future_technology
        )

    @property
    def future_signal_count(self) -> int:
        if self.future_technology is None:
            return 0

        return self.future_technology.signal_count

    @property
    def future_technology_area_count(self) -> int:
        if self.future_technology is None:
            return 0

        return self.future_technology.technology_area_count


def build_company_report(
    *,
    symbol: str,
    anomalies: list[FinancialAnomaly],
    trends: list[FinancialTrend],
    benchmarks: list[BenchmarkResult],
    risk_signals: list[RiskSignal],
    available_data_points: int,
    expected_data_points: int,
    future_technology: FutureTechnologyProfile | None = None,
) -> CompanyResearchReport:
    """
    Build a normalized company research report.

    Future intelligence is optional and remains descriptive.
    It is NOT automatically converted into a stock-ranking factor.
    """

    normalized_symbol = symbol.strip().upper()

    if not normalized_symbol:
        raise ValueError("symbol cannot be empty")

    if (
        future_technology is not None
        and future_technology.symbol.strip().upper()
        != normalized_symbol
    ):
        raise ValueError(
            "future technology symbol does not match "
            "company report symbol"
        )

    strengths: list[str] = []
    risks: list[str] = []
    unknowns: list[str] = []

    for trend in trends:
        if (
            trend.metric in {
                "revenue",
                "net_profit",
                "operating_cash_flow",
                "free_cash_flow",
            }
            and trend.direction == "INCREASING"
        ):
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

    if future_technology is None:
        unknowns.append(
            "Future-technology intelligence is unavailable "
            "because no technology or innovation evidence "
            "was supplied."
        )
    elif future_technology.signal_count == 0:
        unknowns.append(
            "No future-technology signals were available "
            "for the current research snapshot."
        )

    return CompanyResearchReport(
        symbol=normalized_symbol,
        strengths=tuple(strengths),
        risks=tuple(risks),
        unknowns=tuple(unknowns),
        anomalies=tuple(anomalies),
        trends=tuple(trends),
        benchmarks=tuple(benchmarks),
        risk_signals=tuple(risk_signals),
        confidence=confidence,
        future_technology=future_technology,
    )