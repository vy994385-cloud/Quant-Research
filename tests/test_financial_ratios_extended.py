"""Tests for the new B-class financial ratio calculations."""

from datetime import date
from decimal import Decimal

from src.analysis.financial_ratios import (
    accruals_ratio,
    current_ratio,
    return_on_capital_employed,
    return_on_equity,
    working_capital,
)
from src.data.company.financials import FinancialSnapshot


def make_snapshot(
    revenue: str = "1000",
    net_profit: str = "100",
    operating_profit: str = "150",
    total_assets: str = "2000",
    total_debt: str = "500",
    shareholders_equity: str = "800",
    current_assets: str = "600",
    current_liabilities: str = "300",
    inventory: str = "100",
    operating_cash_flow: str = "120",
) -> FinancialSnapshot:

    return FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        revenue=Decimal(revenue),
        net_profit=Decimal(net_profit),
        operating_profit=Decimal(operating_profit),
        total_assets=Decimal(total_assets),
        total_debt=Decimal(total_debt),
        shareholders_equity=Decimal(shareholders_equity),
        current_assets=Decimal(current_assets),
        current_liabilities=Decimal(current_liabilities),
        inventory=Decimal(inventory),
        operating_cash_flow=Decimal(operating_cash_flow),
    )


def test_return_on_equity():
    snapshot = make_snapshot()
    result = return_on_equity(snapshot)
    assert result == Decimal("12.5")


def test_return_on_equity_uses_total_equity_fallback():
    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        net_profit=Decimal("100"),
        total_equity=Decimal("800"),
    )
    result = return_on_equity(snapshot)
    assert result == Decimal("12.5")


def test_return_on_equity_missing_equity():
    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        net_profit=Decimal("100"),
    )
    result = return_on_equity(snapshot)
    assert result is None


def test_return_on_capital_employed():
    snapshot = make_snapshot()
    result = return_on_capital_employed(snapshot)
    expected = (Decimal("150") / Decimal("1300")) * Decimal("100")
    assert result == expected


def test_return_on_capital_employed_missing_data():
    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        operating_profit=Decimal("150"),
    )
    result = return_on_capital_employed(snapshot)
    assert result is None


def test_working_capital():
    snapshot = make_snapshot()
    result = working_capital(snapshot)
    assert result == Decimal("300")


def test_working_capital_missing_current_assets():
    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        current_liabilities=Decimal("300"),
    )
    result = working_capital(snapshot)
    assert result is None


def test_working_capital_missing_current_liabilities():
    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        current_assets=Decimal("600"),
    )
    result = working_capital(snapshot)
    assert result is None


def test_current_ratio():
    snapshot = make_snapshot()
    result = current_ratio(snapshot)
    assert result == Decimal("2")


def test_current_ratio_missing_data():
    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        current_assets=Decimal("600"),
    )
    result = current_ratio(snapshot)
    assert result is None


def test_accruals_ratio():
    snapshot = make_snapshot()
    result = accruals_ratio(snapshot)
    accruals = Decimal("100") - Decimal("120")
    expected = accruals / Decimal("2000")
    assert result == expected


def test_accruals_ratio_missing_net_profit():
    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        operating_cash_flow=Decimal("120"),
        total_assets=Decimal("2000"),
    )
    result = accruals_ratio(snapshot)
    assert result is None


def test_accruals_ratio_missing_total_assets():
    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        net_profit=Decimal("100"),
        operating_cash_flow=Decimal("120"),
    )
    result = accruals_ratio(snapshot)
    assert result is None


def test_accruals_ratio_zero_total_assets():
    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        net_profit=Decimal("100"),
        operating_cash_flow=Decimal("120"),
        total_assets=Decimal("0"),
    )
    result = accruals_ratio(snapshot)
    assert result is None


def test_all_new_ratios_with_complete_data():
    snapshot = make_snapshot()
    assert return_on_equity(snapshot) is not None
    assert return_on_capital_employed(snapshot) is not None
    assert working_capital(snapshot) is not None
    assert current_ratio(snapshot) is not None
    assert accruals_ratio(snapshot) is None or accruals_ratio(snapshot) is not None


def test_all_new_ratios_with_empty_snapshot():
    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
    )
    assert return_on_equity(snapshot) is None
    assert return_on_capital_employed(snapshot) is None
    assert working_capital(snapshot) is None
    assert current_ratio(snapshot) is None
    assert accruals_ratio(snapshot) is None
