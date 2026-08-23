"""
Cross-domain derived observations engine.

Combines signals from multiple analysis domains to surface
non-obvious observations that require multi-source evidence:
  - Segment divergence vs. overall revenue trend
  - Revenue growth without cash generation
  - Management turnover vs. financial deterioration
  - Technology investment signals
  - Capital structure changes

All observations carry full provenance and are classified
as FACT, OBSERVATION, or INTERPRETATION.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from src.data.company.financials import FinancialSnapshot
from src.data.company.management import ManagementChange


class EvidenceClassification(str):
    FACT = "FACT"
    OBSERVATION = "OBSERVATION"
    INTERPRETATION = "INTERPRETATION"


@dataclass(frozen=True)
class DerivedObservation:
    """A cross-domain derived observation."""

    observation_id: str
    evidence_classification: str
    domain: str
    title: str
    description: str
    source_domains: tuple[str, ...] = ()
    supporting_data: dict[str, str] = field(default_factory=dict)
    explanation: str = ""


@dataclass(frozen=True)
class DerivedObservationsResult:
    """Complete set of derived observations."""

    symbol: str
    as_of: str

    observations: tuple[DerivedObservation, ...] = ()

    fact_count: int = 0
    observation_count: int = 0
    interpretation_count: int = 0

    coverage: dict[str, int] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    available_analyses: tuple[str, ...] = ()
    missing_analyses: tuple[str, ...] = ()


def _ordered_snapshots(
    snapshots: Sequence[FinancialSnapshot],
) -> list[FinancialSnapshot]:
    return sorted(snapshots, key=lambda s: s.period_end)


def derive_revenue_cash_divergence(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
) -> DerivedObservation | None:
    """
    OBSERVATION: Revenue growing while operating cash flow declining.
    """

    ordered = _ordered_snapshots(snapshots)
    if len(ordered) < 2:
        return None

    latest = ordered[-1]
    prev = ordered[-2]

    if (
        latest.revenue is None
        or prev.revenue is None
        or latest.operating_cash_flow is None
        or prev.operating_cash_flow is None
    ):
        return None

    rev_grew = latest.revenue > prev.revenue
    ocf_declined = latest.operating_cash_flow < prev.operating_cash_flow

    if rev_grew and ocf_declined:
        return DerivedObservation(
            observation_id=f"{symbol}_REV_CASH_DIVERGENCE_{latest.period_end}",
            evidence_classification=EvidenceClassification.OBSERVATION,
            domain="FINANCIAL_HEALTH",
            title="Revenue-cash flow divergence",
            description=(
                f"Revenue increased from {prev.revenue} to {latest.revenue} "
                f"but operating cash flow decreased from "
                f"{prev.operating_cash_flow} to {latest.operating_cash_flow}."
            ),
            source_domains=("fundamentals", "cash_flow"),
            supporting_data={
                "previous_revenue": str(prev.revenue),
                "current_revenue": str(latest.revenue),
                "previous_ocf": str(prev.operating_cash_flow),
                "current_ocf": str(latest.operating_cash_flow),
            },
            explanation=(
                "Revenue growth without corresponding cash flow growth "
                "may indicate receivables buildup or other working "
                "capital dynamics."
            ),
        )

    return None


def derive_segment_vs_overall_divergence(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
) -> DerivedObservation | None:
    """
    OBSERVATION: Some segments growing while overall revenue declining.
    """

    ordered = _ordered_snapshots(snapshots)
    if len(ordered) < 2:
        return None

    latest = ordered[-1]
    prev = ordered[-2]

    if not latest.segments or not prev.segments:
        return None

    if latest.revenue is None or prev.revenue is None:
        return None

    overall_declined = latest.revenue < prev.revenue
    if not overall_declined:
        return None

    # Check if any segment grew
    prev_seg_map = {s.segment_name: s.revenue for s in prev.segments}
    growing_segments = []
    for seg in latest.segments:
        prev_rev = prev_seg_map.get(seg.segment_name)
        if (
            seg.revenue is not None
            and prev_rev is not None
            and seg.revenue > prev_rev
        ):
            growing_segments.append(seg.segment_name)

    if growing_segments:
        return DerivedObservation(
            observation_id=f"{symbol}_SEG_DIVERGENCE_{latest.period_end}",
            evidence_classification=EvidenceClassification.OBSERVATION,
            domain="SEGMENT_MIX",
            title="Segment-level divergence during revenue decline",
            description=(
                f"Overall revenue declined from {prev.revenue} to {latest.revenue} "
                f"but segments showed mixed performance: "
                f"{', '.join(growing_segments)} grew."
            ),
            source_domains=("fundamentals", "segments"),
            supporting_data={
                "previous_revenue": str(prev.revenue),
                "current_revenue": str(latest.revenue),
                "growing_segments": ", ".join(growing_segments),
            },
            explanation=(
                "Divergence between segment performance and overall revenue "
                "may indicate mix shifts or segment-specific dynamics."
            ),
        )

    return None


def derive_management_financial_deterioration(
    changes: Sequence[ManagementChange],
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
) -> DerivedObservation | None:
    """
    INTERPRETATION: Management departures coinciding with
    financial deterioration.
    """

    ordered = _ordered_snapshots(snapshots)
    if len(ordered) < 2 or not changes:
        return None

    # Count departures
    departures = [
        c for c in changes
        if "resign" in c.change_type.lower() or "step down" in c.change_type.lower()
    ]

    if len(departures) < 2:
        return None

    # Check financial deterioration
    latest = ordered[-1]
    prev = ordered[-2]

    deterioration_signals = 0
    if (
        latest.net_profit is not None
        and prev.net_profit is not None
        and latest.net_profit < prev.net_profit
    ):
        deterioration_signals += 1

    if (
        latest.revenue is not None
        and prev.revenue is not None
        and latest.revenue < prev.revenue
    ):
        deterioration_signals += 1

    if (
        latest.operating_cash_flow is not None
        and prev.operating_cash_flow is not None
        and latest.operating_cash_flow < prev.operating_cash_flow
    ):
        deterioration_signals += 1

    if deterioration_signals >= 2:
        return DerivedObservation(
            observation_id=f"{symbol}_MGMT_FINANCIAL_{latest.period_end}",
            evidence_classification=EvidenceClassification.INTERPRETATION,
            domain="MANAGEMENT_EXECUTION",
            title="Management departures during financial deterioration",
            description=(
                f"{len(departures)} management departures detected "
                f"coinciding with {deterioration_signals} financial deterioration signals."
            ),
            source_domains=("management", "fundamentals"),
            supporting_data={
                "departure_count": str(len(departures)),
                "deterioration_signals": str(deterioration_signals),
            },
            explanation=(
                "Management departures during financial deterioration "
                "may indicate strategic disagreement or performance "
                "concerns. This is an analytical interpretation, not a fact."
            ),
        )

    return None


def derive_leverage_trajectory_signal(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
) -> DerivedObservation | None:
    """
    FACT: Leverage trajectory analysis.
    """

    ordered = _ordered_snapshots(snapshots)
    if len(ordered) < 3:
        return None

    ratios = []
    for snap in ordered:
        if (
            snap.total_debt is not None
            and snap.shareholders_equity is not None
            and snap.shareholders_equity > 0
        ):
            ratios.append(
                (snap.period_end.isoformat(), snap.total_debt / snap.shareholders_equity)
            )

    if len(ratios) < 3:
        return None

    increasing = all(
        ratios[i][1] < ratios[i + 1][1]
        for i in range(len(ratios) - 1)
    )

    if increasing and ratios[-1][1] > Decimal("1.5"):
        return DerivedObservation(
            observation_id=f"{symbol}_LEVERAGE_TRAJECTORY",
            evidence_classification=EvidenceClassification.FACT,
            domain="CAPITAL_STRUCTURE",
            title="Consistently increasing leverage",
            description=(
                f"Debt-to-equity ratio has increased across "
                f"{len(ratios)} consecutive periods, reaching "
                f"{ratios[-1][1].quantize(Decimal('0.01'))}."
            ),
            source_domains=("fundamentals",),
            supporting_data={
                f"period_{r[0]}": str(r[1].quantize(Decimal("0.01")))
                for r in ratios
            },
            explanation=(
                "Consistent leverage increase is a factual trend. "
                "Whether this represents risk depends on business context."
            ),
        )

    return None


def derive_working_capital_strain(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
) -> DerivedObservation | None:
    """
    OBSERVATION: Working capital strain from receivables and inventory growth.
    """

    ordered = _ordered_snapshots(snapshots)
    if len(ordered) < 2:
        return None

    latest = ordered[-1]
    prev = ordered[-2]

    strain_signals = 0

    if (
        latest.receivables is not None
        and prev.receivables is not None
        and prev.receivables > 0
    ):
        recv_growth = (latest.receivables - prev.receivables) / prev.receivables
        if recv_growth > Decimal("0.2"):
            strain_signals += 1

    if (
        latest.inventory is not None
        and prev.inventory is not None
        and prev.inventory > 0
    ):
        inv_growth = (latest.inventory - prev.inventory) / prev.inventory
        if inv_growth > Decimal("0.2"):
            strain_signals += 1

    if strain_signals >= 2:
        return DerivedObservation(
            observation_id=f"{symbol}_WC_STRAIN_{latest.period_end}",
            evidence_classification=EvidenceClassification.OBSERVATION,
            domain="WORKING_CAPITAL",
            title="Working capital strain",
            description="Both receivables and inventory grew significantly, indicating working capital strain.",
            source_domains=("fundamentals",),
            supporting_data={
                "current_receivables": str(latest.receivables),
                "previous_receivables": str(prev.receivables),
                "current_inventory": str(latest.inventory),
                "previous_inventory": str(prev.inventory),
            },
            explanation=(
                "Significant growth in both receivables and inventory "
                "may indicate collection difficulties or inventory buildup."
            ),
        )

    return None


def analyze_derived_observations(
    snapshots: Sequence[FinancialSnapshot],
    management_changes: Sequence[ManagementChange],
    symbol: str,
    as_of: datetime,
) -> DerivedObservationsResult:
    """
    Run the full derived observations pipeline.
    """

    notes: list[str] = []
    available: list[str] = []
    missing: list[str] = []

    observations: list[DerivedObservation] = []

    # Revenue-cash divergence
    obs = derive_revenue_cash_divergence(snapshots, symbol)
    if obs:
        observations.append(obs)
        available.append("revenue_cash_divergence")
    else:
        missing.append("revenue_cash_divergence")

    # Segment vs overall divergence
    obs = derive_segment_vs_overall_divergence(snapshots, symbol)
    if obs:
        observations.append(obs)
        available.append("segment_divergence")
    else:
        missing.append("segment_divergence")

    # Management-financial deterioration
    obs = derive_management_financial_deterioration(
        management_changes, snapshots, symbol
    )
    if obs:
        observations.append(obs)
        available.append("management_financial_deterioration")
    else:
        missing.append("management_financial_deterioration")

    # Leverage trajectory
    obs = derive_leverage_trajectory_signal(snapshots, symbol)
    if obs:
        observations.append(obs)
        available.append("leverage_trajectory")
    else:
        missing.append("leverage_trajectory")

    # Working capital strain
    obs = derive_working_capital_strain(snapshots, symbol)
    if obs:
        observations.append(obs)
        available.append("working_capital_strain")
    else:
        missing.append("working_capital_strain")

    # Counts
    fact_count = sum(1 for o in observations if o.evidence_classification == EvidenceClassification.FACT)
    observation_count = sum(1 for o in observations if o.evidence_classification == EvidenceClassification.OBSERVATION)
    interpretation_count = sum(1 for o in observations if o.evidence_classification == EvidenceClassification.INTERPRETATION)

    return DerivedObservationsResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        observations=tuple(observations),
        fact_count=fact_count,
        observation_count=observation_count,
        interpretation_count=interpretation_count,
        notes=tuple(notes),
        available_analyses=tuple(available),
        missing_analyses=tuple(missing),
    )
