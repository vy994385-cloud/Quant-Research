from __future__ import annotations

from decimal import Decimal

from src.research.narrative.models import EvidenceNarrative
from src.research.synthesis.models import (
    EvidenceDirection,
    EvidenceItem,
    EvidenceSynthesis,
)


def _validate_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()

    if not normalized:
        raise ValueError("symbol cannot be empty")

    return normalized


def _usable(
    synthesis: EvidenceSynthesis,
    *,
    symbol: str,
) -> list[EvidenceItem]:
    normalized = _validate_symbol(symbol)

    return [
        item
        for item in synthesis.evidence
        if item.symbol == normalized
        and item.observation_at <= synthesis.as_of
    ]


def _label(item: EvidenceItem) -> str:
    return (
        f"{item.title}: {item.explanation}"
    )


def _strongest(
    evidence: list[EvidenceItem],
) -> tuple[str, ...]:
    if not evidence:
        return ()

    ranked = sorted(
        evidence,
        key=lambda item: (
            item.weighted_confidence,
            item.confidence,
            item.reliability_weight,
        ),
        reverse=True,
    )

    return tuple(
        _label(item)
        for item in ranked[:3]
    )


def _uncertainty(
    evidence: list[EvidenceItem],
) -> tuple[str, ...]:
    notes: list[str] = []

    for item in evidence:
        if item.reliability_weight < Decimal("0.65"):
            notes.append(
                f"{item.title} has limited evidence reliability."
            )

        if item.confidence < Decimal("0.50"):
            notes.append(
                f"{item.title} has relatively low confidence."
            )

    return tuple(dict.fromkeys(notes))


def _thesis(
    *,
    symbol: str,
    synthesis: EvidenceSynthesis,
) -> str:
    if not synthesis.evidence:
        return (
            f"{symbol} does not have enough validated "
            "evidence to form a research thesis."
        )

    if synthesis.direction == EvidenceDirection.MIXED:
        return (
            f"{symbol} presents mixed evidence. "
            f"The available research contains "
            f"{synthesis.positive_count} positive and "
            f"{synthesis.negative_count} negative "
            "evidence item(s), so the competing evidence "
            "should be evaluated rather than reduced to a "
            "single directional conclusion."
        )

    if synthesis.direction == EvidenceDirection.POSITIVE:
        return (
            f"{symbol} has predominantly positive evidence "
            "within the validated research set."
        )

    if synthesis.direction == EvidenceDirection.NEGATIVE:
        return (
            f"{symbol} has predominantly negative evidence "
            "within the validated research set."
        )

    return (
        f"{symbol} has evidence available, but it does not "
        "establish a clear directional research thesis."
    )


def build_evidence_narrative(
    synthesis: EvidenceSynthesis,
) -> EvidenceNarrative:
    """
    Build a deterministic explanatory narrative.

    No external facts are introduced and no return forecast
    or trading instruction is produced.
    """

    symbol = _validate_symbol(synthesis.symbol)

    evidence = _usable(
        synthesis,
        symbol=symbol,
    )

    supporting = [
        item
        for item in evidence
        if item.direction == EvidenceDirection.POSITIVE
    ]

    contradicting = [
        item
        for item in evidence
        if item.direction == EvidenceDirection.NEGATIVE
    ]

    uncertainty = list(
        _uncertainty(evidence)
    )

    risks = [
        _label(item)
        for item in contradicting
    ]

    gaps: list[str] = []

    if not evidence:
        gaps.append(
            "No validated point-in-time evidence is available."
        )

    if not supporting and not contradicting and evidence:
        gaps.append(
            "Available evidence is neutral and does not "
            "establish directional support."
        )

    if synthesis.conflict_detected:
        uncertainty.append(
            "Positive and negative evidence conflict; "
            "the disagreement remains unresolved."
        )

    changes: list[str] = []

    if contradicting:
        changes.append(
            "Material negative evidence could strengthen "
            "the opposing interpretation if it persists "
            "or is independently confirmed."
        )

    if supporting:
        changes.append(
            "Additional high-reliability evidence could "
            "strengthen the supporting interpretation."
        )

    if not changes:
        changes.append(
            "Additional validated point-in-time evidence "
            "is required to materially change the thesis."
        )

    return EvidenceNarrative(
        symbol=symbol,
        thesis=_thesis(
            symbol=symbol,
            synthesis=synthesis,
        ),
        supporting_evidence=tuple(
            _label(item)
            for item in supporting
        ),
        contradicting_evidence=tuple(
            _label(item)
            for item in contradicting
        ),
        strongest_evidence=_strongest(evidence),
        uncertainty=tuple(
            dict.fromkeys(uncertainty)
        ),
        key_risks=tuple(
            risks
        ),
        evidence_gaps=tuple(
            gaps
        ),
        what_could_change_thesis=tuple(
            dict.fromkeys(changes)
        ),
    )


__all__ = [
    "build_evidence_narrative",
]
