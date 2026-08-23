"""
Multi-period fundamental trajectory analysis.

Computes CAGR, period-over-period growth rates, margin expansion/
contraction, and leverage trajectories across consecutive financial
snapshots.  Every calculation is deterministic and returns None when
the underlying data is insufficient -- no values are invented.

Thresholds (documented here for traceability):
  - CAGR: requires >= 2 periods; first value must be positive.
  - Margin expansion: uses absolute percentage-point change.
  - Acceleration/deceleration: compares consecutive growth-rate deltas.
  - Leverage trajectory: tracks total_debt / revenue over time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Sequence

from src.data.company.financials import FinancialSnapshot


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HUNDRED = Decimal("100")

# Margin trajectory: how many periods of consistent
# direction before we call it PERSISTENT.
_PERSISTENCE_MIN_PERIODS = 2

# Leverage threshold: debt/revenue above this is considered elevated.
_LEVERAGE_HIGH_THRESHOLD = Decimal("1.5")

# Margin deterioration: absolute pp change that triggers flag.
_MARGIN_DETERIORATION_THRESHOLD = Decimal("5")


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
    except InvalidOperation:
        return None


def _pct(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value * _HUNDRED


def _pct_change(
    previous: Decimal | None,
    current: Decimal | None,
) -> Decimal | None:
    """Percentage change from previous to current."""
    if previous is None or current is None:
        return None
    if previous == 0:
        return None
    try:
        return ((current - previous) / abs(previous)) * _HUNDRED
    except InvalidOperation:
        return None


def _ordered_snapshots(
    snapshots: Sequence[FinancialSnapshot],
) -> list[FinancialSnapshot]:
    return sorted(snapshots, key=lambda s: s.period_end)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PeriodGrowthRate:
    """One period-to-period growth observation."""

    from_period: str
    to_period: str
    previous_value: str
    current_value: str
    growth_rate: str
    metric: str


@dataclass(frozen=True)
class TrajectoryAnalysis:
    """
    Multi-period trajectory for one metric.

    Every field is a plain string or list so it serialises cleanly.
    None values are represented as the literal string "null" only
    in the API contract; here they remain Python None.
    """

    metric: str
    symbol: str
    period_count: int

    first_period: str
    last_period: str

    first_value: str | None = None
    last_value: str | None = None

    cagr: str | None = None
    total_change: str | None = None
    total_change_pct: str | None = None

    growth_rates: list[PeriodGrowthRate] = field(
        default_factory=list
    )

    direction: str | None = None
    acceleration: str | None = None
    persistence_pct: str | None = None

    average_growth_rate: str | None = None
    min_growth_rate: str | None = None
    max_growth_rate: str | None = None

    explanation: str = ""


@dataclass(frozen=True)
class MarginTrajectory:
    """Expansion / contraction of one margin across periods."""

    margin_name: str
    symbol: str
    period_count: int

    first_period: str
    last_period: str

    first_value: str | None = None
    last_value: str | None = None

    total_change_pp: str | None = None
    direction: str | None = None
    persistent: bool = False

    values: list[tuple[str, str | None]] = field(
        default_factory=list
    )

    explanation: str = ""


@dataclass(frozen=True)
class LeverageTrajectory:
    """Debt / revenue (or debt / EBITDA) trajectory."""

    metric: str
    symbol: str
    period_count: int

    first_period: str
    last_period: str

    first_value: str | None = None
    last_value: str | None = None

    direction: str | None = None
    elevated: bool = False
    peak_value: str | None = None
    trough_value: str | None = None

    values: list[tuple[str, str | None]] = field(
        default_factory=list
    )

    explanation: str = ""


# ---------------------------------------------------------------------------
# Trajectory computation
# ---------------------------------------------------------------------------

def _extract_series(
    snapshots: Sequence[FinancialSnapshot],
    metric: str,
) -> list[tuple[str, Decimal]]:
    """Return (period_end_iso, value) pairs where value is not None."""
    ordered = _ordered_snapshots(snapshots)
    series: list[tuple[str, Decimal]] = []
    for s in ordered:
        val = getattr(s, metric, None)
        if val is not None:
            series.append((s.period_end.isoformat(), val))
    return series


def _cagr(
    first_value: Decimal,
    last_value: Decimal,
    periods: int,
) -> Decimal | None:
    """
    Compound annual growth rate.

    Requires first_value > 0 and periods >= 1.
    """
    if first_value <= 0 or periods < 1:
        return None
    if last_value <= 0:
        return None

    try:
        ratio = last_value / first_value
        # Use integer power approximation for small exponents.
        # CAGR = (last/first)^(1/n) - 1
        # For precision we use Decimal power via ln/exp approximation.
        # Since n is small (typically 1-10), we iterate.
        if ratio <= 0:
            return None

        # Use the formula directly for exactness with Decimal.
        n = Decimal(periods)
        result = ratio ** (Decimal("1") / n) - Decimal("1")
        return result * _HUNDRED
    except (InvalidOperation, ValueError):
        return None


def _direction_label(values: list[Decimal]) -> str | None:
    if not values:
        return None
    if all(v > 0 for v in values):
        return "INCREASING"
    if all(v < 0 for v in values):
        return "DECREASING"
    if all(v == 0 for v in values):
        return "STABLE"
    return "MIXED"


def _acceleration_label(
    growth_rates: list[Decimal],
) -> str | None:
    """Compare last two growth-rate deltas."""
    if len(growth_rates) < 3:
        return None

    deltas = [
        growth_rates[i + 1] - growth_rates[i]
        for i in range(len(growth_rates) - 1)
    ]

    if all(d > 0 for d in deltas):
        return "ACCELERATING"
    if all(d < 0 for d in deltas):
        return "DECELERATING"
    return "UNSTEADY"


def _persistence_pct(values: list[Decimal]) -> Decimal | None:
    """Percentage of consecutive changes in the same direction."""
    if len(values) < 2:
        return None

    changes = [
        values[i + 1] - values[i]
        for i in range(len(values) - 1)
    ]

    if not changes:
        return None

    positive = sum(1 for c in changes if c > 0)
    negative = sum(1 for c in changes if c < 0)

    dominant = max(positive, negative)
    return (
        Decimal(dominant) / Decimal(len(changes))
    ) * _HUNDRED


def compute_trajectory(
    snapshots: Sequence[FinancialSnapshot],
    metric: str,
    symbol: str,
) -> TrajectoryAnalysis | None:
    """
    Compute a full trajectory for one metric.

    Returns None when fewer than 2 data points are available.
    """
    series = _extract_series(snapshots, metric)
    if len(series) < 2:
        return None

    values = [v for _, v in series]
    periods = len(series) - 1

    first_period = series[0][0]
    last_period = series[-1][0]
    first_value = values[0]
    last_value = values[-1]

    total_change = last_value - first_value
    total_change_pct = _pct_change(first_value, last_value)

    cagr_val = _cagr(first_value, last_value, periods)

    # Period-over-period growth rates
    growth_rates_data: list[PeriodGrowthRate] = []
    growth_rate_values: list[Decimal] = []

    for i in range(len(series) - 1):
        p_prev = series[i]
        p_curr = series[i + 1]
        gr = _pct_change(p_prev[1], p_curr[1])
        gr_str = str(gr) if gr is not None else None
        growth_rates_data.append(
            PeriodGrowthRate(
                from_period=p_prev[0],
                to_period=p_curr[0],
                previous_value=str(p_prev[1]),
                current_value=str(p_curr[1]),
                growth_rate=gr_str,
                metric=metric,
            )
        )
        if gr is not None:
            growth_rate_values.append(gr)

    direction = _direction_label(
        [
            curr - prev
            for prev, curr in zip(values, values[1:])
        ]
    )

    acceleration = _acceleration_label(growth_rate_values)
    persist = _persistence_pct(values)

    avg_gr = None
    min_gr = None
    max_gr = None
    if growth_rate_values:
        avg_gr = sum(growth_rate_values) / Decimal(
            len(growth_rate_values)
        )
        min_gr = min(growth_rate_values)
        max_gr = max(growth_rate_values)

    explanation_parts = [
        f"{metric} trajectory across {len(series)} periods "
        f"({first_period} to {last_period})."
    ]

    if cagr_val is not None:
        explanation_parts.append(
            f"CAGR: {cagr_val:.2f}%."
        )

    if direction:
        explanation_parts.append(
            f"Direction: {direction.lower()}."
        )

    if acceleration:
        explanation_parts.append(
            f"Pattern: {acceleration.lower()}."
        )

    return TrajectoryAnalysis(
        metric=metric,
        symbol=symbol,
        period_count=len(series),
        first_period=first_period,
        last_period=last_period,
        first_value=str(first_value),
        last_value=str(last_value),
        cagr=str(cagr_val) if cagr_val is not None else None,
        total_change=str(total_change),
        total_change_pct=(
            str(total_change_pct)
            if total_change_pct is not None
            else None
        ),
        growth_rates=growth_rates_data,
        direction=direction,
        acceleration=acceleration,
        persistence_pct=(
            str(persist) if persist is not None else None
        ),
        average_growth_rate=(
            str(avg_gr) if avg_gr is not None else None
        ),
        min_growth_rate=(
            str(min_gr) if min_gr is not None else None
        ),
        max_growth_rate=(
            str(max_gr) if max_gr is not None else None
        ),
        explanation=" ".join(explanation_parts),
    )


# ---------------------------------------------------------------------------
# Margin trajectories
# ---------------------------------------------------------------------------

_MARGIN_DEFINITIONS: list[tuple[str, str, str]] = [
    ("net_margin", "net_profit", "revenue"),
    ("operating_margin", "operating_profit", "revenue"),
    ("ocf_margin", "operating_cash_flow", "revenue"),
    ("fcf_margin", "free_cash_flow", "revenue"),
]


def compute_margin_trajectory(
    snapshots: Sequence[FinancialSnapshot],
    margin_name: str,
    numerator: str,
    denominator: str,
    symbol: str,
) -> MarginTrajectory | None:
    """Compute margin expansion/contraction trajectory."""
    ordered = _ordered_snapshots(snapshots)

    values_per_period: list[tuple[str, Decimal | None]] = []
    for s in ordered:
        num = getattr(s, numerator, None)
        den = getattr(s, denominator, None)
        margin = _safe_div(num, den)
        values_per_period.append(
            (s.period_end.isoformat(), _pct(margin))
        )

    valid = [
        (p, v) for p, v in values_per_period if v is not None
    ]

    if len(valid) < 2:
        return None

    first_period = valid[0][0]
    last_period = valid[-1][0]
    first_value = valid[0][1]
    last_value = valid[-1][1]

    total_change = last_value - first_value

    if total_change > 0:
        direction = "EXPANDING"
    elif total_change < 0:
        direction = "CONTRACTING"
    else:
        direction = "STABLE"

    # Persistence: how many consecutive periods move same direction
    margin_vals = [v for _, v in valid]
    persist = _persistence_pct(margin_vals)
    persistent = (
        persist is not None
        and persist >= Decimal("75")
        and len(margin_vals) >= _PERSISTENCE_MIN_PERIODS
    )

    all_values = [
        (p, str(v)) for p, v in values_per_period
    ]

    explanation = (
        f"{margin_name} {direction.lower()} from "
        f"{first_value}% to {last_value}% "
        f"({total_change:+.2f} pp) across {len(valid)} periods."
    )

    if persistent:
        explanation += " Movement is persistent."

    return MarginTrajectory(
        margin_name=margin_name,
        symbol=symbol,
        period_count=len(valid),
        first_period=first_period,
        last_period=last_period,
        first_value=str(first_value),
        last_value=str(last_value),
        total_change_pp=str(total_change),
        direction=direction,
        persistent=persistent,
        values=all_values,
        explanation=explanation,
    )


def compute_all_margin_trajectories(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
) -> list[MarginTrajectory]:
    """Compute all standard margin trajectories."""
    results: list[MarginTrajectory] = []
    for name, num, den in _MARGIN_DEFINITIONS:
        mt = compute_margin_trajectory(
            snapshots, name, num, den, symbol
        )
        if mt is not None:
            results.append(mt)
    return results


# ---------------------------------------------------------------------------
# Leverage trajectories
# ---------------------------------------------------------------------------

def compute_leverage_trajectory(
    snapshots: Sequence[FinancialSnapshot],
    metric: str,
    numerator: str,
    denominator: str,
    symbol: str,
) -> LeverageTrajectory | None:
    """Compute a leverage ratio trajectory (e.g. debt/revenue)."""
    ordered = _ordered_snapshots(snapshots)

    values_per_period: list[tuple[str, Decimal | None]] = []
    for s in ordered:
        num = getattr(s, numerator, None)
        den = getattr(s, denominator, None)
        ratio = _safe_div(num, den)
        values_per_period.append(
            (s.period_end.isoformat(), ratio)
        )

    valid = [
        (p, v) for p, v in values_per_period if v is not None
    ]

    if len(valid) < 2:
        return None

    first_period = valid[0][0]
    last_period = valid[-1][0]
    first_value = valid[0][1]
    last_value = valid[-1][1]

    vals = [v for _, v in valid]
    peak = max(vals)
    trough = min(vals)

    direction = None
    if last_value > first_value:
        direction = "INCREASING"
    elif last_value < first_value:
        direction = "DECREASING"
    else:
        direction = "STABLE"

    elevated = peak >= _LEVERAGE_HIGH_THRESHOLD

    all_values = [
        (p, str(v)) for p, v in values_per_period
    ]

    explanation = (
        f"{metric} trajectory: {first_value} to {last_value} "
        f"across {len(valid)} periods. "
        f"Peak: {peak}, trough: {trough}."
    )

    if elevated:
        explanation += (
            f" Ratio exceeded {_LEVERAGE_HIGH_THRESHOLD} "
            "at peak -- elevated leverage observed."
        )

    return LeverageTrajectory(
        metric=metric,
        symbol=symbol,
        period_count=len(valid),
        first_period=first_period,
        last_period=last_period,
        first_value=str(first_value),
        last_value=str(last_value),
        direction=direction,
        elevated=elevated,
        peak_value=str(peak),
        trough_value=str(trough),
        values=all_values,
        explanation=explanation,
    )


def compute_all_leverage_trajectories(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
) -> list[LeverageTrajectory]:
    """Compute all standard leverage trajectories."""
    definitions: list[tuple[str, str, str]] = [
        ("debt_to_revenue", "total_debt", "revenue"),
        ("debt_to_equity", "total_debt", "shareholders_equity"),
        ("debt_to_total_assets", "total_debt", "total_assets"),
    ]

    results: list[LeverageTrajectory] = []
    for name, num, den in definitions:
        lt = compute_leverage_trajectory(
            snapshots, name, num, den, symbol
        )
        if lt is not None:
            results.append(lt)
    return results


# ---------------------------------------------------------------------------
# High-level orchestrator
# ---------------------------------------------------------------------------

# Metrics for which we compute CAGR / trajectory.
_TRAJECTORY_METRICS: tuple[str, ...] = (
    "revenue",
    "net_profit",
    "operating_profit",
    "operating_cash_flow",
    "free_cash_flow",
    "total_debt",
    "cash_and_equivalents",
    "receivables",
    "inventory",
    "current_assets",
    "current_liabilities",
    "total_equity",
    "shareholders_equity",
)


def analyze_trajectories(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
) -> list[TrajectoryAnalysis]:
    """Compute trajectories for all tracked metrics."""
    results: list[TrajectoryAnalysis] = []
    for metric in _TRAJECTORY_METRICS:
        t = compute_trajectory(snapshots, metric, symbol)
        if t is not None:
            results.append(t)
    return results


def analyze_all_trajectories(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
) -> dict:
    """
    Full trajectory analysis: metric trajectories, margin
    trajectories, and leverage trajectories.
    """
    return {
        "trajectories": analyze_trajectories(snapshots, symbol),
        "margin_trajectories": compute_all_margin_trajectories(
            snapshots, symbol
        ),
        "leverage_trajectories": compute_all_leverage_trajectories(
            snapshots, symbol
        ),
    }
