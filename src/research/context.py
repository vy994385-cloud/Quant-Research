from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ResearchContext:
    """
    Point-in-time research snapshot.

    A strategy will eventually receive this context instead of
    directly reaching into external providers.

    That separation is intentional.

    Strategy:
        ResearchContext -> signal

    Research system:
        sources -> ResearchContext
    """

    symbol: str
    timestamp: datetime

    market: tuple[Any, ...] = ()
    fundamentals: tuple[Any, ...] = ()
    macro: tuple[Any, ...] = ()
    events: tuple[Any, ...] = ()
    corporate_actions: tuple[Any, ...] = ()

    source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError(
                "symbol cannot be empty"
            )

        if self.timestamp.tzinfo is None:
            raise ValueError(
                "timestamp must be timezone-aware"
            )

        normalized_sources = tuple(
            sorted(
                {
                    source.strip().lower()
                    for source in self.source_ids
                    if source.strip()
                }
            )
        )

        object.__setattr__(
            self,
            "source_ids",
            normalized_sources,
        )

    @property
    def observation_count(self) -> int:
        return sum(
            len(group)
            for group in (
                self.market,
                self.fundamentals,
                self.macro,
                self.events,
                self.corporate_actions,
            )
        )

    @property
    def is_empty(self) -> bool:
        return self.observation_count == 0