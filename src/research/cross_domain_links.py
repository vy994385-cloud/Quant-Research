"""Cross-Domain Research Links (T1-W5).

Deterministic linkage across research domains using shared identifiers,
dates, and context.  Safe vocabulary only: RELATED, SAME_CONTEXT,
OCCURRED_ALONGSIDE, TEMPORALLY_ADJACENT.  No causal language.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LinkType(StrEnum):
    RELATED = "RELATED"
    SAME_CONTEXT = "SAME_CONTEXT"
    OCCURRED_ALONGSIDE = "OCCURRED_ALONGSIDE"
    TEMPORALLY_ADJACENT = "TEMPORALLY_ADJACENT"


class CrossDomainLink(BaseModel):
    """A deterministic link between two research items."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    link_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    link_type: LinkType
    source_item_id: str = Field(min_length=1)
    source_domain: str = Field(min_length=1)
    source_date: datetime | None = None
    target_item_id: str = Field(min_length=1)
    target_domain: str = Field(min_length=1)
    target_date: datetime | None = None
    evidence_ids: tuple[str, ...] = ()
    shared_context: str = ""


class CrossDomainResult(BaseModel):
    """Cross-domain link audit for one company."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    links: tuple[CrossDomainLink, ...] = ()
    link_count: int = Field(ge=0)
    link_type_counts: dict[str, int] = Field(default_factory=dict)
    domains_connected: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


def _same_source_context(
    item_a: Any, item_b: Any
) -> bool:
    """Check if two items share the same source context."""
    src_a = getattr(item_a, "source", None)
    src_b = getattr(item_b, "source", None)
    if src_a and src_b:
        name_a = getattr(src_a, "source_name", None) or (src_a.get("source_name") if isinstance(src_a, dict) else None)
        name_b = getattr(src_b, "source_name", None) or (src_b.get("source_name") if isinstance(src_b, dict) else None)
        if name_a and name_b and name_a == name_b:
            return True
    return False


def _temporal_adjacency(dt_a: datetime | None, dt_b: datetime | None, threshold_days: int = 7) -> bool:
    """Check if two dates are within threshold_days of each other."""
    if dt_a is None or dt_b is None:
        return False
    diff = abs((dt_a - dt_b).total_seconds())
    return diff <= threshold_days * 86400


def _extract_date(item: Any, field: str) -> datetime | None:
    """Safely extract a datetime from an item."""
    val = getattr(item, field, None)
    if val is None:
        src = getattr(item, "source", None)
        if src:
            val = getattr(src, field, None)
    return val if isinstance(val, datetime) else None


def _build_links_for_pair(
    item_a: Any,
    item_b: Any,
    domain_a: str,
    domain_b: str,
    symbol: str,
    as_of: datetime,
) -> list[CrossDomainLink]:
    """Build links between two items if criteria are met."""
    links: list[CrossDomainLink] = []
    id_a = getattr(item_a, "item_id", "") or getattr(item_a, "evidence_id", "") or ""
    id_b = getattr(item_b, "item_id", "") or getattr(item_b, "evidence_id", "") or ""

    if not id_a or not id_b or id_a == id_b:
        return links

    date_a = _extract_date(item_a, "published_at") or _extract_date(item_a, "available_at")
    date_b = _extract_date(item_b, "published_at") or _extract_date(item_b, "available_at")

    # SAME_CONTEXT: same source
    if _same_source_context(item_a, item_b):
        links.append(CrossDomainLink(
            link_id=f"LINK:{symbol}:{domain_a}:{id_a}:{domain_b}:{id_b}:SAME_CONTEXT",
            symbol=symbol,
            link_type=LinkType.SAME_CONTEXT,
            source_item_id=id_a,
            source_domain=domain_a,
            source_date=date_a,
            target_item_id=id_b,
            target_domain=domain_b,
            target_date=date_b,
            shared_context="same_source",
        ))

    # TEMPORALLY_ADJACENT: within 7 days
    elif _temporal_adjacency(date_a, date_b):
        links.append(CrossDomainLink(
            link_id=f"LINK:{symbol}:{domain_a}:{id_a}:{domain_b}:{id_b}:TEMPORAL",
            symbol=symbol,
            link_type=LinkType.TEMPORALLY_ADJACENT,
            source_item_id=id_a,
            source_domain=domain_a,
            source_date=date_a,
            target_item_id=id_b,
            target_domain=domain_b,
            target_date=date_b,
            shared_context="temporal_proximity",
        ))

    # OCCURRED_ALONGSIDE: same date
    elif date_a and date_b and date_a.date() == date_b.date():
        links.append(CrossDomainLink(
            link_id=f"LINK:{symbol}:{domain_a}:{id_a}:{domain_b}:{id_b}:ALONGSIDE",
            symbol=symbol,
            link_type=LinkType.OCCURRED_ALONGSIDE,
            source_item_id=id_a,
            source_domain=domain_a,
            source_date=date_a,
            target_item_id=id_b,
            target_domain=domain_b,
            target_date=date_b,
            shared_context="same_date",
        ))

    return links


def build_cross_domain_links(
    result: Any, *, as_of: datetime
) -> CrossDomainResult:
    """Build cross-domain links for one company."""
    symbol = getattr(result, "company", "") or ""
    intel = result.intelligence

    # Collect items by domain
    domains: dict[str, list[Any]] = {}
    biz_events = getattr(intel, "business_events", ()) or ()
    risk_items = getattr(intel, "risk_intelligence", ()) or ()
    indirect = getattr(intel, "indirect_intelligence", ()) or ()
    other = getattr(intel, "other_intelligence", ()) or ()
    mgmt = getattr(intel, "management_commentary", ()) or ()
    fin_items = getattr(intel, "financial_intelligence_items", ()) or ()

    if biz_events:
        domains["business_event"] = list(biz_events)
    if risk_items:
        domains["risk_event"] = list(risk_items)
    if indirect:
        domains["market"] = list(indirect)
    if other:
        domains["other"] = list(other)
    if mgmt:
        domains["management"] = list(mgmt)
    if fin_items:
        domains["financial_event"] = list(fin_items)

    # Build links between all domain pairs
    all_links: list[CrossDomainLink] = []
    domain_names = sorted(domains.keys())
    for i, d_a in enumerate(domain_names):
        for d_b in domain_names[i + 1:]:
            for item_a in domains[d_a]:
                for item_b in domains[d_b]:
                    all_links.extend(
                        _build_links_for_pair(item_a, item_b, d_a, d_b, symbol, as_of)
                    )

    # Deduplicate by link_id
    seen: set[str] = set()
    unique_links: list[CrossDomainLink] = []
    for link in all_links:
        if link.link_id not in seen:
            seen.add(link.link_id)
            unique_links.append(link)

    # Sort deterministically
    unique_links.sort(key=lambda l: l.link_id)

    type_counts: dict[str, int] = {}
    for link in unique_links:
        type_counts[link.link_type.value] = type_counts.get(link.link_type.value, 0) + 1

    connected = tuple(sorted({
        d for link in unique_links for d in [link.source_domain, link.target_domain]
    }))

    return CrossDomainResult(
        symbol=symbol,
        as_of=as_of,
        links=tuple(unique_links),
        link_count=len(unique_links),
        link_type_counts=type_counts,
        domains_connected=connected,
        notes=(
            "Links are deterministic and use safe vocabulary only. No causal language.",
        ),
    )
