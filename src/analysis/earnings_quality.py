"""
Earnings quality analysis.

Compares profit measures against cash-flow measures, and analyses
the relationship between growth in receivables/inventory and revenue
growth.  Persistent divergences between accrual-based profit and
cash-based measures are flagged as quality observations.

Thresholds (documented for traceability):
  - Cash/profit ratio below 70%: LOW earnings quality signal.
  - Cash/profit ratio below 50%: HIGH earnings quality signal.
  - Receivables growth exceeding revenue growth by >= 20pp:
    flagged as a monitoring observation.
  - Inventory growth exceeding revenue growth by >= 20pp:
    flagged as a monitoring observation.
  - Net profit positive but OCF negative for >= 2 consecutive
    periods: persistent divergence flagged as HIGH severity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Sequence

from src.data.company.financials import FinancialSnapshot


_HUNDRED = Decimal("100")

# Earnings quality thresholds
_CASH_PROFIT_LOW = Decimal("70")
_CASH_PROFIT_HIGH = Decimal("50")

# Growth divergence threshold (percentage points)
_GROWTH_DIVERGENCE_THRESHOLD = Decimal("20")

# Persistent divergence: consecutive periods
_PERSISTENT_DIVERGENCE_MIN = 2


def _pct_change(
    previous: Decimal | None,
    current: Decimal | None,
) -> Decimal | None:
    if previous is None or current is None:
        return None
    if previous == 0:
        return None
    try:
        return ((current - previous) / abs(previous)) * _HUNDRED
    except Exception:
        return None


def _safe_div(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> Decimal | None:
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    try:
        return numerator / denominator
    except Exception:
        return None


def _ordered_snapshots(
    snapshots: Sequence[FinancialSnapshot],
) -> list[FinancialSnapshot]:
    return sorted(snapshots, key=lambda s: s.period_end)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CashProfitComparison:
    """One period's comparison of cash flow vs profit."""

    period: str
    net_profit: str | None = None
    operating_cash_flow: str | None = None
    free_cash_flow: str | None = None

    ocf_to_profit_ratio: str | None = None
    fcf_to_profit_ratio: str | None = None

    ocf_exceeds_profit: bool | None = None
    fcf_exceeds_profit: bool | None = None

    explanation: str = ""


@dataclass(frozen=True)
class GrowthDivergence:
    """One period's comparison of a growth rate vs revenue growth."""

    period: str
    metric: str
    metric_growth_rate: str | None = None
    revenue_growth_rate: str | None = None
    divergence_pp: str | None = None
    flagged: bool = False
    explanation: str = ""


@dataclass(frozen=True)
class EarningsQualityObservation:
    """
    A derived earnings-quality observation across multiple periods.

    Each observation is descriptive only -- it does not predict
    future performance or assign blame.
    """

    observation_type: str
    symbol: str
    severity: str

    periods_covered: int = 0
    first_period: str = ""
    last_period: str = ""

    value: str | None = None
    metric: str = ""

    cash_profit_comparisons: list[CashProfitComparison] = field(
        default_factory=list
    )
    growth_divergences: list[GrowthDivergence] = field(
        default_factory=list
    )

    persistent: bool = False
    explanation: str = ""


# ---------------------------------------------------------------------------
# Cash / profit analysis
# ---------------------------------------------------------------------------

