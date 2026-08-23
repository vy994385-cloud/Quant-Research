"""Tests for price-move attribution engine."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.analysis.price_attribution import (
    AttributionCandidate,
    AttributionCategory,
    AttributionConfidence,
    AttributionDirection,
    PriceAttributionResult,
    PriceMove,
    attribute_price_move,
)
from src.data.models import PriceBar


_AS_OF = datetime(2024, 6, 15, tzinfo=timezone.utc)


def _rising_bars(
    n: int,
    start: str = "2024-01-01",
    base_price: Decimal = Decimal("100"),
    daily_change: Decimal = Decimal("1"),
) -> list[PriceBar]:
    bars = []
    base = date.fromisoformat(start)
    for i in range(n):
        d = base + timedelta(days=i)
        o = base_price + daily_change * Decimal(i)
        bars.append(
            PriceBar(
                symbol="TEST",
                trading_date=d,
                open=o,
                high=o + Decimal("2"),
                low=o - Decimal("2"),
                close=o + Decimal("1"),
                volume=1000 + i * 100,
            )
        )
    return bars


def _flat_bars(
    n: int,
    start: str = "2024-01-01",
    price: Decimal = Decimal("100"),
) -> list[PriceBar]:
    bars = []
    base = date.fromisoformat(start)
    for i in range(n):
        d = base + timedelta(days=i)
        bars.append(
            PriceBar(
                symbol="TEST",
                trading_date=d,
                open=price,
                high=price + Decimal("1"),
                low=price - Decimal("1"),
                close=price,
                volume=1000,
            )
        )
    return bars


def _high_volume_bars(
    n: int,
    start: str = "2024-01-01",
) -> list[PriceBar]:
    bars = []
    base = date.fromisoformat(start)
    for i in range(n):
        d = base + timedelta(days=i)
        vol = 1000 if i < n - 1 else 10000
        bars.append(
            PriceBar(
                symbol="TEST",
                trading_date=d,
                open=Decimal("100"),
                high=Decimal("102"),
                low=Decimal("98"),
                close=Decimal("101"),
                volume=vol,
            )
        )
    return bars


# ---------------------------------------------------------------------------
# Empty / insufficient data
# ---------------------------------------------------------------------------


class TestInsufficientData:
    def test_empty_bars(self):
        result = attribute_price_move([], "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert result.price_move is None
        assert len(result.notes) > 0

    def test_single_bar(self):
        bars = [
            PriceBar(
                symbol="TEST",
                trading_date=date(2024, 1, 1),
                open=Decimal("100"),
                high=Decimal("102"),
                low=Decimal("98"),
                close=Decimal("101"),
                volume=1000,
            )
        ]
        result = attribute_price_move(bars, "TEST", _AS_OF)
        assert result.price_move is None


# ---------------------------------------------------------------------------
# Price move computation
# ---------------------------------------------------------------------------


class TestPriceMove:
    def test_positive_move(self):
        bars = _rising_bars(40, daily_change=Decimal("2"))
        result = attribute_price_move(
            bars, "TEST", _AS_OF, lookback_days=30
        )
        assert result.price_move is not None
        assert result.price_move.direction == "POSITIVE"
        assert Decimal(result.price_move.percentage_change) > 0

    def test_negative_move(self):
        bars = _rising_bars(40, daily_change=Decimal("-2"))
        result = attribute_price_move(
            bars, "TEST", _AS_OF, lookback_days=30
        )
        assert result.price_move is not None
        assert result.price_move.direction == "NEGATIVE"
        assert Decimal(result.price_move.percentage_change) < 0

    def test_flat_move(self):
        bars = _flat_bars(40)
        result = attribute_price_move(
            bars, "TEST", _AS_OF, lookback_days=30
        )
        assert result.price_move is not None
        assert result.price_move.direction == "NEUTRAL"


# ---------------------------------------------------------------------------
# Volume attribution
# ---------------------------------------------------------------------------


class TestVolumeAttribution:
    def test_unusual_volume_detected(self):
        bars = _high_volume_bars(30)
        result = attribute_price_move(
            bars, "TEST", _AS_OF, lookback_days=20
        )
        categories = [c.category for c in result.candidates]
        assert AttributionCategory.VOLUME.value in categories

    def test_no_unusual_volume(self):
        bars = _flat_bars(30)
        result = attribute_price_move(
            bars, "TEST", _AS_OF, lookback_days=20
        )
        vol_candidates = [
            c
            for c in result.candidates
            if c.category == AttributionCategory.VOLUME.value
        ]
        assert len(vol_candidates) == 0


# ---------------------------------------------------------------------------
# Trend attribution
# ---------------------------------------------------------------------------


class TestTrendAttribution:
    def test_bullish_trend(self):
        bars = _rising_bars(60, daily_change=Decimal("1"))
        result = attribute_price_move(
            bars, "TEST", _AS_OF, lookback_days=30
        )
        trend_candidates = [
            c
            for c in result.candidates
            if c.category == AttributionCategory.TECHNICAL.value
        ]
        assert len(trend_candidates) >= 1

    def test_insufficient_bars_for_trend(self):
        bars = _rising_bars(10, daily_change=Decimal("1"))
        result = attribute_price_move(
            bars, "TEST", _AS_OF, lookback_days=5
        )
        trend_candidates = [
            c
            for c in result.candidates
            if c.category == AttributionCategory.TECHNICAL.value
        ]
        assert len(trend_candidates) == 0


# ---------------------------------------------------------------------------
# Confidence levels
# ---------------------------------------------------------------------------


class TestConfidence:
    def test_confidence_counts(self):
        bars = _rising_bars(60, daily_change=Decimal("2"))
        result = attribute_price_move(
            bars, "TEST", _AS_OF, lookback_days=30
        )
        total = (
            result.high_confidence_count
            + result.medium_confidence_count
            + result.low_confidence_count
        )
        assert total == result.total_candidates

    def test_has_disclaimer(self):
        bars = _rising_bars(40)
        result = attribute_price_move(
            bars, "TEST", _AS_OF, lookback_days=30
        )
        assert "correlational" in result.disclaimer.lower()


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------


class TestCoverage:
    def test_coverage_keys(self):
        bars = _rising_bars(60, daily_change=Decimal("2"))
        result = attribute_price_move(
            bars, "TEST", _AS_OF, lookback_days=30
        )
        assert "volume_candidates" in result.coverage
        assert "trend_candidates" in result.coverage
        assert "market_candidates" in result.coverage
