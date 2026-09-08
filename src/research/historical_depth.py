"""Historical Research Depth Audit (T1-W5).

Descriptive coverage facts for each research domain across recorded
companies.  Produces period counts, date ranges, source counts,
evidence counts, gap counts.  No scores, no rankings, no
recommendations.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ── Domain coverage ──────────────────────────────────────────────────
class DomainCoverage(BaseModel):
    """Descriptive coverage facts for one research domain."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    domain: str = Field(min_length=1)
    period_count: int = Field(default=0, ge=0)
    earliest_period: date | None = None
    latest_period: date | None = None
    evidence_count: int = Field(default=0, ge=0)
    source_count: int = Field(default=0, ge=0)
    gap_count: int = Field(default=0, ge=0)
    available_as_of_range: tuple[str, ...] = ()


# ── Company depth ────────────────────────────────────────────────────
class CompanyDepth(BaseModel):
    """Historical depth for one company across all domains."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    total_evidence_count: int = Field(ge=0)
    total_source_count: int = Field(ge=0)
    total_gap_count: int = Field(ge=0)
    total_timeline_count: int = Field(ge=0)
    domains: tuple[DomainCoverage, ...] = ()


# ── Universe depth ───────────────────────────────────────────────────
class UniverseDepth(BaseModel):
    """Historical depth for all recorded companies."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of: datetime
    company_count: int = Field(ge=0)
    companies: tuple[CompanyDepth, ...] = ()


def _extract_periods(result: Any) -> tuple[dict[str, Any], ...]:
    """Extract financial periods from a verification result."""
    intel = result.intelligence
    fi = getattr(intel, "financial_intelligence", None)
    if fi is None:
        return ()
    return tuple(
        {
            "period_end": p.get("period_end"),
            "period_type": str(p.get("period_type", "")),
        }
        for p in (fi.periods if hasattr(fi, "periods") else ())
    )


def _domain_finance(result: Any, as_of: datetime) -> DomainCoverage:
    """Financial domain coverage."""
    intel = result.intelligence
    fi = getattr(intel, "financial_intelligence", None)
    evidence = result.evidence_items or []
    gaps = getattr(intel, "research_gaps", None)
    source_statuses = getattr(intel, "source_statuses", ()) or ()

    period_count = fi.period_count if fi else 0
    earliest = fi.earliest_period_end if fi else None
    latest = fi.latest_period_end if fi else None

    # Count financial evidence
    fin_evidence = sum(
        1 for e in evidence
        if getattr(e, "evidence_type", "") == "FEATURE"
    )

    # Count financial sources
    fin_sources = sum(
        1 for s in source_statuses
        if any("FINANCIAL" in c.upper() for c in (getattr(s, "categories", ()) or ()))
    )

    gap_list = list(gaps.gaps) if gaps and hasattr(gaps, "gaps") else []
    fin_gaps = sum(1 for g in gap_list if getattr(g, "category", "") == "financial_data")

    return DomainCoverage(
        domain="financials",
        period_count=period_count,
        earliest_period=earliest,
        latest_period=latest,
        evidence_count=fin_evidence,
        source_count=fin_sources,
        gap_count=fin_gaps,
    )


def _domain_business(result: Any) -> DomainCoverage:
    """Business domain coverage."""
    intel = result.intelligence
    items = getattr(intel, "items", ()) or ()
    evidence = result.evidence_items or []
    gaps = getattr(intel, "research_gaps", None)

    biz_events = getattr(intel, "business_events", ()) or ()
    mgmt = getattr(intel, "management_commentary", ()) or ()
    other = getattr(intel, "other_intelligence", ()) or ()

    biz_count = len(biz_events) + len(mgmt) + len(other)

    biz_evidence = sum(
        1 for e in evidence
        if any(kw in (getattr(e, "title", "") or "").lower()
               for kw in ["business", "management", "customer", "model", "strategy"])
    )

    gap_list = list(gaps.gaps) if gaps and hasattr(gaps, "gaps") else []
    biz_gaps = sum(
        1 for g in gap_list
        if getattr(g, "category", "") in ("business_profile", "business_segments")
    )

    return DomainCoverage(
        domain="business",
        period_count=biz_count,
        evidence_count=biz_evidence,
        source_count=0,
        gap_count=biz_gaps,
    )


def _domain_technology(result: Any) -> DomainCoverage:
    """Technology domain coverage."""
    intel = result.intelligence
    items = getattr(intel, "items", ()) or ()
    evidence = result.evidence_items or []
    gaps = getattr(intel, "research_gaps", None)

    tech_count = sum(
        1 for item in items
        if any(kw in (getattr(item, "topic", "") or "").lower()
               for kw in ["technology", "ai", "cloud", "platform", "rd", "innovation"])
    )

    tech_evidence = sum(
        1 for e in evidence
        if any(kw in (getattr(e, "title", "") or "").lower()
               for kw in ["technology", "ai", "cloud", "platform", "tech"])
    )

    return DomainCoverage(
        domain="technology",
        period_count=tech_count,
        evidence_count=tech_evidence,
        source_count=0,
    )


