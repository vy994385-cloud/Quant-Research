from datetime import datetime, timezone

import pytest

from src.events.provider import RawEvent
from src.events.registry import EventProviderRegistry


class FakeProvider:
    name = "FakeNews"

    def fetch(
        self,
        *,
        symbols,
        start,
        end,
    ):
        return [
            RawEvent(
                event_id="fake-1",
                source="FakeNews",
                source_url="https://example.com/fake-1",
                title="Example headline",
                published_at=start,
                available_at=start,
                symbols=("AAPL",),
                event_type="NEWS",
                importance=70,
                confidence=90,
            )
        ]


class AnotherProvider:
    name = "Macro"

    def fetch(
        self,
        *,
        symbols,
        start,
        end,
    ):
        return [
            RawEvent(
                event_id="macro-1",
                source="Macro",
                source_url="https://example.com/macro-1",
                title="Rate decision",
                published_at=start,
                available_at=start,
                symbols=("AAPL",),
                event_type="MACRO",
                importance=90,
                confidence=95,
            )
        ]


def make_period():
    return (
        datetime(
            2026, 1, 1, tzinfo=timezone.utc
        ),
        datetime(
            2026, 1, 2, tzinfo=timezone.utc
        ),
    )


def test_registry_registers_provider():
    registry = EventProviderRegistry()

    registry.register(FakeProvider())

    assert registry.names == ("fakenews",)


def test_registry_rejects_duplicate_provider():
    registry = EventProviderRegistry()

    registry.register(FakeProvider())

    with pytest.raises(ValueError):
        registry.register(FakeProvider())


def test_registry_fetches_and_normalizes_events():
    registry = EventProviderRegistry()
    registry.register(FakeProvider())

    start, end = make_period()

    events = registry.fetch(
        symbols=("AAPL",),
        start=start,
        end=end,
    )

    assert len(events) == 1
    assert events[0].source == "FakeNews"
    assert events[0].source_url == (
        "https://example.com/fake-1"
    )


def test_registry_can_combine_multiple_providers():
    registry = EventProviderRegistry()

    registry.register(FakeProvider())
    registry.register(AnotherProvider())

    start, end = make_period()

    events = registry.fetch(
        symbols=("AAPL",),
        start=start,
        end=end,
    )

    assert len(events) == 2
    assert {
        event.event_type
        for event in events
    } == {"NEWS", "MACRO"}


def test_registry_can_select_provider():
    registry = EventProviderRegistry()

    registry.register(FakeProvider())
    registry.register(AnotherProvider())

    start, end = make_period()

    events = registry.fetch(
        symbols=("AAPL",),
        start=start,
        end=end,
        providers=("macro",),
    )

    assert len(events) == 1
    assert events[0].event_type == "MACRO"


def test_unknown_provider_is_rejected():
    registry = EventProviderRegistry()

    start, end = make_period()

    with pytest.raises(KeyError):
        registry.fetch(
            symbols=("AAPL",),
            start=start,
            end=end,
            providers=("unknown",),
        )
