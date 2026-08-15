from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Iterable

from src.research.acquisition.models import ResearchObservation
from src.research.synthesis.models import (
    EvidenceDirection,
    EvidenceItem,
    EvidenceReliability,
    EvidenceType,
)


def _reliability_for_tier(
    tier: int | None,
) -> EvidenceReliability:
    """
    Map the acquisition reliability tier into the normalized
    evidence reliability contract.

    The mapping is deliberately conservative:
    an unknown tier never becomes primary evidence.
    """

    if tier in (1, 2):
        return EvidenceReliability.PRIMARY

    if tier == 3:
        return EvidenceReliability.SECONDARY

    if tier == 4:
        return EvidenceReliability.TERTIARY

    return EvidenceReliability.UNKNOWN


def observation_to_evidence_item(
    observation: ResearchObservation,
    *,
    as_of: datetime,
) -> EvidenceItem | None:
    """
    Convert one acquired research observation into normalized evidence.

    Point-in-time integrity is strict:

    - observations without a timezone-aware available_at are never
      usable in historical research
    - observations whose available_at is after as_of are never used
    - the extracted observation model deliberately carries no
      direction, so the normalized evidence is NEUTRAL

    This function never modifies the input observation.
    """

    if as_of.tzinfo is None:
        raise ValueError(
            "as_of must be timezone-aware"
        )

    available_at = observation.available_at

    if available_at is None:
        return None

    if available_at.tzinfo is None:
        return None

    if available_at > as_of:
        return None

    return EvidenceItem(
        evidence_id=(
            f"ACQUIRED:{observation.observation_id}"
        ),
        symbol=observation.company,
        evidence_type=EvidenceType.ACQUIRED,
        title=observation.claim,
        explanation=observation.evidence_excerpt,
        direction=EvidenceDirection.NEUTRAL,
        confidence=Decimal(
            str(observation.confidence)
        ),
        reliability=_reliability_for_tier(
            observation.reliability_tier
        ),
        observation_at=available_at,
        source_ids=(observation.source_id,),
        provenance_ids=(),
    )


def research_observations_to_evidence(
    observations: Iterable[ResearchObservation],
    *,
    symbol: str,
    as_of: datetime,
) -> tuple[EvidenceItem, ...]:
    """
    Convert acquired observations into deterministic, deduplicated,
    point-in-time-safe evidence for one company.

    Evidence for another symbol and evidence that was not knowable
    at as_of is excluded before it can reach synthesis.
    """

    normalized_symbol = symbol.strip().upper()

    if not normalized_symbol:
        raise ValueError(
            "symbol cannot be empty"
        )

    items: dict[str, EvidenceItem] = {}

    for observation in observations:
        if (
            observation.company.strip().upper()
            != normalized_symbol
        ):
            continue

        item = observation_to_evidence_item(
            observation,
            as_of=as_of,
        )

        if item is None:
            continue

        items[item.evidence_id] = item

    return tuple(
        items[key]
        for key in sorted(items)
    )


__all__ = [
    "observation_to_evidence_item",
    "research_observations_to_evidence",
]
