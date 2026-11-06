from datetime import date, datetime, timezone

import pytest

from src.data.providers import yahoo_provider


def chart_payload():
    timestamps = [
        int(datetime(2026, 8, 3, tzinfo=timezone.utc).timestamp()),
        int(datetime(2026, 8, 4, tzinfo=timezone.utc).timestamp()),
    ]

    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "longName": "Test Industries Limited",
                        "shortName": "Test Industries",
                        "fullExchangeName": "NSE",
                        "currency": "INR",
                        "instrumentType": "EQUITY",
                    },
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [{
                            "open": [100, 105],
                            "high": [110, 115],
                            "low": [95, 100],
                            "close": [105, 112],
                            "volume": [100000, 120000],
                        }],
                        "adjclose": [{
                            "adjclose": [104, 111],
                        }],
                    },
                }
            ],
            "error": None,
        }
    }


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        import json
        return json.dumps(self.payload).encode("utf-8")


def test_prices_and_metadata_are_returned_from_one_chart_request(monkeypatch):
    calls = []
    payload = chart_payload()

    def fake_urlopen(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeResponse(payload)

    monkeypatch.setattr(yahoo_provider, "urlopen", fake_urlopen)

    provider = yahoo_provider.YahooFinanceMarketDataProvider()

    bars, metadata = provider.get_daily_prices_with_metadata(
        "TCS",
        date(2026, 8, 3),
        date(2026, 8, 4),
    )

    assert len(calls) == 1
    assert [bar.trading_date for bar in bars] == [
        date(2026, 8, 3),
        date(2026, 8, 4),
    ]
    assert bars[0].symbol == "TCS"
    assert str(bars[1].close) == "112"
    assert str(bars[1].adjusted_close) == "111"

    assert metadata.symbol == "TCS"
    assert metadata.company_name == "Test Industries Limited"
    assert metadata.exchange == "NSE"
    assert metadata.currency == "INR"
    assert metadata.instrument_type == "EQUITY"
    assert metadata.metadata_source == "yahoo_chart"


def test_existing_get_daily_prices_contract_is_preserved(monkeypatch):
    monkeypatch.setattr(
        yahoo_provider,
        "urlopen",
        lambda *args, **kwargs: FakeResponse(chart_payload()),
    )

    provider = yahoo_provider.YahooFinanceMarketDataProvider()

    bars = provider.get_daily_prices(
        "TCS",
        date(2026, 8, 3),
        date(2026, 8, 4),
    )

    assert len(bars) == 2
    assert bars[0].symbol == "TCS"
    assert bars[0].trading_date == date(2026, 8, 3)


def test_empty_chart_returns_empty_prices_and_fallback_metadata(monkeypatch):
    monkeypatch.setattr(
        yahoo_provider,
        "urlopen",
        lambda *args, **kwargs: FakeResponse({
            "chart": {"result": [], "error": None}
        }),
    )

    provider = yahoo_provider.YahooFinanceMarketDataProvider()

    bars, metadata = provider.get_daily_prices_with_metadata(
        "UNKNOWN",
        date(2026, 8, 3),
        date(2026, 8, 4),
    )

    assert bars == []
    assert metadata.symbol == "UNKNOWN"
    assert metadata.company_name is None


def test_yahoo_chart_error_is_reported(monkeypatch):
    monkeypatch.setattr(
        yahoo_provider,
        "urlopen",
        lambda *args, **kwargs: FakeResponse({
            "chart": {
                "result": None,
                "error": {
                    "description": "Symbol not found",
                    "code": "Not Found",
                },
            }
        }),
    )

    provider = yahoo_provider.YahooFinanceMarketDataProvider()

    with pytest.raises(RuntimeError, match="Symbol not found"):
        provider.get_daily_prices_with_metadata(
            "INVALID",
            date(2026, 8, 3),
            date(2026, 8, 4),
        )


def test_provider_rejects_invalid_date_range():
    provider = yahoo_provider.YahooFinanceMarketDataProvider()

    with pytest.raises(ValueError, match="start_date"):
        provider.get_daily_prices_with_metadata(
            "TCS",
            date(2026, 8, 5),
            date(2026, 8, 3),
        )


def test_provider_rejects_empty_symbol():
    provider = yahoo_provider.YahooFinanceMarketDataProvider()

    with pytest.raises(ValueError, match="symbol"):
        provider.get_daily_prices_with_metadata(
            "   ",
            date(2026, 8, 3),
            date(2026, 8, 4),
        )
