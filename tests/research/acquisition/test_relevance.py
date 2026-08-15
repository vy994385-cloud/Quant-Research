from datetime import datetime, timezone

from src.research.acquisition.models import (
    ResearchCategory,
    ResearchQuestion,
    SourceCandidate,
)
from src.research.acquisition.relevance import (
    SourceRelevanceRouter,
)


def make_question():
    return ResearchQuestion(
        question_id="q-ai",
        category=ResearchCategory.AI_TECHNOLOGY,
        question="What evidence exists regarding AI and technology?",
        priority=1,
    )


def make_source(
    source_id="source-1",
    title="AI technology transformation",
):
    return SourceCandidate(
        source_id=source_id,
        source_name="Example Source",
        source_type="NEWS",
        url="https://example.com",
        title=title,
        available_at=datetime(
            2026,
            8,
            10,
            12,
            tzinfo=timezone.utc,
        ),
        reliability_tier=1,
    )


def test_relevant_source_is_accepted():
    router = SourceRelevanceRouter()

    assert router.is_relevant(
        make_question(),
        make_source(),
    )


def test_unrelated_source_is_rejected():
    router = SourceRelevanceRouter()

    source = make_source(
        title="Historical dividend announcement"
    )

    assert not router.is_relevant(
        make_question(),
        source,
    )


def test_filter_deduplicates_sources():
    router = SourceRelevanceRouter()

    sources = [
        make_source(),
        make_source(),
        make_source(
            source_id="source-2",
            title="Cloud technology contract",
        ),
    ]

    accepted = router.filter(
        make_question(),
        sources,
    )

    assert [
        source.source_id
        for source in accepted
    ] == [
        "source-1",
        "source-2",
    ]
