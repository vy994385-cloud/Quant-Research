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


from src.analysis.financial_scoring import (
    financial_component_status,
)
from src.analysis.research_coverage import (
    ResearchComponentStatus,
)


def test_financial_component_status_is_available_with_complete_data():
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

    status = financial_component_status(
        previous=previous,
        current=current,
    )

    assert status["fundamentals"] == ResearchComponentStatus.AVAILABLE
    assert status["financial_trends"] == ResearchComponentStatus.AVAILABLE
    assert status["cash_flow"] == ResearchComponentStatus.AVAILABLE
    assert status["balance_sheet"] == ResearchComponentStatus.AVAILABLE


def test_missing_cash_flow_is_not_treated_as_available():
    current = make_snapshot(
        period_end=date(2026, 3, 31),
        revenue="1100",
        profit="220",
        debt="50",
        fcf="190",
        receivables="105",
        ocf="230",
    ).model_copy(
        update={
            "operating_cash_flow": None,
        }
    )

    status = financial_component_status(
        previous=None,
        current=current,
    )

    assert (
        status["cash_flow"]
        == ResearchComponentStatus.MISSING
    )


def test_missing_previous_period_makes_trends_partial():
    current = make_snapshot(
        period_end=date(2026, 3, 31),
        revenue="1100",
        profit="220",
        debt="50",
        fcf="190",
        receivables="105",
        ocf="230",
    )

    status = financial_component_status(
        previous=None,
        current=current,
    )

    assert (
        status["financial_trends"]
        == ResearchComponentStatus.PARTIAL
    )


def test_missing_debt_makes_balance_sheet_missing():
    current = make_snapshot(
        period_end=date(2026, 3, 31),
        revenue="1100",
        profit="220",
        debt="50",
        fcf="190",
        receivables="105",
        ocf="230",
    ).model_copy(
        update={
            "total_debt": None,
        }
    )

    status = financial_component_status(
        previous=None,
        current=current,
    )

    assert (
        status["balance_sheet"]
        == ResearchComponentStatus.MISSING
    )