from datetime import date

import pytest

from src.data.providers.base import MarketDataProvider
from src.data.providers.upstox_provider import (
    UpstoxMarketDataProvider,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, *, headers, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return self.response


def make_provider(session):
    return UpstoxMarketDataProvider(
        access_token="test-token",
        instrument_keys={
            "RELIANCE": "NSE_EQ|INE002A01018",
        },
        session=session,
    )


def test_upstox_provider_implements_market_data_provider():
    session = FakeSession(
        FakeResponse(
            {
                "status": "success",
                "data": {"candles": []},
            }
        )
    )

    provider = make_provider(session)

    assert isinstance(
        provider,
        MarketDataProvider,
    )


def test_upstox_provider_normalizes_daily_candles():
    session = FakeSession(
        FakeResponse(
            {
                "status": "success",
                "data": {
                    "candles": [
                        [
                            "2026-08-05T00:00:00+05:30",
                            112.0,
                            118.0,
                            108.0,
                            115.0,
                            130000,
                            0,
                        ],
                        [
                            "2026-08-03T00:00:00+05:30",
                            100.0,
                            110.0,
                            95.0,
                            105.0,
                            100000,
                            0,
                        ],
                    ]
                },
            }
        )
    )

    provider = make_provider(session)

    bars = provider.get_daily_prices(
        symbol=" reliance ",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 5),
    )

    assert len(bars) == 2

    assert bars[0].trading_date == date(2026, 8, 3)
    assert bars[1].trading_date == date(2026, 8, 5)

    assert bars[0].symbol == "RELIANCE"
    assert bars[0].close == 105
    assert bars[1].volume == 130000


def test_upstox_provider_sends_authorization():
    session = FakeSession(
        FakeResponse(
            {
                "status": "success",
                "data": {"candles": []},
            }
        )
    )

    provider = make_provider(session)

    provider.get_daily_prices(
        symbol="RELIANCE",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 5),
    )

    call = session.calls[0]

    assert (
        call["headers"]["Authorization"]
        == "Bearer test-token"
    )

    assert (
        "NSE_EQ%7CINE002A01018"
        in call["url"]
    )

    assert "/days/1/" in call["url"]


def test_upstox_provider_rejects_invalid_date_range():
    session = FakeSession(
        FakeResponse(
            {
                "status": "success",
                "data": {"candles": []},
            }
        )
    )

    provider = make_provider(session)

    with pytest.raises(ValueError):
        provider.get_daily_prices(
            symbol="RELIANCE",
            start_date=date(2026, 8, 10),
            end_date=date(2026, 8, 1),
        )


def test_upstox_provider_rejects_unknown_symbol():
    session = FakeSession(
        FakeResponse(
            {
                "status": "success",
                "data": {"candles": []},
            }
        )
    )

    provider = make_provider(session)

    with pytest.raises(KeyError):
        provider.get_daily_prices(
            symbol="UNKNOWN",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 5),
        )


def test_upstox_provider_rejects_empty_token():
    with pytest.raises(ValueError):
        UpstoxMarketDataProvider(
            access_token=" ",
            instrument_keys={
                "RELIANCE": "NSE_EQ|INE002A01018",
            },
        )


def test_upstox_provider_rejects_unsuccessful_response():
    session = FakeSession(
        FakeResponse(
            {
                "status": "error",
                "data": {},
            }
        )
    )

    provider = make_provider(session)

    with pytest.raises(ValueError):
        provider.get_daily_prices(
            symbol="RELIANCE",
            start_date=date(2026, 8, 3),
            end_date=date(2026, 8, 5),
        )


def test_upstox_provider_rejects_malformed_candle():
    session = FakeSession(
        FakeResponse(
            {
                "status": "success",
                "data": {
                    "candles": [
                        ["2026-08-05T00:00:00+05:30"]
                    ]
                },
            }
        )
    )

    provider = make_provider(session)

    with pytest.raises(ValueError):
        provider.get_daily_prices(
            symbol="RELIANCE",
            start_date=date(2026, 8, 3),
            end_date=date(2026, 8, 5),
        )
