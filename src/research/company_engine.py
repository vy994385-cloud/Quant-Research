from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.research.features.models import FeatureValue
from src.research.features.financial_trends import FinancialTrendSummary
from src.research.report.builder import build_company_report
from src.research.report.models import ResearchReport
from src.research.signals.models import ResearchSignal


@dataclass(frozen=True)
class CompanyResearchInput:
    """
    Complete point-in-time input for one company research run.
    """

    symbol: str
    as_of: datetime

    features: tuple[FeatureValue, ...] = ()
    signals: tuple[ResearchSignal, ...] = ()
    trend_summaries: tuple[FinancialTrendSummary, ...] = ()

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()

        if not symbol:
            raise ValueError("symbol cannot be empty")

        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        object.__setattr__(self, "symbol", symbol)


class CompanyResearchEngine:
    """
    Main orchestration boundary for company research.

    This class deliberately does NOT fetch external data.

    Data acquisition belongs to providers.
    Research orchestration belongs here.
    """

    def run(
        self,
        research_input: CompanyResearchInput,
    ) -> ResearchReport:
        return build_company_report(
            symbol=research_input.symbol,
            as_of=research_input.as_of,
            features=list(research_input.features),
            signals=list(research_input.signals),
            trend_summaries=list(
                research_input.trend_summaries
            ),
        )


def run_company_research(
    *,
    symbol: str,
    as_of: datetime,
    features: list[FeatureValue] | None = None,
    signals: list[ResearchSignal] | None = None,
    trend_summaries: list[FinancialTrendSummary] | None = None,
) -> ResearchReport:
    """
    Convenience API for running one company research report.
    """

    engine = CompanyResearchEngine()

    return engine.run(
        CompanyResearchInput(
            symbol=symbol,
            as_of=as_of,
            features=tuple(features or []),
            signals=tuple(signals or []),
            trend_summaries=tuple(
                trend_summaries or []
            ),
        )
    )
