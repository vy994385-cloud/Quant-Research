from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
    IntelligenceDirection,
)
from src.research.signals.models import (
    ResearchSignal,
    SignalDirection,
    SignalSeverity,
)


def _direction(
    direction: IntelligenceDirection,
) -> SignalDirection:
    mapping = {
        IntelligenceDirection.POSITIVE:
            SignalDirection.POSITIVE,
        IntelligenceDirection.NEGATIVE:
            SignalDirection.NEGATIVE,
        IntelligenceDirection.NEUTRAL:
            SignalDirection.NEUTRAL,
        IntelligenceDirection.MIXED:
            SignalDirection.MIXED,
    }

    return mapping[direction]


def _severity(
    materiality: int,
) -> SignalSeverity:
    if materiality >= 5:
        return SignalSeverity.CRITICAL

    if materiality >= 4:
        return SignalSeverity.HIGH

    if materiality >= 3:
        return SignalSeverity.MEDIUM

    if materiality >= 2:
        return SignalSeverity.LOW

    return SignalSeverity.INFO


def _observation_at(
    snapshot: CompanyResearchSnapshot,
) -> datetime:
    """
    Snapshot observations are date-based.

    Convert the snapshot's as-of date to the earliest UTC instant
    on that date. This preserves the fact that the adapter does not
    invent an intraday observation timestamp.
    """

    return datetime(
        snapshot.as_of_date.year,
        snapshot.as_of_date.month,
        snapshot.as_of_date.day,
        tzinfo=timezone.utc,
    )


def snapshot_to_research_signals(
    snapshot: CompanyResearchSnapshot,
) -> tuple[ResearchSignal, ...]:
    """
    Convert normalized company-intelligence signals into the
    point-in-time ResearchSignal representation.

    This adapter does not create new intelligence.

    It only translates the already-normalized snapshot signals
    into the research-report signal contract.
    """

    observation_at = _observation_at(snapshot)

    result: list[ResearchSignal] = []

    for signal in snapshot.signals:
        result.append(
            ResearchSignal(
                signal_id=signal.code,
                category="COMPANY_INTELLIGENCE",
                direction=_direction(signal.direction),
                severity=_severity(signal.materiality),
                confidence=Decimal(str(signal.confidence)),
                title=signal.title,
                explanation=signal.description,
                symbol=snapshot.symbol,
                observation_at=observation_at,
                supporting_features=(),
                supporting_metrics=(),
            )
        )

    return tuple(result)


__all__ = [
    "snapshot_to_research_signals",
]
