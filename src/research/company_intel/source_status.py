"""
Source status construction for company intelligence.

Describes the *sources* feeding a company's intelligence snapshot:
how much evidence each source contributes, how fresh it is, and
whether provenance survives. Like every status in this layer it
describes the research, not the company.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from src.research.company_intel.models import (
    CorporateIntelItem,
    SourceStatus,
)
from src.research.company_intel.semantics import (
    IntelCategory,
    default_intel_category,
)

_STALE_DAYS = 90


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")


def build_source_statuses(
    items: list[CorporateIntelItem],
    *,
    symbol: str,
    as_of: datetime,
) -> tuple[SourceStatus, ...]:
    """
    Build one status per source for the items known at `as_of`.

    A source is stale when its latest published disclosure is more
    than 90 days old at `as_of`. Provenance is complete when every
    item contributed by the source carries a provenance id.
    """

    _require_aware(as_of)

    known = [
        item
        for item in items
        if item.symbol == symbol and item.is_known_at(as_of)
    ]

    by_source: dict[str, list[CorporateIntelItem]] = defaultdict(list)

    for item in known:
        by_source[item.source.source_name].append(item)

    statuses: list[SourceStatus] = []

    for source_name, group in sorted(by_source.items()):
        source_type = group[0].source.source_type
        categories: set[str] = set()

        for item in group:
            category = item.intel_category or default_intel_category(
                item.kind,
                item.event_type,
            )
            categories.add(category.value)

        published = [
            item.published_at
            for item in group
            if item.published_at is not None
            and item.published_at.tzinfo is not None
        ]
        available = [
            item.available_at
            for item in group
            if item.available_at is not None
            and item.available_at.tzinfo is not None
        ]

        latest_published = max(published) if published else None
        latest_available = max(available) if available else None

        days_since_latest_published: int | None = None

        if latest_published is not None:
            days_since_latest_published = (
                as_of.date() - latest_published.date()
            ).days

        stale = (
            latest_published is None
            or days_since_latest_published is None
            or days_since_latest_published > _STALE_DAYS
        )

        provenance_complete = all(
            item.provenance_id is not None
            for item in group
        )

        notes: list[str] = []

        if stale:
            notes.append(
                "This source's latest published disclosure is more "
                "than 90 days old at as_of."
            )

        if not provenance_complete:
            notes.append(
                "Some items from this source lack a provenance id."
            )

        statuses.append(
            SourceStatus(
                source_name=source_name,
                source_type=source_type,
                item_count=len(group),
                categories=tuple(sorted(categories)),
                latest_published_at=latest_published,
                latest_available_at=latest_available,
                days_since_latest_published=(
                    days_since_latest_published
                ),
                stale=stale,
                provenance_completeness=provenance_complete,
                notes=tuple(notes),
            )
        )

    return tuple(statuses)


def stale_source_count(
    statuses: list[SourceStatus],
) -> int:
    """Count sources whose latest disclosure is stale at as_of."""
    return sum(1 for status in statuses if status.stale)


__all__ = [
    "build_source_statuses",
    "stale_source_count",
]
