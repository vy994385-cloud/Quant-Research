from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from src.research.synthesis.models import (
    EvidenceDirection,
    EvidenceItem,
    EvidenceSynthesis,
)


def _validate_as_of(as_of: datetime) -> None:
    if as_of.tzinfo is None:
        raise ValueError(
            "as_of must be timezone-aware"
        )


def _usable_evidence(
    evidence: list[EvidenceItem],
    *,
    symbol: str,
    as_of: datetime,
) -> list[EvidenceItem]:
    usable: list[EvidenceItem] = []

    for item in evidence:
        if item.symbol != symbol:
            continue

        if item.observation_at > as_of:
            continue

        usable.append(item)

    return usable


def _direction(
    evidence: list[EvidenceItem],
) -> EvidenceDirection:
    positive = any(
        item.direction == EvidenceDirection.POSITIVE
        for item in evidence
    )

    negative = any(
        item.direction == EvidenceDirection.NEGATIVE
        for item in evidence
    )

    neutral = any(
        item.direction == EvidenceDirection.NEUTRAL
        for item in evidence
    )

    # Conflicting validated evidence remains MIXED.
    # Weighting must not erase the existence of disagreement.
    if positive and negative:
        return EvidenceDirection.MIXED

    if positive:
        return EvidenceDirection.POSITIVE

    if negative:
        return EvidenceDirection.NEGATIVE

    if neutral:
        return EvidenceDirection.NEUTRAL

    return EvidenceDirection.MIXED

def _average_confidence(
    evidence: list[EvidenceItem],
) -> Decimal:
    if not evidence:
        return Decimal("0")

    total = sum(
        (item.confidence for item in evidence),
        Decimal("0"),
    )

    return total / Decimal(len(evidence))


def _weighted_confidence(
    evidence: list[EvidenceItem],
) -> Decimal:
    if not evidence:
        return Decimal("0")

    total_weight = sum(
        (
            item.reliability_weight
            for item in evidence
        ),
        Decimal("0"),
    )

    if total_weight == 0:
        return Decimal("0")

    weighted = sum(
        (
            item.confidence
            * item.reliability_weight
            for item in evidence
        ),
        Decimal("0"),
    )

    return weighted / total_weight


def synthesize_evidence(
    *,
    symbol: str,
    as_of: datetime,
    evidence: list[EvidenceItem],
) -> EvidenceSynthesis:
    """
    Build a deterministic point-in-time evidence synthesis.

    Evidence from another symbol or observed after `as_of`
    is excluded.

    Conflicting evidence is retained rather than discarded.
    Reliability and confidence determine its contribution.
    """

    _validate_as_of(as_of)

    normalized_symbol = symbol.strip().upper()

    if not normalized_symbol:
        raise ValueError("symbol cannot be empty")

    usable = _usable_evidence(
        evidence,
        symbol=normalized_symbol,
        as_of=as_of,
    )

    positive_weight = sum(
        (
            item.weighted_confidence
            for item in usable
            if item.direction
            == EvidenceDirection.POSITIVE
        ),
        Decimal("0"),
    )

    negative_weight = sum(
        (
            item.weighted_confidence
            for item in usable
            if item.direction
            == EvidenceDirection.NEGATIVE
        ),
        Decimal("0"),
    )

    positive_count = sum(
        item.direction == EvidenceDirection.POSITIVE
        for item in usable
    )

    negative_count = sum(
        item.direction == EvidenceDirection.NEGATIVE
        for item in usable
    )

    neutral_count = sum(
        item.direction == EvidenceDirection.NEUTRAL
        for item in usable
    )

    conflict_detected = (
        positive_count > 0
        and negative_count > 0
    )

    return EvidenceSynthesis(
        symbol=normalized_symbol,
        as_of=as_of,
        evidence=tuple(usable),
        positive_count=positive_count,
        negative_count=negative_count,
        neutral_count=neutral_count,
        positive_weight=positive_weight,
        negative_weight=negative_weight,
        average_confidence=_average_confidence(usable),
        weighted_confidence=_weighted_confidence(usable),
        conflict_detected=conflict_detected,
        direction=_direction(usable),
    )


__all__ = [
    "synthesize_evidence",
]
