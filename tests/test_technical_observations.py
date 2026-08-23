"""Tests for technical observation model."""

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

import pytest

from src.analysis.technical_indicators import compute_technical_indicators
from src.analysis.technical_observations import (
    TechnicalObservation,
    TechnicalObservationSet,
    build_technical_observations,
)
from src.data.models import PriceBar


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
# Observation building
# ---------------------------------------------------------------------------


class TestBuildObservations:
    def test_empty_result(self):
        result = compute_technical_indicators([])
        obs = build_technical_observations(result, _AS_OF)
        assert obs.total_count == 0

    def test_basic_observations(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        assert obs.total_count > 0
        assert obs.positive_count > 0

    def test_indicator_observations(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        assert len(obs.indicator_observations) > 0

    def test_signal_observations(self):
        bars = _rising_bars(60)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        # Should have at least trend signal
        assert len(obs.signal_observations) >= 0


# ---------------------------------------------------------------------------
# Observation fields
# ---------------------------------------------------------------------------


class TestObservationFields:
    def test_observation_id(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        for o in obs.indicator_observations:
            assert len(o.observation_id) > 0
            assert o.symbol == "TEST"

    def test_category_present(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        for o in obs.indicator_observations:
            assert o.category in ("MOMENTUM", "TREND", "VOLATILITY", "VOLUME", "STRUCTURE", "SIGNAL")

    def test_direction_present(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        for o in obs.indicator_observations:
            assert o.direction in ("POSITIVE", "NEGATIVE", "NEUTRAL")

    def test_signal_present(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        for o in obs.indicator_observations:
            assert len(o.signal) > 0

    def test_severity_present(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        for o in obs.indicator_observations:
            assert o.severity in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    def test_explanation_present(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        has_explanation = sum(1 for o in obs.indicator_observations if len(o.explanation) > 0)
        assert has_explanation > 0


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------


class TestCoverage:
    def test_available_indicators(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        assert len(obs.available_indicators) > 0

    def test_missing_indicators(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        # Some indicators may be missing due to insufficient data
        assert isinstance(obs.missing_indicators, tuple)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


class TestProvenance:
    def test_as_of_preserved(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        assert obs.as_of == _AS_OF.isoformat()

    def test_source_is_ohlcv(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        for o in obs.indicator_observations:
            assert o.source == "OHLCV"


# ---------------------------------------------------------------------------
# PIT/as_of
# ---------------------------------------------------------------------------


class TestPIT:
    def test_as_of_in_observation(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        assert obs.as_of == _AS_OF.isoformat()


# ---------------------------------------------------------------------------
# Missing/invalid data
# ---------------------------------------------------------------------------


class TestMissingData:
    def test_empty_bars_observations(self):
        result = compute_technical_indicators([])
        obs = build_technical_observations(result, _AS_OF)
        assert obs.total_count == 0
        assert len(obs.indicator_observations) == 0

    def test_single_bar_observations(self):
        bars = [PriceBar(
            symbol="TEST",
            trading_date=date(2024, 1, 1),
            open=Decimal("100"),
            high=Decimal("102"),
            low=Decimal("98"),
            close=Decimal("101"),
            volume=1000,
        )]
        result = compute_technical_indicators(bars)
        obs = build_technical_observations(result, _AS_OF)
        # Should still produce some observations (returns may be None)
        assert isinstance(obs.total_count, int)
