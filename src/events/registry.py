from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from src.events.normalizer import (
    NormalizedEvent,
    normalize_events,
)
from src.events.provider import (
    EventProvider,
    ProviderRequest,
)


@dataclass
class EventProviderRegistry:
    """
    Registry for event providers.

    Multiple providers can cover different information classes,
    while the rest of the research system consumes one canonical
    event representation.
    """

    _providers: dict[str, EventProvider]

    def __init__(self) -> None:
        self._providers = {}

    def register(
        self,
        provider: EventProvider,
    ) -> None:
        name = provider.name.strip().lower()

        if not name:
            raise ValueError(
                "provider name cannot be empty"
            )

        if name in self._providers:
            raise ValueError(
                f"provider already registered: {name}"
            )

        self._providers[name] = provider

    def get(
        self,
        name: str,
    ) -> EventProvider:
        key = name.strip().lower()

        try:
            return self._providers[key]
        except KeyError as exc:
            raise KeyError(
                f"unknown event provider: {name}"
            ) from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def fetch(
        self,
        *,
        symbols: Sequence[str],
        start: datetime,
        end: datetime,
        providers: Sequence[str] | None = None,
    ) -> tuple[NormalizedEvent, ...]:
        request = ProviderRequest(
            symbols=tuple(symbols),
            start=start,
            end=end,
        )

        selected_names = (
            tuple(providers)
            if providers is not None
            else self.names
        )

        raw_events = []

        for name in selected_names:
            provider = self.get(name)

            raw_events.extend(
                provider.fetch(
                    symbols=request.symbols,
                    start=request.start,
                    end=request.end,
                )
            )

        return normalize_events(raw_events)
