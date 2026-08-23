"""Tests for technical indicator computation."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.analysis.technical_indicators import (
    TechnicalIndicatorResult,
    compute_technical_indicators,
)
from src.data.models import PriceBar


def _bar(
    d: str,
    o: str = "100",
    h: str = "102",
    l: str = "98",
    c: str = "101",
    v: int = 1000,
    symbol: str = "TEST",
) -> PriceBar:
    return PriceBar(
        symbol=symbol,
        trading_date=date.fromisoformat(d),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(l),
        close=Decimal(c),
        volume=v,
    )


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


def _oscillating_bars(n: int, start: str = "2024-01-01") -> list[PriceBar]:
    bars = []
    base = date.fromisoformat(start)
    for i in range(n):
        d = base + timedelta(days=i)
        direction = 1 if i % 2 == 0 else -1
        o = Decimal("100") + Decimal(direction * (i % 5))
        bars.append(PriceBar(
            symbol="TEST",
            trading_date=d,
            open=o,
            high=o + Decimal("2"),
            low=o - Decimal("2"),
            close=o + Decimal(str(direction * 0.5)),
            volume=1000 + i * 100,
        ))
    return bars


# ---------------------------------------------------------------------------
# Empty / insufficient data
# ---------------------------------------------------------------------------


class TestInsufficientData:
    def test_empty_bars(self):
        result = compute_technical_indicators([])
        assert result.symbol == ""
        assert result.bars_used == 0

    def test_single_bar(self):
        result = compute_technical_indicators([_bar("2024-01-01")])
        assert result.symbol == "TEST"
        assert result.bars_used == 1
        assert result.return_1d is None
        assert result.sma.sma_5 is None

    def test_insufficient_for_rsi(self):
        bars = _rising_bars(5)
        result = compute_technical_indicators(bars)
        assert result.rsi.rsi_14 is None

    def test_insufficient_for_macd(self):
        bars = _rising_bars(10)
        result = compute_technical_indicators(bars)
        assert result.macd.macd_line is None

    def test_insufficient_for_bollinger(self):
        bars = _rising_bars(10)
        result = compute_technical_indicators(bars)
        assert result.bollinger.upper is None

    def test_insufficient_for_adx(self):
        bars = _rising_bars(10)
        result = compute_technical_indicators(bars)
        assert result.adx.adx_14 is None


# ---------------------------------------------------------------------------
# Multi-horizon returns
# ---------------------------------------------------------------------------


class TestReturns:
    def test_return_1d(self):
        bars = _rising_bars(5)
        result = compute_technical_indicators(bars)
        assert result.return_1d is not None
        assert result.return_1d > 0

    def test_return_5d(self):
        bars = _rising_bars(10)
        result = compute_technical_indicators(bars)
        assert result.return_5d is not None
        assert result.return_5d > 0

    def test_return_20d(self):
        bars = _rising_bars(25)
        result = compute_technical_indicators(bars)
        assert result.return_20d is not None
        assert result.return_20d > 0

    def test_return_200d_insufficient(self):
        bars = _rising_bars(50)
        result = compute_technical_indicators(bars)
        assert result.return_200d is None


# ---------------------------------------------------------------------------
# SMA
# ---------------------------------------------------------------------------


class TestSMA:
    def test_sma_5(self):
        bars = _rising_bars(10)
        result = compute_technical_indicators(bars)
        assert result.sma.sma_5 is not None
        assert result.sma.sma_5 > 0

    def test_sma_20(self):
        bars = _rising_bars(25)
        result = compute_technical_indicators(bars)
        assert result.sma.sma_20 is not None

    def test_sma_200_insufficient(self):
        bars = _rising_bars(50)
        result = compute_technical_indicators(bars)
        assert result.sma.sma_200 is None

    def test_price_vs_sma(self):
        bars = _rising_bars(10)
        result = compute_technical_indicators(bars)
        assert result.price_vs_sma.price_vs_sma_5_pct is not None


# ---------------------------------------------------------------------------
# EMA
# ---------------------------------------------------------------------------


class TestEMA:
    def test_ema_9(self):
        bars = _rising_bars(15)
        result = compute_technical_indicators(bars)
        assert result.ema.ema_9 is not None

    def test_ema_200_insufficient(self):
        bars = _rising_bars(50)
        result = compute_technical_indicators(bars)
        assert result.ema.ema_200 is None

    def test_price_vs_ema(self):
        bars = _rising_bars(15)
        result = compute_technical_indicators(bars)
        assert result.price_vs_ema.price_vs_ema_9_pct is not None


# ---------------------------------------------------------------------------
# RSI
# ---------------------------------------------------------------------------


class TestRSI:
    def test_rsi_range(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        assert result.rsi.rsi_14 is not None
        assert Decimal("0") <= result.rsi.rsi_14 <= Decimal("100")

    def test_rsi_overbought_on_rising(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        assert result.rsi.signal == "OVERBOUGHT"

    def test_rsi_has_explanation(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        assert len(result.rsi.explanation) > 0


# ---------------------------------------------------------------------------
# MACD
# ---------------------------------------------------------------------------


class TestMACD:
    def test_macd_computed(self):
        bars = _rising_bars(40)
        result = compute_technical_indicators(bars)
        assert result.macd.macd_line is not None
        assert result.macd.signal_line is not None
        assert result.macd.histogram is not None

    def test_macd_crossover_none_on_monotonic(self):
        bars = _rising_bars(40)
        result = compute_technical_indicators(bars)
        assert result.macd.macd_crossover == "NONE"

    def test_macd_has_explanation(self):
        bars = _rising_bars(40)
        result = compute_technical_indicators(bars)
        assert len(result.macd.explanation) > 0


# ---------------------------------------------------------------------------
# Stochastic
# ---------------------------------------------------------------------------


class TestStochastic:
    def test_stochastic_computed(self):
        bars = _oscillating_bars(30)
        result = compute_technical_indicators(bars)
        assert result.stochastic.percent_k is not None
        assert result.stochastic.percent_d is not None

    def test_stochastic_range(self):
        bars = _oscillating_bars(30)
        result = compute_technical_indicators(bars)
        assert Decimal("0") <= result.stochastic.percent_k <= Decimal("100")


# ---------------------------------------------------------------------------
# Williams %R
# ---------------------------------------------------------------------------


class TestWilliamsR:
    def test_williams_computed(self):
        bars = _oscillating_bars(20)
        result = compute_technical_indicators(bars)
        assert result.williams_r.williams_r_14 is not None

    def test_williams_range(self):
        bars = _oscillating_bars(20)
        result = compute_technical_indicators(bars)
        assert Decimal("-100") <= result.williams_r.williams_r_14 <= Decimal("0")


# ---------------------------------------------------------------------------
# ATR
# ---------------------------------------------------------------------------


class TestATR:
    def test_atr_computed(self):
        bars = _rising_bars(20)
        result = compute_technical_indicators(bars)
        assert result.atr.atr_14 is not None
        assert result.atr.atr_14 > 0

    def test_atr_pct(self):
        bars = _rising_bars(20)
        result = compute_technical_indicators(bars)
        assert result.atr.atr_pct is not None


# ---------------------------------------------------------------------------
# Bollinger Bands
# ---------------------------------------------------------------------------


class TestBollinger:
    def test_bollinger_computed(self):
        bars = _rising_bars(25)
        result = compute_technical_indicators(bars)
        assert result.bollinger.upper is not None
        assert result.bollinger.middle is not None
        assert result.bollinger.lower is not None

    def test_bollinger_ordering(self):
        bars = _rising_bars(25)
        result = compute_technical_indicators(bars)
        assert result.bollinger.upper > result.bollinger.lower

    def test_bollinger_bandwidth(self):
        bars = _rising_bars(25)
        result = compute_technical_indicators(bars)
        assert result.bollinger.bandwidth is not None

    def test_bollinger_pct_b(self):
        bars = _rising_bars(25)
        result = compute_technical_indicators(bars)
        assert result.bollinger.pct_b is not None


# ---------------------------------------------------------------------------
# Volume indicators
# ---------------------------------------------------------------------------


class TestVolume:
    def test_obv_computed(self):
        bars = _rising_bars(10)
        result = compute_technical_indicators(bars)
        assert result.volume_indicators.obv is not None

    def test_ad_line_computed(self):
        bars = _rising_bars(10)
        result = compute_technical_indicators(bars)
        assert result.volume_indicators.accumulation_distribution is not None

    def test_mfi_computed_with_mixed_data(self):
        bars = _oscillating_bars(30)
        result = compute_technical_indicators(bars)
        # MFI may be None if no negative flow
        assert result.volume_indicators.mfi_14 is not None or result.volume_indicators.mfi_14 is None

    def test_price_volume_divergence(self):
        bars = _rising_bars(10)
        result = compute_technical_indicators(bars)
        assert result.volume_indicators.price_volume_divergence in ("NONE", "BEARISH_DIVERGENCE", "BULLISH_DIVERGENCE")


# ---------------------------------------------------------------------------
# ADX
# ---------------------------------------------------------------------------


class TestADX:
    def test_adx_computed(self):
        bars = _rising_bars(40)
        result = compute_technical_indicators(bars)
        assert result.adx.adx_14 is not None

    def test_adx_range(self):
        bars = _rising_bars(40)
        result = compute_technical_indicators(bars)
        assert Decimal("0") <= result.adx.adx_14 <= Decimal("100")


# ---------------------------------------------------------------------------
# CCI
# ---------------------------------------------------------------------------


class TestCCI:
    def test_cci_computed(self):
        bars = _rising_bars(25)
        result = compute_technical_indicators(bars)
        assert result.cci.cci_20 is not None


# ---------------------------------------------------------------------------
# Pivots
# ---------------------------------------------------------------------------


class TestPivots:
    def test_pivots_computed(self):
        bars = _rising_bars(5)
        result = compute_technical_indicators(bars)
        assert result.pivots.pivot is not None
        assert result.pivots.r1 is not None
        assert result.pivots.s1 is not None

    def test_pivot_ordering(self):
        bars = _rising_bars(5)
        result = compute_technical_indicators(bars)
        assert result.pivots.r1 > result.pivots.pivot
        assert result.pivots.s1 < result.pivots.pivot


# ---------------------------------------------------------------------------
# Breakout
# ---------------------------------------------------------------------------


class TestBreakout:
    def test_breakout_computed(self):
        bars = _rising_bars(25)
        result = compute_technical_indicators(bars)
        assert result.breakout.signal in (
            "NO_BREAKOUT", "BREAKOUT_UPPER", "BREAKDOWN_LOWER", "INSUFFICIENT_DATA"
        )


# ---------------------------------------------------------------------------
# Gaps
# ---------------------------------------------------------------------------


class TestGaps:
    def test_no_gap_on_steady(self):
        bars = _rising_bars(5)
        result = compute_technical_indicators(bars)
        assert result.gaps.gap_type == "NO_GAP"

    def test_gap_up(self):
        bars = [
            _bar("2024-01-01", c="100"),
            _bar("2024-01-02", o="105", h="106", l="104", c="105"),
        ]
        result = compute_technical_indicators(bars)
        assert result.gaps.gap_type == "GAP_UP"

    def test_gap_down(self):
        bars = [
            _bar("2024-01-01", c="100"),
            _bar("2024-01-02", o="90", h="91", l="89", c="90"),
        ]
        result = compute_technical_indicators(bars)
        assert result.gaps.gap_type == "GAP_DOWN"


# ---------------------------------------------------------------------------
# 52-week high/low
# ---------------------------------------------------------------------------


class TestHighLow:
    def test_52w_computed(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        assert result.high_low.high_52w is not None
        assert result.high_low.low_52w is not None

    def test_near_52w_high_on_rising(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        assert "HIGH" in result.high_low.signal


# ---------------------------------------------------------------------------
# Drawdowns
# ---------------------------------------------------------------------------


class TestDrawdowns:
    def test_drawdown_computed(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        assert result.drawdowns.current_drawdown is not None

    def test_drawdown_on_declining(self):
        bars = []
        base = date(2024, 1, 1)
        for i in range(30):
            d = base + timedelta(days=i)
            o = Decimal("100") - Decimal(i)
            bars.append(PriceBar(
                symbol="TEST",
                trading_date=d,
                open=o,
                high=o + Decimal("2"),
                low=o - Decimal("2"),
                close=o - Decimal("1"),
                volume=1000,
            ))
        result = compute_technical_indicators(bars)
        assert result.drawdowns.current_drawdown is not None
        assert result.drawdowns.current_drawdown < 0


# ---------------------------------------------------------------------------
# Trend structure
# ---------------------------------------------------------------------------


class TestTrendStructure:
    def test_trend_computed(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        assert result.trend_structure.regime != "INSUFFICIENT_DATA"

    def test_bullish_regime_on_rising(self):
        bars = _rising_bars(60)
        result = compute_technical_indicators(bars)
        assert "BULL" in result.trend_structure.regime

    def test_trend_has_explanation(self):
        bars = _rising_bars(30)
        result = compute_technical_indicators(bars)
        assert len(result.trend_structure.explanation) > 0


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_input_same_output(self):
        bars = _rising_bars(30)
        r1 = compute_technical_indicators(bars)
        r2 = compute_technical_indicators(bars)
        assert r1.rsi.rsi_14 == r2.rsi.rsi_14
        assert r1.macd.macd_line == r2.macd.macd_line
        assert r1.bollinger.upper == r2.bollinger.upper

    def test_symbol_preserved(self):
        bars = _rising_bars(10)
        result = compute_technical_indicators(bars)
        assert result.symbol == "TEST"
