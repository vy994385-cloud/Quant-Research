"""
Research report data contract module.

Defines the complete data contract for research reports,
ensuring all required sections are available and properly
structured. This module validates that the backend can
produce all necessary data for a comprehensive research report.

Sections:
  - Company Overview
  - Business Model
  - Financials
  - Financial Quality
  - Cash Flow
  - Balance Sheet
  - Growth
  - Market Behaviour
  - Technical Observations
  - Events
  - Technology/Future Intelligence
  - Sector Context
  - Positive Evidence
  - Negative Evidence
  - Conflicting Evidence
  - Risks
  - Unknowns
  - Research Gaps
  - Data Quality
  - Provenance
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SectionStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True)
class SectionCoverage:
    """
    Status of a single report section.
    """

    section_name: str
    status: str = SectionStatus.MISSING.value
    data_available: bool = False
    observation_count: int = 0
    completeness_pct: float = 0.0
    notes: tuple[str, ...] = ()
    source_modules: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReportDataContract:
    """
    Complete data contract for a research report.

    Validates that all required sections are available
    and tracks completeness of each section.
    """

    symbol: str
    as_of: str

    # Section coverage
    sections: tuple[SectionCoverage, ...] = ()

    # Overall metrics
    total_sections: int = 0
    complete_sections: int = 0
    partial_sections: int = 0
    missing_sections: int = 0

    overall_completeness_pct: float = 0.0
    overall_status: str = SectionStatus.MISSING.value

    # Provenance
    data_sources: tuple[str, ...] = ()
    last_updated: str | None = None

    notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Required sections definition
# ---------------------------------------------------------------------------

REQUIRED_SECTIONS = [
    "company_overview",
    "business_model",
    "financials",
    "financial_quality",
    "cash_flow",
    "balance_sheet",
    "growth",
    "market_behaviour",
    "technical_observations",
    "events",
    "technology_intelligence",
    "sector_context",
    "positive_evidence",
    "negative_evidence",
    "conflicting_evidence",
    "risks",
    "unknowns",
    "research_gaps",
    "data_quality",
    "provenance",
]

SECTION_DESCRIPTIONS = {
    "company_overview": "Basic company information, sector, industry",
    "business_model": "Products, services, segments, geography",
    "financials": "Revenue, profit, margins, key metrics",
    "financial_quality": "Earnings quality, accruals, anomalies",
    "cash_flow": "OCF, FCF, working capital, cash conversion",
    "balance_sheet": "Debt, equity, liquidity, leverage",
    "growth": "Revenue growth, profit growth, margin trends",
    "market_behaviour": "Returns, volatility, volume, trend",
    "technical_observations": "Indicators, signals, patterns",
    "events": "Timeline, corporate actions, announcements",
    "technology_intelligence": "AI, digital, patents, R&D",
    "sector_context": "Industry trends, competitive position",
    "positive_evidence": "Evidence supporting positive observations",
    "negative_evidence": "Evidence supporting negative observations",
    "conflicting_evidence": "Evidence with mixed signals",
    "risks": "Identified risks and concerns",
    "unknowns": "Information gaps and missing data",
    "research_gaps": "What additional research would help",
    "data_quality": "Data freshness, coverage, limitations",
    "provenance": "Sources, timestamps, methodologies",
}


# ---------------------------------------------------------------------------
# Builder functions
# ---------------------------------------------------------------------------


def _check_section(
    section_name: str,
    data: Any,
    observation_count: int = 0,
    source_modules: tuple[str, ...] = (),
) -> SectionCoverage:
    """Check if a section has data available."""
    if data is None:
        return SectionCoverage(
            section_name=section_name,
            status=SectionStatus.MISSING.value,
            data_available=False,
            observation_count=0,
            completeness_pct=0.0,
            source_modules=source_modules,
        )

    # Check for empty collections
    if isinstance(data, (list, tuple, dict)):
        if len(data) == 0:
            return SectionCoverage(
                section_name=section_name,
                status=SectionStatus.MISSING.value,
                data_available=False,
                observation_count=0,
                completeness_pct=0.0,
                source_modules=source_modules,
            )

    # Data is available
    completeness = min(100.0, observation_count * 10)  # Rough estimate

    status = (
        SectionStatus.COMPLETE.value
        if completeness >= 80
        else SectionStatus.PARTIAL.value
        if completeness > 0
        else SectionStatus.MISSING.value
    )

    return SectionCoverage(
        section_name=section_name,
        status=status,
        data_available=True,
        observation_count=observation_count,
        completeness_pct=completeness,
        source_modules=source_modules,
    )


def build_report_data_contract(
    *,
    symbol: str,
    as_of: datetime,
    # Company data
    company_profile: Any = None,
    business_profile: Any = None,
    # Financial data
    financial_snapshots: tuple = (),
    # Analysis results
    deep_fundamental: Any = None,
    cash_flow_quality: Any = None,
    balance_sheet_deep: Any = None,
    # Market data
    market_observations: tuple = (),
    deep_technical: Any = None,
    # Event data
    event_analysis: Any = None,
    event_timeline: Any = None,
    # Business intelligence
    business_intelligence: Any = None,
    # Research gaps
    research_gaps: Any = None,
    # Cross-domain
    cross_domain: Any = None,
) -> ReportDataContract:
    """
    Build a complete report data contract.

    Validates that all required sections are available and
    tracks completeness of each section.
    """
    sections: list[SectionCoverage] = []

    # Company Overview
    sections.append(
        _check_section(
            "company_overview",
            company_profile,
            source_modules=("company_profile",),
        )
    )

    # Business Model
    sections.append(
        _check_section(
            "business_model",
            business_profile,
            source_modules=("business_profile", "business_intelligence"),
        )
    )

    # Financials
    sections.append(
        _check_section(
            "financials",
            financial_snapshots,
            observation_count=len(financial_snapshots),
            source_modules=("financial_snapshots",),
        )
    )

    # Financial Quality
    sections.append(
        _check_section(
            "financial_quality",
            deep_fundamental,
            observation_count=(
                deep_fundamental.observation_set.total_count
                if deep_fundamental
                and deep_fundamental.observation_set
                else 0
            ),
            source_modules=("deep_fundamental",),
        )
    )

    # Cash Flow
    sections.append(
        _check_section(
            "cash_flow",
            cash_flow_quality,
            observation_count=(
                cash_flow_quality.observation_count
                if cash_flow_quality
                else 0
            ),
            source_modules=("cash_flow_quality",),
        )
    )

    # Balance Sheet
    sections.append(
        _check_section(
            "balance_sheet",
            balance_sheet_deep,
            observation_count=(
                balance_sheet_deep.observation_count
                if balance_sheet_deep
                else 0
            ),
            source_modules=("balance_sheet_deep",),
        )
    )

    # Growth
    growth_data = None
    if deep_fundamental and deep_fundamental.trajectories:
        growth_data = deep_fundamental.trajectories
    sections.append(
        _check_section(
            "growth",
            growth_data,
            observation_count=(
                len(deep_fundamental.trajectories)
                if deep_fundamental
                else 0
            ),
            source_modules=("deep_fundamental", "financial_trends"),
        )
    )

    # Market Behaviour
    sections.append(
        _check_section(
            "market_behaviour",
            market_observations,
            observation_count=len(market_observations),
            source_modules=("market_observations",),
        )
    )

    # Technical Observations
    sections.append(
        _check_section(
            "technical_observations",
            deep_technical,
            observation_count=(
                deep_technical.observation_set.total_count
                if deep_technical
                and deep_technical.observation_set
                else 0
            ),
            source_modules=("deep_technical",),
        )
    )

    # Events
    sections.append(
        _check_section(
            "events",
            event_timeline or event_analysis,
            observation_count=(
                event_timeline.entry_count
                if event_timeline
                else (
                    event_analysis.event_count
                    if event_analysis
                    else 0
                )
            ),
            source_modules=("event_analysis", "event_timeline"),
        )
    )

    # Technology Intelligence
    sections.append(
        _check_section(
            "technology_intelligence",
            business_intelligence,
            source_modules=("business_intelligence",),
        )
    )

    # Sector Context
    sections.append(
        _check_section(
            "sector_context",
            business_intelligence,
            source_modules=("business_intelligence",),
        )
    )

    # Positive Evidence
    positive_evidence = None
    if cross_domain and cross_domain.positive_count > 0:
        positive_evidence = cross_domain
    sections.append(
        _check_section(
            "positive_evidence",
            positive_evidence,
            observation_count=(
                cross_domain.positive_count
                if cross_domain
                else 0
            ),
            source_modules=("cross_domain",),
        )
    )

    # Negative Evidence
    negative_evidence = None
    if cross_domain and cross_domain.negative_count > 0:
        negative_evidence = cross_domain
    sections.append(
        _check_section(
            "negative_evidence",
            negative_evidence,
            observation_count=(
                cross_domain.negative_count
                if cross_domain
                else 0
            ),
            source_modules=("cross_domain",),
        )
    )

    # Conflicting Evidence
    conflicting_evidence = None
    if cross_domain and cross_domain.mixed_count > 0:
        conflicting_evidence = cross_domain
    sections.append(
        _check_section(
            "conflicting_evidence",
            conflicting_evidence,
            observation_count=(
                cross_domain.mixed_count
                if cross_domain
                else 0
            ),
            source_modules=("cross_domain",),
        )
    )

    # Risks
    risks = None
    if business_intelligence and hasattr(business_intelligence, 'risk_analysis'):
        risks = business_intelligence.risk_analysis
    sections.append(
        _check_section(
            "risks",
            risks,
            source_modules=("business_intelligence",),
        )
    )

    # Unknowns
    unknowns = None
    if research_gaps:
        unknowns = research_gaps
    sections.append(
        _check_section(
            "unknowns",
            unknowns,
            observation_count=(
                research_gaps.gap_count
                if research_gaps
                else 0
            ),
            source_modules=("research_gaps",),
        )
    )

    # Research Gaps
    sections.append(
        _check_section(
            "research_gaps",
            research_gaps,
            observation_count=(
                research_gaps.gap_count
                if research_gaps
                else 0
            ),
            source_modules=("research_gaps",),
        )
    )

    # Data Quality
    data_quality = research_gaps  # Reuse research gaps for data quality
    sections.append(
        _check_section(
            "data_quality",
            data_quality,
            source_modules=("research_gaps",),
        )
    )

    # Provenance
    provenance_data = financial_snapshots if financial_snapshots else None
    sections.append(
        _check_section(
            "provenance",
            provenance_data,
            source_modules=("financial_snapshots",),
        )
    )

    # Calculate summary metrics
    complete = sum(
        1 for s in sections
        if s.status == SectionStatus.COMPLETE.value
    )
    partial = sum(
        1 for s in sections
        if s.status == SectionStatus.PARTIAL.value
    )
    missing = sum(
        1 for s in sections
        if s.status == SectionStatus.MISSING.value
    )

    total = len(sections)
    overall_pct = (
        (complete * 100 + partial * 50) / total
        if total > 0
        else 0.0
    )

    if complete == total:
        overall_status = SectionStatus.COMPLETE.value
    elif missing == 0:
        overall_status = SectionStatus.PARTIAL.value
    else:
        overall_status = SectionStatus.MISSING.value

    # Collect data sources
    data_sources: set[str] = set()
    for s in sections:
        data_sources.update(s.source_modules)

    return ReportDataContract(
        symbol=symbol,
        as_of=as_of.isoformat(),
        sections=tuple(sections),
        total_sections=total,
        complete_sections=complete,
        partial_sections=partial,
        missing_sections=missing,
        overall_completeness_pct=overall_pct,
        overall_status=overall_status,
        data_sources=tuple(sorted(data_sources)),
        last_updated=as_of.isoformat(),
        notes=(),
    )
