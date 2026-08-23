"""
Research gap detection module.

Identifies what information is known, partially known,
unavailable, conflicting, stale, or insufficient for each
company. Makes research gaps first-class output.

Every gap carries:
  - gap description
  - status (KNOWN, PARTIALLY_KNOWN, UNAVAILABLE, CONFLICTING, STALE, INSUFFICIENT_EVIDENCE)
  - reason for the status
  - what would resolve it
  - sources checked
  - evidence references

This module does NOT invent missing information.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Sequence

from src.data.company.financials import FinancialSnapshot
from src.data.company.business_profile import BusinessProfile
from src.data.company.events import CompanyEvent


class ResearchGapStatus(str, Enum):
    KNOWN = "KNOWN"
    PARTIALLY_KNOWN = "PARTIALLY_KNOWN"
    UNAVAILABLE = "UNAVAILABLE"
    CONFLICTING = "CONFLICTING"
    STALE = "STALE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


@dataclass(frozen=True)
class ResearchGap:
    """
    A single research gap for a company.

    Identifies what information is missing or insufficient
    for comprehensive research.
    """

    gap_id: str
    symbol: str

    category: str
    gap: str

    status: str = ResearchGapStatus.UNAVAILABLE.value
    reason: str = ""

    what_would_resolve: str = ""
    sources_checked: tuple[str, ...] = ()

    evidence_refs: tuple[str, ...] = ()
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    as_of: str = ""

    related_metrics: tuple[str, ...] = ()
    supporting_data: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchGapResult:
    """
    Complete research gap analysis for one company.
    """

    symbol: str
    as_of: str

    gaps: tuple[ResearchGap, ...] = ()
    gap_count: int = 0

    # Summary counts by status
    status_counts: dict[str, int] = field(default_factory=dict)

    # Summary counts by category
    category_counts: dict[str, int] = field(default_factory=dict)

    # Overall coverage assessment
    coverage_score: str | None = None  # HIGH, MEDIUM, LOW
    coverage_explanation: str = ""

    notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Gap detection functions
# ---------------------------------------------------------------------------

_gap_counter = 0


def _next_gap_id(prefix: str) -> str:
    global _gap_counter
    _gap_counter += 1
    return f"GAP-{prefix}-{_gap_counter:04d}"


def _check_financial_data_gaps(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[ResearchGap]:
    """Check for gaps in financial data coverage."""
    gaps: list[ResearchGap] = []

    if not snapshots:
        gaps.append(
            ResearchGap(
                gap_id=_next_gap_id("FIN"),
                symbol=symbol,
                category="financial_data",
                gap="No financial snapshots available",
                status=ResearchGapStatus.UNAVAILABLE.value,
                reason="No financial data has been provided for analysis.",
                what_would_resolve=(
                    "Provide financial snapshots covering "
                    "revenue, profit, cash flow, and balance "
                    "sheet items."
                ),
                sources_checked=(),
                priority="HIGH",
                as_of=as_of.isoformat(),
            )
        )
        return gaps

    # Check for key metrics coverage
    required_metrics = {
        "revenue": "Revenue data",
        "net_profit": "Net profit data",
        "operating_cash_flow": "Operating cash flow data",
        "total_debt": "Total debt data",
        "cash_and_equivalents": "Cash and equivalents data",
    }

    metric_availability: dict[str, int] = {
        metric: 0 for metric in required_metrics
    }

    for snapshot in snapshots:
        for metric in required_metrics:
            if getattr(snapshot, metric, None) is not None:
                metric_availability[metric] += 1

    for metric, description in required_metrics.items():
        available_count = metric_availability[metric]
        total_count = len(snapshots)

        if available_count == 0:
            gaps.append(
                ResearchGap(
                    gap_id=_next_gap_id("FIN"),
                    symbol=symbol,
                    category="financial_data",
                    gap=f"{description} unavailable",
                    status=ResearchGapStatus.UNAVAILABLE.value,
                    reason=(
                        f"{description} is not available in "
                        f"any of the {total_count} periods."
                    ),
                    what_would_resolve=(
                        f"Provide {description.lower()} for "
                        f"at least one reporting period."
                    ),
                    sources_checked=("financial_snapshots",),
                    priority="HIGH",
                    as_of=as_of.isoformat(),
                    related_metrics=(metric,),
                )
            )
        elif available_count < total_count:
            gaps.append(
                ResearchGap(
                    gap_id=_next_gap_id("FIN"),
                    symbol=symbol,
                    category="financial_data",
                    gap=f"{description} partially available",
                    status=ResearchGapStatus.PARTIALLY_KNOWN.value,
                    reason=(
                        f"{description} is available for "
                        f"{available_count} of {total_count} "
                        f"periods."
                    ),
                    what_would_resolve=(
                        f"Provide {description.lower()} for "
                        f"all reporting periods."
                    ),
                    sources_checked=("financial_snapshots",),
                    priority="MEDIUM",
                    as_of=as_of.isoformat(),
                    related_metrics=(metric,),
                    supporting_data={
                        "available_periods": str(available_count),
                        "total_periods": str(total_count),
                    },
                )
            )

    return gaps


def _check_segment_data_gaps(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[ResearchGap]:
    """Check for gaps in segment/business data."""
    gaps: list[ResearchGap] = []

    has_segments = any(
        len(s.segments) > 0 for s in snapshots
    )

    if not has_segments:
        gaps.append(
            ResearchGap(
                gap_id=_next_gap_id("SEG"),
                symbol=symbol,
                category="business_segments",
                gap="No segment/business breakdown available",
                status=ResearchGapStatus.UNAVAILABLE.value,
                reason=(
                    "No segment data is available to analyze "
                    "revenue breakdown by business line."
                ),
                what_would_resolve=(
                    "Provide segment-level revenue and profit "
                    "data from annual reports or financial "
                    "statements."
                ),
                sources_checked=("financial_snapshots",),
                priority="MEDIUM",
                as_of=as_of.isoformat(),
            )
        )

    return gaps


def _check_event_data_gaps(
    events: Sequence[CompanyEvent],
    symbol: str,
    as_of: datetime,
) -> list[ResearchGap]:
    """Check for gaps in event/announcement data."""
    gaps: list[ResearchGap] = []

    if not events:
        gaps.append(
            ResearchGap(
                gap_id=_next_gap_id("EVT"),
                symbol=symbol,
                category="events",
                gap="No company events available",
                status=ResearchGapStatus.UNAVAILABLE.value,
                reason=(
                    "No events or announcements are available "
                    "for timeline analysis."
                ),
                what_would_resolve=(
                    "Provide company events including earnings "
                    "announcements, corporate actions, and "
                    "business developments."
                ),
                sources_checked=(),
                priority="MEDIUM",
                as_of=as_of.isoformat(),
            )
        )
        return gaps

    # Check event recency
    event_dates = [e.event_date for e in events]
    latest_event = max(event_dates)
    days_since_latest = (as_of.date() - latest_event).days

    if days_since_latest > 180:
        gaps.append(
            ResearchGap(
                gap_id=_next_gap_id("EVT"),
                symbol=symbol,
                category="events",
                gap="Stale event data",
                status=ResearchGapStatus.STALE.value,
                reason=(
                    f"Latest event is {days_since_latest} days "
                    f"old (date: {latest_event.isoformat()})."
                ),
                what_would_resolve=(
                    "Provide more recent event data to ensure "
                    "timeline reflects current situation."
                ),
                sources_checked=("company_events",),
                priority="MEDIUM",
                as_of=as_of.isoformat(),
                supporting_data={
                    "latest_event_date": latest_event.isoformat(),
                    "days_since_latest": str(days_since_latest),
                },
            )
        )

    return gaps


def _check_business_profile_gaps(
    profile: BusinessProfile | None,
    symbol: str,
    as_of: datetime,
) -> list[ResearchGap]:
    """Check for gaps in business profile data."""
    gaps: list[ResearchGap] = []

    if profile is None:
        gaps.append(
            ResearchGap(
                gap_id=_next_gap_id("BIZ"),
                symbol=symbol,
                category="business_profile",
                gap="No business profile available",
                status=ResearchGapStatus.UNAVAILABLE.value,
                reason=(
                    "No business profile data is available "
                    "to understand the company's operations."
                ),
                what_would_resolve=(
                    "Provide business profile including "
                    "sector, industry, products, and "
                    "geographic presence."
                ),
                sources_checked=(),
                priority="HIGH",
                as_of=as_of.isoformat(),
            )
        )
        return gaps

    # Check key profile fields
    missing_fields = []
    if not profile.sector:
        missing_fields.append("sector")
    if not profile.industry:
        missing_fields.append("industry")
    if not profile.description:
        missing_fields.append("description")

    if missing_fields:
        gaps.append(
            ResearchGap(
                gap_id=_next_gap_id("BIZ"),
                symbol=symbol,
                category="business_profile",
                gap=f"Incomplete business profile: {', '.join(missing_fields)}",
                status=ResearchGapStatus.PARTIALLY_KNOWN.value,
                reason=(
                    f"Business profile is missing: "
                    f"{', '.join(missing_fields)}."
                ),
                what_would_resolve=(
                    f"Provide {', '.join(missing_fields)} "
                    f"in the business profile."
                ),
                sources_checked=("business_profile",),
                priority="MEDIUM",
                as_of=as_of.isoformat(),
                supporting_data={
                    "missing_fields": ", ".join(missing_fields),
                },
            )
        )

    return gaps


def _check_data_quality_gaps(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[ResearchGap]:
    """Check for data quality issues."""
    gaps: list[ResearchGap] = []

    if not snapshots:
        return gaps

    # Check for stale data
    latest_period = max(s.period_end for s in snapshots)
    days_stale = (as_of.date() - latest_period).days

    if days_stale > 365:
        gaps.append(
            ResearchGap(
                gap_id=_next_gap_id("DQ"),
                symbol=symbol,
                category="data_quality",
                gap="Stale financial data",
                status=ResearchGapStatus.STALE.value,
                reason=(
                    f"Latest financial data is from "
                    f"{latest_period.isoformat()} "
                    f"({days_stale} days ago)."
                ),
                what_would_resolve=(
                    "Provide more recent financial data to "
                    "ensure analysis reflects current situation."
                ),
                sources_checked=("financial_snapshots",),
                priority="HIGH",
                as_of=as_of.isoformat(),
                supporting_data={
                    "latest_period": latest_period.isoformat(),
                    "days_stale": str(days_stale),
                },
            )
        )

    # Check for missing source attribution
    no_source = sum(
        1 for s in snapshots
        if s.source_name is None
    )
    if no_source > 0:
        gaps.append(
            ResearchGap(
                gap_id=_next_gap_id("DQ"),
                symbol=symbol,
                category="data_quality",
                gap="Missing source attribution",
                status=ResearchGapStatus.PARTIALLY_KNOWN.value,
                reason=(
                    f"{no_source} of {len(snapshots)} periods "
                    f"lack source attribution."
                ),
                what_would_resolve=(
                    "Provide source attribution for all "
                    "financial data points."
                ),
                sources_checked=("financial_snapshots",),
                priority="LOW",
                as_of=as_of.isoformat(),
                supporting_data={
                    "periods_without_source": str(no_source),
                    "total_periods": str(len(snapshots)),
                },
            )
        )

    return gaps


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


def analyze_research_gaps(
    *,
    symbol: str,
    as_of: datetime,
    snapshots: Sequence[FinancialSnapshot] = (),
    events: Sequence[CompanyEvent] = (),
    business_profile: BusinessProfile | None = None,
) -> ResearchGapResult:
    """
    Analyze research gaps for one company.

    Identifies what information is known, partially known,
    unavailable, conflicting, stale, or insufficient.
    """
    gaps: list[ResearchGap] = []

    # Run all gap checks
    gaps.extend(
        _check_financial_data_gaps(snapshots, symbol, as_of)
    )
    gaps.extend(
        _check_segment_data_gaps(snapshots, symbol, as_of)
    )
    gaps.extend(
        _check_event_data_gaps(events, symbol, as_of)
    )
    gaps.extend(
        _check_business_profile_gaps(
            business_profile, symbol, as_of
        )
    )
    gaps.extend(
        _check_data_quality_gaps(snapshots, symbol, as_of)
    )

    # Calculate summary counts
    status_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}

    for gap in gaps:
        status_counts[gap.status] = (
            status_counts.get(gap.status, 0) + 1
        )
        category_counts[gap.category] = (
            category_counts.get(gap.category, 0) + 1
        )

    # Calculate coverage score
    high_priority_gaps = sum(
        1 for g in gaps if g.priority == "HIGH"
    )
    unavailable_gaps = sum(
        1 for g in gaps
        if g.status == ResearchGapStatus.UNAVAILABLE.value
    )

    if high_priority_gaps == 0 and unavailable_gaps == 0:
        coverage_score = "HIGH"
        coverage_explanation = (
            "All critical data points are available with "
            "no high-priority gaps."
        )
    elif high_priority_gaps <= 2 and unavailable_gaps <= 2:
        coverage_score = "MEDIUM"
        coverage_explanation = (
            f"{high_priority_gaps} high-priority gaps and "
            f"{unavailable_gaps} unavailable data points "
            f"identified."
        )
    else:
        coverage_score = "LOW"
        coverage_explanation = (
            f"{high_priority_gaps} high-priority gaps and "
            f"{unavailable_gaps} unavailable data points "
            f"significantly limit research coverage."
        )

    return ResearchGapResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        gaps=tuple(gaps),
        gap_count=len(gaps),
        status_counts=status_counts,
        category_counts=category_counts,
        coverage_score=coverage_score,
        coverage_explanation=coverage_explanation,
        notes=(),
    )
