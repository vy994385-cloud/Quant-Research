from datetime import datetime, timezone

import pytest

from src.research.acquisition.models import (
    ResearchCategory,
    ResearchQuestion,
    SourceCandidate,
)
from src.research.acquisition.providers import ResearchSourceProvider


class ExampleProvider(ResearchSourceProvider):
    def search(
        self,
        company: str,
        question: ResearchQuestion,
        as_of: datetime,
    ) -> list[SourceCandidate]:
        return [
            SourceCandidate(
                source_id="source-1",
                source_name="Example Source",
                source_type="REGULATORY",
                url="https://example.com/source-1",
                title="Example filing",
                reliability_tier=1,
            )
        ]


def make_question() -> ResearchQuestion:
    return ResearchQuestion(
        question_id="ai-technology",
        category=ResearchCategory.AI_TECHNOLOGY,
        question="What evidence exists of AI adoption?",
        priority=1,
    )


def test_provider_returns_source_candidates():
    provider = ExampleProvider()

    results = provider.search(
        "TCS",
        make_question(),
        datetime(
            2026,
            8,
            15,
            12,
            tzinfo=timezone.utc,
        ),
    )

    assert len(results) == 1
    assert results[0].source_id == "source-1"


def test_provider_contract_is_abstract():
    with pytest.raises(TypeError):
        ResearchSourceProvider()
