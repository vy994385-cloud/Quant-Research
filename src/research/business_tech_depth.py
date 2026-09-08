"""Business/Tech Evidence Depth (T1-W5).

Audits all actual recorded business/technology evidence.  Produces
descriptive availability across research domains.  Classifies evidence
depth as STRONG, PARTIAL, WEAK, or MISSING.  This is a coverage
state, not a quality score.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DepthState(StrEnum):
    STRONG = "STRONG"
    PARTIAL = "PARTIAL"
    WEAK = "WEAK"
    MISSING = "MISSING"


class DomainDepth(BaseModel):
    """Evidence depth for one research domain."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    domain: str = Field(min_length=1)
    depth: DepthState
    evidence_count: int = Field(ge=0)
    source_count: int = Field(ge=0)
    item_ids: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class BusinessTechDepthReport(BaseModel):
    """Business/tech evidence depth report for one company."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    domains: tuple[DomainDepth, ...] = ()
    strong_count: int = Field(ge=0)
    partial_count: int = Field(ge=0)
    weak_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    notes: tuple[str, ...] = ()


# Domain definitions with keywords to match
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "business_model": ["business", "model", "strategy", "operations"],
    "customers": ["customer", "client", "order", "book"],
    "management": ["management", "ceo", "cfo", "board", "earnings call"],
    "competitive": ["competitor", "competitive", "market share", "positioning"],
    "capital_allocation": ["buyback", "dividend", "capex", "debt", "capital"],
    "technology": ["technology", "platform", "infrastructure", "digital"],
    "ai": ["ai", "artificial intelligence", "machine learning", "gen ai", "llm"],
    "cloud": ["cloud", "aws", "azure", "gcp"],
    "platforms": ["platform", "product", "saas"],
    "rd": ["research", "development", "rnd", "innovation", "lab"],
    "innovation": ["innovation", "patent", "breakthrough", "new"],
}


def _classify_depth(evidence_count: int, source_count: int) -> DepthState:
    """Classify evidence depth based on counts."""
    if evidence_count >= 3 and source_count >= 2:
        return DepthState.STRONG
    if evidence_count >= 2 or (evidence_count >= 1 and source_count >= 1):
        return DepthState.PARTIAL
    if evidence_count >= 1:
        return DepthState.WEAK
    return DepthState.MISSING


def _match_domain(item: Any, keywords: list[str]) -> bool:
    """Check if an item matches domain keywords."""
    title = (getattr(item, "title", "") or "").lower()
    topic = (getattr(item, "topic", "") or "").lower()
    description = (getattr(item, "description", "") or "").lower()
    text = f"{title} {topic} {description}"
    return any(kw in text for kw in keywords)


def build_business_tech_depth_report(
    result: Any, *, as_of: datetime
) -> BusinessTechDepthReport:
    """Build business/tech evidence depth report for one company."""
    symbol = getattr(result, "company", "") or ""
    intel = result.intelligence

    # Collect all relevant items
    all_items: list[Any] = []
    for field_name in ("business_events", "management_commentary",
                       "other_intelligence", "indirect_intelligence"):
        items = getattr(intel, field_name, ()) or ()
        all_items.extend(items)

    # Also include items from the main items list
    main_items = getattr(intel, "items", ()) or ()
    all_items.extend(main_items)

    # Deduplicate by item_id
    seen_ids: set[str] = set()
    unique_items: list[Any] = []
    for item in all_items:
        item_id = getattr(item, "item_id", "") or ""
        if item_id and item_id not in seen_ids:
            seen_ids.add(item_id)
            unique_items.append(item)

    domains: list[DomainDepth] = []
    strong = 0
    partial = 0
    weak = 0
    missing = 0

    for domain_name, keywords in sorted(DOMAIN_KEYWORDS.items()):
        matched = [item for item in unique_items if _match_domain(item, keywords)]
        evidence_count = len(matched)
        sources = set()
        for item in matched:
            src = getattr(item, "source", None)
            if src:
                name = getattr(src, "source_name", None) or (src.get("source_name") if isinstance(src, dict) else None)
                if name:
                    sources.add(name)

        depth = _classify_depth(evidence_count, len(sources))
        item_ids = tuple(getattr(item, "item_id", "") for item in matched)

        domains.append(DomainDepth(
            domain=domain_name,
            depth=depth,
            evidence_count=evidence_count,
            source_count=len(sources),
            item_ids=item_ids,
        ))

        if depth == DepthState.STRONG:
            strong += 1
        elif depth == DepthState.PARTIAL:
            partial += 1
        elif depth == DepthState.WEAK:
            weak += 1
        else:
            missing += 1

    return BusinessTechDepthReport(
        symbol=symbol,
        as_of=as_of,
        domains=tuple(domains),
        strong_count=strong,
        partial_count=partial,
        weak_count=weak,
        missing_count=missing,
        notes=(
            "Depth classification is coverage state, not quality score.",
            "STRONG: ≥3 evidence from ≥2 sources. PARTIAL: ≥2 evidence or ≥1 with source.",
            "WEAK: 1 evidence. MISSING: no evidence found.",
        ),
    )
