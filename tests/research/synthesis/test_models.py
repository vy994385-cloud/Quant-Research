from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.research.synthesis.models import (
    EvidenceDirection,
    EvidenceItem,
    EvidenceType,
)


def test_evidence_item_normalizes_symbol():
    item = EvidenceItem(
        evidence_id="E1",
        symbol="  reliance  ",
        evidence_type=EvidenceType.FEATURE,
        title="Revenue growth",
        explanation="Revenue increased.",
        direction=EvidenceDirection.POSITIVE,
        confidence=Decimal("0.90"),
        observation_at=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
    )

    assert item.symbol == "RELIANCE"


def test_observation_requires_timezone():
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="E1",
            symbol="RELIANCE",
            evidence_type=EvidenceType.FEATURE,
            title="Revenue growth",
            explanation="Revenue increased.",
            direction=EvidenceDirection.POSITIVE,
            confidence=Decimal("0.90"),
            observation_at=datetime(2026, 1, 1),
        )


def test_confidence_must_be_between_zero_and_one():
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="E1",
            symbol="RELIANCE",
            evidence_type=EvidenceType.FEATURE,
            title="Revenue growth",
            explanation="Revenue increased.",
            direction=EvidenceDirection.POSITIVE,
            confidence=Decimal("1.10"),
            observation_at=datetime(
                2026,
                1,
                1,
                tzinfo=timezone.utc,
            ),
        )


def test_empty_reference_is_rejected():
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="E1",
            symbol="RELIANCE",
            evidence_type=EvidenceType.FEATURE,
            title="Revenue growth",
            explanation="Revenue increased.",
            direction=EvidenceDirection.POSITIVE,
            confidence=Decimal("0.90"),
            observation_at=datetime(
                2026,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            source_ids=("",),
        )
