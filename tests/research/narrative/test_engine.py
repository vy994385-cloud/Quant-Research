from datetime import datetime, timezone
from decimal import Decimal

from src.research.narrative.engine import (
    build_evidence_narrative,
)
from src.research.synthesis.models import (
    EvidenceDirection,
    EvidenceItem,
    EvidenceReliability,
    EvidenceSynthesis,
    EvidenceType,
)


AS_OF = datetime(
    2026,
    8,
    10,
    12,
    0,
    tzinfo=timezone.utc,
)


def evidence(
    evidence_id: str,
    direction: EvidenceDirection,
    *,
    confidence: str = "0.80",
    reliability: EvidenceReliability = (
        EvidenceReliability.PRIMARY
    ),
    observation_at: datetime = AS_OF,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        symbol="TEST",
        evidence_type=EvidenceType.FEATURE,
        title=f"Title {evidence_id}",
        explanation=f"Explanation {evidence_id}",
        direction=direction,
        confidence=Decimal(confidence),
        reliability=reliability,
        observation_at=observation_at,
    )


def synthesis(
    evidence_items: list[EvidenceItem],
    *,
    direction: EvidenceDirection,
    conflict: bool = False,
) -> EvidenceSynthesis:
    positive = sum(
        item.direction == EvidenceDirection.POSITIVE
        for item in evidence_items
    )

    negative = sum(
        item.direction == EvidenceDirection.NEGATIVE
        for item in evidence_items
    )

    neutral = sum(
        item.direction == EvidenceDirection.NEUTRAL
        for item in evidence_items
    )

    return EvidenceSynthesis(
        symbol="TEST",
        as_of=AS_OF,
        evidence=tuple(evidence_items),
        positive_count=positive,
        negative_count=negative,
        neutral_count=neutral,
        positive_weight=Decimal("0.80"),
        negative_weight=Decimal("0.80"),
        average_confidence=Decimal("0.80"),
        weighted_confidence=Decimal("0.80"),
        conflict_detected=conflict,
        direction=direction,
    )


def test_positive_narrative():
    item = evidence(
        "POSITIVE",
        EvidenceDirection.POSITIVE,
    )

    narrative = build_evidence_narrative(
        synthesis(
            [item],
            direction=EvidenceDirection.POSITIVE,
        )
    )

    assert narrative.symbol == "TEST"
    assert "positive evidence" in narrative.thesis
    assert len(narrative.supporting_evidence) == 1
    assert narrative.contradicting_evidence == ()
    assert narrative.strongest_evidence


def test_mixed_narrative_preserves_conflict():
    items = [
        evidence(
            "POSITIVE",
            EvidenceDirection.POSITIVE,
        ),
        evidence(
            "NEGATIVE",
            EvidenceDirection.NEGATIVE,
        ),
    ]

    narrative = build_evidence_narrative(
        synthesis(
            items,
            direction=EvidenceDirection.MIXED,
            conflict=True,
        )
    )

    assert "mixed evidence" in narrative.thesis
    assert len(narrative.supporting_evidence) == 1
    assert len(narrative.contradicting_evidence) == 1
    assert narrative.has_conflict is True
    assert narrative.key_risks


def test_future_evidence_is_excluded():
    future = datetime(
        2026,
        8,
        11,
        12,
        0,
        tzinfo=timezone.utc,
    )

    item = evidence(
        "FUTURE",
        EvidenceDirection.POSITIVE,
        observation_at=future,
    )

    narrative = build_evidence_narrative(
        synthesis(
            [item],
            direction=EvidenceDirection.POSITIVE,
        )
    )

    assert narrative.supporting_evidence == ()
    assert narrative.evidence_gaps


def test_low_quality_evidence_creates_uncertainty():
    item = evidence(
        "LOW",
        EvidenceDirection.POSITIVE,
        confidence="0.30",
        reliability=EvidenceReliability.UNKNOWN,
    )

    narrative = build_evidence_narrative(
        synthesis(
            [item],
            direction=EvidenceDirection.POSITIVE,
        )
    )

    assert narrative.uncertainty
