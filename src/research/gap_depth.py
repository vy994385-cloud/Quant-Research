"""Research Gap Depth (T1-W5).

Audits the gap engine for completeness across all gap categories.
Provides structured grouped representation where multiple gaps are
the same logical issue.  Never over-collapses genuinely different gaps.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GapGroup(BaseModel):
    """Group of related gaps sharing the same logical issue."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    group_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    gap_count: int = Field(ge=1)
    gap_ids: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()
    shared_reason: str = ""
    symbols: tuple[str, ...] = ()


class GapDepthAudit(BaseModel):
    """Gap depth audit for one company."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    total_gap_count: int = Field(ge=0)
    category_counts: dict[str, int] = Field(default_factory=dict)
    status_counts: dict[str, int] = Field(default_factory=dict)
    gap_groups: tuple[GapGroup, ...] = ()
    gap_categories_present: tuple[str, ...] = ()
    gap_categories_absent: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


# All expected gap categories
EXPECTED_CATEGORIES = (
    "financial_data",
    "business_segments",
    "events",
    "business_profile",
    "data_quality",
    "technology",
    "risk",
    "market",
    "ownership",
    "news",
    "corporate_actions",
    "segments",
    "management",
    "customers",
    "competition",
    "innovation",
)


def _group_gaps(gaps: list[Any]) -> list[GapGroup]:
    """Group gaps that share the same logical issue.

    Gaps are grouped if they share the same category and a similar reason.
    Genuinely different gaps within the same category remain separate.
    """
    if not gaps:
        return []

    # Group by category first
    by_category: dict[str, list[Any]] = {}
    for gap in gaps:
        cat = getattr(gap, "category", "unknown")
        by_category.setdefault(cat, []).append(gap)

    groups: list[GapGroup] = []
    for cat, cat_gaps in sorted(by_category.items()):
        if len(cat_gaps) == 1:
            gap = cat_gaps[0]
            groups.append(GapGroup(
                group_id=f"GROUP:{cat}:{getattr(gap, 'gap_id', '')}",
                category=cat,
                gap_count=1,
                gap_ids=(getattr(gap, "gap_id", ""),),
                statuses=(getattr(gap, "status", ""),),
                shared_reason=getattr(gap, "reason", ""),
                symbols=(getattr(gap, "symbol", ""),),
            ))
        else:
            # Check if gaps share the same reason pattern
            reason_groups: dict[str, list[Any]] = {}
            for gap in cat_gaps:
                reason = getattr(gap, "reason", "")
                # Normalize reason for grouping
                key = reason[:80] if reason else "no_reason"
                reason_groups.setdefault(key, []).append(gap)

            for reason_key, r_gaps in reason_groups.items():
                groups.append(GapGroup(
                    group_id=f"GROUP:{cat}:{r_gaps[0].gap_id if r_gaps else ''}",
                    category=cat,
                    gap_count=len(r_gaps),
                    gap_ids=tuple(getattr(g, "gap_id", "") for g in r_gaps),
                    statuses=tuple(getattr(g, "status", "") for g in r_gaps),
                    shared_reason=reason_key,
                    symbols=tuple(getattr(g, "symbol", "") for g in r_gaps),
                ))

    return groups


def build_gap_depth_audit(result: Any, *, as_of: datetime) -> GapDepthAudit:
    """Build gap depth audit for one company."""
    symbol = getattr(result, "company", "") or ""
    intel = result.intelligence
    gaps_result = getattr(intel, "research_gaps", None)

    gap_list = list(gaps_result.gaps) if gaps_result and hasattr(gaps_result, "gaps") else []

    category_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for gap in gap_list:
        cat = getattr(gap, "category", "unknown")
        status = getattr(gap, "status", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1

    present = tuple(sorted(category_counts.keys()))
    absent = tuple(c for c in EXPECTED_CATEGORIES if c not in category_counts)

    return GapDepthAudit(
        symbol=symbol,
        as_of=as_of,
        total_gap_count=len(gap_list),
        category_counts=category_counts,
        status_counts=status_counts,
        gap_groups=tuple(_group_gaps(gap_list)),
        gap_categories_present=present,
        gap_categories_absent=absent,
        notes=(
            "Gaps are deterministic and traceable to specific data sources.",
            "Grouped gaps share the same logical issue across periods.",
        ),
    )
