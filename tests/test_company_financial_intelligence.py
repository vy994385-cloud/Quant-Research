from datetime import date
from decimal import Decimal

from src.analysis.company_financial_intelligence import (
    build_financial_company_intelligence,
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
        total_debt=Decimal(debt),
        free_cash_flow=Decimal(fcf),
        receivables=Decimal(receivables),
        operating_cash_flow=Decimal(ocf),
    )


def test_financial_intelligence_contains_real_observations():
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

    result = build_financial_company_intelligence(
        symbol="TCS",
        as_of_date=date(2026, 3, 31),
        snapshots=[previous, current],
    )

    assert result.symbol == "TCS"
    assert result.signal_count > 0
    assert result.financial_observations
    assert any(
        "revenue growth" in item.lower()
        for item in result.financial_observations
    )


def test_financial_intelligence_detects_profit_cash_divergence():
    current = make_snapshot(
        period_end=date(2026, 3, 31),
        revenue="1000",
        profit="150",
        debt="50",
        fcf="50",
        receivables="100",
        ocf="-20",
    )

    result = build_financial_company_intelligence(
        symbol="TCS",
        as_of_date=date(2026, 3, 31),
        snapshots=[current],
    )

    assert any(
        signal.code == "PROFIT_CASH_DIVERGENCE"
        for signal in result.signals
    )

    assert any(
        "cash flow" in item.lower()
        for item in result.risk_observations
    )


def test_missing_financial_data_is_explicit():
    result = build_financial_company_intelligence(
        symbol="TCS",
        as_of_date=date(2026, 3, 31),
        snapshots=[],
    )

    assert result.signal_count == 0
    assert result.financial_observations
    assert result.risk_observations
