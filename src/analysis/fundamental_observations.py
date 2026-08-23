"""
Typed research-observation model for fundamental analysis.

Every derived observation carries:
  - metric(s) used
  - period
  - value / change
  - calculation / method
  - source / provenance
  - available_at, as_of
  - data-quality / status
  - positive / negative / neutral direction

This module provides the dataclass and a builder that converts
trajectory, earnings-quality, and balance-sheet observations into
the unified observation format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Sequence

from src.data.company.financials import FinancialSnapshot


class ObservationDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class ObservationStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    UNVERIFIED = "UNVERIFIED"


class ObservationSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class FundamentalObservation:
    """
    A single research observation derived from financial data.

    Every field is required or has a safe default.  The model
    is intentionally verbose to make provenance traceable.
    """

    observation_id: str
    symbol: str

    category: str
    observation_type: str

    period: str
    metric: str

    value: str | None = None
    previous_value: str | None = None
    change: str | None = None
    change_pct: str | None = None

    calculation_method: str = ""

    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None

    available_at: str | None = None
    as_of: str | None = None

    status: str = ObservationStatus.AVAILABLE.value
    direction: str = ObservationDirection.NEUTRAL.value
    severity: str = ObservationSeverity.LOW.value

    explanation: str = ""

    related_metrics: tuple[str, ...] = ()
    supporting_data: dict[str, str] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class FundamentalObservationSet:
    """
    A collection of observations for one company at one point
    in time.
    """

    symbol: str
    as_of: str

    trajectory_observations: tuple[
        FundamentalObservation, ...
    ] = ()
    earnings_quality_observations: tuple[
        FundamentalObservation, ...
    ] = ()
    balance_sheet_observations: tuple[
        FundamentalObservation, ...
    ] = ()
    anomaly_observations: tuple[
        FundamentalObservation, ...
    ] = ()

    total_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0

    coverage: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------

_observation_counter = 0


def _next_id(prefix: str) -> str:
    global _observation_counter
    _observation_counter += 1
    return f"{prefix}-{_observation_counter:06d}"


def _snapshot_source(
    snapshot: FinancialSnapshot,
) -> tuple[str | None, str | None, str | None]:
    return (
        snapshot.source_name,
        snapshot.source_type,
        snapshot.source_url,
    )


def _snapshot_as_of(
    snapshot: FinancialSnapshot,
) -> tuple[str | None, str | None]:
    available = None
    if snapshot.available_at is not None:
        available = snapshot.available_at.isoformat()
    elif snapshot.published_at is not None:
        available = snapshot.published_at.isoformat()

    effective = None
    if snapshot.effective_at is not None:
        effective = snapshot.effective_at.isoformat()

    return available, effective


def _determine_direction(
    change: str | None,
    metric: str,
) -> str:
    """Heuristic direction for a numeric change."""
    if change is None:
        return ObservationDirection.NEUTRAL.value

    try:
        val = Decimal(change)
    except Exception:
        return ObservationDirection.NEUTRAL.value

    # Higher is generally positive for most metrics.
    # For debt, lower is positive.
    negative_is_bad_metrics = {
        "total_debt",
        "current_liabilities",
        "receivables",
        "inventory",
    }

    if metric in negative_is_bad_metrics:
        if val < 0:
            return ObservationDirection.POSITIVE.value
        if val > 0:
            return ObservationDirection.NEGATIVE.value
    else:
        if val > 0:
            return ObservationDirection.POSITIVE.value
        if val < 0:
            return ObservationDirection.NEGATIVE.value

    return ObservationDirection.NEUTRAL.value


def _determine_severity(
    observation_type: str,
    flagged: bool = False,
    persistent: bool = False,
) -> str:
    if persistent:
        return ObservationSeverity.HIGH.value
    if flagged:
        return ObservationSeverity.MEDIUM.value

    anomaly_types = {
        "receivables_growth_divergence",
        "inventory_growth_divergence",
        "accelerating_debt",
        "persistent_cash_profit_divergence",
        "liquidity_deterioration",
        "equity_erosion",
    }

    if observation_type in anomaly_types:
        return ObservationSeverity.MEDIUM.value

    return ObservationSeverity.LOW.value


# ---------------------------------------------------------------------------
# Observation builders
# ---------------------------------------------------------------------------

def build_trajectory_observations(
    trajectories: list,
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[FundamentalObservation]:
    """Convert trajectory analyses into FundamentalObservation list."""
    observations: list[FundamentalObservation] = []

    # Build a source lookup by period
    source_by_period: dict[
        str, tuple[str | None, str | None, str | None]
    ] = {}
    as_of_by_period: dict[str, tuple[str | None, str | None]] = {}

    for s in snapshots:
        p = s.period_end.isoformat()
        source_by_period[p] = _snapshot_source(s)
        as_of_by_period[p] = _snapshot_as_of(s)

    for traj in trajectories:
        if not traj.first_period:
            continue

        src = source_by_period.get(
            traj.first_period, (None, None, None)
        )
        ao = as_of_by_period.get(
            traj.first_period, (None, None)
        )

        direction = _determine_direction(
            traj.total_change, traj.metric
        )

        observations.append(
            FundamentalObservation(
                observation_id=_next_id("TRAJ"),
                symbol=symbol,
                category="trajectory",
                observation_type=f"{traj.metric}_trajectory",
                period=f"{traj.first_period} to {traj.last_period}",
                metric=traj.metric,
                value=traj.last_value,
                previous_value=traj.first_value,
                change=traj.total_change,
                change_pct=traj.total_change_pct,
                calculation_method=(
                    f"CAGR: {traj.cagr}, "
                    f"total change: {traj.total_change_pct}%"
                ),
                source_name=src[0],
                source_type=src[1],
                source_url=src[2],
                available_at=ao[0],
                as_of=as_of.isoformat(),
                status=(
                    ObservationStatus.AVAILABLE.value
                    if traj.period_count >= 2
                    else ObservationStatus.PARTIAL.value
                ),
                direction=direction,
                severity=ObservationSeverity.LOW.value,
                explanation=traj.explanation,
                related_metrics=(traj.metric,),
                supporting_data={
                    "cagr": traj.cagr or "",
                    "periods": str(traj.period_count),
                    "direction": traj.direction or "",
                    "acceleration": traj.acceleration or "",
                },
            )
        )

    return observations


def build_margin_observations(
    margin_trajectories: list,
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[FundamentalObservation]:
    """Convert margin trajectories into observations."""
    observations: list[FundamentalObservation] = []

    for mt in margin_trajectories:
        direction = (
            ObservationDirection.POSITIVE.value
            if mt.direction == "EXPANDING"
            else (
                ObservationDirection.NEGATIVE.value
                if mt.direction == "CONTRACTING"
                else ObservationDirection.NEUTRAL.value
            )
        )

        observations.append(
            FundamentalObservation(
                observation_id=_next_id("MARGIN"),
                symbol=symbol,
                category="margin_trajectory",
                observation_type=f"{mt.margin_name}_trajectory",
                period=f"{mt.first_period} to {mt.last_period}",
                metric=mt.margin_name,
                value=mt.last_value,
                previous_value=mt.first_value,
                change=mt.total_change_pp,
                calculation_method=(
                    "Net profit margin, operating margin, "
                    "OCF margin, or FCF margin as percentage "
                    "of revenue"
                ),
                available_at=None,
                as_of=as_of.isoformat(),
                status=ObservationStatus.AVAILABLE.value,
                direction=direction,
                severity=(
                    ObservationSeverity.MEDIUM.value
                    if mt.persistent
                    else ObservationSeverity.LOW.value
                ),
                explanation=mt.explanation,
                related_metrics=(mt.margin_name,),
                supporting_data={
                    "persistent": str(mt.persistent),
                    "total_change_pp": mt.total_change_pp or "",
                },
            )
        )

    return observations


def build_earnings_quality_observations(
    eq_observations: list,
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[FundamentalObservation]:
    """Convert earnings-quality observations into FundamentalObservation list."""
    observations: list[FundamentalObservation] = []

    for eq in eq_observations:
        # Determine status based on data availability
        status = ObservationStatus.AVAILABLE.value
        if not eq.cash_profit_comparisons and not eq.growth_divergences:
            status = ObservationStatus.MISSING.value

        observations.append(
            FundamentalObservation(
                observation_id=_next_id("EQ"),
                symbol=symbol,
                category="earnings_quality",
                observation_type=eq.observation_type,
                period=f"{eq.first_period} to {eq.last_period}",
                metric=eq.metric,
                value=eq.value,
                calculation_method=(
                    "Cash-profit ratio comparison, "
                    "receivables/inventory growth vs "
                    "revenue growth divergence"
                ),
                available_at=None,
                as_of=as_of.isoformat(),
                status=status,
                direction=(
                    ObservationDirection.NEGATIVE.value
                    if eq.severity in ("MEDIUM", "HIGH")
                    else ObservationDirection.NEUTRAL.value
                ),
                severity=_determine_severity(
                    eq.observation_type,
                    persistent=eq.persistent,
                ),
                explanation=eq.explanation,
                related_metrics=(eq.metric,),
                supporting_data={
                    "periods_covered": str(eq.periods_covered),
                    "persistent": str(eq.persistent),
                },
            )
        )

    return observations


def build_balance_sheet_observations(
    bs_observations: list,
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[FundamentalObservation]:
    """Convert balance-sheet observations into FundamentalObservation list."""
    observations: list[FundamentalObservation] = []

    for bs in bs_observations:
        observations.append(
            FundamentalObservation(
                observation_id=_next_id("BS"),
                symbol=symbol,
                category="balance_sheet_quality",
                observation_type=bs.observation_type,
                period=f"{bs.first_period} to {bs.last_period}",
                metric=bs.observation_type,
                calculation_method=(
                    "Debt vs revenue growth, current-ratio "
                    "trajectory, working-capital trajectory, "
                    "cash/debt trajectory, equity changes"
                ),
                available_at=None,
                as_of=as_of.isoformat(),
                status=ObservationStatus.AVAILABLE.value,
                direction=(
                    ObservationDirection.NEGATIVE.value
                    if bs.severity in ("MEDIUM", "HIGH")
                    else ObservationDirection.NEUTRAL.value
                ),
                severity=_determine_severity(
                    bs.observation_type,
                    persistent=bs.persistent,
                ),
                explanation=bs.explanation,
                related_metrics=(bs.observation_type,),
                supporting_data={
                    "periods_covered": str(bs.periods_covered),
                    "persistent": str(bs.persistent),
                },
            )
        )

    return observations


def build_anomaly_observations(
    anomalies: list,
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[FundamentalObservation]:
    """Convert FinancialAnomaly objects into FundamentalObservation list."""
    observations: list[FundamentalObservation] = []

    for anomaly in anomalies:
        observations.append(
            FundamentalObservation(
                observation_id=_next_id("ANOM"),
                symbol=symbol,
                category="anomaly",
                observation_type=f"{anomaly.metric}_anomaly",
                period="",
                metric=anomaly.metric,
                value=str(anomaly.current_change),
                previous_value=(
                    str(anomaly.comparison_change)
                    if anomaly.comparison_change is not None
                    else None
                ),
                calculation_method=(
                    "Percentage-point divergence vs "
                    "comparison metric"
                ),
                available_at=None,
                as_of=as_of.isoformat(),
                status=ObservationStatus.AVAILABLE.value,
                direction=ObservationDirection.NEGATIVE.value,
                severity=_determine_severity(
                    f"{anomaly.metric}_anomaly",
                    flagged=anomaly.severity in (
                        "MEDIUM",
                        "HIGH",
                        "CRITICAL",
                    ),
                ),
                explanation=anomaly.explanation,
                related_metrics=(anomaly.metric,),
                supporting_data={
                    "current_change": str(
                        anomaly.current_change
                    ),
                    "comparison_change": (
                        str(anomaly.comparison_change)
                        if anomaly.comparison_change
                        is not None
                        else ""
                    ),
                    "severity": anomaly.severity,
                },
            )
        )

    return observations


# ---------------------------------------------------------------------------
# High-level builder
# ---------------------------------------------------------------------------

def build_fundamental_observations(
    *,
    symbol: str,
    as_of: datetime,
    snapshots: Sequence[FinancialSnapshot],
    trajectory_results: dict,
    earnings_quality_results: list,
    balance_sheet_results: list,
    anomaly_results: list,
) -> FundamentalObservationSet:
    """
    Build a complete FundamentalObservationSet from all analyses.

    This is the main entry point that the deep-fundamental
    orchestrator calls.
    """
    traj_obs = build_trajectory_observations(
        trajectory_results.get("trajectories", []),
        snapshots,
        symbol,
        as_of,
    )

    margin_obs = build_margin_observations(
        trajectory_results.get("margin_trajectories", []),
        snapshots,
        symbol,
        as_of,
    )

    eq_obs = build_earnings_quality_observations(
        earnings_quality_results,
        snapshots,
        symbol,
        as_of,
    )

    bs_obs = build_balance_sheet_observations(
        balance_sheet_results,
        snapshots,
        symbol,
        as_of,
    )

    anom_obs = build_anomaly_observations(
        anomaly_results,
        snapshots,
        symbol,
        as_of,
    )

    all_obs = (
        traj_obs
        + margin_obs
        + eq_obs
        + bs_obs
        + anom_obs
    )

    positive = sum(
        1
        for o in all_obs
        if o.direction == ObservationDirection.POSITIVE.value
    )
    negative = sum(
        1
        for o in all_obs
        if o.direction == ObservationDirection.NEGATIVE.value
    )
    neutral = sum(
        1
        for o in all_obs
        if o.direction == ObservationDirection.NEUTRAL.value
    )

    # Coverage: how many categories have observations
    coverage: dict[str, int] = {}
    for o in all_obs:
        coverage[o.category] = coverage.get(o.category, 0) + 1

    notes: list[str] = []
    if not snapshots:
        notes.append(
            "No financial data available for observation building."
        )

    return FundamentalObservationSet(
        symbol=symbol,
        as_of=as_of.isoformat(),
        trajectory_observations=tuple(traj_obs + margin_obs),
        earnings_quality_observations=tuple(eq_obs),
        balance_sheet_observations=tuple(bs_obs),
        anomaly_observations=tuple(anom_obs),
        total_count=len(all_obs),
        positive_count=positive,
        negative_count=negative,
        neutral_count=neutral,
        coverage=coverage,
        notes=notes,
    )
