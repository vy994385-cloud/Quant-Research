from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.data.models import PriceBar
from src.features.market_structure import (
    calculate_market_structure,
)


def make_bars(
    count: int = 30,
    start_price: int = 100,
    step: int = 1,
) -> list[PriceBar]:
    bars = []

    start = date(2026, 1, 1)

    for index in range(count):
        price = Decimal(
            start_price + index * step
        )

        bars.append(
            PriceBar(
                symbol="TEST",
                trading_date=start + timedelta(days=index),
                open=price,
                high=price + Decimal("2"),
                low=price - Decimal("2"),
                close=price,
                volume=1000 + index * 20,
            )
        )

    return bars


def test_rising_market_is_bullish():
    structure = calculate_market_structure(
        make_bars()
    )

    assert structure.regime == "BULLISH"
    assert structure.price_vs_sma_5_pct > 0
    assert structure.price_vs_sma_20_pct > 0
    assert structure.sma_5_vs_sma_20_pct > 0


def test_falling_market_is_bearish():
    structure = calculate_market_structure(
        make_bars(
            start_price=200,
            step=-1,
        )
    )

    assert structure.regime == "BEARISH"
    assert structure.price_vs_sma_5_pct < 0
    assert structure.price_vs_sma_20_pct < 0
    assert structure.sma_5_vs_sma_20_pct < 0


def test_insufficient_history_is_reported():
    structure = calculate_market_structure(
        make_bars(4)
    )

    assert structure.regime == "INSUFFICIENT_DATA"
    assert structure.price_vs_sma_5_pct is None
    assert structure.price_vs_sma_20_pct is None
    assert structure.volume_confirmation is None


def test_trend_persistence_is_high_for_consistent_move():
    structure = calculate_market_structure(
        make_bars()
    )

    assert structure.trend_persistence == Decimal("100")


def test_volume_confirmation_is_available():
    structure = calculate_market_structure(
        make_bars()
    )

    assert structure.volume_confirmation is not None
    assert structure.volume_confirmation > 0


def test_momentum_acceleration_requires_sufficient_history():
    short = calculate_market_structure(
        make_bars(20)
    )

    long = calculate_market_structure(
        make_bars(30)
    )

    assert short.momentum_acceleration is None
    assert long.momentum_acceleration is not None


def test_drawdown_recovery_is_bounded():
    structure = calculate_market_structure(
        make_bars()
    )

    assert structure.recovery_from_drawdown_pct is not None
    assert (
        Decimal("0")
        <= structure.recovery_from_drawdown_pct
        <= Decimal("100")
    )


def test_unsorted_data_is_rejected():
    bars = make_bars(5)

    bars[0], bars[1] = bars[1], bars[0]

    with pytest.raises(ValueError):
        calculate_market_structure(bars)


def test_multiple_symbols_are_rejected():
    bars = make_bars(5)

    bars[-1] = PriceBar(
        symbol="OTHER",
        trading_date=bars[-1].trading_date,
        open=100,
        high=102,
        low=98,
        close=100,
        volume=1000,
    )

    with pytest.raises(ValueError):
        calculate_market_structure(bars)
