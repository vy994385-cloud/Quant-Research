from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.backtest.benchmark import (
    calculate_benchmark_result,
)
from src.backtest.engine import BacktestEngine
from src.backtest.models import (
    BacktestBar,
    BacktestSignal,
)


def make_bars(
    prices: list[str],
    symbol: str = "BENCH",
) -> list[BacktestBar]:
    start = date(2026, 1, 1)

    return [
        BacktestBar(
            symbol=symbol,
            trading_date=start + timedelta(days=index),
            close=Decimal(price),
        )
        for index, price in enumerate(prices)
    ]


def make_strategy_result():
    strategy_bars = make_bars(
        ["100", "110", "120"],
        symbol="TEST",
    )

    signals = [
        BacktestSignal(
            symbol="TEST",
            trading_date=date(2026, 1, 1),
            action="BUY",
            score=Decimal("80"),
        ),
        BacktestSignal(
            symbol="TEST",
            trading_date=date(2026, 1, 3),
            action="SELL",
            score=Decimal("20"),
        ),
    ]

    engine = BacktestEngine(
        Decimal("1000")
    )

    return engine.run(
        strategy_bars,
        signals,
    )


def test_benchmark_calculates_buy_and_hold_return():
    result = make_strategy_result()

    benchmark = calculate_benchmark_result(
        result,
        make_bars(["100", "110", "125"]),
    )

    assert benchmark.benchmark_return == Decimal("25")
    assert benchmark.final_value == Decimal("1250")


def test_benchmark_calculates_strategy_return():
    result = make_strategy_result()

    benchmark = calculate_benchmark_result(
        result,
        make_bars(["100", "110", "125"]),
    )

    assert benchmark.strategy_return == Decimal("20")


def test_benchmark_calculates_excess_return():
    result = make_strategy_result()

    benchmark = calculate_benchmark_result(
        result,
        make_bars(["100", "110", "125"]),
    )

    assert benchmark.excess_return == Decimal("-5")
    assert benchmark.outperforming is False


def test_benchmark_detects_outperformance():
    result = make_strategy_result()

    benchmark = calculate_benchmark_result(
        result,
        make_bars(["100", "110", "115"]),
    )

    assert benchmark.benchmark_return == Decimal("15")
    assert benchmark.excess_return == Decimal("5")
    assert benchmark.outperforming is True


def test_benchmark_drawdown_is_calculated():
    result = make_strategy_result()

    benchmark = calculate_benchmark_result(
        result,
        make_bars(["100", "120", "90", "110"]),
    )

    assert benchmark.benchmark_max_drawdown == Decimal("300")
    assert benchmark.benchmark_max_drawdown_percent == Decimal(
        "25"
    )


def test_strategy_drawdown_is_preserved():
    result = make_strategy_result()

    benchmark = calculate_benchmark_result(
        result,
        make_bars(["100", "110", "120"]),
    )

    assert benchmark.strategy_max_drawdown == Decimal("0")
    assert benchmark.strategy_max_drawdown_percent == Decimal(
        "0"
    )


def test_empty_benchmark_is_rejected():
    result = make_strategy_result()

    with pytest.raises(ValueError):
        calculate_benchmark_result(
            result,
            [],
        )


def test_unordered_benchmark_is_rejected():
    result = make_strategy_result()

    bars = make_bars(
        ["100", "120"],
    )

    bars[1] = BacktestBar(
        symbol="BENCH",
        trading_date=date(2025, 12, 31),
        close=Decimal("120"),
    )

    with pytest.raises(ValueError):
        calculate_benchmark_result(
            result,
            bars,
        )


def test_multiple_benchmark_symbols_are_rejected():
    result = make_strategy_result()

    bars = [
        BacktestBar(
            symbol="BENCH",
            trading_date=date(2026, 1, 1),
            close=Decimal("100"),
        ),
        BacktestBar(
            symbol="OTHER",
            trading_date=date(2026, 1, 2),
            close=Decimal("110"),
        ),
    ]

    with pytest.raises(ValueError):
        calculate_benchmark_result(
            result,
            bars,
        )
