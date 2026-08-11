from datetime import datetime, timezone

from src.research.context import ResearchContext
from src.research.features.context_adapter import (
    research_context_to_feature_context,
)


AS_OF = datetime(
    2026,
    8,
    10,
    10,
    tzinfo=timezone.utc,
)


def test_research_context_is_converted():
    context = ResearchContext(
        symbol="test",
        timestamp=AS_OF,
        market=(
            {"close": 100},
            {"return_1d": 0.02},
        ),
        fundamentals=(
            {"revenue": 120},
            {"net_profit": 12},
        ),
        source_ids=("Annual Report",),
    )

    result = research_context_to_feature_context(
        context
    )

    assert result.symbol == "TEST"
    assert result.timestamp == AS_OF
    assert result.observations["close"] == 100
    assert result.observations["return_1d"] == 0.02
    assert result.observations["revenue"] == 120
    assert result.observations["net_profit"] == 12
    assert result.source_ids == ("annual report",)


def test_later_groups_override_earlier_keys_deterministically():
    context = ResearchContext(
        symbol="TEST",
        timestamp=AS_OF,
        market=(
            {"value": "market"},
        ),
        fundamentals=(
            {"value": "fundamental"},
        ),
    )

    result = research_context_to_feature_context(
        context
    )

    assert result.observations["value"] == "fundamental"


def test_empty_research_context_produces_empty_observations():
    context = ResearchContext(
        symbol="TEST",
        timestamp=AS_OF,
    )

    result = research_context_to_feature_context(
        context
    )

    assert result.observations == {}