def _domain_events(result: Any) -> DomainCoverage:
    """Events domain coverage."""
    intel = result.intelligence
    timeline = getattr(intel, "timeline", None)
    entries = tuple(timeline.entries) if timeline and hasattr(timeline, "entries") else ()
    evidence = result.evidence_items or []
    gaps = getattr(intel, "research_gaps", None)

    event_evidence = sum(
        1 for e in evidence
        if any(kw in (getattr(e, "title", "") or "").lower()
               for kw in ["event", "announcement", "board", "meeting", "dividend", "earnings"])
    )

    gap_list = list(gaps.gaps) if gaps and hasattr(gaps, "gaps") else []
    event_gaps = sum(1 for g in gap_list if getattr(g, "category", "") == "events")

    return DomainCoverage(
        domain="events",
        period_count=len(entries),
        evidence_count=event_evidence,
        source_count=0,
        gap_count=event_gaps,
    )


def _domain_risk(result: Any) -> DomainCoverage:
    """Risk domain coverage."""
    intel = result.intelligence
    risk = getattr(intel, "risk_intelligence", ()) or ()
    evidence = result.evidence_items or []

    risk_evidence = sum(
        1 for e in evidence
        if any(kw in (getattr(e, "title", "") or "").lower()
               for kw in ["risk", "regulatory", "compliance", "litigation"])
    )

    return DomainCoverage(
        domain="risk",
        period_count=len(risk),
        evidence_count=risk_evidence,
        source_count=0,
    )


def _domain_market(result: Any) -> DomainCoverage:
    """Market domain coverage."""
    intel = result.intelligence
    indirect = getattr(intel, "indirect_intelligence", ()) or ()
    evidence = result.evidence_items or []

    market_evidence = sum(
        1 for e in evidence
        if any(kw in (getattr(e, "title", "") or "").lower()
               for kw in ["market", "sector", "industry", "competitor"])
    )

    return DomainCoverage(
        domain="market",
        period_count=len(indirect),
        evidence_count=market_evidence,
        source_count=0,
    )


def _domain_sources(result: Any) -> DomainCoverage:
    """Source coverage."""
    intel = result.intelligence
    source_statuses = getattr(intel, "source_statuses", ()) or ()
    gaps = getattr(intel, "research_gaps", None)

    gap_list = list(gaps.gaps) if gaps and hasattr(gaps, "gaps") else []
    src_gaps = sum(1 for g in gap_list if "source" in getattr(g, "category", "").lower())

    return DomainCoverage(
        domain="sources",
        period_count=len(source_statuses),
        source_count=len(source_statuses),
        gap_count=src_gaps,
    )


def _domain_evidence(result: Any) -> DomainCoverage:
    """Evidence coverage."""
    evidence = result.evidence_items or ()
    intel = result.intelligence
    evidence_links = getattr(intel, "evidence_links", ()) or ()

    return DomainCoverage(
        domain="evidence",
        period_count=len(evidence),
        evidence_count=len(evidence),
        source_count=0,
    )


def _domain_ownership(result: Any) -> DomainCoverage:
    """Ownership coverage — BLOCKED (no fixture data)."""
    return DomainCoverage(
        domain="ownership",
        period_count=0,
        evidence_count=0,
        source_count=0,
        gap_count=1,
    )


def build_company_depth(result: Any, *, as_of: datetime) -> CompanyDepth:
    """Build historical depth for one company."""
    symbol = getattr(result, "company", "") or ""
    evidence = result.evidence_items or ()
    intel = result.intelligence
    source_statuses = getattr(intel, "source_statuses", ()) or ()
    gaps = getattr(intel, "research_gaps", None)
    timeline = getattr(intel, "timeline", None)

    gap_list = list(gaps.gaps) if gaps and hasattr(gaps, "gaps") else []
    entries = tuple(timeline.entries) if timeline and hasattr(timeline, "entries") else ()

    domains = (
        _domain_finance(result, as_of),
        _domain_business(result),
        _domain_technology(result),
        _domain_events(result),
        _domain_risk(result),
        _domain_market(result),
        _domain_sources(result),
        _domain_evidence(result),
        _domain_ownership(result),
    )

    return CompanyDepth(
        symbol=symbol,
        as_of=as_of,
        total_evidence_count=len(evidence),
        total_source_count=len(source_statuses),
        total_gap_count=len(gap_list),
        total_timeline_count=len(entries),
        domains=domains,
    )


def build_universe_depth(
    results: list[Any], *, as_of: datetime
) -> UniverseDepth:
    """Build historical depth for all companies."""
    companies = tuple(build_company_depth(r, as_of=as_of) for r in results)
    return UniverseDepth(
        as_of=as_of,
        company_count=len(companies),
        companies=companies,
    )
