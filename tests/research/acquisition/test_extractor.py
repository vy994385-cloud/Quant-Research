from datetime import datetime, timezone

import pytest

from src.research.acquisition.extractor import ObservationExtractor
from src.research.acquisition.models import (
    ResearchCategory,
    ResearchQuestion,
    SourceCandidate,
)


AS_OF = datetime(
    2026,
    8,
    15,
    12,
    tzinfo=timezone.utc,
)


def make_question() -> ResearchQuestion:
    return ResearchQuestion(
        question_id="ai-technology",
        category=ResearchCategory.AI_TECHNOLOGY,
        question="What evidence exists of AI adoption?",
        priority=1,
    )


def make_source() -> SourceCandidate:
    return SourceCandidate(
        source_id="source-1",
        source_name="Example Source",
        source_type="REGULATORY",
        url="https://example.com/source-1",
        title="Example filing",
        available_at=datetime(
            2026,
            8,
            10,
            12,
            tzinfo=timezone.utc,
        ),
        reliability_tier=1,
    )


def test_extractor_creates_observation():
    extractor = ObservationExtractor()

    observation = extractor.extract(
        company="TCS",
        question=make_question(),
        source=make_source(),
        claim="TCS announced an AI initiative.",
        evidence_excerpt="Example evidence.",
        extracted_at=AS_OF,
        confidence=0.9,
    )

    assert observation.company == "TCS"
    assert observation.category == ResearchCategory.AI_TECHNOLOGY
    assert observation.source_id == "source-1"
    assert observation.confidence == 0.9
    assert observation.available_at == make_source().available_at


def test_extractor_generates_stable_observation_id():
    extractor = ObservationExtractor()

    observation = extractor.extract(
        company="TCS",
        question=make_question(),
        source=make_source(),
        claim="TCS announced an AI initiative.",
        evidence_excerpt="Example evidence.",
        extracted_at=AS_OF,
        confidence=0.9,
    )

    assert observation.observation_id == (
        "TCS:ai-technology:source-1"
    )


def test_extractor_rejects_empty_company():
    extractor = ObservationExtractor()

    with pytest.raises(
        ValueError,
        match="company must not be empty",
    ):
        extractor.extract(
            company="   ",
            question=make_question(),
            source=make_source(),
            claim="Valid claim.",
            evidence_excerpt="Evidence.",
            extracted_at=AS_OF,
            confidence=0.9,
        )


def test_extractor_rejects_empty_claim():
    extractor = ObservationExtractor()

    with pytest.raises(
        ValueError,
        match="claim must not be empty",
    ):
        extractor.extract(
            company="TCS",
            question=make_question(),
            source=make_source(),
            claim="   ",
            evidence_excerpt="Evidence.",
            extracted_at=AS_OF,
            confidence=0.9,
        )


def test_extractor_rejects_empty_excerpt():
    extractor = ObservationExtractor()

    with pytest.raises(
        ValueError,
        match="evidence_excerpt must not be empty",
    ):
        extractor.extract(
            company="TCS",
            question=make_question(),
            source=make_source(),
            claim="Valid claim.",
            evidence_excerpt="   ",
            extracted_at=AS_OF,
            confidence=0.9,
        )


def test_extractor_rejects_naive_extracted_at():
    extractor = ObservationExtractor()

    with pytest.raises(
        ValueError,
        match="extracted_at must be timezone-aware",
    ):
        extractor.extract(
            company="TCS",
            question=make_question(),
            source=make_source(),
            claim="Valid claim.",
            evidence_excerpt="Evidence.",
            extracted_at=datetime(
                2026,
                8,
                15,
                12,
            ),
            confidence=0.9,
        )
