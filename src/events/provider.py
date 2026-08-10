from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class RawEvent:
    """
    Provider-neutral representation of an externally sourced event.

    The ingestion layer deliberately keeps the original source,
    URL, timestamps, and raw payload so downstream research can
    preserve provenance.
    """

    event_id: str
    source: str
    source_url: str
    title: str

    published_at: datetime
    available_at: datetime

    symbols: tuple[str, ...] = ()
    event_type: str = "NEWS"
    summary: str | None = None

    importance: int = 0
    confidence: int = 0

    raw_payload: Any = None


class EventProvider(Protocol):
    """
    Interface implemented by live or historical event providers.

    Providers are responsible only for retrieving source data.
    Normalization and research interpretation happen elsewhere.
    """

    name: str

    def fetch(
        self,
        *,
        symbols: Sequence[str],
        start: datetime,
        end: datetime,
    ) -> list[RawEvent]:
        ...


@dataclass(frozen=True)
class ProviderRequest:
    symbols: tuple[str, ...]
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise ValueError(
                "start must be earlier than end"
            )

        normalized_symbols = tuple(
            symbol.strip().upper()
            for symbol in self.symbols
            if symbol.strip()
        )

        if not normalized_symbols:
            raise ValueError(
                "symbols cannot be empty"
            )

        object.__setattr__(
            self,
            "symbols",
            normalized_symbols,
        )
