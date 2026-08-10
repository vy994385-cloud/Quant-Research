from __future__ import annotations

from dataclasses import dataclass

from src.research.source_catalog import (
    RESEARCH_SOURCES,
    ResearchSource,
    SourceDomain,
    SourceTier,
)


@dataclass
class ResearchSourceRegistry:
    """
    Runtime registry of research sources.

    The registry does not download data.

    It answers:
    - Which sources are available?
    - Which sources cover a domain?
    - Which sources are safe for point-in-time research?
    """

    _sources: dict[str, ResearchSource]

    def __init__(self) -> None:
        self._sources = {}

        for source in RESEARCH_SOURCES:
            self.register(source)

    def register(
        self,
        source: ResearchSource,
    ) -> None:
        source_id = source.source_id.strip().lower()

        if source_id in self._sources:
            raise ValueError(
                f"source already registered: {source_id}"
            )

        self._sources[source_id] = source

    def get(
        self,
        source_id: str,
    ) -> ResearchSource:
        key = source_id.strip().lower()

        try:
            return self._sources[key]
        except KeyError as exc:
            raise KeyError(
                f"unknown research source: {source_id}"
            ) from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._sources))

    def enabled(self) -> tuple[ResearchSource, ...]:
        return tuple(
            source
            for source in self._sources.values()
            if source.enabled
        )

    def by_domain(
        self,
        domain: SourceDomain,
    ) -> tuple[ResearchSource, ...]:
        return tuple(
            source
            for source in self._sources.values()
            if source.domain == domain
        )

    def by_tier(
        self,
        tier: SourceTier,
    ) -> tuple[ResearchSource, ...]:
        return tuple(
            source
            for source in self._sources.values()
            if source.tier == tier
        )

    def point_in_time_ready(
        self,
    ) -> tuple[ResearchSource, ...]:
        return tuple(
            source
            for source in self._sources.values()
            if (
                source.enabled
                and source.supports_point_in_time
            )
        )