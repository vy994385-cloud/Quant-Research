"""
Balance-sheet quality analysis.

Tracks changes in leverage, liquidity, working capital, cash vs
debt, and equity across consecutive financial periods.  Each
observation is descriptive and carries its own data-quality status.

Thresholds (documented for traceability):
  - Debt/revenue growth exceeding revenue growth by >= 20pp:
    accelerating-debt signal.
  - Current ratio decline >= 0.5 between periods:
    liquidity-deterioration signal.
  - Working capital negative for >= 2 consecutive periods:
    sustained negative working capital.
  - Cash/debt ratio decline >= 20% (relative):
    cash-position weakening.
  - Equity decline >= 10% in a single period:
    equity-erosion signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Sequence

from src.data.company.financials import FinancialSnapshot


_HUNDRED = Decimal("100")

# Thresholds
_ACCELERATING_DEBT_DIVERGENCE = Decimal("20")
_LIQUIDITY_DECLINE_THRESHOLD = Decimal("0.5")
_NEGATIVE_WORKING_CAPITAL_PERIODS = 2
_CASH_DEBT_DECLINE_PCT = Decimal("20")
_EQUITY_EROSION_THRESHOLD = Decimal("10")


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
class DebtGrowthComparison:
    """Comparison of debt growth vs revenue growth for one period."""

    period: str
    debt_growth_rate: str | None = None
    revenue_growth_rate: str | None = None
    divergence_pp: str | None = None
    flagged: bool = False
    explanation: str = ""


@dataclass(frozen=True)
class LiquidityChange:
    """Change in current ratio between two periods."""

    from_period: str
    to_period: str
    previous_ratio: str | None = None
    current_ratio: str | None = None
    change: str | None = None
    deteriorated: bool = False
    explanation: str = ""


@dataclass(frozen=True)
class WorkingCapitalChange:
    """Working capital change between two periods."""

    from_period: str
    to_period: str
    previous_value: str | None = None
    current_value: str | None = None
    change: str | None = None
    explanation: str = ""


@dataclass(frozen=True)
class CashDebtChange:
    """Change in cash/debt ratio between two periods."""

    from_period: str
    to_period: str
    previous_ratio: str | None = None
    current_ratio: str | None = None
    change_pct: str | None = None
    weakened: bool = False
    explanation: str = ""


@dataclass(frozen=True)
class EquityChange:
    """Change in equity between two periods."""

    from_period: str
    to_period: str
    previous_value: str | None = None
    current_value: str | None = None
    change_pct: str | None = None
    eroded: bool = False
    explanation: str = ""


@dataclass(frozen=True)
class BalanceSheetObservation:
    """
    A derived balance-sheet quality observation across periods.

    Each observation is descriptive only.
    """

    observation_type: str
    symbol: str
    severity: str

    periods_covered: int = 0
    first_period: str = ""
    last_period: str = ""

    debt_comparisons: list[DebtGrowthComparison] = field(
        default_factory=list
    )
    liquidity_changes: list[LiquidityChange] = field(
        default_factory=list
    )
    working_capital_changes: list[WorkingCapitalChange] = field(
        default_factory=list
    )
    cash_debt_changes: list[CashDebtChange] = field(
        default_factory=list
    )
    equity_changes: list[EquityChange] = field(
        default_factory=list
    )

    persistent: bool = False
    explanation: str = ""


# ---------------------------------------------------------------------------
# Debt growth vs revenue growth
# ---------------------------------------------------------------------------

def compare_debt_vs_revenue_growth(
    snapshots: Sequence[FinancialSnapshot],
) -> list[DebtGrowthComparison]:
    """Compare debt growth rate to revenue growth rate per period."""
    ordered = _ordered_snapshots(snapshots)
    results: list[DebtGrowthComparison] = []

    for i in range(len(ordered) - 1):
        prev = ordered[i]
        curr = ordered[i + 1]
        period = curr.period_end.isoformat()

        debt_gr = _pct_change(prev.total_debt, curr.total_debt)
        rev_gr = _pct_change(prev.revenue, curr.revenue)

        if debt_gr is None or rev_gr is None:
            results.append(
                DebtGrowthComparison(
                    period=period,
                    explanation="Insufficient data.",
                )
            )
            continue

        divergence = debt_gr - rev_gr
        flagged = divergence >= _ACCELERATING_DEBT_DIVERGENCE

        explanation = (
            f"Debt grew {debt_gr:.1f}% vs revenue "
            f"{rev_gr:.1f}% (divergence: "
            f"{divergence:+.1f}pp)."
        )
        if flagged:
            explanation += (
                " Debt is accelerating relative to revenue."
            )

        results.append(
            DebtGrowthComparison(
                period=period,
                debt_growth_rate=str(debt_gr),
                revenue_growth_rate=str(rev_gr),
                divergence_pp=str(divergence),
                flagged=flagged,
                explanation=explanation,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Liquidity trajectory
# ---------------------------------------------------------------------------

def track_liquidity(
    snapshots: Sequence[FinancialSnapshot],
) -> list[LiquidityChange]:
    """Track current-ratio changes across periods."""
    ordered = _ordered_snapshots(snapshots)
    results: list[LiquidityChange] = []

    for i in range(len(ordered) - 1):
        prev = ordered[i]
        curr = ordered[i + 1]

        prev_ratio = _safe_div(
            prev.current_assets, prev.current_liabilities
        )
        curr_ratio = _safe_div(
            curr.current_assets, curr.current_liabilities
        )

        if prev_ratio is None or curr_ratio is None:
            continue

        change = curr_ratio - prev_ratio
        deteriorated = change <= -_LIQUIDITY_DECLINE_THRESHOLD

        explanation = (
            f"Current ratio: {prev_ratio} -> {curr_ratio} "
            f"(change: {change:+.2f})."
        )
        if deteriorated:
            explanation += (
                " Material liquidity decline detected."
            )

        results.append(
            LiquidityChange(
                from_period=prev.period_end.isoformat(),
                to_period=curr.period_end.isoformat(),
                previous_ratio=str(prev_ratio),
                current_ratio=str(curr_ratio),
                change=str(change),
                deteriorated=deteriorated,
                explanation=explanation,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Working capital trajectory
# ---------------------------------------------------------------------------

def track_working_capital(
    snapshots: Sequence[FinancialSnapshot],
) -> list[WorkingCapitalChange]:
    """Track working capital changes across periods."""
    ordered = _ordered_snapshots(snapshots)
    results: list[WorkingCapitalChange] = []

    for i in range(len(ordered) - 1):
        prev = ordered[i]
        curr = ordered[i + 1]

        if (
            prev.current_assets is None
            or prev.current_liabilities is None
            or curr.current_assets is None
            or curr.current_liabilities is None
        ):
            continue

        prev_wc = (
            prev.current_assets - prev.current_liabilities
        )
        curr_wc = (
            curr.current_assets - curr.current_liabilities
        )
        change = curr_wc - prev_wc

        explanation = (
            f"Working capital: {prev_wc} -> {curr_wc} "
            f"(change: {change:+.2f})."
        )

        results.append(
            WorkingCapitalChange(
                from_period=prev.period_end.isoformat(),
                to_period=curr.period_end.isoformat(),
                previous_value=str(prev_wc),
                current_value=str(curr_wc),
                change=str(change),
                explanation=explanation,
            )
        )

    return results


def detect_sustained_negative_working_capital(
    snapshots: Sequence[FinancialSnapshot],
) -> BalanceSheetObservation | None:
    """Flag sustained negative working capital."""
    ordered = _ordered_snapshots(snapshots)

    negative_periods: list[str] = []
    wc_changes = track_working_capital(snapshots)

    for s in ordered:
        if (
            s.current_assets is None
            or s.current_liabilities is None
        ):
            continue
        wc = s.current_assets - s.current_liabilities
        if wc < 0:
            negative_periods.append(s.period_end.isoformat())

    if len(negative_periods) < _NEGATIVE_WORKING_CAPITAL_PERIODS:
        return None

    return BalanceSheetObservation(
        observation_type="sustained_negative_working_capital",
        symbol=ordered[0].symbol if ordered else "",
        severity="MEDIUM",
        periods_covered=len(negative_periods),
        first_period=negative_periods[0],
        last_period=negative_periods[-1],
        working_capital_changes=wc_changes,
        persistent=True,
        explanation=(
            f"Working capital was negative in "
            f"{len(negative_periods)} period(s) "
            f"({negative_periods[0]} to "
            f"{negative_periods[-1]}). This is a monitoring "
            f"signal -- not an automatic finding of distress."
        ),
    )


# ---------------------------------------------------------------------------
# Cash vs debt changes
# ---------------------------------------------------------------------------

def track_cash_debt_ratio(
    snapshots: Sequence[FinancialSnapshot],
) -> list[CashDebtChange]:
    """Track changes in cash/debt ratio."""
    ordered = _ordered_snapshots(snapshots)
    results: list[CashDebtChange] = []

    for i in range(len(ordered) - 1):
        prev = ordered[i]
        curr = ordered[i + 1]

        prev_ratio = _safe_div(
            prev.cash_and_equivalents, prev.total_debt
        )
        curr_ratio = _safe_div(
            curr.cash_and_equivalents, curr.total_debt
        )

        if prev_ratio is None or curr_ratio is None:
            continue

        change_pct = _pct_change(prev_ratio, curr_ratio)

        weakened = False
        if change_pct is not None:
            weakened = change_pct <= -_CASH_DEBT_DECLINE_PCT

        explanation = (
            f"Cash/debt ratio: {prev_ratio:.4f} -> "
            f"{curr_ratio:.4f}."
        )
        if weakened:
            explanation += (
                " Cash position weakened materially "
                "relative to debt."
            )

        results.append(
            CashDebtChange(
                from_period=prev.period_end.isoformat(),
                to_period=curr.period_end.isoformat(),
                previous_ratio=str(prev_ratio),
                current_ratio=str(curr_ratio),
                change_pct=(
                    str(change_pct)
                    if change_pct is not None
                    else None
                ),
                weakened=weakened,
                explanation=explanation,
            )
        )

    return results


# ---------------------------------------------------------------------------
# Equity changes
# ---------------------------------------------------------------------------

def track_equity_changes(
    snapshots: Sequence[FinancialSnapshot],
) -> list[EquityChange]:
    """Track equity changes across periods."""
    ordered = _ordered_snapshots(snapshots)
    results: list[EquityChange] = []

    for i in range(len(ordered) - 1):
        prev = ordered[i]
        curr = ordered[i + 1]

        prev_eq = prev.shareholders_equity or prev.total_equity
        curr_eq = curr.shareholders_equity or curr.total_equity

        if prev_eq is None or curr_eq is None:
            continue

        change_pct = _pct_change(prev_eq, curr_eq)
        eroded = False

        if change_pct is not None:
            eroded = change_pct <= -_EQUITY_EROSION_THRESHOLD

        explanation = (
            f"Equity: {prev_eq} -> {curr_eq}."
        )
        if change_pct is not None:
            explanation += f" Change: {change_pct:.1f}%."
        if eroded:
            explanation += " Material equity erosion detected."

        results.append(
            EquityChange(
                from_period=prev.period_end.isoformat(),
                to_period=curr.period_end.isoformat(),
                previous_value=str(prev_eq),
                current_value=str(curr_eq),
                change_pct=(
                    str(change_pct)
                    if change_pct is not None
                    else None
                ),
                eroded=eroded,
                explanation=explanation,
            )
        )

    return results


# ---------------------------------------------------------------------------
# High-level orchestrator
# ---------------------------------------------------------------------------

def analyze_balance_sheet_quality(
    snapshots: Sequence[FinancialSnapshot],
) -> list[BalanceSheetObservation]:
    """
    Full balance-sheet quality analysis across all periods.

    Returns a list of observations. Empty list means no quality
    signals were detected with the available data.
    """
    observations: list[BalanceSheetObservation] = []
    ordered = _ordered_snapshots(snapshots)

    if len(ordered) < 2:
        return observations

    symbol = ordered[0].symbol

    # Debt vs revenue divergence
    debt_comparisons = compare_debt_vs_revenue_growth(snapshots)
    flagged_debt = [d for d in debt_comparisons if d.flagged]

    if flagged_debt:
        observations.append(
            BalanceSheetObservation(
                observation_type="accelerating_debt",
                symbol=symbol,
                severity=(
                    "HIGH" if len(flagged_debt) >= 2 else "MEDIUM"
                ),
                periods_covered=len(flagged_debt),
                first_period=flagged_debt[0].period,
                last_period=flagged_debt[-1].period,
                debt_comparisons=debt_comparisons,
                explanation=(
                    f"Debt growth exceeded revenue growth by "
                    f">={_ACCELERATING_DEBT_DIVERGENCE}pp in "
                    f"{len(flagged_debt)} period(s)."
                ),
            )
        )

    # Liquidity deterioration
    liquidity = track_liquidity(snapshots)
    deteriorated = [l for l in liquidity if l.deteriorated]

    if deteriorated:
        observations.append(
            BalanceSheetObservation(
                observation_type="liquidity_deterioration",
                symbol=symbol,
                severity=(
                    "HIGH"
                    if len(deteriorated) >= 2
                    else "MEDIUM"
                ),
                periods_covered=len(deteriorated),
                first_period=deteriorated[0].to_period,
                last_period=deteriorated[-1].to_period,
                liquidity_changes=liquidity,
                explanation=(
                    f"Current ratio declined by "
                    f">={_LIQUIDITY_DECLINE_THRESHOLD} in "
                    f"{len(deteriorated)} period(s)."
                ),
            )
        )

    # Sustained negative working capital
    neg_wc = detect_sustained_negative_working_capital(snapshots)
    if neg_wc is not None:
        observations.append(neg_wc)

    # Cash/debt weakening
    cash_debt = track_cash_debt_ratio(snapshots)
    weakened = [c for c in cash_debt if c.weakened]

    if weakened:
        observations.append(
            BalanceSheetObservation(
                observation_type="cash_debt_weakening",
                symbol=symbol,
                severity="MEDIUM",
                periods_covered=len(weakened),
                first_period=weakened[0].to_period,
                last_period=weakened[-1].to_period,
                cash_debt_changes=cash_debt,
                explanation=(
                    f"Cash/debt ratio declined by "
                    f">={_CASH_DEBT_DECLINE_PCT}% "
                    f"(relative) in {len(weakened)} period(s)."
                ),
            )
        )

    # Equity erosion
    equity = track_equity_changes(snapshots)
    eroded = [e for e in equity if e.eroded]

    if eroded:
        observations.append(
            BalanceSheetObservation(
                observation_type="equity_erosion",
                symbol=symbol,
                severity="MEDIUM",
                periods_covered=len(eroded),
                first_period=eroded[0].to_period,
                last_period=eroded[-1].to_period,
                equity_changes=equity,
                explanation=(
                    f"Equity declined by "
                    f">={_EQUITY_EROSION_THRESHOLD}% in "
                    f"{len(eroded)} period(s)."
                ),
            )
        )

    return observations
