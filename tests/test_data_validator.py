from datetime import date
from decimal import Decimal

from src.data.models import PriceBar
from src.data.validator import validate_price_bars


def make_bar(
    *,
    open_price: str = "100",
    high: str = "110",
    low: str = "95",
    close: str = "105",
) -> PriceBar:
    return PriceBar(
        symbol="TEST",
        trading_date=date(2026, 8, 7),
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=100_000,
    )


def test_valid_price_bar():
    bar = make_bar()

    assert bar.is_valid_ohlc
    assert validate_price_bars([bar]) == []


def test_invalid_ohlc_is_detected():
    bar = make_bar(
        open_price="120",
        high="110",
        low="95",
        close="105",
    )

    errors = validate_price_bars([bar])

    assert errors
    assert "Invalid OHLC" in errors[0]


def test_duplicate_bars_are_detected():
    bar = make_bar()

    errors = validate_price_bars([bar, bar])

    assert any("Duplicate" in error for error in errors)
