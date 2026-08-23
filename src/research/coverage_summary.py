"""
Consolidated research-coverage output.

One coherent model that lets a UI render a single research-coverage
view per company instead of stitching together separate gap lists,
source lists, and PIT counters:

- canonical statuses: AVAILABLE / LIMITED / MISSING / STALE /
  CONFLICTING / INSUFFICIENT
- per-area rows with counts, reasons, source availability,
  freshness, and PIT implication
- repeated near-identical reasons are grouped, never spammed
- one source summary row per source with provenance completeness
- one PIT summary carrying the point-in-time accounting

Nothing here invents information: every field mirrors an existing
recorded artifact (ResearchGapResult, SourceStatus, PIT counters).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


def _require_aware(as_of: datetime) -> None:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")


class CoverageStatus(str, Enum):
    """Canonical coverage vocabulary for all research areas."""

    AVAILABLE = "AVAILABLE"
    LIMITED = "LIMITED"
    MISSING = "MISSING"
    STALE = "STALE"
    CONFLICTING = "CONFLICTING"
    INSUFFICIENT = "INSUFFICIENT"


# Recorded gap status -> canonical coverage status.
GAP_STATUS_TO_COVERAGE = {
    "KNOWN": CoverageStatus.AVAILABLE,
    "PARTIALLY_KNOWN": CoverageStatus.LIMITED,
    "UNAVAILABLE": CoverageStatus.MISSING,
    "CONFLICTING": CoverageStatus.CONFLICTING,
    "STALE": CoverageStatus.STALE,
    "INSUFFICIENT_EVIDENCE": CoverageStatus.INSUFFICIENT,
}

# Display priority: problems first, availability last.
_SEVERITY_ORDER = {
    CoverageStatus.CONFLICTING: 0,
    CoverageStatus.MISSING: 1,
    CoverageStatus.STALE: 2,
    CoverageStatus.INSUFFICIENT: 3,
    CoverageStatus.LIMITED: 4,
    CoverageStatus.AVAILABLE: 5,
}

_PIT_IMPLICATION = {
    CoverageStatus.AVAILABLE: (
        "Recorded evidence is knowable at as_of."
    ),
    CoverageStatus.LIMITED: (
        "Only part of this area has evidence knowable at as_of."
    ),
    CoverageStatus.MISSING: (
        "No recorded evidence for this area was knowable at as_of."
    ),
    CoverageStatus.STALE: (
        "Recorded evidence exists but predates as_of; treat as "
        "historical context only."
    ),
    CoverageStatus.CONFLICTING: (
        "Knowable evidence disagrees within this area; both sides "
        "are preserved."
    ),
    CoverageStatus.INSUFFICIENT: (
        "Some evidence is knowable at as_of but not enough to "
        "characterize the area."
    ),
}


class AreaCoverage(BaseModel):
    """Canonical coverage state of one research area."""

    model_config = ConfigDict(extra="forbid")

    area: str = Field(min_length=1)
    status: CoverageStatus
    detail: str = ""
    reason: str = ""
    what_would_resolve: str = ""
    item_count: int = Field(ge=0)
    related_metrics: tuple[str, ...] = ()
    source_names: tuple[str, ...] = ()
    evidence_ref_count: int = Field(ge=0)
    priority: str = "MEDIUM"
    latest_evidence_at: datetime | None = None
    stale: bool = False
    pit_implication: str


class GroupedReason(BaseModel):
    """
    One deduplicated reason shared by multiple areas.

    Repeated near-identical warnings collapse into a single grouped
    entry listing every affected area.
    """

    model_config = ConfigDict(extra="forbid")

    status: CoverageStatus
    reason: str
    areas: tuple[str, ...]
    occurrence_count: int = Field(ge=1)


class SourceCoverage(BaseModel):
    """One row of the source summary."""

    model_config = ConfigDict(extra="forbid")

    source: str
    type: str
    items: int = Field(ge=0)
    categories: tuple[str, ...] = ()
    latest_published_at: datetime | None = None
    latest_available_at: datetime | None = None
    freshness_days: int | None = None
    stale: bool = False
    provenance_completeness: bool = False


class PitSummary(BaseModel):
    """Point-in-time accounting for a research response."""

    model_config = ConfigDict(extra="forbid")

    requested_as_of: str
    effective_as_of: str
    market_as_of: str | None = None
    evidence_included: int = Field(ge=0)
    future_evidence_excluded: int = Field(ge=0)
    sources_discovered: int | None = None
    sources_accepted: int | None = None
    pit_checks_passed: bool | None = None


class CompanyCoverageSummary(BaseModel):
    """The single coherent research-coverage model for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    as_of: datetime

    areas: tuple[AreaCoverage, ...] = ()
    status_counts: dict[str, int] = Field(default_factory=dict)

    grouped_reasons: tuple[GroupedReason, ...] = ()

    sources: tuple[SourceCoverage, ...] = ()
    source_count: int = 0
    stale_source_count: int = 0

    pit: PitSummary | None = None

    notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def _area_from_gap(gap) -> AreaCoverage:
    status = GAP_STATUS_TO_COVERAGE.get(
        str(gap.status).upper(), CoverageStatus.MISSING
    )

    return AreaCoverage(
        area=gap.category,
        status=status,
        detail=gap.gap,
        reason=gap.reason,
        what_would_resolve=gap.what_would_resolve,
        item_count=max(len(gap.related_metrics), 1),
        related_metrics=tuple(sorted(gap.related_metrics)),
        source_names=tuple(sorted(set(gap.sources_checked))),
        evidence_ref_count=len(gap.evidence_refs),
        priority=gap.priority,
        stale=status == CoverageStatus.STALE,
        pit_implication=_PIT_IMPLICATION[status],
    )


