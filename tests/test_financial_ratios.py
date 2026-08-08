from datetime import date
from decimal import Decimal

from src.analysis.financial_ratios import (
    cash_conversion_ratio,
    cash_to_debt,
    debt_to_revenue,
    free_cash_flow_margin,
    net_profit_margin,
    operating_cash_flow_margin,
    payables_to_revenue,
    receivables_to_revenue,
    revenue_growth,
)
from src.data.company.financials import FinancialSnapshot


def make_snapshot(
    revenue: str = "1000",
    net_profit: str = "100",
    operating_cash_flow: str = "120",
    free_cash_flow: str = "80",
    receivables: str = "150",
    payables: str = "100",
    debt: str = "500",
    cash: str = "200",
) -> FinancialSnapshot:

    return FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        revenue=Decimal(revenue),
        net_profit=Decimal(net_profit),
        operating_cash_flow=Decimal(operating_cash_flow),
        free_cash_flow=Decimal(free_cash_flow),
        receivables=Decimal(receivables),
        payables=Decimal(payables),
        total_debt=Decimal(debt),
        cash_and_equivalents=Decimal(cash),
    )


def test_revenue_growth():

    previous = make_snapshot(revenue="1000")
    current = make_snapshot(revenue="1200")

    assert revenue_growth(
        previous,
        current,
    ) == Decimal("20")


def test_net_profit_margin():

    snapshot = make_snapshot()

    assert net_profit_margin(
        snapshot,
    ) == Decimal("10.0")


def test_operating_cash_flow_margin():

    snapshot = make_snapshot()

    assert operating_cash_flow_margin(
        snapshot,
    ) == Decimal("12.0")


def test_free_cash_flow_margin():

    snapshot = make_snapshot()

    assert free_cash_flow_margin(
        snapshot,
    ) == Decimal("8.0")


def test_receivables_to_revenue():

    snapshot = make_snapshot()

    assert receivables_to_revenue(
        snapshot,
    ) == Decimal("15.0")


def test_payables_to_revenue():

    snapshot = make_snapshot()

    assert payables_to_revenue(
        snapshot,
    ) == Decimal("10.0")


def test_debt_to_revenue():

    snapshot = make_snapshot()

    assert debt_to_revenue(
        snapshot,
    ) == Decimal("0.5")


def test_cash_to_debt():

    snapshot = make_snapshot()

    assert cash_to_debt(
        snapshot,
    ) == Decimal("0.4")


def test_cash_conversion_ratio():

    snapshot = make_snapshot()

    assert cash_conversion_ratio(
        snapshot,
    ) == Decimal("120")
