from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.backtest.event import (
    ResearchEvent,
    events_available_at,
)


def make_event(
    *,
    event_id: str = "EVENT-1",
    available_minute: int = 30,
) -> ResearchEvent:
    published = datetime(
        2026,
        1,
        2,
        9,
        0,
        tzinfo=timezone.utc,
    )

    available = datetime(
        2026,
        1,
        2,
        9,
        available_minute,
        tzinfo=timezone.utc,
    )

    return ResearchEvent(
        event_id=event_id,
        symbol="TEST",
        event_type="NEWS",
        title="Test market event",
        summary="Historical research event.",
        source="Test Source",
        source_url="https://example.com/event",
        published_at=published,
        effective_at=None,
        available_at=available,
        sentiment="POSITIVE",
        importance="HIGH",
        confidence=Decimal("90"),
    )


def test_event_accepts_valid_point_in_time_data():
    event = make_event()

    assert event.event_id == "EVENT-1"
    assert event.symbol == "TEST"
    assert event.confidence == Decimal("90")


def test_event_requires_timezone_aware_published_at():
    with pytest.raises(ValueError):
        ResearchEvent(
            event_id="EVENT-1",
            symbol="TEST",
            event_type="NEWS",
            title="Test",
            summary="Test",
            source="Test Source",
            source_url=None,
            published_at=datetime(2026, 1, 2, 9, 0),
            effective_at=None,
            available_at=datetime(
                2026,
                1,
                2,
                9,
                30,
                tzinfo=timezone.utc,
            ),
        )


def test_event_cannot_be_available_before_publication():
    with pytest.raises(ValueError):
        ResearchEvent(
            event_id="EVENT-1",
            symbol="TEST",
            event_type="NEWS",
            title="Test",
            summary="Test",
            source="Test Source",
            source_url=None,
            published_at=datetime(
                2026,
                1,
                2,
                9,
                30,
                tzinfo=timezone.utc,
            ),
            effective_at=None,
            available_at=datetime(
                2026,
                1,
                2,
                9,
                15,
                tzinfo=timezone.utc,
            ),
        )


def test_confidence_must_be_between_zero_and_hundred():
    with pytest.raises(ValueError):
        ResearchEvent(
            event_id="EVENT-2",
            symbol="TEST",
            event_type="NEWS",
            title="Test",
            summary="Test",
            source="Test Source",
            source_url=None,
            published_at=datetime(
                2026,
                1,
                2,
                9,
                0,
                tzinfo=timezone.utc,
            ),
            effective_at=None,
            available_at=datetime(
                2026,
                1,
                2,
                9,
                30,
                tzinfo=timezone.utc,
            ),
            confidence=Decimal("101"),
        )


def test_event_is_unavailable_before_release():
    event = make_event()

    timestamp = datetime(
        2026,
        1,
        2,
        9,
        29,
        tzinfo=timezone.utc,
    )

    assert not event.is_available_at(timestamp)


def test_event_is_available_at_release_time():
    event = make_event()

    timestamp = datetime(
        2026,
        1,
        2,
        9,
        30,
        tzinfo=timezone.utc,
    )

    assert event.is_available_at(timestamp)


def test_future_events_are_excluded():
    events = [
        make_event(
            event_id="EARLY",
            available_minute=15,
        ),
        make_event(
            event_id="LATE",
            available_minute=45,
        ),
    ]

    timestamp = datetime(
        2026,
        1,
        2,
        9,
        30,
        tzinfo=timezone.utc,
    )

    available = events_available_at(
        events,
        timestamp,
    )

    assert [event.event_id for event in available] == [
        "EARLY"
    ]


def test_events_are_returned_in_availability_order():
    events = [
        make_event(
            event_id="LATE",
            available_minute=45,
        ),
        make_event(
            event_id="EARLY",
            available_minute=15,
        ),
    ]

    timestamp = datetime(
        2026,
        1,
        2,
        10,
        0,
        tzinfo=timezone.utc,
    )

    available = events_available_at(
        events,
        timestamp,
    )

    assert [event.event_id for event in available] == [
        "EARLY",
        "LATE",
    ]


def test_naive_lookup_timestamp_is_rejected():
    event = make_event()

    with pytest.raises(ValueError):
        event.is_available_at(
            datetime(2026, 1, 2, 9, 30)
        )