def compare_cash_profit(
    snapshot: FinancialSnapshot,
) -> CashProfitComparison:
    """Compare cash-flow measures to profit for one period."""
    period = snapshot.period_end.isoformat()
    np_val = snapshot.net_profit
    ocf_val = snapshot.operating_cash_flow
    fcf_val = snapshot.free_cash_flow

    ocf_ratio = _safe_div(ocf_val, np_val)
    fcf_ratio = _safe_div(fcf_val, np_val)

    ocf_exceeds = None
    fcf_exceeds = None

    if ocf_val is not None and np_val is not None:
        ocf_exceeds = ocf_val > np_val
    if fcf_val is not None and np_val is not None:
        fcf_exceeds = fcf_val > np_val

    parts: list[str] = []

    if ocf_ratio is not None:
        ocf_pct = ocf_ratio * _HUNDRED
        parts.append(f"OCF/profit: {ocf_pct:.1f}%")
        if ocf_pct < _CASH_PROFIT_HIGH:
            parts.append("below 50% -- HIGH quality concern")
        elif ocf_pct < _CASH_PROFIT_LOW:
            parts.append(
                "below 70% -- monitoring signal"
            )
    else:
        parts.append("OCF/profit: insufficient data")

    if fcf_ratio is not None:
        fcf_pct = fcf_ratio * _HUNDRED
        parts.append(f"FCF/profit: {fcf_pct:.1f}%")

    return CashProfitComparison(
        period=period,
        net_profit=str(np_val) if np_val is not None else None,
        operating_cash_flow=(
            str(ocf_val) if ocf_val is not None else None
        ),
        free_cash_flow=(
            str(fcf_val) if fcf_val is not None else None
        ),
        ocf_to_profit_ratio=(
            str(ocf_ratio) if ocf_ratio is not None else None
        ),
        fcf_to_profit_ratio=(
            str(fcf_ratio) if fcf_ratio is not None else None
        ),
        ocf_exceeds_profit=ocf_exceeds,
        fcf_exceeds_profit=fcf_exceeds,
        explanation=". ".join(parts) + ".",
    )


def analyze_cash_profit_series(
    snapshots: Sequence[FinancialSnapshot],
) -> list[CashProfitComparison]:
    """Compare cash flow vs profit for every period."""
    ordered = _ordered_snapshots(snapshots)
    return [compare_cash_profit(s) for s in ordered]


def detect_persistent_cash_profit_divergence(
    snapshots: Sequence[FinancialSnapshot],
) -> EarningsQualityObservation | None:
    """
    Detect persistent divergence where net profit is positive
    but operating cash flow is negative (or vice versa) across
    multiple consecutive periods.
    """
    ordered = _ordered_snapshots(snapshots)

    divergent_periods: list[str] = []
    all_comparisons = analyze_cash_profit_series(snapshots)

    for s in ordered:
        np_val = s.net_profit
        ocf_val = s.operating_cash_flow
        if np_val is None or ocf_val is None:
            continue
        if np_val > 0 and ocf_val < 0:
            divergent_periods.append(s.period_end.isoformat())
        elif np_val < 0 and ocf_val > 0:
            divergent_periods.append(s.period_end.isoformat())

    if len(divergent_periods) < _PERSISTENT_DIVERGENCE_MIN:
        return None

    severity = (
        "HIGH"
        if len(divergent_periods) >= 3
        else "MEDIUM"
    )

    return EarningsQualityObservation(
        observation_type="persistent_cash_profit_divergence",
        symbol=ordered[0].symbol if ordered else "",
        severity=severity,
        periods_covered=len(divergent_periods),
        first_period=divergent_periods[0],
        last_period=divergent_periods[-1],
        metric="net_profit vs operating_cash_flow",
        cash_profit_comparisons=all_comparisons,
        persistent=True,
        explanation=(
            f"Net profit and operating cash flow showed opposite "
            f"signs in {len(divergent_periods)} consecutive "
            f"periods ({divergent_periods[0]} to "
            f"{divergent_periods[-1]}). This is a monitoring "
            f"signal -- not an automatic finding of misconduct."
        ),
    )


# ---------------------------------------------------------------------------
# Receivables / inventory vs revenue growth
# ---------------------------------------------------------------------------

