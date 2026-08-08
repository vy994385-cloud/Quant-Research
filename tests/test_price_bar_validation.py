from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.data.models import PriceBar


def make_bar(**overrides):
    values = {
        "symbol": "TEST",
        "trading_date": date(2026, 8, 7),
        "open": Decimal("100"),
        "high": Decimal("110"),
        "low": Decimal("95"),
        "close": Decimal("105"),
        "volume": 100000,
    }

    values.update(overrides)

    return PriceBar(**values)


def test_valid_price_bar():

    bar = make_bar()

    assert bar.is_valid_ohlc


def test_negative_volume_is_rejected():

    with pytest.raises(ValidationError):
        make_bar(
            volume=-1,
        )


def test_zero_price_is_rejected():

    with pytest.raises(ValidationError):
        make_bar(
            close=Decimal("0"),
        )


def test_extra_fields_are_rejected():

    with pytest.raises(ValidationError):
        make_bar(
            unexpected_field="bad",
        )


def test_invalid_high_is_detected_by_property():

    bar = make_bar(
        high=Decimal("99"),
    )

    assert not bar.is_valid_ohlc


def test_invalid_low_is_detected_by_property():

    bar = make_bar(
        low=Decimal("106"),
    )

    assert not bar.is_valid_ohlc
