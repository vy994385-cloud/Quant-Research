from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.backtest.event import ResearchEvent
from src.backtest.event_context import (
    get_available_events,
    get_events_by_importance,
    get_events_by_type,
    get_latest_event,
)


BASE_TIME = datetime(
    2026,
    1,
    2,
    9,
    0,
    tzinfo=timezone.utc,
)


def make_event(
    event_id: str,
    *,
    minute: int,
    symbol: str | None = "TEST",
    event_type: str = "NEWS",
    importance: str = "MEDIUM",
) -> ResearchEvent:
    return ResearchEvent(
        event_id=event_id,
        symbol=symbol,
        event_type=event_type,
        title=f"Event {event_id}",
        summary="Historical research event.",
        source="Test Source",
        source_url=None,
        published_at=BASE_TIME,
        effective_at=None,
        available_at=BASE_TIME.replace(
            minute=minute
        ),
        importance=importance,
        confidence=Decimal("90"),
    )


def test_future_events_are_hidden():
    events = [
        make_event("EARLY", minute=15),
        make_event("FUTURE", minute=45),
    ]

    result = get_available_events(
        events,
        timestamp=BASE_TIME.replace(minute=30),
        symbol="TEST",
    )

    assert [event.event_id for event in result] == [
        "EARLY"
    ]


def test_events_at_exact_timestamp_are_visible():
    event = make_event("CURRENT", minute=30)

    result = get_available_events(
        [event],
        timestamp=BASE_TIME.replace(minute=30),
        symbol="TEST",
    )

    assert len(result) == 1
    assert result[0].event_id == "CURRENT"


def test_market_wide_events_are_visible_for_company():
    events = [
        make_event(
            "MARKET",
            minute=10,
            symbol=None,
            event_type="MACRO",
        ),
        make_event(
            "COMPANY",
            minute=20,
            symbol="TEST",
        ),
    ]

    result = get_available_events(
        events,
        timestamp=BASE_TIME.replace(minute=30),
        symbol="TEST",
    )

    assert [event.event_id for event in result] == [
        "MARKET",
        "COMPANY",
    ]


def test_other_company_events_are_hidden():
    events = [
        make_event(
            "TEST-EVENT",
            minute=10,
            symbol="TEST",
        ),
        make_event(
            "OTHER-EVENT",
            minute=20,
            symbol="OTHER",
        ),
    ]

    result = get_available_events(
        events,
        timestamp=BASE_TIME.replace(minute=30),
        symbol="TEST",
    )

    assert [event.event_id for event in result] == [
        "TEST-EVENT"
    ]


def test_events_are_sorted_by_availability_time():
    events = [
        make_event("LATE", minute=30),
        make_event("EARLY", minute=10),
        make_event("MIDDLE", minute=20),
    ]

    result = get_available_events(
        events,
        timestamp=BASE_TIME.replace(minute=40),
        symbol="TEST",
    )

    assert [event.event_id for event in result] == [
        "EARLY",
        "MIDDLE",
        "LATE",
    ]


def test_latest_event_returns_most_recent_visible_event():
    events = [
        make_event("EARLY", minute=10),
        make_event("LATEST", minute=25),
        make_event("FUTURE", minute=45),
    ]

    result = get_latest_event(
        events,
        timestamp=BASE_TIME.replace(minute=30),
        symbol="TEST",
    )

    assert result is not None
    assert result.event_id == "LATEST"


def test_latest_event_returns_none_when_no_event_is_available():
    event = make_event("FUTURE", minute=45)

    result = get_latest_event(
        [event],
        timestamp=BASE_TIME.replace(minute=30),
        symbol="TEST",
    )

    assert result is None


def test_events_can_be_filtered_by_type():
    events = [
        make_event(
            "NEWS",
            minute=10,
            event_type="NEWS",
        ),
        make_event(
            "EARNINGS",
            minute=20,
            event_type="EARNINGS",
        ),
        make_event(
            "MACRO",
            minute=30,
            event_type="MACRO",
        ),
    ]

    result = get_events_by_type(
        events,
        timestamp=BASE_TIME.replace(minute=40),
        event_type="EARNINGS",
        symbol="TEST",
    )

    assert [event.event_id for event in result] == [
        "EARNINGS"
    ]


def test_events_can_be_filtered_by_importance():
    events = [
        make_event(
            "LOW",
            minute=10,
            importance="LOW",
        ),
        make_event(
            "HIGH",
            minute=20,
            importance="HIGH",
        ),
        make_event(
            "CRITICAL",
            minute=30,
            importance="CRITICAL",
        ),
    ]

    result = get_events_by_importance(
        events,
        timestamp=BASE_TIME.replace(minute=40),
        minimum_importance="HIGH",
        symbol="TEST",
    )

    assert [event.event_id for event in result] == [
        "HIGH",
        "CRITICAL",
    ]


def test_invalid_importance_filter_is_rejected():
    with pytest.raises(ValueError):
        get_events_by_importance(
            [],
            timestamp=BASE_TIME,
            minimum_importance="INVALID",
        )


def test_naive_timestamp_is_rejected():
    with pytest.raises(ValueError):
        get_available_events(
            [],
            timestamp=datetime(2026, 1, 2, 9, 0),
            symbol="TEST",
        )
