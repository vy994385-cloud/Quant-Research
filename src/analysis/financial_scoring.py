from __future__ import annotations

from decimal import Decimal

from src.analysis.financial_ratios import (
    cash_conversion_ratio,
    debt_to_revenue,
    free_cash_flow_margin,
    net_profit_margin,
    receivables_to_revenue,
    revenue_growth,
)
from src.data.company.financials import FinancialSnapshot


def _clamp(value: Decimal) -> Decimal:
    return max(
        Decimal("0"),
        min(Decimal("100"), value),
    )


def _score_range(
    value: Decimal | None,
    low: Decimal,
    high: Decimal,
) -> Decimal:
    if value is None:
        return Decimal("50")

    if value <= low:
        return Decimal("0")

    if value >= high:
        return Decimal("100")

    return _clamp(
        ((value - low) / (high - low))
        * Decimal("100")
    )


def _score_lower_is_better(
    value: Decimal | None,
    good: Decimal,
    bad: Decimal,
) -> Decimal:
    if value is None:
        return Decimal("50")

    if value <= good:
        return Decimal("100")

    if value >= bad:
        return Decimal("0")

    return _clamp(
        ((bad - value) / (bad - good))
        * Decimal("100")
    )


def score_fundamentals(
    snapshot: FinancialSnapshot,
) -> Decimal:
    """
    Score profitability and cash generation.

    Uses:
    - net profit margin
    - free cash flow margin
    """

    npm = _score_range(
        net_profit_margin(snapshot),
        Decimal("5"),
        Decimal("25"),
    )

    fcf_margin = _score_range(
        free_cash_flow_margin(snapshot),
        Decimal("3"),
        Decimal("20"),
    )

    return (npm + fcf_margin) / Decimal("2")


def score_balance_sheet(
    snapshot: FinancialSnapshot,
) -> Decimal:
    """
    Lower debt relative to revenue receives a higher score.
    """

    return _score_lower_is_better(
        debt_to_revenue(snapshot),
        Decimal("0.05"),
        Decimal("0.50"),
    )


def score_cash_flow(
    snapshot: FinancialSnapshot,
) -> Decimal:
    """
    Operating cash conversion relative to accounting profit.
    """

    return _score_range(
        cash_conversion_ratio(snapshot),
        Decimal("70"),
        Decimal("120"),
    )


def score_receivables_quality(
    snapshot: FinancialSnapshot,
) -> Decimal:
    """
    Lower receivables relative to revenue receives a higher
    descriptive score.

    This is a provisional cross-sector heuristic and must
    eventually be calibrated by sector.
    """

    return _score_lower_is_better(
        receivables_to_revenue(snapshot),
        Decimal("10"),
        Decimal("35"),
    )


def score_growth(
    previous: FinancialSnapshot,
    current: FinancialSnapshot,
) -> Decimal:
    """
    Score year-over-year revenue growth.
    """

    return _score_range(
        revenue_growth(previous, current),
        Decimal("0"),
        Decimal("20"),
    )


def score_financial_snapshot(
    *,
    previous: FinancialSnapshot | None,
    current: FinancialSnapshot,
) -> dict[str, Decimal]:
    """
    Produce normalized financial research components.

    Missing previous-period data does not get fabricated.
    Growth receives a neutral score when unavailable.
    """

    growth = (
        score_growth(previous, current)
        if previous is not None
        else Decimal("50")
    )

    fundamentals = score_fundamentals(current)

    cash_flow = score_cash_flow(current)

    balance_sheet = score_balance_sheet(current)

    receivables_quality = score_receivables_quality(current)

    financial_trends = (
        growth + receivables_quality
    ) / Decimal("2")

    return {
        "fundamentals": _clamp(fundamentals),
        "financial_trends": _clamp(financial_trends),
        "cash_flow": _clamp(cash_flow),
        "balance_sheet": _clamp(balance_sheet),
    }
