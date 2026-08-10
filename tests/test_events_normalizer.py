from datetime import datetime, timezone

import pytest

from src.events.normalizer import (
    normalize_event,
    normalize_events,
)
from src.events.provider import RawEvent


def make_event(
    event_id: str,
    available_hour: int,
    *,
    symbols=("aapl",),
):
    published = datetime(
        2026, 1, 1, 9, tzinfo=timezone.utc
    )

    return RawEvent(
        event_id=event_id,
        source="Example News",
        source_url=f"https://example.com/{event_id}",
        title=" Example headline ",
        summary=" Example summary ",
        event_type="news",
        symbols=symbols,
        published_at=published,
        available_at=datetime(
            2026,
            1,
            1,
            available_hour,
            tzinfo=timezone.utc,
        ),
        importance=80,
        confidence=90,
    )


def test_normalizer_canonicalizes_event():
    event = normalize_event(
        make_event("event-1", 10)
    )

    assert event.event_id == "event-1"
    assert event.source == "Example News"
    assert event.source_url == (
        "https://example.com/event-1"
    )
    assert event.title == "Example headline"
    assert event.event_type == "NEWS"
    assert event.symbols == ("AAPL",)


def test_normalizer_requires_source_url():
    raw = make_event("event-1", 10)

    raw = RawEvent(
        event_id=raw.event_id,
        source=raw.source,
        source_url="",
        title=raw.title,
        published_at=raw.published_at,
        available_at=raw.available_at,
        symbols=raw.symbols,
    )

    with pytest.raises(ValueError):
        normalize_event(raw)


def test_available_time_cannot_precede_publication():
    published = datetime(
        2026, 1, 1, 10, tzinfo=timezone.utc
    )

    raw = RawEvent(
        event_id="event-1",
        source="Example",
        source_url="https://example.com/1",
        title="Headline",
        published_at=published,
        available_at=datetime(
            2026, 1, 1, 9, tzinfo=timezone.utc
        ),
        symbols=("AAPL",),
    )

    with pytest.raises(ValueError):
        normalize_event(raw)


def test_events_are_sorted_by_available_time():
    events = normalize_events(
        [
            make_event("late", 12),
            make_event("early", 10),
        ]
    )

    assert [
        event.event_id
        for event in events
    ] == ["early", "late"]


def test_duplicate_event_ids_are_rejected():
    with pytest.raises(ValueError):
        normalize_events(
            [
                make_event("same", 10),
                make_event("same", 11),
            ]
        )


def test_multiple_symbols_are_normalized():
    event = normalize_event(
        make_event(
            "event-1",
            10,
            symbols=("msft", " aapl ", "MSFT"),
        )
    )

    assert event.symbols == ("AAPL", "MSFT")
