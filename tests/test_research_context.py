from datetime import datetime, timezone

from src.research.context import ResearchContext


def test_research_context_normalizes_sources():
    context = ResearchContext(
        symbol="AAPL",
        timestamp=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        source_ids=(
            "SEC_EDGAR",
            "fred",
            "SEC_EDGAR",
        ),
    )

    assert context.source_ids == (
        "fred",
        "sec_edgar",
    )


def test_research_context_counts_observations():
    context = ResearchContext(
        symbol="AAPL",
        timestamp=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        market=(1, 2),
        fundamentals=(3,),
        macro=(4, 5),
        events=(6,),
    )

    assert context.observation_count == 6
    assert context.is_empty is False


def test_empty_research_context():
    context = ResearchContext(
        symbol="AAPL",
        timestamp=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
    )

    assert context.observation_count == 0
    assert context.is_empty is True