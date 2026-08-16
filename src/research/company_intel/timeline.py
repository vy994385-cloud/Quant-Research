"""
Chronological company evidence timeline construction.

The timeline is a deterministic, point-in-time-safe view of the
evidence known about a company at `as_of`. Ordering uses the
canonical `timeline_at` date:

1. published date, when present;
2. otherwise the effective date;
3. otherwise the available date.

Ties are broken by entry id so the ordering is fully reproducible.
Nothing here adds new information or an opinion.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from src.research.company_intel.models import (
    CompanyTimeline,
    CorporateIntelItem,
    TimelineEntry,
)
from src.research.company_intel.semantics import (
    IntelCategory,
    default_intel_category,
)


def timeline_at(item: CorporateIntelItem) -> datetime | None:
    """Canonical timeline date for an item."""
    if item.published_at is not None:
        return item.published_at

    if item.effective_at is not None:
        return item.effective_at

    return item.available_at


def timeline_entry_from_item(
    item: CorporateIntelItem,
) -> TimelineEntry:
    """One timeline entry mirroring a source item verbatim."""
    category = item.intel_category or default_intel_category(
        item.kind,
        item.event_type,
    )

    return TimelineEntry(
        entry_id=f"timeline:{item.item_id}",
        symbol=item.symbol,
        kind=item.kind,
        intel_category=category,
        semantic_category=item.semantic_category,
        verification_status=item.verification_status,
        event_type=item.event_type,
        topic=item.topic,
        title=item.title,
        description=item.description,
        direction=item.direction,
        stance=item.stance,
        published_at=item.published_at,
        available_at=item.available_at,
        effective_at=item.effective_at,
        timeline_at=timeline_at(item),
        source=item.source,
        provenance_id=item.provenance_id,
        checksum=item.checksum,
    )


def build_timeline(
    items: list[CorporateIntelItem],
    *,
    symbol: str,
    as_of: datetime,
) -> CompanyTimeline:
    """
    Build the chronological evidence timeline for a company.

    Only items knowable at `as_of` are included; entries never leak
    future information.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    known = [
        item
        for item in items
        if item.symbol == symbol and item.is_known_at(as_of)
    ]

    entries = [timeline_entry_from_item(item) for item in known]

    def _order_key(entry: TimelineEntry) -> tuple[str, str]:
        stamp = entry.timeline_at.isoformat() if entry.timeline_at else ""
        return (stamp, entry.entry_id)

    ordered = sorted(entries, key=_order_key)

    counts: Counter[str] = Counter()

    for entry in ordered:
        counts[entry.intel_category.value] += 1

    latest_at = ordered[-1].timeline_at if ordered else None
    earliest_at = ordered[0].timeline_at if ordered else None

    notes: list[str] = []

    if not ordered:
        notes.append("No evidence was knowable at as_of.")

    return CompanyTimeline(
        company=symbol,
        as_of=as_of,
        entries=tuple(ordered),
        counts=dict(counts),
        latest_at=latest_at,
        earliest_at=earliest_at,
        notes=tuple(notes),
    )


__all__ = [
    "build_timeline",
    "timeline_at",
    "timeline_entry_from_item",
]
