from datetime import date
from decimal import Decimal

import pytest

from src.backtest.models import (
    BacktestBar,
    BacktestResult,
    BacktestSignal,
    BacktestTrade,
    EquityPoint,
)


def test_backtest_bar_accepts_valid_price():
    bar = BacktestBar(
        symbol="TEST",
        trading_date=date(2026, 1, 1),
        close=Decimal("100"),
    )

    assert bar.close == Decimal("100")


def test_backtest_bar_rejects_non_positive_price():
    with pytest.raises(ValueError):
        BacktestBar(
            symbol="TEST",
            trading_date=date(2026, 1, 1),
            close=Decimal("0"),
        )


def test_signal_score_must_be_between_zero_and_hundred():
    with pytest.raises(ValueError):
        BacktestSignal(
            symbol="TEST",
            trading_date=date(2026, 1, 1),
            action="BUY",
            score=Decimal("101"),
        )


def test_trade_calculates_gross_value():
    trade = BacktestTrade(
        symbol="TEST",
        trading_date=date(2026, 1, 1),
        side="LONG",
        quantity=Decimal("10"),
        price=Decimal("100"),
        transaction_cost=Decimal("5"),
    )

    assert trade.gross_value == Decimal("1000")
    assert trade.total_cost == Decimal("1005")


def test_equity_point_contains_total_equity():
    point = EquityPoint(
        trading_date=date(2026, 1, 1),
        cash=Decimal("900"),
        positions_value=Decimal("100"),
        equity=Decimal("1000"),
    )

    assert point.equity == Decimal("1000")


def test_backtest_result_calculates_profit_and_return():
    result = BacktestResult(
        initial_capital=Decimal("1000"),
        final_equity=Decimal("1100"),
        trades=(),
        equity_curve=(),
    )

    assert result.profit_loss == Decimal("100")
    assert result.return_percent == Decimal("10")
    assert result.trade_count == 0
