from __future__ import annotations

from datetime import datetime
from typing import Sequence

from src.backtest.event import ResearchEvent


def get_available_events(
    events: Sequence[ResearchEvent],
    *,
    timestamp: datetime,
    symbol: str | None = None,
) -> tuple[ResearchEvent, ...]:
    """
    Return only research events that were known at timestamp.

    This is the primary point-in-time protection used by the
    historical research pipeline.

    An event is visible only when:

        event.available_at <= timestamp

    If a symbol is supplied, company-specific events are limited
    to that symbol while market-wide events (symbol=None) remain
    available.
    """

    if timestamp.tzinfo is None:
        raise ValueError(
            "timestamp must be timezone-aware"
        )

    available: list[ResearchEvent] = []

    for event in events:
        if event.available_at > timestamp:
            continue

        if symbol is not None:
            if (
                event.symbol is not None
                and event.symbol != symbol
            ):
                continue

        available.append(event)

    return tuple(
        sorted(
            available,
            key=lambda event: (
                event.available_at,
                event.event_id,
            ),
        )
    )


def get_latest_event(
    events: Sequence[ResearchEvent],
    *,
    timestamp: datetime,
    symbol: str | None = None,
) -> ResearchEvent | None:
    """
    Return the most recently available event.

    Future events are never considered.
    """

    available = get_available_events(
        events,
        timestamp=timestamp,
        symbol=symbol,
    )

    if not available:
        return None

    return available[-1]


def get_events_by_type(
    events: Sequence[ResearchEvent],
    *,
    timestamp: datetime,
    event_type: str,
    symbol: str | None = None,
) -> tuple[ResearchEvent, ...]:
    """
    Return available events matching one event type.
    """

    available = get_available_events(
        events,
        timestamp=timestamp,
        symbol=symbol,
    )

    return tuple(
        event
        for event in available
        if event.event_type == event_type
    )


def get_events_by_importance(
    events: Sequence[ResearchEvent],
    *,
    timestamp: datetime,
    minimum_importance: str = "MEDIUM",
    symbol: str | None = None,
) -> tuple[ResearchEvent, ...]:
    """
    Return available events whose importance is at least the
    requested level.
    """

    levels = {
        "LOW": 0,
        "MEDIUM": 1,
        "HIGH": 2,
        "CRITICAL": 3,
    }

    if minimum_importance not in levels:
        raise ValueError(
            "minimum_importance must be LOW, MEDIUM, HIGH, "
            "or CRITICAL"
        )

    minimum_level = levels[minimum_importance]

    available = get_available_events(
        events,
        timestamp=timestamp,
        symbol=symbol,
    )

    return tuple(
        event
        for event in available
        if levels[event.importance] >= minimum_level
    )
