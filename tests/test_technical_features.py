from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.data.models import PriceBar
from src.features.technical import calculate_technical_features


def make_bars(
    count: int = 25,
    start_price: int = 100,
) -> list[PriceBar]:
    bars = []

    start = date(2026, 1, 1)

    for index in range(count):
        price = Decimal(start_price + index)

        bars.append(
            PriceBar(
                symbol="TEST",
                trading_date=start + timedelta(days=index),
                open=price,
                high=price + Decimal("2"),
                low=price - Decimal("2"),
                close=price,
                volume=1000 + index * 10,
            )
        )

    return bars


def test_calculates_basic_returns():
    bars = make_bars(25)

    features = calculate_technical_features(bars)

    assert features.return_1d is not None
    assert features.return_5d is not None
    assert features.return_20d is not None

    assert features.return_1d > Decimal("0")
    assert features.return_5d > Decimal("0")
    assert features.return_20d > Decimal("0")


def test_calculates_moving_averages():
    bars = make_bars(25)

    features = calculate_technical_features(bars)

    assert features.sma_5 == Decimal("122")
    assert features.sma_20 == Decimal("114.5")


def test_momentum_matches_20_day_return():
    bars = make_bars(25)

    features = calculate_technical_features(bars)

    assert features.momentum == features.return_20d


def test_volume_ratio_is_available_with_twenty_bars():
    bars = make_bars(25)

    features = calculate_technical_features(bars)

    assert features.average_volume_20d is not None
    assert features.volume_ratio is not None
    assert features.volume_ratio > Decimal("1")


def test_drawdown_is_zero_at_new_high():
    bars = make_bars(25)

    features = calculate_technical_features(bars)

    assert features.drawdown_20d == Decimal("0")


def test_insufficient_history_returns_none():
    bars = make_bars(4)

    features = calculate_technical_features(bars)

    assert features.return_5d is None
    assert features.return_20d is None
    assert features.sma_5 is None
    assert features.sma_20 is None
    assert features.average_volume_20d is None
    assert features.drawdown_20d is None


def test_unsorted_bars_are_rejected():
    bars = make_bars(5)

    bars[0], bars[1] = bars[1], bars[0]

    with pytest.raises(ValueError):
        calculate_technical_features(bars)


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
        calculate_technical_features(bars)


def test_invalid_ohlc_is_rejected():
    bars = make_bars(5)

    bars[-1] = PriceBar(
        symbol="TEST",
        trading_date=bars[-1].trading_date,
        open=100,
        high=90,
        low=95,
        close=100,
        volume=1000,
    )

    with pytest.raises(Exception):
        calculate_technical_features(bars)
