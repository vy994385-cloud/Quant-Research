"""
Deep balance sheet analysis module.

Analyzes leverage, liquidity, and balance sheet structure to
derive structured research observations.

Every observation carries full provenance, calculation inputs,
and PIT metadata. This module does NOT produce scores or
recommendations -- it produces evidence-based observations.

All calculations use Decimal precision for determinism.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Sequence

from src.data.company.financials import FinancialSnapshot


class BalanceSheetDirection(str, Enum):
    IMPROVING = "IMPROVING"
    DETERIORATING = "DETERIORATING"
    STABLE = "STABLE"
    UNKNOWN = "UNKNOWN"


class BalanceSheetSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class BalanceSheetDeepObservation:
    """
    A single balance sheet research observation.

    Carries full provenance and calculation inputs for
    reproducibility and audit.
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

    direction: str = BalanceSheetDirection.UNKNOWN.value
    severity: str = BalanceSheetSeverity.LOW.value

    calculation_method: str = ""
    calculation_inputs: dict[str, str] = field(default_factory=dict)

    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None

    available_at: str | None = None
    as_of: str | None = None
    effective_at: str | None = None

    status: str = "AVAILABLE"
    explanation: str = ""
    limitations: tuple[str, ...] = ()

    related_metrics: tuple[str, ...] = ()
    supporting_data: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BalanceSheetDeepResult:
    """
    Complete balance sheet analysis for one company.
    """

    symbol: str
    as_of: str

    observations: tuple[BalanceSheetDeepObservation, ...] = ()

    # Summary metrics
    avg_net_debt_to_revenue: str | None = None
    avg_cash_to_debt: str | None = None
    avg_debt_to_equity: str | None = None
    latest_leverage: str | None = None

    direction: str = BalanceSheetDirection.UNKNOWN.value
    period_count: int = 0
    notes: tuple[str, ...] = ()

    @property
    def observation_count(self) -> int:
        return len(self.observations)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_observation_counter = 0


def _next_id(prefix: str) -> str:
    global _observation_counter
    _observation_counter += 1
    return f"{prefix}-{_observation_counter:06d}"


def _fmt(value: Decimal | None, decimals: int = 2) -> str:
    if value is None:
        return "unavailable"
    return f"{value:.{decimals}f}"


def _pct_change(
    previous: Decimal | None,
    current: Decimal | None,
) -> Decimal | None:
    if previous is None or current is None:
        return None
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * Decimal("100")


def _determine_direction(
    current: Decimal | None,
    previous: Decimal | None,
    higher_is_better: bool = True,
) -> str:
    if current is None or previous is None:
        return BalanceSheetDirection.UNKNOWN.value

    if current > previous:
        return (
            BalanceSheetDirection.IMPROVING.value
            if higher_is_better
            else BalanceSheetDirection.DETERIORATING.value
        )
    if current < previous:
        return (
            BalanceSheetDirection.DETERIORATING.value
            if higher_is_better
            else BalanceSheetDirection.IMPROVING.value
        )
    return BalanceSheetDirection.STABLE.value


def _determine_severity(
    observation_type: str,
    value: Decimal | None,
    threshold_high: Decimal | None = None,
    threshold_medium: Decimal | None = None,
) -> str:
    if value is None:
        return BalanceSheetSeverity.LOW.value

    if threshold_high is not None and abs(value) > threshold_high:
        return BalanceSheetSeverity.HIGH.value
    if threshold_medium is not None and abs(value) > threshold_medium:
        return BalanceSheetSeverity.MEDIUM.value
    return BalanceSheetSeverity.LOW.value


# ---------------------------------------------------------------------------
# Core Analysis Functions
# ---------------------------------------------------------------------------


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
) -> tuple[str | None, str | None, str | None]:
    available = None
    if snapshot.available_at is not None:
        available = snapshot.available_at.isoformat()
    elif snapshot.published_at is not None:
        available = snapshot.published_at.isoformat()

    effective = None
    if snapshot.effective_at is not None:
        effective = snapshot.effective_at.isoformat()

    published = None
    if snapshot.published_at is not None:
        published = snapshot.published_at.isoformat()

    return available, effective, published


