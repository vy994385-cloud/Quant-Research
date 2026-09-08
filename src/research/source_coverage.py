"""Source Coverage Intelligence (T1-W5).

Descriptive information for every company source set.  No scores, no
rankings, no source quality metrics.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SourceCoverageEntry(BaseModel):
    """Descriptive coverage for one source."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_name: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    evidence_count: int = Field(ge=0)
    latest_published_at: datetime | None = None
    latest_available_at: datetime | None = None
    freshness_state: str = ""
    pit_eligible: bool = False
    provenance_complete: bool = False
    covered_domains: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()


class SourceCoverageReport(BaseModel):
    """Source coverage report for one company."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    source_count: int = Field(ge=0)
    sources: tuple[SourceCoverageEntry, ...] = ()
    total_evidence_count: int = Field(ge=0)
    stale_source_count: int = Field(ge=0)
    complete_provenance_count: int = Field(ge=0)
    notes: tuple[str, ...] = ()


def _map_freshness(stale: bool, latest_published: datetime | None, as_of: datetime) -> str:
    """Map freshness state from source status."""
    if stale:
        return "STALE"
    if latest_published is None:
        return "UNKNOWN"
    days = (as_of - latest_published).days
    if days <= 30:
        return "CURRENT"
    if days <= 90:
        return "RECENT"
    return "AGING"


def _map_domains(categories: tuple[str, ...] | None) -> tuple[str, ...]:
    """Map categories to research domains."""
    if not categories:
        return ()
    domain_map = {
        "FINANCIAL_DISCLOSURE": "financials",
        "BUSINESS_NEWS": "business",
        "MANAGEMENT_STATEMENT": "management",
        "CORPORATE_ACTION": "events",
        "ORDER_CONTRACT": "business",
        "PRODUCT_BUSINESS_UPDATE": "technology",
    }
    domains = set()
    for cat in categories:
        domain = domain_map.get(cat, cat.lower())
        domains.add(domain)
    return tuple(sorted(domains))


def build_source_coverage_report(
    result: Any, *, as_of: datetime
) -> SourceCoverageReport:
    """Build source coverage report for one company."""
    symbol = getattr(result, "company", "") or ""
    intel = result.intelligence
    source_statuses = getattr(intel, "source_statuses", ()) or ()

    entries: list[SourceCoverageEntry] = []
    total_evidence = 0
    stale_count = 0
    complete_count = 0

    for src in source_statuses:
        src_name = getattr(src, "source_name", "") or ""
        src_type = getattr(src, "source_type", "") or ""
        item_count = getattr(src, "item_count", 0)
        categories = tuple(getattr(src, "categories", ()) or ())
        stale = getattr(src, "stale", False)
        provenance_complete = getattr(src, "provenance_completeness", False)
        latest_pub = getattr(src, "latest_published_at", None)
        latest_avail = getattr(src, "latest_available_at", None)

        entry = SourceCoverageEntry(
            source_name=src_name,
            source_type=src_type,
            evidence_count=item_count,
            latest_published_at=latest_pub,
            latest_available_at=latest_avail,
            freshness_state=_map_freshness(stale, latest_pub, as_of),
            pit_eligible=latest_avail is not None and latest_avail <= as_of,
            provenance_complete=provenance_complete,
            covered_domains=_map_domains(categories),
            categories=categories,
        )
        entries.append(entry)
        total_evidence += item_count
        if stale:
            stale_count += 1
        if provenance_complete:
            complete_count += 1

    entries.sort(key=lambda e: e.source_name)

    return SourceCoverageReport(
        symbol=symbol,
        as_of=as_of,
        source_count=len(entries),
        sources=tuple(entries),
        total_evidence_count=total_evidence,
        stale_source_count=stale_count,
        complete_provenance_count=complete_count,
        notes=(
            "Source coverage is descriptive. No scores or rankings applied.",
            "Freshness states: CURRENT (≤30d), RECENT (≤90d), AGING (>90d), STALE, UNKNOWN.",
        ),
    )
