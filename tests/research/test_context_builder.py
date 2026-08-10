from datetime import datetime, timezone

import pytest

from src.research.context_builder import (
    ContextObservation,
    ResearchContextBuilder,
)
from src.research.provenance import DataProvenance


AS_OF = datetime(
    2026,
    8,
    10,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_provenance(
    *,
    source: str = "primary",
    available_at=AS_OF,
    record_id: str = "record-1",
):
    return DataProvenance(
        source=source,
        source_url=None,
        retrieved_at=datetime(
            2026,
            8,
            10,
            13,
            0,
            tzinfo=timezone.utc,
        ),
        published_at=datetime(
            2026,
            8,
            10,
            11,
            0,
            tzinfo=timezone.utc,
        ),
        available_at=available_at,
        record_id=record_id,
    )


def test_only_point_in_time_known_observations_enter_context():
    observations = [
        ContextObservation(
            value={"price": 100},
            provenance=make_provenance(
                record_id="known",
            ),
            domain="market",
            observation_id="known",
        ),
        ContextObservation(
            value={"price": 999},
            provenance=make_provenance(
                available_at=datetime(
                    2026,
                    8,
                    10,
                    13,
                    0,
                    tzinfo=timezone.utc,
                ),
                record_id="future",
            ),
            domain="market",
            observation_id="future",
        ),
    ]

    result = ResearchContextBuilder().build(
        symbol="TEST",
        as_of=AS_OF,
        observations=observations,
    )

    assert result.context.market == (
        {"price": 100},
    )
    assert result.accepted_count == 1
    assert result.rejected_count == 1
    assert result.rejected_not_known_at == 1


def test_missing_available_at_is_rejected():
    observation = ContextObservation(
        value={"eps": 5},
        provenance=make_provenance(
            available_at=None,
        ),
        domain="fundamentals",
    )

    result = ResearchContextBuilder().build(
        symbol="TEST",
        as_of=AS_OF,
        observations=[observation],
    )

    assert result.context.is_empty
    assert result.accepted_count == 0
    assert result.rejected_count == 1
    assert result.rejected_missing_availability == 1


def test_sources_are_normalized_and_deduplicated():
    observations = [
        ContextObservation(
            value=1,
            provenance=make_provenance(
                source=" SEC_EDGAR ",
                record_id="a",
            ),
            domain="fundamentals",
            observation_id="a",
        ),
        ContextObservation(
            value=2,
            provenance=make_provenance(
                source="sec_edgar",
                record_id="b",
            ),
            domain="fundamentals",
            observation_id="b",
        ),
    ]

    result = ResearchContextBuilder().build(
        symbol="TEST",
        as_of=AS_OF,
        observations=observations,
    )

    assert result.context.source_ids == (
        "sec_edgar",
    )


def test_context_order_is_deterministic():
    first = ContextObservation(
        value="first",
        provenance=make_provenance(record_id="b"),
        domain="market",
        observation_id="b",
    )

    second = ContextObservation(
        value="second",
        provenance=make_provenance(record_id="a"),
        domain="market",
        observation_id="a",
    )

    builder = ResearchContextBuilder()

    result_a = builder.build(
        symbol="TEST",
        as_of=AS_OF,
        observations=[first, second],
    )

    result_b = builder.build(
        symbol="TEST",
        as_of=AS_OF,
        observations=[second, first],
    )

    assert result_a.context == result_b.context


def test_naive_as_of_is_rejected():
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        ResearchContextBuilder().build(
            symbol="TEST",
            as_of=datetime(
                2026,
                8,
                10,
                12,
            ),
            observations=[],
        )


def test_empty_symbol_is_rejected():
    with pytest.raises(
        ValueError,
        match="symbol cannot be empty",
    ):
        ResearchContextBuilder().build(
            symbol="   ",
            as_of=AS_OF,
            observations=[],
        )


def test_unknown_domain_is_rejected():
    observation = ContextObservation(
        value=1,
        provenance=make_provenance(),
        domain="sentiment_score",
    )

    with pytest.raises(
        ValueError,
        match="unsupported research domain",
    ):
        ResearchContextBuilder().build(
            symbol="TEST",
            as_of=AS_OF,
            observations=[observation],
        )


def test_rejected_future_data_never_enters_any_context_bucket():
    future = ContextObservation(
        value={
            "management_change": "future_event"
        },
        provenance=make_provenance(
            available_at=datetime(
                2026,
                8,
                11,
                0,
                0,
                tzinfo=timezone.utc,
            ),
        ),
        domain="events",
    )

    result = ResearchContextBuilder().build(
        symbol="TEST",
        as_of=AS_OF,
        observations=[future],
    )

    assert result.context.events == ()
    assert result.context.observation_count == 0
    assert result.rejected_count == 1