def compare_growth_rates(
    snapshots: Sequence[FinancialSnapshot],
    metric: str,
) -> list[GrowthDivergence]:
    """
    Compare period-over-period growth of `metric` vs revenue growth.
    """
    ordered = _ordered_snapshots(snapshots)
    divergences: list[GrowthDivergence] = []

    for i in range(len(ordered) - 1):
        prev = ordered[i]
        curr = ordered[i + 1]

        metric_growth = _pct_change(
            getattr(prev, metric, None),
            getattr(curr, metric, None),
        )
        revenue_growth = _pct_change(prev.revenue, curr.revenue)

        period = curr.period_end.isoformat()

        if metric_growth is None or revenue_growth is None:
            divergences.append(
                GrowthDivergence(
                    period=period,
                    metric=metric,
                    explanation="Insufficient data for comparison.",
                )
            )
            continue

        divergence = metric_growth - revenue_growth
        flagged = divergence >= _GROWTH_DIVERGENCE_THRESHOLD

        explanation = (
            f"{metric} grew {metric_growth:.1f}% vs "
            f"revenue {revenue_growth:.1f}% "
            f"(divergence: {divergence:+.1f}pp)."
        )

        if flagged:
            explanation += (
                " Materially faster growth -- monitoring signal."
            )

        divergences.append(
            GrowthDivergence(
                period=period,
                metric=metric,
                metric_growth_rate=str(metric_growth),
                revenue_growth_rate=str(revenue_growth),
                divergence_pp=str(divergence),
                flagged=flagged,
                explanation=explanation,
            )
        )

    return divergences


def detect_receivables_divergence(
    snapshots: Sequence[FinancialSnapshot],
) -> EarningsQualityObservation | None:
    """Flag periods where receivables growth materially exceeds revenue."""
    divergences = compare_growth_rates(snapshots, "receivables")
    flagged = [d for d in divergences if d.flagged]

    if not flagged:
        return None

    ordered = _ordered_snapshots(snapshots)

    return EarningsQualityObservation(
        observation_type="receivables_growth_divergence",
        symbol=ordered[0].symbol if ordered else "",
        severity="MEDIUM" if len(flagged) < 2 else "HIGH",
        periods_covered=len(flagged),
        first_period=flagged[0].period,
        last_period=flagged[-1].period,
        metric="receivables",
        growth_divergences=divergences,
        explanation=(
            f"Receivables growth exceeded revenue growth by "
            f">={_GROWTH_DIVERGENCE_THRESHOLD}pp in "
            f"{len(flagged)} period(s). This may indicate "
            f"changes in collection timing, customer "
            f"concentration, or revenue recognition."
        ),
    )


def detect_inventory_divergence(
    snapshots: Sequence[FinancialSnapshot],
) -> EarningsQualityObservation | None:
    """Flag periods where inventory growth materially exceeds revenue."""
    divergences = compare_growth_rates(snapshots, "inventory")
    flagged = [d for d in divergences if d.flagged]

    if not flagged:
        return None

    ordered = _ordered_snapshots(snapshots)

    return EarningsQualityObservation(
        observation_type="inventory_growth_divergence",
        symbol=ordered[0].symbol if ordered else "",
        severity="MEDIUM" if len(flagged) < 2 else "HIGH",
        periods_covered=len(flagged),
        first_period=flagged[0].period,
        last_period=flagged[-1].period,
        metric="inventory",
        growth_divergences=divergences,
        explanation=(
            f"Inventory growth exceeded revenue growth by "
            f">={_GROWTH_DIVERGENCE_THRESHOLD}pp in "
            f"{len(flagged)} period(s). This may indicate "
            f"build-up of unsold stock or changing inventory "
            f"management practices."
        ),
    )


# ---------------------------------------------------------------------------
# High-level orchestrator
# ---------------------------------------------------------------------------

def analyze_earnings_quality(
    snapshots: Sequence[FinancialSnapshot],
) -> list[EarningsQualityObservation]:
    """
    Full earnings-quality analysis across all periods.

    Returns a list of observations. Empty list means no quality
    signals were detected with the available data.
    """
    observations: list[EarningsQualityObservation] = []

    persistent = detect_persistent_cash_profit_divergence(
        snapshots
    )
    if persistent is not None:
        observations.append(persistent)

    recv = detect_receivables_divergence(snapshots)
    if recv is not None:
        observations.append(recv)

    inv = detect_inventory_divergence(snapshots)
    if inv is not None:
        observations.append(inv)

    return observations