def analyze_net_debt(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[BalanceSheetDeepObservation]:
    """
    Analyze net debt position and trend.

    Net debt = Total debt - Cash and equivalents.
    Net debt/revenue indicates debt burden relative to earning power.
    """
    observations: list[BalanceSheetDeepObservation] = []

    ordered = sorted(snapshots, key=lambda s: s.period_end)

    for i, snapshot in enumerate(ordered):
        if (
            snapshot.total_debt is None
            or snapshot.cash_and_equivalents is None
        ):
            continue

        net_debt = snapshot.total_debt - snapshot.cash_and_equivalents

        # Net debt to revenue ratio
        net_debt_to_revenue = None
        if snapshot.revenue is not None and snapshot.revenue > 0:
            net_debt_to_revenue = (
                (net_debt / snapshot.revenue) * Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        src = _snapshot_source(snapshot)
        ao, eff, pub = _snapshot_as_of(snapshot)

        # Calculate change from previous period
        change = None
        change_pct = None
        prev_value = None
        if i > 0:
            prev = ordered[i - 1]
            if (
                prev.total_debt is not None
                and prev.cash_and_equivalents is not None
            ):
                prev_net_debt = (
                    prev.total_debt - prev.cash_and_equivalents
                )
                prev_value = str(prev_net_debt)
                change = str(
                    (net_debt - prev_net_debt).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                )
                change_pct = str(
                    _pct_change(prev_net_debt, net_debt)
                )

        # Direction: lower net debt is better
        direction = _determine_direction(
            net_debt,
            Decimal(prev_value) if prev_value else None,
            higher_is_better=False,
        )

        observations.append(
            BalanceSheetDeepObservation(
                observation_id=_next_id("BSD"),
                symbol=symbol,
                category="balance_sheet_deep",
                observation_type="net_debt",
                period=snapshot.period_end.isoformat(),
                metric="net_debt",
                value=str(net_debt),
                previous_value=prev_value,
                change=change,
                change_pct=change_pct,
                direction=direction,
                severity=_determine_severity(
                    "net_debt",
                    net_debt_to_revenue,
                    threshold_high=Decimal("100"),
                    threshold_medium=Decimal("50"),
                ),
                calculation_method=(
                    "Total debt - Cash and equivalents"
                ),
                calculation_inputs={
                    "total_debt": str(snapshot.total_debt),
                    "cash_and_equivalents": str(
                        snapshot.cash_and_equivalents
                    ),
                },
                source_name=src[0],
                source_type=src[1],
                source_url=src[2],
                available_at=ao,
                as_of=as_of.isoformat(),
                effective_at=eff,
                explanation=(
                    f"Net debt is {net_debt} "
                    f"(debt: {snapshot.total_debt}, "
                    f"cash: {snapshot.cash_and_equivalents}). "
                    + (
                        f"Net debt/revenue is "
                        f"{net_debt_to_revenue}%, indicating "
                        "significant leverage."
                        if net_debt_to_revenue
                        and net_debt_to_revenue > Decimal("50")
                        else "This is within moderate range."
                    )
                ),
                limitations=(
                    "Does not consider off-balance-sheet "
                    "obligations or contingent liabilities.",
                ),
                related_metrics=(
                    "total_debt",
                    "cash_and_equivalents",
                    "revenue",
                ),
                supporting_data={
                    "total_debt": str(snapshot.total_debt),
                    "cash": str(snapshot.cash_and_equivalents),
                    "net_debt_to_revenue": (
                        str(net_debt_to_revenue)
                        if net_debt_to_revenue is not None
                        else "unavailable"
                    ),
                    "period": snapshot.period_end.isoformat(),
                },
            )
        )

    return observations


def analyze_cash_to_debt(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[BalanceSheetDeepObservation]:
    """
    Analyze cash/debt ratio.

    Higher ratio indicates stronger debt coverage by cash.
    """
    observations: list[BalanceSheetDeepObservation] = []

    ordered = sorted(snapshots, key=lambda s: s.period_end)

    for i, snapshot in enumerate(ordered):
        if (
            snapshot.total_debt is None
            or snapshot.total_debt == 0
            or snapshot.cash_and_equivalents is None
        ):
            continue

        ratio = (
            snapshot.cash_and_equivalents / snapshot.total_debt
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        src = _snapshot_source(snapshot)
        ao, eff, pub = _snapshot_as_of(snapshot)

        # Calculate change from previous period
        change = None
        change_pct = None
        prev_value = None
        if i > 0:
            prev = ordered[i - 1]
            if (
                prev.total_debt is not None
                and prev.total_debt != 0
                and prev.cash_and_equivalents is not None
            ):
                prev_ratio = (
                    prev.cash_and_equivalents / prev.total_debt
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                prev_value = str(prev_ratio)
                change = str(
                    (ratio - prev_ratio).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                )
                change_pct = str(
                    _pct_change(prev_ratio, ratio)
                )

        # Direction: higher ratio is better
        direction = _determine_direction(
            ratio,
            Decimal(prev_value) if prev_value else None,
            higher_is_better=True,
        )

        observations.append(
            BalanceSheetDeepObservation(
                observation_id=_next_id("BSD"),
                symbol=symbol,
                category="balance_sheet_deep",
                observation_type="cash_to_debt",
                period=snapshot.period_end.isoformat(),
                metric="cash_to_debt_ratio",
                value=str(ratio),
                previous_value=prev_value,
                change=change,
                change_pct=change_pct,
                direction=direction,
                severity=_determine_severity(
                    "cash_to_debt",
                    ratio,
                    threshold_high=Decimal("0.3"),
                    threshold_medium=Decimal("0.5"),
                ),
                calculation_method=(
                    "Cash and equivalents / Total debt"
                ),
                calculation_inputs={
                    "cash_and_equivalents": str(
                        snapshot.cash_and_equivalents
                    ),
                    "total_debt": str(snapshot.total_debt),
                },
                source_name=src[0],
                source_type=src[1],
                source_url=src[2],
                available_at=ao,
                as_of=as_of.isoformat(),
                effective_at=eff,
                explanation=(
                    f"Cash/debt ratio is {ratio}x. "
                    + (
                        "This indicates cash covers a low "
                        "portion of total debt."
                        if ratio < Decimal("0.3")
                        else "This indicates adequate cash "
                        "coverage of debt."
                    )
                ),
                limitations=(
                    "Does not consider debt maturity profile "
                    "or interest coverage.",
                ),
                related_metrics=(
                    "cash_and_equivalents",
                    "total_debt",
                ),
                supporting_data={
                    "cash": str(snapshot.cash_and_equivalents),
                    "debt": str(snapshot.total_debt),
                    "period": snapshot.period_end.isoformat(),
                },
            )
        )

    return observations


def analyze_debt_to_equity(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[BalanceSheetDeepObservation]:
    """
    Analyze debt/equity ratio (leverage).

    Higher ratio indicates higher financial leverage.
    """
    observations: list[BalanceSheetDeepObservation] = []

    ordered = sorted(snapshots, key=lambda s: s.period_end)

    for i, snapshot in enumerate(ordered):
        equity = snapshot.total_equity or snapshot.shareholders_equity
        if (
            snapshot.total_debt is None
            or equity is None
            or equity == 0
        ):
            continue

        ratio = (
            snapshot.total_debt / equity
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        src = _snapshot_source(snapshot)
        ao, eff, pub = _snapshot_as_of(snapshot)

        # Calculate change from previous period
        change = None
        change_pct = None
        prev_value = None
        if i > 0:
            prev = ordered[i - 1]
            prev_equity = (
                prev.total_equity or prev.shareholders_equity
            )
            if (
                prev.total_debt is not None
                and prev_equity is not None
                and prev_equity != 0
            ):
                prev_ratio = (
                    prev.total_debt / prev_equity
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                prev_value = str(prev_ratio)
                change = str(
                    (ratio - prev_ratio).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                )
                change_pct = str(
                    _pct_change(prev_ratio, ratio)
                )

        # Direction: lower ratio is better (less leverage)
        direction = _determine_direction(
            ratio,
            Decimal(prev_value) if prev_value else None,
            higher_is_better=False,
        )

        observations.append(
            BalanceSheetDeepObservation(
                observation_id=_next_id("BSD"),
                symbol=symbol,
                category="balance_sheet_deep",
                observation_type="debt_to_equity",
                period=snapshot.period_end.isoformat(),
                metric="debt_to_equity_ratio",
                value=str(ratio),
                previous_value=prev_value,
                change=change,
                change_pct=change_pct,
                direction=direction,
                severity=_determine_severity(
                    "debt_to_equity",
                    ratio,
                    threshold_high=Decimal("2.0"),
                    threshold_medium=Decimal("1.0"),
                ),
                calculation_method=(
                    "Total debt / Total equity"
                ),
                calculation_inputs={
                    "total_debt": str(snapshot.total_debt),
                    "equity": str(equity),
                },
                source_name=src[0],
                source_type=src[1],
                source_url=src[2],
                available_at=ao,
                as_of=as_of.isoformat(),
                effective_at=eff,
                explanation=(
                    f"Debt/equity ratio is {ratio}x. "
                    + (
                        "This indicates high financial leverage."
                        if ratio > Decimal("2.0")
                        else "This indicates moderate leverage."
                        if ratio > Decimal("1.0")
                        else "This indicates low leverage."
                    )
                ),
                limitations=(
                    "Does not consider off-balance-sheet "
                    "obligations or contingent liabilities.",
                ),
                related_metrics=(
                    "total_debt",
                    "total_equity",
                ),
                supporting_data={
                    "debt": str(snapshot.total_debt),
                    "equity": str(equity),
                    "period": snapshot.period_end.isoformat(),
                },
            )
        )

    return observations


def analyze_leverage_trend(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[BalanceSheetDeepObservation]:
    """
    Analyze leverage trend across periods.

    Looks at debt growth vs equity growth to determine if
    leverage is increasing or decreasing.
    """
    observations: list[BalanceSheetDeepObservation] = []

    ordered = sorted(snapshots, key=lambda s: s.period_end)

    if len(ordered) < 2:
        return observations

    # Calculate debt and equity for first and last periods
    first = ordered[0]
    last = ordered[-1]

    first_equity = first.total_equity or first.shareholders_equity
    last_equity = last.total_equity or last.shareholders_equity

    if (
        first.total_debt is None
        or last.total_debt is None
        or first_equity is None
        or last_equity is None
        or first_equity == 0
        or last_equity == 0
    ):
        return observations

    # Debt growth
    debt_growth = _pct_change(first.total_debt, last.total_debt)
    equity_growth = _pct_change(first_equity, last_equity)

    if debt_growth is None or equity_growth is None:
        return observations

    # Leverage change
    first_leverage = (
        first.total_debt / first_equity
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    last_leverage = (
        last.total_debt / last_equity
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    leverage_change = last_leverage - first_leverage

    src = _snapshot_source(last)
    ao, eff, pub = _snapshot_as_of(last)

    # Direction: lower leverage is better
    if leverage_change < 0:
        direction = BalanceSheetDirection.IMPROVING.value
        explanation = (
            f"Leverage decreased from {first_leverage}x to "
            f"{last_leverage}x ({leverage_change:+.2f}x) over "
            f"{len(ordered)} periods. Debt grew {debt_growth:.1f}% "
            f"while equity grew {equity_growth:.1f}%."
        )
    elif leverage_change > 0:
        direction = BalanceSheetDirection.DETERIORATING.value
        explanation = (
            f"Leverage increased from {first_leverage}x to "
            f"{last_leverage}x ({leverage_change:+.2f}x) over "
            f"{len(ordered)} periods. Debt grew {debt_growth:.1f}% "
            f"while equity grew {equity_growth:.1f}%."
        )
    else:
        direction = BalanceSheetDirection.STABLE.value
        explanation = (
            f"Leverage remained stable at {last_leverage}x over "
            f"{len(ordered)} periods."
        )

    observations.append(
        BalanceSheetDeepObservation(
            observation_id=_next_id("BSD"),
            symbol=symbol,
            category="balance_sheet_deep",
            observation_type="leverage_trend",
            period=(
                f"{first.period_end.isoformat()} to "
                f"{last.period_end.isoformat()}"
            ),
            metric="leverage",
            value=str(last_leverage),
            previous_value=str(first_leverage),
            change=str(
                leverage_change.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            ),
            direction=direction,
            severity=_determine_severity(
                "leverage_trend",
                leverage_change,
                threshold_high=Decimal("0.5"),
                threshold_medium=Decimal("0.25"),
            ),
            calculation_method=(
                "Leverage trend: debt/equity ratio change "
                "across reporting periods"
            ),
            calculation_inputs={
                "first_leverage": str(first_leverage),
                "last_leverage": str(last_leverage),
                "debt_growth_pct": str(debt_growth),
                "equity_growth_pct": str(equity_growth),
            },
            source_name=src[0],
            source_type=src[1],
            source_url=src[2],
            available_at=ao,
            as_of=as_of.isoformat(),
            effective_at=eff,
            explanation=explanation,
            limitations=(
                "Uses period-end values. "
                "Does not consider seasonal variations.",
            ),
            related_metrics=(
                "total_debt",
                "total_equity",
            ),
            supporting_data={
                "first_period": first.period_end.isoformat(),
                "last_period": last.period_end.isoformat(),
                "first_leverage": str(first_leverage),
                "last_leverage": str(last_leverage),
                "leverage_change": str(leverage_change),
                "debt_growth_pct": str(debt_growth),
                "equity_growth_pct": str(equity_growth),
                "periods": str(len(ordered)),
            },
        )
    )

    return observations


def analyze_current_ratio(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[BalanceSheetDeepObservation]:
    """
    Analyze current ratio (liquidity).

    Current ratio = Current assets / Current liabilities.
    """
    observations: list[BalanceSheetDeepObservation] = []

    ordered = sorted(snapshots, key=lambda s: s.period_end)

    for i, snapshot in enumerate(ordered):
        if (
            snapshot.current_assets is None
            or snapshot.current_liabilities is None
            or snapshot.current_liabilities == 0
        ):
            continue

        ratio = (
            snapshot.current_assets / snapshot.current_liabilities
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        src = _snapshot_source(snapshot)
        ao, eff, pub = _snapshot_as_of(snapshot)

        # Calculate change from previous period
        change = None
        change_pct = None
        prev_value = None
        if i > 0:
            prev = ordered[i - 1]
            if (
                prev.current_assets is not None
                and prev.current_liabilities is not None
                and prev.current_liabilities != 0
            ):
                prev_ratio = (
                    prev.current_assets / prev.current_liabilities
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                prev_value = str(prev_ratio)
                change = str(
                    (ratio - prev_ratio).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                )
                change_pct = str(
                    _pct_change(prev_ratio, ratio)
                )

        # Direction: higher ratio is generally better
        direction = _determine_direction(
            ratio,
            Decimal(prev_value) if prev_value else None,
            higher_is_better=True,
        )

        observations.append(
            BalanceSheetDeepObservation(
                observation_id=_next_id("BSD"),
                symbol=symbol,
                category="balance_sheet_deep",
                observation_type="current_ratio",
                period=snapshot.period_end.isoformat(),
                metric="current_ratio",
                value=str(ratio),
                previous_value=prev_value,
                change=change,
                change_pct=change_pct,
                direction=direction,
                severity=_determine_severity(
                    "current_ratio",
                    ratio,
                    threshold_high=Decimal("0.8"),
                    threshold_medium=Decimal("1.0"),
                ),
                calculation_method=(
                    "Current assets / Current liabilities"
                ),
                calculation_inputs={
                    "current_assets": str(
                        snapshot.current_assets
                    ),
                    "current_liabilities": str(
                        snapshot.current_liabilities
                    ),
                },
                source_name=src[0],
                source_type=src[1],
                source_url=src[2],
                available_at=ao,
                as_of=as_of.isoformat(),
                effective_at=eff,
                explanation=(
                    f"Current ratio is {ratio}x. "
                    + (
                        "This indicates potential liquidity "
                        "concerns."
                        if ratio < Decimal("1.0")
                        else "This indicates adequate short-term "
                        "liquidity."
                    )
                ),
                limitations=(
                    "Does not consider quality of current "
                    "assets or maturity of current liabilities.",
                ),
                related_metrics=(
                    "current_assets",
                    "current_liabilities",
                ),
                supporting_data={
                    "current_assets": str(
                        snapshot.current_assets
                    ),
                    "current_liabilities": str(
                        snapshot.current_liabilities
                    ),
                    "period": snapshot.period_end.isoformat(),
                },
            )
        )

    return observations


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


def analyze_balance_sheet_deep(
    *,
    symbol: str,
    as_of: datetime,
    snapshots: Sequence[FinancialSnapshot],
) -> BalanceSheetDeepResult:
    """
    Complete balance sheet analysis for one company.

    Combines all balance sheet dimensions into a single
    result with full provenance.
    """
    if not snapshots:
        return BalanceSheetDeepResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            notes=("No financial data available.",),
        )

    observations: list[BalanceSheetDeepObservation] = []

    # Run all analyses
    observations.extend(
        analyze_net_debt(snapshots, symbol, as_of)
    )
    observations.extend(
        analyze_cash_to_debt(snapshots, symbol, as_of)
    )
    observations.extend(
        analyze_debt_to_equity(snapshots, symbol, as_of)
    )
    observations.extend(
        analyze_leverage_trend(snapshots, symbol, as_of)
    )
    observations.extend(
        analyze_current_ratio(snapshots, symbol, as_of)
    )

    # Calculate summary metrics
    net_debt_rev_values = [
        Decimal(o.supporting_data.get("net_debt_to_revenue", "0"))
        for o in observations
        if o.observation_type == "net_debt"
        and o.supporting_data.get("net_debt_to_revenue")
        != "unavailable"
    ]
    cash_debt_values = [
        Decimal(o.value)
        for o in observations
        if o.observation_type == "cash_to_debt"
        and o.value is not None
    ]
    debt_equity_values = [
        Decimal(o.value)
        for o in observations
        if o.observation_type == "debt_to_equity"
        and o.value is not None
    ]

    avg_ndr = (
        str(
            (
                sum(net_debt_rev_values)
                / len(net_debt_rev_values)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )
        if net_debt_rev_values
        else None
    )
    avg_cd = (
        str(
            (sum(cash_debt_values) / len(cash_debt_values)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        )
        if cash_debt_values
        else None
    )
    avg_de = (
        str(
            (
                sum(debt_equity_values) / len(debt_equity_values)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        )
        if debt_equity_values
        else None
    )

    # Get latest leverage from trend observation
    latest_leverage = None
    for o in observations:
        if o.observation_type == "leverage_trend":
            latest_leverage = o.value
            break

    # Determine overall direction
    improving = sum(
        1
        for o in observations
        if o.direction == BalanceSheetDirection.IMPROVING.value
    )
    deteriorating = sum(
        1
        for o in observations
        if o.direction == BalanceSheetDirection.DETERIORATING.value
    )

    if improving > deteriorating:
        overall_direction = BalanceSheetDirection.IMPROVING.value
    elif deteriorating > improving:
        overall_direction = BalanceSheetDirection.DETERIORATING.value
    else:
        overall_direction = BalanceSheetDirection.STABLE.value

    return BalanceSheetDeepResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        observations=tuple(observations),
        avg_net_debt_to_revenue=avg_ndr,
        avg_cash_to_debt=avg_cd,
        avg_debt_to_equity=avg_de,
        latest_leverage=latest_leverage,
        direction=overall_direction,
        period_count=len(snapshots),
        notes=(),
    )
