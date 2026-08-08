from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.data.models import PriceBar
from src.features.relative_strength import (
    calculate_relative_strength,
)


def make_bars(
    symbol: str,
    prices: list[int],
    start: date = date(2026, 1, 1),
) -> list[PriceBar]:
    bars = []

    for index, price in enumerate(prices):
        value = Decimal(price)

        bars.append(
            PriceBar(
                symbol=symbol,
                trading_date=start + timedelta(days=index),
                open=value,
                high=value + Decimal("2"),
                low=value - Decimal("2"),
                close=value,
                volume=1000,
            )
        )

    return bars


def test_stock_outperforms_benchmark():
    stock = make_bars(
        "TEST",
        [100, 101, 102, 104, 108, 112],
    )

    benchmark = make_bars(
        "NIFTY",
        [100, 100, 101, 102, 103, 104],
    )

    result = calculate_relative_strength(
        stock,
        benchmark,
    )

    assert result.relative_return_1d > 0
    assert result.relative_return_5d > 0


def test_stock_underperforms_benchmark():
    stock = make_bars(
        "TEST",
        [100, 100, 99, 98, 97, 96],
    )

    benchmark = make_bars(
        "NIFTY",
        [100, 101, 103, 105, 107, 110],
    )

    result = calculate_relative_strength(
        stock,
        benchmark,
    )

    assert result.relative_return_1d < 0
    assert result.relative_return_5d < 0


def test_equal_performance_has_zero_relative_return():
    stock = make_bars(
        "TEST",
        [100, 105, 110, 115, 120, 125],
    )

    benchmark = make_bars(
        "NIFTY",
        [200, 210, 220, 230, 240, 250],
    )

    result = calculate_relative_strength(
        stock,
        benchmark,
    )

    assert result.relative_return_1d == Decimal("0")
    assert result.relative_return_5d == Decimal("0")


def test_insufficient_history_returns_none():
    stock = make_bars(
        "TEST",
        [100, 101, 102],
    )

    benchmark = make_bars(
        "NIFTY",
        [100, 101, 102],
    )

    result = calculate_relative_strength(
        stock,
        benchmark,
    )

    assert result.relative_return_1d is not None
    assert result.relative_return_5d is None
    assert result.relative_return_20d is None
    assert result.relative_momentum is None


def test_different_calendars_are_aligned():
    stock = make_bars(
        "TEST",
        [100, 101, 102],
    )

    benchmark = make_bars(
        "NIFTY",
        [200, 201],
        start=date(2026, 1, 2),
    )

    result = calculate_relative_strength(
        stock,
        benchmark,
    )

    assert result.trading_date == date(2026, 1, 3)
    assert result.stock_return_1d is not None


def test_no_common_dates_are_rejected():
    stock = make_bars(
        "TEST",
        [100, 101],
        start=date(2026, 1, 1),
    )

    benchmark = make_bars(
        "NIFTY",
        [200, 201],
        start=date(2027, 1, 1),
    )

    with pytest.raises(ValueError):
        calculate_relative_strength(
            stock,
            benchmark,
        )


def test_unsorted_stock_data_is_rejected():
    stock = make_bars(
        "TEST",
        [100, 101, 102],
    )

    stock[0], stock[1] = stock[1], stock[0]

    benchmark = make_bars(
        "NIFTY",
        [100, 101, 102],
    )

    with pytest.raises(ValueError):
        calculate_relative_strength(
            stock,
            benchmark,
        )


def test_unsorted_benchmark_data_is_rejected():
    stock = make_bars(
        "TEST",
        [100, 101, 102],
    )

    benchmark = make_bars(
        "NIFTY",
        [100, 101, 102],
    )

    benchmark[0], benchmark[1] = (
        benchmark[1],
        benchmark[0],
    )

    with pytest.raises(ValueError):
        calculate_relative_strength(
            stock,
            benchmark,
        )
