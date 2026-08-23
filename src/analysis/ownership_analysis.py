"""
Ownership analysis engine.

Analyzes ownership snapshots over time to derive:
  - Ownership concentration (promoter vs non-promoter)
  - Institutional holdings trends
  - Pledge percentage changes
  - Ownership signals (increases, decreases, concentration shifts)

All analysis is deterministic and PIT-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Sequence

from src.data.company.evidence import Evidence
from src.data.company.ownership import OwnershipSnapshot


class OwnershipDirection(str, Enum):
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    STABLE = "STABLE"
    UNKNOWN = "UNKNOWN"


class OwnershipSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class OwnershipPeriod:
    """One ownership observation period with computed fields."""

    period_end: str
    promoter_pct: str | None = None
    institutional_pct: str | None = None
    public_pct: str | None = None
    pledge_pct: str | None = None
    concentration_ratio: str | None = None
    coverage_pct: str | None = None
    evidence_count: int = 0


@dataclass(frozen=True)
class OwnershipTrend:
    """Multi-period ownership trend."""

    metric: str
    direction: str
    periods_analyzed: int
    first_period: str
    last_period: str
    first_value: str | None = None
    last_value: str | None = None
    change: str | None = None
    change_pct: str | None = None
    min_value: str | None = None
    max_value: str | None = None
    explanation: str = ""


@dataclass(frozen=True)
class OwnershipSignal:
    """An ownership-based research observation."""

    signal_id: str
    signal_type: str
    direction: str
    severity: str
    title: str
    description: str
    current_value: str | None = None
    previous_value: str | None = None
    change: str | None = None
    evidence_ids: tuple[str, ...] = ()
    explanation: str = ""


@dataclass(frozen=True)
class OwnershipAnalysisResult:
    """Complete ownership analysis for one company."""

    symbol: str
    as_of: str
    snapshot_count: int = 0
    periods: tuple[OwnershipPeriod, ...] = ()
    trends: tuple[OwnershipTrend, ...] = ()
    signals: tuple[OwnershipSignal, ...] = ()
    coverage: dict[str, int] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    evidence: tuple[Evidence, ...] = ()


def _safe_decimal_str(val: Decimal | None) -> str | None:
    """Convert Decimal to string, or None."""
    if val is None:
        return None
    return str(val)


def _pct_change(
    previous: Decimal | None, current: Decimal | None
) -> Decimal | None:
    """Compute percentage change between two values."""
    if previous is None or current is None:
        return None
    if previous == 0:
        return None
    try:
        change = ((current - previous) / abs(previous)) * Decimal("100")
        return change.quantize(Decimal("0.01"))
    except Exception:
        return None


def _build_period(snapshot: OwnershipSnapshot) -> OwnershipPeriod:
    """Build an OwnershipPeriod from a snapshot."""
    promoter = _safe_decimal_str(snapshot.promoter_percentage)
    institutional = _safe_decimal_str(snapshot.institutional_percentage)
    public = _safe_decimal_str(snapshot.public_percentage)
    pledge = _safe_decimal_str(snapshot.promoter_pledged_percentage)

    # Concentration ratio: promoter / (institutional + public)
    concentration = None
    if (
        snapshot.promoter_percentage is not None
        and snapshot.institutional_percentage is not None
        and snapshot.public_percentage is not None
    ):
        non_promoter = (
            snapshot.institutional_percentage + snapshot.public_percentage
        )
        if non_promoter > 0:
            concentration = str(
                (snapshot.promoter_percentage / non_promoter).quantize(
                    Decimal("0.01")
                )
            )

    # Coverage: sum of available percentages
    coverage_parts = [
        snapshot.promoter_percentage,
        snapshot.institutional_percentage,
        snapshot.public_percentage,
    ]
    coverage_pct = None
    available = [p for p in coverage_parts if p is not None]
    if available:
        coverage_pct = str(
            sum(available).quantize(Decimal("0.01"))
        )

    return OwnershipPeriod(
        period_end=snapshot.period_end.isoformat(),
        promoter_pct=promoter,
        institutional_pct=institutional,
        public_pct=public,
        pledge_pct=pledge,
        concentration_ratio=concentration,
        coverage_pct=coverage_pct,
        evidence_count=0,
    )


def _build_trend(
    metric: str,
    values: list[tuple[str, Decimal | None]],
) -> OwnershipTrend | None:
    """Build a trend for a single ownership metric."""
    valid = [(p, v) for p, v in values if v is not None]
    if len(valid) < 2:
        return None

    first_period, first_val = valid[0]
    last_period, last_val = valid[-1]

    change = last_val - first_val
    change_pct = _pct_change(first_val, last_val)

    if change > 0:
        direction = OwnershipDirection.INCREASING.value
    elif change < 0:
        direction = OwnershipDirection.DECREASING.value
    else:
        direction = OwnershipDirection.STABLE.value

    all_vals = [v for _, v in valid]

    return OwnershipTrend(
        metric=metric,
        direction=direction,
        periods_analyzed=len(valid),
        first_period=first_period,
        last_period=last_period,
        first_value=str(first_val),
        last_value=str(last_val),
        change=str(change.quantize(Decimal("0.01"))),
        change_pct=str(change_pct) if change_pct is not None else None,
        min_value=str(min(all_vals)),
        max_value=str(max(all_vals)),
        explanation=(
            f"{metric} {direction.lower()} from "
            f"{first_val} to {last_val} across "
            f"{len(valid)} periods."
        ),
    )


def _build_signals(
    periods: list[OwnershipPeriod],
    symbol: str,
) -> list[OwnershipSignal]:
    """Derive ownership signals from period data."""
    signals: list[OwnershipSignal] = []
    signal_idx = 0

    if not periods:
        return signals

    latest = periods[-1]

    # Low promoter ownership
    if latest.promoter_pct is not None:
        promoter_val = Decimal(latest.promoter_pct)
        if promoter_val < Decimal("25"):
            signals.append(
                OwnershipSignal(
                    signal_id=f"OWN-{symbol}-{signal_idx:03d}",
                    signal_type="LOW_PROMOTER",
                    direction=OwnershipDirection.UNKNOWN.value,
                    severity=OwnershipSeverity.MEDIUM.value,
                    title="Low promoter ownership",
                    description=(
                        f"Promoter ownership is {latest.promoter_pct}%, "
                        f"below the 25% threshold."
                    ),
                    current_value=latest.promoter_pct,
                    explanation=(
                        "Low promoter ownership may indicate "
                        "reduced insider commitment."
                    ),
                )
            )
            signal_idx += 1

    # High pledge
    if latest.pledge_pct is not None:
        pledge_val = Decimal(latest.pledge_pct)
        if pledge_val > Decimal("50"):
            signals.append(
                OwnershipSignal(
                    signal_id=f"OWN-{symbol}-{signal_idx:03d}",
                    signal_type="HIGH_PLEDGE",
                    direction=OwnershipDirection.UNKNOWN.value,
                    severity=OwnershipSeverity.HIGH.value,
                    title="High promoter pledge",
                    description=(
                        f"Promoter pledge is {latest.pledge_pct}%, "
                        f"above the 50% threshold."
                    ),
                    current_value=latest.pledge_pct,
                    explanation=(
                        "High pledge levels may indicate "
                        "financing pressure on promoters."
                    ),
                )
            )
            signal_idx += 1
        elif pledge_val > Decimal("20"):
            signals.append(
                OwnershipSignal(
                    signal_id=f"OWN-{symbol}-{signal_idx:03d}",
                    signal_type="MODERATE_PLEDGE",
                    direction=OwnershipDirection.UNKNOWN.value,
                    severity=OwnershipSeverity.MEDIUM.value,
                    title="Moderate promoter pledge",
                    description=(
                        f"Promoter pledge is {latest.pledge_pct}%, "
                        f"above the 20% threshold."
                    ),
                    current_value=latest.pledge_pct,
                    explanation=(
                        "Moderate pledge levels should be monitored."
                    ),
                )
            )
            signal_idx += 1

    # Institutional dominance
    if latest.institutional_pct is not None:
        inst_val = Decimal(latest.institutional_pct)
        if inst_val > Decimal("70"):
            signals.append(
                OwnershipSignal(
                    signal_id=f"OWN-{symbol}-{signal_idx:03d}",
                    signal_type="HIGH_INSTITUTIONAL",
                    direction=OwnershipDirection.STABLE.value,
                    severity=OwnershipSeverity.LOW.value,
                    title="High institutional ownership",
                    description=(
                        f"Institutional ownership is "
                        f"{latest.institutional_pct}%."
                    ),
                    current_value=latest.institutional_pct,
                    explanation=(
                        "High institutional ownership suggests "
                        "professional investor interest."
                    ),
                )
            )
            signal_idx += 1

    # Trend-based signals: large moves in any metric
    for period_pair in _pairwise(periods):
        prev, curr = period_pair
        for metric_name, prev_val, curr_val in [
            ("promoter", prev.promoter_pct, curr.promoter_pct),
            ("institutional", prev.institutional_pct, curr.institutional_pct),
            ("pledge", prev.pledge_pct, curr.pledge_pct),
        ]:
            if prev_val is not None and curr_val is not None:
                move = abs(
                    Decimal(curr_val) - Decimal(prev_val)
                )
                if move > Decimal("5"):
                    direction = (
                        OwnershipDirection.INCREASING.value
                        if Decimal(curr_val) > Decimal(prev_val)
                        else OwnershipDirection.DECREASING.value
                    )
                    signals.append(
                        OwnershipSignal(
                            signal_id=f"OWN-{symbol}-{signal_idx:03d}",
                            signal_type=f"{metric_name.upper()}_SHIFT",
                            direction=direction,
                            severity=OwnershipSeverity.MEDIUM.value,
                            title=f"{metric_name.title()} ownership shift",
                            description=(
                                f"{metric_name.title()} ownership changed by "
                                f"{move}% between {prev.period_end} "
                                f"and {curr.period_end}."
                            ),
                            current_value=curr_val,
                            previous_value=prev_val,
                            change=str(move.quantize(Decimal("0.01"))),
                            explanation=(
                                f"Significant {metric_name} ownership "
                                f"movement detected."
                            ),
                        )
                    )
                    signal_idx += 1

    return signals


def _pairwise(
    items: list,
) -> list[tuple]:
    """Return consecutive pairs."""
    return list(zip(items, items[1:]))


def analyze_ownership(
    snapshots: Sequence[OwnershipSnapshot],
    symbol: str,
    as_of: datetime,
) -> OwnershipAnalysisResult:
    """
    Run the full ownership analysis pipeline.

    Deterministic: no external calls, no network, no randomness.
    """
    notes: list[str] = []
    evidence_list: list[Evidence] = []

    if not snapshots:
        notes.append("No ownership data available.")
        return OwnershipAnalysisResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            notes=tuple(notes),
        )

    # Filter to as_of PIT
    filtered = [
        s for s in snapshots
        if datetime.combine(
            s.period_end, datetime.min.time()
        ).replace(tzinfo=as_of.tzinfo) <= as_of
    ] if as_of.tzinfo else [
        s for s in snapshots
        if s.period_end <= as_of.date()
    ]

    if not filtered:
        notes.append("No ownership data available at as_of date.")
        return OwnershipAnalysisResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            notes=tuple(notes),
        )

    # Build periods
    periods = [_build_period(s) for s in filtered]

    # Build trends
    promoter_values = [
        (p.period_end, Decimal(p.promoter_pct) if p.promoter_pct else None)
        for p in periods
    ]
    institutional_values = [
        (p.period_end, Decimal(p.institutional_pct) if p.institutional_pct else None)
        for p in periods
    ]
    pledge_values = [
        (p.period_end, Decimal(p.pledge_pct) if p.pledge_pct else None)
        for p in periods
    ]

    trends: list[OwnershipTrend] = []
    for metric, values in [
        ("promoter_percentage", promoter_values),
        ("institutional_percentage", institutional_values),
        ("promoter_pledged_percentage", pledge_values),
    ]:
        trend = _build_trend(metric, values)
        if trend is not None:
            trends.append(trend)

    # Build signals
    signals = _build_signals(periods, symbol)

    # Coverage
    coverage: dict[str, int] = {}
    if periods:
        coverage["period_count"] = len(periods)
        has_promoter = sum(1 for p in periods if p.promoter_pct is not None)
        has_institutional = sum(
            1 for p in periods if p.institutional_pct is not None
        )
        has_pledge = sum(1 for p in periods if p.pledge_pct is not None)
        if has_promoter:
            coverage["promoter_percentage"] = has_promoter
        if has_institutional:
            coverage["institutional_percentage"] = has_institutional
        if has_pledge:
            coverage["pledge_percentage"] = has_pledge

    return OwnershipAnalysisResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        snapshot_count=len(filtered),
        periods=tuple(periods),
        trends=tuple(trends),
        signals=tuple(signals),
        coverage=coverage,
        notes=tuple(notes),
        evidence=tuple(evidence_list),
    )
