from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.research.acquisition.models import (
    ResearchCategory,
    ResearchObservation,
    ResearchQuestion,
    SourceCandidate,
)


def test_research_question_requires_valid_priority():
    question = ResearchQuestion(
        question_id="q1",
        category=ResearchCategory.AI_TECHNOLOGY,
        question="What meaningful AI exposure does the company have?",
        priority=1,
    )

    assert question.category == ResearchCategory.AI_TECHNOLOGY


def test_source_candidate_requires_reliability_tier():
    source = SourceCandidate(
        source_id="source-1",
        source_name="Example Source",
        source_type="REGULATORY",
        url="https://example.com/source",
        title="Example filing",
        reliability_tier=1,
    )

    assert source.reliability_tier == 1


def test_observation_rejects_empty_claim():
    with pytest.raises(ValidationError):
        ResearchObservation(
            observation_id="obs-1",
            company="TCS",
            category=ResearchCategory.INNOVATION,
            claim="",
            evidence_excerpt="Evidence",
            source_id="source-1",
            extracted_at=datetime.now(timezone.utc),
            confidence=0.9,
        )


def test_observation_is_known_at_requires_available_at():
    observation = ResearchObservation(
        observation_id="obs-1",
        company="TCS",
        category=ResearchCategory.AI_TECHNOLOGY,
        claim="Company announced an AI initiative.",
        evidence_excerpt="Example evidence.",
        source_id="source-1",
        extracted_at=datetime.now(timezone.utc),
        confidence=0.9,
    )

    assert not observation.is_known_at(
        datetime(2026, 8, 15, 12, tzinfo=timezone.utc)
    )


def test_observation_is_known_at_uses_availability_time():
    observation = ResearchObservation(
        observation_id="obs-1",
        company="TCS",
        category=ResearchCategory.AI_TECHNOLOGY,
        claim="Company announced an AI initiative.",
        evidence_excerpt="Example evidence.",
        source_id="source-1",
        available_at=datetime(
            2026, 8, 10, 12, tzinfo=timezone.utc
        ),
        extracted_at=datetime.now(timezone.utc),
        confidence=0.9,
    )

    assert observation.is_known_at(
        datetime(2026, 8, 15, 12, tzinfo=timezone.utc)
    )

    assert not observation.is_known_at(
        datetime(2026, 8, 9, 12, tzinfo=timezone.utc)
    )


def test_observation_rejects_naive_as_of():
    observation = ResearchObservation(
        observation_id="obs-1",
        company="TCS",
        category=ResearchCategory.AI_TECHNOLOGY,
        claim="Company announced an AI initiative.",
        evidence_excerpt="Example evidence.",
        source_id="source-1",
        available_at=datetime(
            2026, 8, 10, 12, tzinfo=timezone.utc
        ),
        extracted_at=datetime.now(timezone.utc),
        confidence=0.9,
    )

    with pytest.raises(
        ValueError,
        match="as_of must be timezone-aware",
    ):
        observation.is_known_at(datetime(2026, 8, 15, 12))
