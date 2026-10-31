"""Tests for technical API contract serialization."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.api.contracts import (
    CompanyDeepTechnicalContract,
    ContractDeepTechnicalResult,
    ContractTechnicalIndicatorSet,
    ContractTechnicalObservation,
    ContractTechnicalObservationSet,
)
from src.api.technical_router import (
    _d,
    _serialize_indicators,
    _serialize_observation,
    _serialize_observation_set,
)
from src.analysis.technical_indicators import compute_technical_indicators
from src.analysis.technical_observations import build_technical_observations
from src.data.models import PriceBar
from datetime import datetime, timezone


def _rising_bars(n: int, start: str = "2024-01-01") -> list[PriceBar]:
    bars = []
    base = date.fromisoformat(start)
    for i in range(n):
        d = base + timedelta(days=i)
        o = Decimal("100") + Decimal(i)
        bars.append(PriceBar(
            symbol="TEST",
            trading_date=d,
            open=o,
            high=o + Decimal("2"),
            low=o - Decimal("2"),
            close=o + Decimal("1"),
            volume=1000 + i * 100,
        ))
    return bars

_AS_OF = datetime(2024, 3, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


class TestSerializationHelpers:
    def test_d_none(self):
        assert _d(None) is None

    def test_d_value(self):
        assert _d(Decimal("100")) == "100"

    def test_d_zero(self):
        assert _d(Decimal("0")) == "0"


# ---------------------------------------------------------------------------
# Indicator serialization
# ---------------------------------------------------------------------------


class TestIndicatorSerialization:
    def test_serializes_returns(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        contract = _serialize_indicators(result)
        assert isinstance(contract, ContractTechnicalIndicatorSet)
        assert contract.return_1d is not None
        assert contract.return_20d is not None

    def test_serializes_sma(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        contract = _serialize_indicators(result)
        assert contract.sma_5 is not None
        assert contract.sma_20 is not None

    def test_serializes_ema(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        contract = _serialize_indicators(result)
        assert contract.ema_9 is not None
        assert contract.ema_20 is not None

    def test_serializes_rsi(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        contract = _serialize_indicators(result)
        assert contract.rsi_14 is not None
        assert contract.rsi_signal in ("OVERBOUGHT", "OVERSOLD", "NEUTRAL", "INSUFFICIENT_DATA")

    def test_serializes_macd(self):
        bars = _rising_bars(40)
        result = compute_technical_indicators(bars)
        contract = _serialize_indicators(result)
        assert contract.macd_line is not None
        assert contract.macd_signal_line is not None
        assert contract.macd_histogram is not None

    def test_serializes_bollinger(self):
        bars = _rising_bars(25)
        result = compute_technical_indicators(bars)
        contract = _serialize_indicators(result)
        assert contract.bollinger_upper is not None
        assert contract.bollinger_lower is not None
        assert contract.bollinger_bandwidth is not None

    def test_serializes_pivots(self):
        bars = _rising_bars(5)
        result = compute_technical_indicators(bars)
        contract = _serialize_indicators(result)
        assert contract.pivot is not None
        assert contract.r1 is not None
        assert contract.s1 is not None

    def test_serializes_trend(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        contract = _serialize_indicators(result)
        assert contract.regime != "INSUFFICIENT_DATA"

    def test_none_values_handled(self):
        bars = _rising_bars(5)
        result = compute_technical_indicators(bars)
        contract = _serialize_indicators(result)
        # RSI should be None with only 5 bars
        assert contract.rsi_14 is None


# ---------------------------------------------------------------------------
# Observation serialization
# ---------------------------------------------------------------------------


class TestObservationSerialization:
    def test_serialize_observation(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        if obs.indicator_observations:
            contract = _serialize_observation(obs.indicator_observations[0])
            assert isinstance(contract, ContractTechnicalObservation)
            assert len(contract.observation_id) > 0
            assert contract.symbol == "TEST"

    def test_serialize_observation_set(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        contract = _serialize_observation_set(obs)
        assert isinstance(contract, ContractTechnicalObservationSet)
        assert contract.total_count > 0
        assert contract.positive_count >= 0


# ---------------------------------------------------------------------------
# Top-level contract
# ---------------------------------------------------------------------------


class TestTopLevelContract:
    def test_company_contract(self):
        bars = _rising_bars(30)
        indicators = compute_technical_indicators(bars)
        obs = build_technical_observations(indicators, _AS_OF)

        contract = CompanyDeepTechnicalContract(
            company={"symbol": "TEST", "name": "TEST"},
            deep_technicals=ContractDeepTechnicalResult(
                symbol="TEST",
                as_of=_AS_OF.isoformat(),
                trading_date=indicators.trading_date,
                bars_used=30,
                indicators=_serialize_indicators(indicators),
                observation_set=_serialize_observation_set(obs),
                available_indicators=list(obs.available_indicators),
                missing_indicators=list(obs.missing_indicators),
                notes=[],
            ),
        )
        assert contract.company["symbol"] == "TEST"
        assert contract.deep_technicals.bars_used == 30
        assert contract.deep_technicals.indicators is not None
        assert contract.deep_technicals.observation_set is not None

    def test_contract_json_serializable(self):
        bars = _rising_bars(30)
        indicators = compute_technical_indicators(bars)
        obs = build_technical_observations(indicators, _AS_OF)

        contract = CompanyDeepTechnicalContract(
            company={"symbol": "TEST", "name": "TEST"},
            deep_technicals=ContractDeepTechnicalResult(
                symbol="TEST",
                as_of=_AS_OF.isoformat(),
                trading_date=indicators.trading_date,
                bars_used=30,
                indicators=_serialize_indicators(indicators),
                observation_set=_serialize_observation_set(obs),
            ),
        )
        # Should be JSON-serializable
        json_str = contract.model_dump_json()
        assert len(json_str) > 0
        assert "TEST" in json_str


# ---------------------------------------------------------------------------
# ad_line contract regression (decimal-string, never int coercion)
# ---------------------------------------------------------------------------


def _fractional_ad_bars(
    symbol: str,
    n: int = 40,
    start: str = "2024-01-01",
) -> list[PriceBar]:
    """
    Bars whose money-flow multiplier is a repeating decimal
    (mfm = -1/3), guaranteeing accumulation_distribution carries a
    non-trivial fractional part that int coercion cannot represent.
    """

    bars: list[PriceBar] = []
    base = date.fromisoformat(start)
    for i in range(n):
        d = base + timedelta(days=i)
        low = Decimal("100") + Decimal(i)
        bars.append(PriceBar(
            symbol=symbol,
            trading_date=d,
            open=low + Decimal("1"),
            high=low + Decimal("3"),
            close=low + Decimal("1"),
            low=low,
            volume=10_001 + i,
        ))
    return bars


class _FixtureMarketProvider:
    """Deterministic stand-in for YahooFinanceMarketDataProvider."""

    def __init__(self, symbol: str):
        self._symbol = symbol

    def get_daily_prices(self, symbol, start_date, end_date):
        return _fractional_ad_bars(symbol.strip().upper())


class TestAdLineContract:
    def test_ad_value_is_fractional_in_source(self):
        bars = _fractional_ad_bars("TEST")
        result = compute_technical_indicators(bars)
        raw = result.volume_indicators.accumulation_distribution
        assert raw is not None
        assert "." in raw, "fixture must produce fractional AD"

    def test_ad_line_serialized_as_exact_decimal_string(self):
        bars = _fractional_ad_bars("TEST")
        result = compute_technical_indicators(bars)
        contract = _serialize_indicators(result)
        assert isinstance(contract.ad_line, str)
        assert (
            contract.ad_line
            == result.volume_indicators.accumulation_distribution
        )
        assert "." in contract.ad_line

    def test_ad_line_none_stays_none(self):
        from src.analysis.technical_indicators import VolumeIndicators

        empty = VolumeIndicators()
        contract = ContractTechnicalIndicatorSet(ad_line=_d(empty.accumulation_distribution))
        assert contract.ad_line is None

    @pytest.mark.parametrize("symbol", ["HDFCBANK", "TCS"])
    def test_deep_technicals_endpoint_ok_for_recorded_symbols(
        self, monkeypatch, symbol
    ):
        from fastapi.testclient import TestClient

        from src.api import main
        from src.api.recorded_research import COMPANY_NAMES

        monkeypatch.setattr(
            "src.data.providers.yahoo_provider.YahooFinanceMarketDataProvider",
            lambda: _FixtureMarketProvider(symbol),
        )

        response = TestClient(main.app).get(
            f"/api/v1/companies/{symbol}/deep-technicals"
        )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["company"]["symbol"] == symbol
        assert payload["company"]["company_name"] == COMPANY_NAMES[symbol]

        indicators = payload["deep_technicals"]["indicators"]
        assert indicators is not None
        assert isinstance(indicators["ad_line"], str)
        assert "." in indicators["ad_line"]
        # Value preserved exactly — no truncation to int.
        bars = _fractional_ad_bars(symbol)
        expected = str(
            compute_technical_indicators(bars)
            .volume_indicators.accumulation_distribution
        )
        assert indicators["ad_line"] == expected

    def test_deep_technicals_valid_response_shape(self, monkeypatch):
        from fastapi.testclient import TestClient

        from src.api import main

        monkeypatch.setattr(
            "src.data.providers.yahoo_provider.YahooFinanceMarketDataProvider",
            lambda: _FixtureMarketProvider("TCS"),
        )

        response = TestClient(main.app).get(
            "/api/v1/companies/TCS/deep-technicals"
        )

        assert response.status_code == 200
        payload = response.json()

        deep = payload["deep_technicals"]
        assert deep["symbol"] == "TCS"
        assert deep["bars_used"] == 40
        assert deep["trading_date"] == "2024-02-09"
        assert isinstance(deep["available_indicators"], list)
        assert "rsi" in deep["available_indicators"]
        assert isinstance(deep["missing_indicators"], list)
        assert deep["observation_set"] is not None
        assert deep["observation_set"]["total_count"] > 0
        assert deep["observation_set"]["as_of"]
        for obs in deep["observation_set"]["indicator_observations"]:
            assert obs["symbol"] == "TCS"
            assert obs["source"]

    @pytest.mark.parametrize("value", ["36750.5", "12345.6789", "-81234.333"])
    def test_contract_accepts_fractional_decimal_strings_directly(self, value):
        contract = ContractTechnicalIndicatorSet(ad_line=value)
        assert contract.ad_line == value


class TestPriceHistoryEndpoint:
    def test_returns_point_in_time_ohlcv_bars(self, monkeypatch):
        from fastapi.testclient import TestClient
        from src.api import main

        monkeypatch.setattr(
            "src.data.providers.yahoo_provider.YahooFinanceMarketDataProvider",
            lambda: _FixtureMarketProvider("HDFCBANK"),
        )

        response = TestClient(main.app).get(
            "/api/v1/companies/HDFCBANK/price-history",
            params={"as_of": "2024-03-01"},
        )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["symbol"] == "HDFCBANK"
        assert payload["as_of"].startswith("2024-03-01")
        assert payload["bars_returned"] == 40
        assert payload["history_start"] == "2024-01-01"
        assert payload["history_end"] == "2024-02-09"
        assert payload["bars"][0]["open"] == "101"
        assert payload["bars"][0]["close"] == "101"
        assert payload["bars"][0]["volume"] == 10_001
        assert all(bar["trading_date"] <= "2024-03-01" for bar in payload["bars"])

    def test_invalid_ohlc_bars_are_excluded(self, monkeypatch):
        from fastapi.testclient import TestClient
        from src.api import main

        valid = _fractional_ad_bars("HDFCBANK")
        invalid = valid[-1].model_copy(update={"high": Decimal("1")})

        class Provider:
            def get_daily_prices(self, symbol, start_date, end_date):
                return [*valid[:-1], invalid]

        monkeypatch.setattr(
            "src.data.providers.yahoo_provider.YahooFinanceMarketDataProvider",
            Provider,
        )

        response = TestClient(main.app).get(
            "/api/v1/companies/HDFCBANK/price-history",
            params={"as_of": "2024-03-01"},
        )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["bars_returned"] == 39
        assert payload["history_end"] == "2024-02-08"
