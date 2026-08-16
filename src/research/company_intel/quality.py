"""
Research status construction for company intelligence.

Statuses describe the *research itself*, not the company:

- freshness describes how recently evidence was disclosed;
- coverage describes which intelligence dimensions are populated;
- quality describes conflicts, deduplication, and provenance.

All values are derived deterministically from the surviving,
point-in-time-filtered item set plus the snapshot's conflict and
deduplication bookkeeping.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from src.research.company_intel.models import (
    CompanyResearchStatus,
    CorporateIntelItem,
    CoverageStatus,
    EvidenceConflict,
    EvidenceLink,
    FreshnessStatus,
    QualityStatus,
)
from src.research.company_intel.semantics import (
    IntelCategory,
    default_intel_category,
)


def _known_items(
    items: list[CorporateIntelItem],
    *,
    symbol: str,
    as_of: datetime,
) -> list[CorporateIntelItem]:
    return [
        item
        for item in items
        if item.symbol == symbol and item.is_known_at(as_of)
    ]


def _category(item: CorporateIntelItem) -> IntelCategory:
    return item.intel_category or default_intel_category(
        item.kind,
        item.event_type,
    )


def _unique_aware(
    values: list[datetime | None],
) -> list[datetime]:
    result: list[datetime] = []
    seen: set[datetime] = set()

    for value in values:
        if value is None or value.tzinfo is None:
            continue

        if value in seen:
            continue

        seen.add(value)
        result.append(value)

    return sorted(result)


def build_freshness(
    items: list[CorporateIntelItem],
    *,
    as_of: datetime,
) -> FreshnessStatus:
    """Freshness of the evidence knowable at `as_of`."""

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    known = [item for item in items if item.is_known_at(as_of)]

    published = _unique_aware([item.published_at for item in known])
    available = _unique_aware([item.available_at for item in known])
    effective = _unique_aware([item.effective_at for item in known])

    latest_published = published[-1] if published else None
    oldest_published = published[0] if published else None
    latest_available = available[-1] if available else None
    oldest_available = available[0] if available else None
    latest_effective = effective[-1] if effective else None
    oldest_effective = effective[0] if effective else None

    days_since_latest_published: int | None = None

    if latest_published is not None:
        days_since_latest_published = (
            as_of.date() - latest_published.date()
        ).days

    days_since_latest_available: int | None = None

    if latest_available is not None:
        days_since_latest_available = (
            as_of.date() - latest_available.date()
        ).days

    stale = (
        not known
        or days_since_latest_published is None
        or days_since_latest_published > 90
    )

    notes: list[str] = []

    if not known:
        notes.append("No evidence was knowable at as_of.")

    if stale and known:
        notes.append(
            "The most recent disclosure is more than 90 days old "
            "at as_of; research is stale."
        )

    return FreshnessStatus(
        latest_published_at=latest_published,
        latest_available_at=latest_available,
        latest_effective_at=latest_effective,
        oldest_published_at=oldest_published,
        oldest_available_at=oldest_available,
        oldest_effective_at=oldest_effective,
        days_since_latest_published=days_since_latest_published,
        days_since_latest_available=days_since_latest_available,
        stale=stale,
        notes=tuple(notes),
    )


def build_coverage_status(
    items: list[CorporateIntelItem],
    *,
    symbol: str,
    as_of: datetime,
) -> CoverageStatus:
    """Coverage of intelligence dimensions at `as_of`."""

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    known = _known_items(items, symbol=symbol, as_of=as_of)

    by_kind: Counter[str] = Counter(item.kind.value for item in known)
    by_category: Counter[str] = Counter(
        _category(item).value for item in known
    )
    by_semantic: Counter[str] = Counter(
        item.semantic_category.value for item in known
    )
    by_status: Counter[str] = Counter(
        item.verification_status.value for item in known
    )

    present = set(by_category)

    missing_categories = tuple(
        category.value
        for category in IntelCategory
        if category.value not in present
    )

    notes: list[str] = []

    if missing_categories:
        notes.append(
            "No evidence available for categories: "
            + ", ".join(missing_categories)
            + "."
        )

    return CoverageStatus(
        item_count=len(known),
        by_kind=dict(by_kind),
        by_category=dict(by_category),
        by_semantic=dict(by_semantic),
        by_status=dict(by_status),
        missing_categories=missing_categories,
        notes=tuple(notes),
    )


def build_quality_status(
    items: list[CorporateIntelItem],
    *,
    symbol: str,
    as_of: datetime,
    conflicts: list[EvidenceConflict],
    evidence_links: list[EvidenceLink],
    deduplicated_count: int,
    insufficient_evidence_notes: list[str],
    provider_failures: list[str] | tuple[str, ...] = (),
    stale_source_count: int = 0,
) -> QualityStatus:
    """Data-quality status of an intelligence snapshot."""

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    known = _known_items(items, symbol=symbol, as_of=as_of)

    source_id_count = len({item.source.source_name for item in known})
    provenance_id_count = len(
        {item.provenance_id for item in known if item.provenance_id}
    )

    notes: list[str] = []

    if conflicts:
        notes.append(
            "Conflicts are surfaced as-is; the system never "
            "resolves which side is correct automatically."
        )

    if deduplicated_count:
        notes.append(
            "Duplicate candidates were merged without destroying "
            "provenance."
        )

    if provider_failures:
        notes.append(
            "One or more source providers failed and were isolated "
            "from this snapshot."
        )

    if stale_source_count:
        notes.append(
            f"{stale_source_count} source(s) are stale at as_of."
        )

    return QualityStatus(
        conflict_count=len(conflicts),
        evidence_link_count=len(evidence_links),
        deduplicated_count=deduplicated_count,
        source_id_count=source_id_count,
        provenance_id_count=provenance_id_count,
        insufficient_evidence_notes=tuple(insufficient_evidence_notes),
        provider_failures=tuple(provider_failures),
        stale_source_count=stale_source_count,
        notes=tuple(notes),
    )


def build_research_status(
    *,
    company: str,
    as_of: datetime,
    items: list[CorporateIntelItem],
    conflicts: list[EvidenceConflict] | None = None,
    evidence_links: list[EvidenceLink] | None = None,
    deduplicated_count: int = 0,
    insufficient_evidence_notes: list[str] | None = None,
    provider_failures: list[str] | tuple[str, ...] | None = None,
    stale_source_count: int = 0,
) -> CompanyResearchStatus:
    """Aggregate research status for a company at `as_of`."""

    freshness = build_freshness(items, as_of=as_of)
    coverage = build_coverage_status(items, symbol=company, as_of=as_of)
    quality = build_quality_status(
        items,
        symbol=company,
        as_of=as_of,
        conflicts=conflicts or [],
        evidence_links=evidence_links or [],
        deduplicated_count=deduplicated_count,
        insufficient_evidence_notes=insufficient_evidence_notes or [],
        provider_failures=provider_failures or (),
        stale_source_count=stale_source_count,
    )

    return CompanyResearchStatus(
        company=company,
        as_of=as_of,
        freshness=freshness,
        coverage=coverage,
        quality=quality,
    )


__all__ = [
    "build_coverage_status",
    "build_freshness",
    "build_quality_status",
    "build_research_status",
]
