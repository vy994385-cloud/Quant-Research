from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.research.acquisition.evidence import (
    observation_to_evidence_item,
    research_observations_to_evidence,
)
from src.research.acquisition.models import (
    ResearchCategory,
    ResearchObservation,
)
from src.research.synthesis.models import (
    EvidenceDirection,
    EvidenceReliability,
    EvidenceType,
)


AS_OF = datetime(
    2026,
    8,
    15,
    12,
    tzinfo=timezone.utc,
)

AVAILABLE_AT = datetime(
    2026,
    8,
    10,
    12,
    tzinfo=timezone.utc,
)


def make_observation(
    *,
    observation_id: str = "TCS:ai-technology:source-1",
    company: str = "TCS",
    claim: str = "Company announced an AI initiative.",
    excerpt: str = "Example evidence excerpt.",
    source_id: str = "source-1",
    reliability_tier: int | None = 1,
    available_at: datetime | None = AVAILABLE_AT,
) -> ResearchObservation:
    return ResearchObservation(
        observation_id=observation_id,
        company=company,
        category=ResearchCategory.AI_TECHNOLOGY,
        claim=claim,
        evidence_excerpt=excerpt,
        source_id=source_id,
        reliability_tier=reliability_tier,
        available_at=available_at,
        extracted_at=AS_OF,
        confidence=0.9,
    )


def test_observation_becomes_neutral_acquired_evidence():
    item = observation_to_evidence_item(
        make_observation(),
        as_of=AS_OF,
    )

    assert item is not None
    assert item.evidence_id == (
        "ACQUIRED:TCS:ai-technology:source-1"
    )
    assert item.symbol == "TCS"
    assert item.evidence_type == EvidenceType.ACQUIRED
    assert item.direction == EvidenceDirection.NEUTRAL
    assert item.title == "Company announced an AI initiative."
    assert item.explanation == "Example evidence excerpt."
    assert item.confidence == Decimal("0.9")
    assert item.observation_at == AVAILABLE_AT
    assert item.source_ids == ("source-1",)
    assert item.provenance_ids == ()


def test_future_available_at_never_becomes_evidence():
    item = observation_to_evidence_item(
        make_observation(
            available_at=datetime(
                2026,
                8,
                20,
                12,
                tzinfo=timezone.utc,
            )
        ),
        as_of=AS_OF,
    )

    assert item is None


def test_missing_available_at_never_becomes_evidence():
    item = observation_to_evidence_item(
        make_observation(available_at=None),
        as_of=AS_OF,
    )

    assert item is None


def test_naive_available_at_never_becomes_evidence():
    item = observation_to_evidence_item(
        make_observation(
            available_at=datetime(
                2026,
                8,
                10,
                12,
            )
        ),
        as_of=AS_OF,
    )

    assert item is None


def test_naive_as_of_is_rejected():
    with pytest.raises(
        ValueError,
        match="as_of must be timezone-aware",
    ):
        observation_to_evidence_item(
            make_observation(),
            as_of=datetime(2026, 8, 15, 12),
        )


def test_reliability_tier_is_mapped_conservatively():
    assert observation_to_evidence_item(
        make_observation(reliability_tier=1),
        as_of=AS_OF,
    ).reliability == EvidenceReliability.PRIMARY

    assert observation_to_evidence_item(
        make_observation(reliability_tier=3),
        as_of=AS_OF,
    ).reliability == EvidenceReliability.SECONDARY

    assert observation_to_evidence_item(
        make_observation(reliability_tier=4),
        as_of=AS_OF,
    ).reliability == EvidenceReliability.TERTIARY

    assert observation_to_evidence_item(
        make_observation(reliability_tier=None),
        as_of=AS_OF,
    ).reliability == EvidenceReliability.UNKNOWN


def test_evidence_uses_availability_timing_not_extraction_timing():
    item = observation_to_evidence_item(
        make_observation(),
        as_of=AS_OF,
    )

    assert item is not None
    assert item.observation_at == AVAILABLE_AT
    assert item.observation_at <= AS_OF


def test_batch_filters_other_symbols():
    items = research_observations_to_evidence(
        [
            make_observation(),
            make_observation(
                observation_id="INFY:ai-technology:source-9",
                company="INFY",
                source_id="source-9",
            ),
        ],
        symbol="TCS",
        as_of=AS_OF,
    )

    assert [item.symbol for item in items] == ["TCS"]


def test_batch_excludes_future_evidence():
    items = research_observations_to_evidence(
        [
            make_observation(),
            make_observation(
                observation_id="TCS:ai-technology:source-2",
                source_id="source-2",
                available_at=datetime(
                    2026,
                    8,
                    20,
                    12,
                    tzinfo=timezone.utc,
                ),
            ),
        ],
        symbol="TCS",
        as_of=AS_OF,
    )

    assert [item.evidence_id for item in items] == [
        "ACQUIRED:TCS:ai-technology:source-1"
    ]


def test_batch_deduplicates_identical_observation_ids():
    items = research_observations_to_evidence(
        [
            make_observation(),
            make_observation(
                observation_id="TCS:ai-technology:source-1",
            ),
            make_observation(
                observation_id="TCS:ai-technology:source-2",
                source_id="source-2",
            ),
        ],
        symbol="TCS",
        as_of=AS_OF,
    )

    assert [item.evidence_id for item in items] == [
        "ACQUIRED:TCS:ai-technology:source-1",
        "ACQUIRED:TCS:ai-technology:source-2",
    ]


def test_batch_is_deterministic():
    observations = [
        make_observation(
            observation_id="TCS:ai-technology:source-b",
            source_id="source-b",
        ),
        make_observation(
            observation_id="TCS:ai-technology:source-a",
            source_id="source-a",
        ),
    ]

    first = research_observations_to_evidence(
        observations,
        symbol="TCS",
        as_of=AS_OF,
    )

    second = research_observations_to_evidence(
        list(reversed(observations)),
        symbol="TCS",
        as_of=AS_OF,
    )

    assert first == second
    assert [item.evidence_id for item in first] == [
        "ACQUIRED:TCS:ai-technology:source-a",
        "ACQUIRED:TCS:ai-technology:source-b",
    ]


def test_batch_rejects_empty_symbol():
    with pytest.raises(
        ValueError,
        match="symbol cannot be empty",
    ):
        research_observations_to_evidence(
            [],
            symbol="   ",
            as_of=AS_OF,
        )
