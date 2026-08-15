from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
)
from src.research.adapters.company_snapshot import (
    snapshot_to_research_signals,
)
from src.research.features.financial_trends import (
    FinancialTrendSummary,
)
from src.research.features.models import FeatureValue
from src.research.report.builder import build_company_report
from src.research.report.models import ResearchReport
from src.data.company.financials import FinancialSnapshot
from src.features.market_snapshot import MarketFeatureSnapshot
from src.research.signals.models import ResearchSignal
from src.research.acquisition.models import ResearchObservation


@dataclass(frozen=True)
class CompanyResearchInput:
    """
    Complete point-in-time input for one company research run.

    The engine accepts both the newer normalized company-intelligence
    snapshot and the existing feature/signal/trend research inputs.
    """

    symbol: str
    as_of: datetime

    features: tuple[FeatureValue, ...] = ()
    signals: tuple[ResearchSignal, ...] = ()
    trend_summaries: tuple[FinancialTrendSummary, ...] = ()

    company_snapshot: CompanyResearchSnapshot | None = None
    financial_snapshots: tuple[FinancialSnapshot, ...] = ()
    market_snapshot: MarketFeatureSnapshot | None = None
    provenance_ids: tuple[str, ...] = ()
    acquired_observations: tuple[ResearchObservation, ...] = ()

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()

        if not symbol:
            raise ValueError("symbol cannot be empty")

        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        if (
            self.company_snapshot is not None
            and self.company_snapshot.symbol != symbol
        ):
            raise ValueError(
                "company snapshot symbol does not match "
                "research input symbol"
            )

        if (
            self.company_snapshot is not None
            and self.company_snapshot.as_of_date
            > self.as_of.date()
        ):
            raise ValueError(
                "company snapshot date cannot be after as_of"
            )

        object.__setattr__(self, "symbol", symbol)


class CompanyResearchEngine:
    """
    Main orchestration boundary for company research.

    This class does NOT fetch external data.

    Data acquisition belongs to providers.
    Research orchestration belongs here.

    Company-intelligence snapshots are translated into the
    ResearchSignal contract before report construction.
    """

    def run(
        self,
        research_input: CompanyResearchInput,
    ) -> ResearchReport:

        snapshot_signals: tuple[
            ResearchSignal, ...
        ] = ()

        if research_input.company_snapshot is not None:
            snapshot_signals = (
                snapshot_to_research_signals(
                    research_input.company_snapshot
                )
            )

        all_signals = [
            *research_input.signals,
            *snapshot_signals,
        ]

        snapshot = research_input.company_snapshot

        return build_company_report(
            symbol=research_input.symbol,
            as_of=research_input.as_of,
            features=list(research_input.features),
            signals=all_signals,
            trend_summaries=list(
                research_input.trend_summaries
            ),
            company_snapshot=snapshot,
            financial_snapshots=list(
                research_input.financial_snapshots
            ),
            market_snapshot=research_input.market_snapshot,
            provenance_ids=research_input.provenance_ids,
            acquired_observations=list(
                research_input.acquired_observations
            ),
        )

def run_company_research(
    *,
    symbol: str,
    as_of: datetime,
    features: list[FeatureValue] | None = None,
    signals: list[ResearchSignal] | None = None,
    trend_summaries: list[FinancialTrendSummary] | None = None,
    company_snapshot: CompanyResearchSnapshot | None = None,
    financial_snapshots: list[FinancialSnapshot] | None = None,
    market_snapshot: MarketFeatureSnapshot | None = None,
    provenance_ids: tuple[str, ...] = (),
    acquired_observations: list[ResearchObservation] | None = None,
) -> ResearchReport:
    """
    Convenience API for running one company research report.

    Existing callers remain compatible. A company-intelligence
    snapshot can optionally be supplied as an additional evidence
    source, and acquired research observations can optionally feed
    the evidence synthesis pipeline.
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
            company_snapshot=company_snapshot,
            financial_snapshots=tuple(financial_snapshots or []),
            market_snapshot=market_snapshot,
            provenance_ids=provenance_ids,
            acquired_observations=tuple(
                acquired_observations or []
            ),
        )
    )
