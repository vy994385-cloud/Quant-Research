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


ZERO = Decimal("0")
HUNDRED = Decimal("100")
NEUTRAL = Decimal("50")


def _clamp(value: Decimal) -> Decimal:
    return max(
        ZERO,
        min(HUNDRED, value),
    )


def _score_range(
    value: Decimal | None,
    low: Decimal,
    high: Decimal,
) -> Decimal:
    """
    Higher value receives a higher score.

    Thresholds are provisional research heuristics and should
    eventually be calibrated by sector and historical data.
    """

    if value is None:
        return NEUTRAL

    if value <= low:
        return ZERO

    if value >= high:
        return HUNDRED

    return _clamp(
        ((value - low) / (high - low))
        * HUNDRED
    )


def _score_lower_is_better(
    value: Decimal | None,
    good: Decimal,
    bad: Decimal,
) -> Decimal:
    """
    Lower value receives a higher score.
    """

    if value is None:
        return NEUTRAL

    if value <= good:
        return HUNDRED

    if value >= bad:
        return ZERO

    return _clamp(
        ((bad - value) / (bad - good))
        * HUNDRED
    )


def score_profitability(
    snapshot: FinancialSnapshot,
) -> Decimal:
    """
    Evaluate earnings quality using:

    - net profit margin
    - free cash flow margin
    """

    npm_score = _score_range(
        net_profit_margin(snapshot),
        Decimal("5"),
        Decimal("25"),
    )

    fcf_score = _score_range(
        free_cash_flow_margin(snapshot),
        Decimal("3"),
        Decimal("20"),
    )

    return (
        npm_score + fcf_score
    ) / Decimal("2")


def score_growth(
    previous: FinancialSnapshot | None,
    current: FinancialSnapshot,
) -> Decimal:
    """
    Evaluate year-over-year revenue growth.

    No previous period means neutral rather than fabricated growth.
    """

    if previous is None:
        return NEUTRAL

    return _score_range(
        revenue_growth(previous, current),
        Decimal("0"),
        Decimal("20"),
    )


def score_cash_flow(
    snapshot: FinancialSnapshot,
) -> Decimal:
    """
    Evaluate operating cash flow relative to accounting profit.

    A ratio around 100% indicates strong conversion of reported
    earnings into operating cash.
    """

    return _score_range(
        cash_conversion_ratio(snapshot),
        Decimal("70"),
        Decimal("120"),
    )


def score_balance_sheet(
    snapshot: FinancialSnapshot,
) -> Decimal:
    """
    Evaluate leverage relative to revenue.

    Lower debt/revenue receives a higher score.
    """

    return _score_lower_is_better(
        debt_to_revenue(snapshot),
        Decimal("0.05"),
        Decimal("0.50"),
    )


def score_working_capital(
    snapshot: FinancialSnapshot,
) -> Decimal:
    """
    Evaluate receivables relative to revenue.

    This is deliberately only one working-capital signal.
    A high receivables ratio is not automatically evidence
    of misconduct or poor business quality.
    """

    return _score_lower_is_better(
        receivables_to_revenue(snapshot),
        Decimal("10"),
        Decimal("35"),
    )


def score_financial_snapshot(
    *,
    previous: FinancialSnapshot | None,
    current: FinancialSnapshot,
) -> dict[str, Decimal]:
    """
    Produce normalized financial research components.

    Component architecture:

        fundamentals
            = profitability

        financial_trends
            = revenue growth + working-capital quality

        cash_flow
            = cash conversion

        balance_sheet
            = leverage

    Every returned component is normalized to 0-100.

    Missing observations receive a neutral score rather than
    being treated as either good or bad.
    """

    profitability = score_profitability(
        current
    )

    growth = score_growth(
        previous,
        current,
    )

    working_capital = score_working_capital(
        current
    )

    cash_flow = score_cash_flow(
        current
    )

    balance_sheet = score_balance_sheet(
        current
    )

    financial_trends = (
        growth + working_capital
    ) / Decimal("2")

    return {
        "fundamentals": _clamp(
            profitability
        ),
        "financial_trends": _clamp(
            financial_trends
        ),
        "cash_flow": _clamp(
            cash_flow
        ),
        "balance_sheet": _clamp(
            balance_sheet
        ),
    }


def financial_quality_score(
    scores: dict[str, Decimal],
) -> Decimal:
    """
    Combine normalized financial components into one
    descriptive financial-quality score.

    The weights are explicit and provisional.
    They must eventually be validated out-of-sample.
    """

    weights = {
        "fundamentals": Decimal("0.30"),
        "financial_trends": Decimal("0.25"),
        "cash_flow": Decimal("0.25"),
        "balance_sheet": Decimal("0.20"),
    }

    total = sum(
        scores[name] * weight
        for name, weight in weights.items()
    )

    return _clamp(total)
