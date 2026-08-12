from datetime import date
from decimal import Decimal

from src.analysis.financial_scoring import (
    score_financial_snapshot,
)
from src.data.company.financials import FinancialSnapshot


def make_snapshot(
    *,
    period_end: date,
    revenue: str,
    profit: str,
    debt: str,
    fcf: str,
    receivables: str,
    ocf: str,
) -> FinancialSnapshot:
    return FinancialSnapshot(
        symbol="TCS",
        period_end=period_end,
        revenue=Decimal(revenue),
        net_profit=Decimal(profit),
        total_assets=Decimal("1000"),
        total_debt=Decimal(debt),
        free_cash_flow=Decimal(fcf),
        receivables=Decimal(receivables),
        operating_cash_flow=Decimal(ocf),
    )


def test_financial_scoring_returns_normalized_components():
    previous = make_snapshot(
        period_end=date(2025, 3, 31),
        revenue="1000",
        profit="180",
        debt="50",
        fcf="150",
        receivables="100",
        ocf="190",
    )

    current = make_snapshot(
        period_end=date(2026, 3, 31),
        revenue="1100",
        profit="220",
        debt="50",
        fcf="190",
        receivables="105",
        ocf="230",
    )

    scores = score_financial_snapshot(
        previous=previous,
        current=current,
    )

    assert set(scores) == {
        "fundamentals",
        "financial_trends",
        "cash_flow",
        "balance_sheet",
    }

    for value in scores.values():
        assert Decimal("0") <= value <= Decimal("100")


def test_growth_is_reflected_in_financial_trends():
    previous = make_snapshot(
        period_end=date(2025, 3, 31),
        revenue="1000",
        profit="180",
        debt="50",
        fcf="150",
        receivables="100",
        ocf="190",
    )

    current = make_snapshot(
        period_end=date(2026, 3, 31),
        revenue="1200",
        profit="220",
        debt="50",
        fcf="190",
        receivables="105",
        ocf="230",
    )

    scores = score_financial_snapshot(
        previous=previous,
        current=current,
    )

    assert scores["financial_trends"] > Decimal("50")


def test_missing_previous_period_uses_neutral_growth():
    current = make_snapshot(
        period_end=date(2026, 3, 31),
        revenue="1100",
        profit="220",
        debt="50",
        fcf="190",
        receivables="105",
        ocf="230",
    )

    scores = score_financial_snapshot(
        previous=None,
        current=current,
    )

    assert Decimal("0") <= scores["financial_trends"] <= Decimal("100")