def _group_reasons(areas: list[AreaCoverage]) -> list[GroupedReason]:
    grouped: dict[tuple[str, str], list[str]] = {}
    for area in areas:
        key = (area.status.value, area.reason.strip())
        grouped.setdefault(key, []).append(area.area)

    entries = [
        GroupedReason(
            status=CoverageStatus(status_value),
            reason=reason,
            areas=tuple(sorted(set(names))),
            occurrence_count=len(set(names)),
        )
        for (status_value, reason), names in grouped.items()
        if reason
    ]

    return sorted(
        entries,
        key=lambda e: (
            -e.occurrence_count,
            _SEVERITY_ORDER[e.status],
            e.reason,
        ),
    )


def _source_row(status) -> SourceCoverage:
    return SourceCoverage(
        source=status.source_name,
        type=status.source_type,
        items=status.item_count,
        categories=tuple(sorted(status.categories)),
        latest_published_at=status.latest_published_at,
        latest_available_at=status.latest_available_at,
        freshness_days=status.days_since_latest_published,
        stale=bool(status.stale),
        provenance_completeness=bool(status.provenance_completeness),
    )


def build_coverage_summary(
    research_gaps,
    source_statuses,
    *,
    symbol: str,
    as_of: datetime,
    pit: PitSummary | None = None,
) -> CompanyCoverageSummary:
    """
    Build the consolidated coverage model.

    research_gaps: ResearchGapResult-like object (or None).
    source_statuses: iterable of SourceStatus-like objects.
    """

    _require_aware(as_of)

    areas: list[AreaCoverage] = []
    if research_gaps is not None:
        areas = [_area_from_gap(gap) for gap in research_gaps.gaps]

    areas.sort(
        key=lambda a: (_SEVERITY_ORDER[a.status], a.area, a.detail)
    )

    status_counts: dict[str, int] = {}
    for area in areas:
        key = area.status.value
        status_counts[key] = status_counts.get(key, 0) + 1

    grouped_reasons = _group_reasons(areas)

    seen_sources: set[str] = set()
    source_rows: list[SourceCoverage] = []
    for status in source_statuses:
        if status.source_name in seen_sources:
            continue
        seen_sources.add(status.source_name)
        source_rows.append(_source_row(status))

    source_rows.sort(key=lambda s: s.source)
    stale_source_count = sum(1 for s in source_rows if s.stale)

    notes: list[str] = []
    if not areas:
        notes.append(
            "No research-gap analysis was recorded at as_of."
        )
    if not source_rows:
        notes.append(
            "No research sources were recorded for this company."
        )
    if grouped_reasons:
        top = grouped_reasons[0]
        notes.append(
            f"Most frequent issue ({top.occurrence_count} area(s)): "
            f"{top.reason}"
        )

    return CompanyCoverageSummary(
        symbol=symbol.strip().upper(),
        as_of=as_of,
        areas=tuple(areas),
        status_counts=dict(sorted(status_counts.items())),
        grouped_reasons=tuple(grouped_reasons),
        sources=tuple(source_rows),
        source_count=len(source_rows),
        stale_source_count=stale_source_count,
        pit=pit,
        notes=tuple(notes),
    )


__all__ = [
    "AreaCoverage",
    "CompanyCoverageSummary",
    "CoverageStatus",
    "GAP_STATUS_TO_COVERAGE",
    "GroupedReason",
    "PitSummary",
    "SourceCoverage",
    "build_coverage_summary",
]
