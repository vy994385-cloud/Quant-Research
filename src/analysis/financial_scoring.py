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
from src.analysis.research_coverage import (
    ResearchComponentStatus,
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

    Missing data remains numerically neutral for compatibility.
    Evidence availability is tracked separately.
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

    Missing data remains numerically neutral for compatibility.
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

    Missing previous period remains numerically neutral.
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

    A high receivables ratio is a monitoring signal,
    not an automatic misconduct finding.
    """

    return _score_lower_is_better(
        receivables_to_revenue(snapshot),
        Decimal("10"),
        Decimal("35"),
    )


def _profitability_status(
    snapshot: FinancialSnapshot,
) -> ResearchComponentStatus:
    """
    Profitability requires actual profit and revenue evidence.

    FCF is used as a secondary profitability-quality input,
    but its absence makes the component partial rather than
    pretending that the entire component is fully evidenced.
    """

    if (
        snapshot.revenue is None
        or snapshot.net_profit is None
    ):
        return ResearchComponentStatus.MISSING

    if snapshot.free_cash_flow is None:
        return ResearchComponentStatus.PARTIAL

    return ResearchComponentStatus.AVAILABLE


def _financial_trends_status(
    previous: FinancialSnapshot | None,
    current: FinancialSnapshot,
) -> ResearchComponentStatus:
    """
    Financial trends use:

    - revenue growth
    - working-capital quality

    A previous period is required for genuine growth evidence.
    """

    revenue_available = (
        current.revenue is not None
    )

    receivables_available = (
        current.receivables is not None
        and current.revenue is not None
    )

    growth_available = (
        previous is not None
        and previous.revenue is not None
        and current.revenue is not None
    )

    usable_signals = sum(
        (
            growth_available,
            receivables_available,
        )
    )

    if usable_signals == 0:
        return ResearchComponentStatus.MISSING

    if usable_signals == 2:
        return ResearchComponentStatus.AVAILABLE

    return ResearchComponentStatus.PARTIAL


def _cash_flow_status(
    snapshot: FinancialSnapshot,
) -> ResearchComponentStatus:
    """
    Cash-flow quality requires operating cash flow and profit.
    """

    if (
        snapshot.operating_cash_flow is None
        or snapshot.net_profit is None
    ):
        return ResearchComponentStatus.MISSING

    return ResearchComponentStatus.AVAILABLE


def _balance_sheet_status(
    snapshot: FinancialSnapshot,
) -> ResearchComponentStatus:
    """
    Balance-sheet quality requires debt and revenue evidence.
    """

    if (
        snapshot.total_debt is None
        or snapshot.revenue is None
    ):
        return ResearchComponentStatus.MISSING

    return ResearchComponentStatus.AVAILABLE


def score_financial_snapshot(
    *,
    previous: FinancialSnapshot | None,
    current: FinancialSnapshot,
) -> dict[str, Decimal]:
    """
    Produce normalized financial research components.

    Numeric compatibility values may remain neutral when
    observations are missing.

    IMPORTANT:
    Evidence state is exposed separately through
    financial_component_status().
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


def financial_component_status(
    *,
    previous: FinancialSnapshot | None,
    current: FinancialSnapshot,
) -> dict[str, ResearchComponentStatus]:
    """
    Return truthful evidence availability for each financial
    research component.

    Numeric scores and evidence status are intentionally separate.
    """

    return {
        "fundamentals": _profitability_status(
            current
        ),
        "financial_trends": _financial_trends_status(
            previous,
            current,
        ),
        "cash_flow": _cash_flow_status(
            current
        ),
        "balance_sheet": _balance_sheet_status(
            current
        ),
    }


def financial_quality_score(
    scores: dict[str, Decimal],
) -> Decimal:
    """
    Combine normalized financial components into one
    descriptive financial-quality score.
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