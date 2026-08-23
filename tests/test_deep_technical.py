"""Tests for deep technical orchestrator."""

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal

import pytest

from src.analysis.deep_technical import (
    DeepTechnicalResult,
    analyze_deep_technicals,
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
# Empty / insufficient data
# ---------------------------------------------------------------------------


class TestInsufficientData:
    def test_empty_bars(self):
        result = analyze_deep_technicals([], None, "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert result.bars_used == 0
        assert result.indicators is None
        assert len(result.notes) > 0

    def test_single_bar(self):
        bars = [PriceBar(
            symbol="TEST",
            trading_date=date(2024, 1, 1),
            open=Decimal("100"),
            high=Decimal("102"),
            low=Decimal("98"),
            close=Decimal("101"),
            volume=1000,
        )]
        result = analyze_deep_technicals(bars, None, "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert result.bars_used == 1
        assert result.indicators is not None


# ---------------------------------------------------------------------------
# Multi-period analysis
# ---------------------------------------------------------------------------


class TestAnalysis:
    def test_basic_analysis(self):
        bars = _rising_bars(30)
        result = analyze_deep_technicals(bars, None, "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert result.bars_used == 30
        assert result.indicators is not None
        assert result.observation_set is not None

    def test_indicators_computed(self):
        bars = _rising_bars(30)
        result = analyze_deep_technicals(bars, None, "TEST", _AS_OF)
        assert result.indicators.sma.sma_5 is not None
        assert result.indicators.rsi.rsi_14 is not None

    def test_observations_built(self):
        bars = _rising_bars(30)
        result = analyze_deep_technicals(bars, None, "TEST", _AS_OF)
        assert result.observation_set is not None
        assert result.observation_set.total_count > 0

    def test_with_benchmark(self):
        stock_bars = _rising_bars(30)
        bench_bars = []
        base = date(2024, 1, 1)
        for i in range(30):
            d = base + timedelta(days=i)
            o = Decimal("20000") + Decimal(i * 10)
            bench_bars.append(PriceBar(
                symbol="^NSEI",
                trading_date=d,
                open=o,
                high=o + Decimal("50"),
                low=o - Decimal("50"),
                close=o + Decimal("20"),
                volume=1000000,
            ))
        result = analyze_deep_technicals(stock_bars, bench_bars, "TEST", _AS_OF)
        assert result.indicators is not None


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class TestProperties:
    def test_has_observations(self):
        bars = _rising_bars(30)
        result = analyze_deep_technicals(bars, None, "TEST", _AS_OF)
        assert isinstance(result.has_observations, bool)

    def test_positive_count(self):
        bars = _rising_bars(30)
        result = analyze_deep_technicals(bars, None, "TEST", _AS_OF)
        assert result.positive_count >= 0

    def test_negative_count(self):
        bars = _rising_bars(30)
        result = analyze_deep_technicals(bars, None, "TEST", _AS_OF)
        assert result.negative_count >= 0

    def test_neutral_count(self):
        bars = _rising_bars(30)
        result = analyze_deep_technicals(bars, None, "TEST", _AS_OF)
        assert result.neutral_count >= 0


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------


class TestCoverage:
    def test_available_indicators(self):
        bars = _rising_bars(30)
        result = analyze_deep_technicals(bars, None, "TEST", _AS_OF)
        assert len(result.available_indicators) > 0

    def test_missing_indicators(self):
        bars = _rising_bars(30)
        result = analyze_deep_technicals(bars, None, "TEST", _AS_OF)
        assert isinstance(result.missing_indicators, tuple)


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_input_same_output(self):
        bars = _rising_bars(30)
        r1 = analyze_deep_technicals(bars, None, "TEST", _AS_OF)
        r2 = analyze_deep_technicals(bars, None, "TEST", _AS_OF)
        assert r1.bars_used == r2.bars_used
        assert r1.observation_set is not None
        assert r2.observation_set is not None
        assert r1.observation_set.total_count == r2.observation_set.total_count
