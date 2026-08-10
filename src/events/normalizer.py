from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from src.events.provider import RawEvent


@dataclass(frozen=True)
class NormalizedEvent:
    """
    Canonical event used by the research system.

    available_at is the earliest timestamp at which the research
    system is allowed to know about the event.

    This is critical for preventing look-ahead bias.
    """

    event_id: str
    source: str
    source_url: str

    title: str
    summary: str | None

    event_type: str
    symbols: tuple[str, ...]

    published_at: datetime
    available_at: datetime

    importance: int
    confidence: int

    raw_payload: Any = None

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError(
                "event_id cannot be empty"
            )

        if not self.source.strip():
            raise ValueError(
                "source cannot be empty"
            )

        if not self.source_url.strip():
            raise ValueError(
                "source_url cannot be empty"
            )

        if not self.title.strip():
            raise ValueError(
                "title cannot be empty"
            )

        if self.published_at.tzinfo is None:
            raise ValueError(
                "published_at must be timezone-aware"
            )

        if self.available_at.tzinfo is None:
            raise ValueError(
                "available_at must be timezone-aware"
            )

        if self.available_at < self.published_at:
            raise ValueError(
                "available_at cannot be earlier than published_at"
            )

        if not self.symbols:
            raise ValueError(
                "event must reference at least one symbol"
            )

        if not 0 <= self.importance <= 100:
            raise ValueError(
                "importance must be between 0 and 100"
            )

        if not 0 <= self.confidence <= 100:
            raise ValueError(
                "confidence must be between 0 and 100"
            )


def normalize_event(
    raw: RawEvent,
) -> NormalizedEvent:
    """
    Convert a provider event into the canonical research event.

    No prediction or sentiment interpretation happens here.
    """

    symbols = tuple(
        sorted(
            {
                symbol.strip().upper()
                for symbol in raw.symbols
                if symbol.strip()
            }
        )
    )

    if not symbols:
        raise ValueError(
            "event must contain at least one symbol"
        )

    return NormalizedEvent(
        event_id=raw.event_id.strip(),
        source=raw.source.strip(),
        source_url=raw.source_url.strip(),
        title=raw.title.strip(),
        summary=(
            raw.summary.strip()
            if raw.summary
            else None
        ),
        event_type=raw.event_type.strip().upper(),
        symbols=symbols,
        published_at=raw.published_at,
        available_at=raw.available_at,
        importance=raw.importance,
        confidence=raw.confidence,
        raw_payload=raw.raw_payload,
    )


def normalize_events(
    events: Iterable[RawEvent],
) -> tuple[NormalizedEvent, ...]:
    """
    Normalize and deterministically order provider events.
    """

    normalized = [
        normalize_event(event)
        for event in events
    ]

    normalized.sort(
        key=lambda event: (
            event.available_at,
            event.event_id,
        )
    )

    seen: set[str] = set()

    for event in normalized:
        if event.event_id in seen:
            raise ValueError(
                f"duplicate event_id: {event.event_id}"
            )

        seen.add(event.event_id)

    return tuple(normalized)
