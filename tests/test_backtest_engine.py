from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.backtest.engine import BacktestEngine
from src.backtest.models import (
    BacktestBar,
    BacktestSignal,
)


def make_bars(prices: list[str]) -> list[BacktestBar]:
    start = date(2026, 1, 1)

    return [
        BacktestBar(
            symbol="TEST",
            trading_date=start + timedelta(days=index),
            close=Decimal(price),
        )
        for index, price in enumerate(prices)
    ]


def make_signal(
    day: int,
    action: str,
    score: str = "80",
) -> BacktestSignal:
    return BacktestSignal(
        symbol="TEST",
        trading_date=date(2026, 1, day),
        action=action,
        score=Decimal(score),
    )


def test_buy_and_sell_generate_expected_profit():
    bars = make_bars(
        ["100", "110", "120"]
    )

    signals = [
        make_signal(1, "BUY"),
        make_signal(3, "SELL"),
    ]

    engine = BacktestEngine(
        Decimal("1000")
    )

    result = engine.run(
        bars,
        signals,
    )

    assert result.trade_count == 2
    assert result.final_equity == Decimal("1200")


def test_no_signal_preserves_initial_capital():
    bars = make_bars(
        ["100", "110", "120"]
    )

    engine = BacktestEngine(
        Decimal("1000")
    )

    result = engine.run(
        bars,
        [],
    )

    assert result.final_equity == Decimal("1000")
    assert result.trade_count == 0


def test_transaction_cost_reduces_profit():
    bars = make_bars(
        ["100", "120"]
    )

    signals = [
        make_signal(1, "BUY"),
        make_signal(2, "SELL"),
    ]

    engine = BacktestEngine(
        Decimal("1000"),
        transaction_cost_rate=Decimal("0.01"),
    )

    result = engine.run(
        bars,
        signals,
    )

    assert result.final_equity < Decimal("1200")


def test_duplicate_position_buy_is_ignored():
    bars = make_bars(
        ["100", "110", "120"]
    )

    signals = [
        make_signal(1, "BUY"),
        make_signal(2, "BUY"),
        make_signal(3, "SELL"),
    ]

    engine = BacktestEngine(
        Decimal("1000")
    )

    result = engine.run(
        bars,
        signals,
    )

    assert result.trade_count == 2


def test_signal_without_matching_bar_is_rejected():
    bars = make_bars(
        ["100", "110"]
    )

    signals = [
        make_signal(3, "BUY"),
    ]

    engine = BacktestEngine(
        Decimal("1000")
    )

    with pytest.raises(ValueError):
        engine.run(
            bars,
            signals,
        )


def test_equity_curve_contains_each_market_observation():
    bars = make_bars(
        ["100", "105", "110"]
    )

    engine = BacktestEngine(
        Decimal("1000")
    )

    result = engine.run(
        bars,
        [],
    )

    assert len(result.equity_curve) == 3
    assert (
        result.equity_curve[-1].trading_date
        == date(2026, 1, 3)
    )


def test_same_close_execution_is_explicit():
    bars = make_bars(
        ["100", "110", "120"]
    )

    signals = [
        make_signal(1, "BUY"),
        make_signal(2, "SELL"),
    ]

    engine = BacktestEngine(
        Decimal("1000"),
        execution_timing="SAME_CLOSE",
    )

    result = engine.run(
        bars,
        signals,
    )

    assert result.trade_count == 2
    assert result.trades[0].price == Decimal("100")
    assert result.trades[1].price == Decimal("110")


def test_next_bar_executes_signal_on_following_bar():
    bars = make_bars(
        ["100", "110", "120"]
    )

    signals = [
        make_signal(1, "BUY"),
        make_signal(2, "SELL"),
    ]

    engine = BacktestEngine(
        Decimal("1000"),
        execution_timing="NEXT_BAR",
    )

    result = engine.run(
        bars,
        signals,
    )

    assert result.trade_count == 2

    assert result.trades[0].trading_date == date(
        2026,
        1,
        2,
    )
    assert result.trades[0].price == Decimal("110")

    assert result.trades[1].trading_date == date(
        2026,
        1,
        3,
    )
    assert result.trades[1].price == Decimal("120")


def test_next_bar_does_not_execute_signal_on_final_bar():
    bars = make_bars(
        ["100", "110", "120"]
    )

    signals = [
        make_signal(3, "BUY"),
    ]

    engine = BacktestEngine(
        Decimal("1000"),
        execution_timing="NEXT_BAR",
    )

    result = engine.run(
        bars,
        signals,
    )

    assert result.trade_count == 0
    assert result.final_equity == Decimal("1000")


def test_next_bar_uses_next_observation_not_future_price():
    bars = make_bars(
        ["100", "200", "300"]
    )

    signals = [
        make_signal(1, "BUY"),
        make_signal(2, "SELL"),
    ]

    engine = BacktestEngine(
        Decimal("1000"),
        execution_timing="NEXT_BAR",
    )

    result = engine.run(
        bars,
        signals,
    )

    assert result.trade_count == 2

    assert result.trades[0].price == Decimal("200")
    assert result.trades[0].trading_date == date(
        2026,
        1,
        2,
    )

    assert result.trades[1].price == Decimal("300")
    assert result.trades[1].trading_date == date(
        2026,
        1,
        3,
    )


def test_invalid_execution_timing_is_rejected():
    with pytest.raises(ValueError):
        BacktestEngine(
            Decimal("1000"),
            execution_timing="INVALID",
        )
