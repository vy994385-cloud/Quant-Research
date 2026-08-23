"""
Deep business intelligence orchestrator.

Combines all business intelligence dimensions into a single
typed result:
  - Business profile (sector, industry, employees)
  - Business analysis (segments, quality signals)
  - Competitive analysis (peer benchmarking)
  - Management analysis (changes, capital allocation)
  - Risk analysis (multi-dimensional)
  - Derived observations (cross-domain)

This is the primary entry point for Phase 4
business intelligence research backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence

from src.analysis.business_analysis import (
    BusinessAnalysisResult,
    analyze_business,
)
from src.analysis.competitive_analysis import (
    CompetitiveAnalysisResult,
    analyze_competitive,
)
from src.analysis.derived_observations import (
    DerivedObservationsResult,
    analyze_derived_observations,
)
from src.analysis.management_analysis import (
    ManagementAnalysisResult,
    analyze_management,
)
from src.analysis.risk_analysis import (
    RiskAnalysisResult,
    analyze_risks,
)
from src.data.company.business_profile import BusinessProfile
from src.data.company.financials import FinancialSnapshot
from src.data.company.management import ManagementChange


def _pit_filter_snapshots(
    snapshots: Sequence[FinancialSnapshot],
    as_of: datetime,
) -> list[FinancialSnapshot]:
    """Filter snapshots available at or before as_of.

    Rejects snapshots with missing available_at or future available_at.
    """
    filtered: list[FinancialSnapshot] = []
    for s in snapshots:
        if s.available_at is None:
            continue
        if s.available_at > as_of:
            continue
        filtered.append(s)
    return filtered


def _pit_filter_management_changes(
    changes: Sequence[ManagementChange],
    as_of: datetime,
) -> list[ManagementChange]:
    """Filter management changes to those effective at or before as_of."""
    return [c for c in changes if c.effective_date <= as_of.date()]


@dataclass(frozen=True)
class BusinessIntelligenceResult:
    """
    Complete deep business intelligence result for one company.

    Combines all BI dimensions into a single serialisable
    dataclass.
    """

    symbol: str
    as_of: str

    # Profile
    has_profile: bool = False
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    employees: int | None = None

    # Business analysis
    business_analysis: BusinessAnalysisResult | None = None

    # Competitive analysis
    competitive_analysis: CompetitiveAnalysisResult | None = None

    # Management analysis
    management_analysis: ManagementAnalysisResult | None = None

    # Risk analysis
    risk_analysis: RiskAnalysisResult | None = None

    # Derived observations
    derived_observations: DerivedObservationsResult | None = None

    # Coverage and notes
    available_analyses: tuple[str, ...] = ()
    missing_analyses: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @property
    def total_observations(self) -> int:
        """Total observations across all dimensions."""
        count = 0
        if self.business_analysis:
            count += len(self.business_analysis.quality_signals)
        if self.competitive_analysis:
            count += len(self.competitive_analysis.signals)
        if self.management_analysis:
            count += len(self.management_analysis.allocation_signals)
        if self.risk_analysis:
            count += len(self.risk_analysis.observations)
        if self.derived_observations:
            count += len(self.derived_observations.observations)
        return count

    @property
    def risk_count(self) -> int:
        if self.risk_analysis is None:
            return 0
        return len(self.risk_analysis.observations)

    @property
    def derived_count(self) -> int:
        if self.derived_observations is None:
            return 0
        return len(self.derived_observations.observations)


def analyze_business_intelligence(
    snapshots: Sequence[FinancialSnapshot],
    profile: BusinessProfile | None,
    peer_snapshots: Sequence[FinancialSnapshot],
    management_changes: Sequence[ManagementChange],
    symbol: str,
    as_of: datetime,
) -> BusinessIntelligenceResult:
    """
    Run the full business intelligence analysis pipeline.

    This is the primary entry point. It is deterministic and
    returns an empty result when data is insufficient.

    PIT enforcement: only snapshots with available_at <= as_of and
    management changes with effective_date <= as_of are used.
    """

    notes: list[str] = []
    available: list[str] = []
    missing: list[str] = []

    pit_snapshots = _pit_filter_snapshots(snapshots, as_of)
    pit_changes = _pit_filter_management_changes(
        management_changes, as_of
    )

    rejected_snapshots = len(snapshots) - len(pit_snapshots)
    rejected_changes = len(management_changes) - len(pit_changes)
    if rejected_snapshots > 0:
        notes.append(
            f"PIT filter: {rejected_snapshots} snapshot(s) rejected "
            f"(missing available_at or available_at > as_of)."
        )
    if rejected_changes > 0:
        notes.append(
            f"PIT filter: {rejected_changes} management change(s) "
            f"rejected (effective_date > as_of)."
        )

    if not pit_snapshots:
        notes.append("No financial data available for business intelligence.")

        return BusinessIntelligenceResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            has_profile=profile is not None,
            sector=profile.sector if profile else None,
            industry=profile.industry if profile else None,
            country=profile.country if profile else None,
            employees=profile.full_time_employees if profile else None,
            missing_analyses=(
                "business_analysis",
                "competitive_analysis",
                "management_analysis",
                "risk_analysis",
                "derived_observations",
            ),
            notes=tuple(notes),
        )

    # ---- Business analysis ----
    business_result = analyze_business(
        snapshots=pit_snapshots,
        profile=profile,
        symbol=symbol,
        as_of=as_of,
    )
    if business_result.available_analyses:
        available.append("business_analysis")
    else:
        missing.append("business_analysis")

    # ---- Competitive analysis ----
    latest_snapshot = sorted(
        pit_snapshots, key=lambda s: s.period_end
    )[-1]
    competitive_result = analyze_competitive(
        company_snapshot=latest_snapshot,
        peer_snapshots=peer_snapshots,
        symbol=symbol,
        as_of=as_of,
    )
    if competitive_result.available_analyses:
        available.append("competitive_analysis")
    else:
        missing.append("competitive_analysis")

    # ---- Management analysis ----
    management_result = analyze_management(
        changes=pit_changes,
        snapshots=pit_snapshots,
        symbol=symbol,
        as_of=as_of,
    )
    if management_result.available_analyses:
        available.append("management_analysis")
    else:
        missing.append("management_analysis")

    # ---- Risk analysis ----
    risk_result = analyze_risks(
        snapshots=pit_snapshots,
        profile=profile,
        management_changes=pit_changes,
        symbol=symbol,
        as_of=as_of,
    )
    if risk_result.available_analyses:
        available.append("risk_analysis")
    else:
        missing.append("risk_analysis")

    # ---- Derived observations ----
    derived_result = analyze_derived_observations(
        snapshots=pit_snapshots,
        management_changes=pit_changes,
        symbol=symbol,
        as_of=as_of,
    )
    if derived_result.available_analyses:
        available.append("derived_observations")
    else:
        missing.append("derived_observations")

    return BusinessIntelligenceResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        has_profile=profile is not None,
        sector=profile.sector if profile else None,
        industry=profile.industry if profile else None,
        country=profile.country if profile else None,
        employees=profile.full_time_employees if profile else None,
        business_analysis=business_result,
        competitive_analysis=competitive_result,
        management_analysis=management_result,
        risk_analysis=risk_result,
        derived_observations=derived_result,
        available_analyses=tuple(available),
        missing_analyses=tuple(missing),
        notes=tuple(notes),
    )
