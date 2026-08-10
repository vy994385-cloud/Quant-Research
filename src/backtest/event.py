from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal


EventType = Literal[
    "NEWS",
    "EARNINGS",
    "GUIDANCE",
    "REGULATORY",
    "CORPORATE_ACTION",
    "MACRO",
    "SECTOR",
    "ANALYST",
    "GEOPOLITICAL",
    "MARKET",
]

Sentiment = Literal[
    "POSITIVE",
    "NEGATIVE",
    "NEUTRAL",
    "UNKNOWN",
]

EventImportance = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
]


@dataclass(frozen=True)
class ResearchEvent:
    """
    Point-in-time research event.

    published_at:
        When the source publicly released the information.

    effective_at:
        When the event actually takes effect, when applicable.

    available_at:
        Earliest timestamp at which the research system is
        allowed to use the event.

    The backtest must use available_at, not a later timestamp,
    to prevent look-ahead bias.
    """

    event_id: str
    symbol: str | None

    event_type: EventType

    title: str
    summary: str

    source: str
    source_url: str | None

    published_at: datetime
    effective_at: datetime | None
    available_at: datetime

    sentiment: Sentiment = "UNKNOWN"
    importance: EventImportance = "MEDIUM"
    confidence: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("event_id cannot be empty")

        if self.symbol is not None and not self.symbol.strip():
            raise ValueError("symbol cannot be blank")

        if not self.title.strip():
            raise ValueError("title cannot be empty")

        if not self.source.strip():
            raise ValueError("source cannot be empty")

        if self.published_at.tzinfo is None:
            raise ValueError(
                "published_at must be timezone-aware"
            )

        if self.effective_at is not None:
            if self.effective_at.tzinfo is None:
                raise ValueError(
                    "effective_at must be timezone-aware"
                )

        if self.available_at.tzinfo is None:
            raise ValueError(
                "available_at must be timezone-aware"
            )

        if self.available_at < self.published_at:
            raise ValueError(
                "available_at cannot be earlier than published_at"
            )

        if self.confidence < Decimal("0"):
            raise ValueError(
                "confidence cannot be negative"
            )

        if self.confidence > Decimal("100"):
            raise ValueError(
                "confidence cannot exceed 100"
            )

    def is_available_at(
        self,
        timestamp: datetime,
    ) -> bool:
        """
        Return whether this event was known by the supplied time.
        """

        if timestamp.tzinfo is None:
            raise ValueError(
                "timestamp must be timezone-aware"
            )

        return self.available_at <= timestamp


def events_available_at(
    events: list[ResearchEvent],
    timestamp: datetime,
) -> tuple[ResearchEvent, ...]:
    """
    Return only events that were known at timestamp.

    Events are returned in chronological availability order.
    """

    available = [
        event
        for event in events
        if event.is_available_at(timestamp)
    ]

    return tuple(
        sorted(
            available,
            key=lambda event: (
                event.available_at,
                event.event_id,
            ),
        )
    )
