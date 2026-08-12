from decimal import Decimal
from datetime import timezone

import pytest

from src.data.providers.upstox_stream import (
    LivePriceTick,
    UpstoxMarketDataStream,
)


def test_live_price_tick_contract():
    tick = LivePriceTick(
        instrument_key="NSE_EQ|INE002A01018",
        price=Decimal("1450.50"),
        timestamp=__import__(
            "datetime"
        ).datetime.now(timezone.utc),
    )

    assert tick.price == Decimal("1450.50")


def test_stream_rejects_empty_token():
    with pytest.raises(ValueError):
        UpstoxMarketDataStream(
            access_token=" ",
            instrument_keys=[
                "NSE_EQ|INE002A01018"
            ],
        )


def test_stream_rejects_empty_instruments():
    with pytest.raises(ValueError):
        UpstoxMarketDataStream(
            access_token="token",
            instrument_keys=[],
        )


def test_stream_rejects_invalid_mode():
    with pytest.raises(ValueError):
        UpstoxMarketDataStream(
            access_token="token",
            instrument_keys=[
                "NSE_EQ|INE002A01018"
            ],
            mode="invalid",
        )
