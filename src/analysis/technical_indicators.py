"""
Technical indicator engine.

Computes indicators from OHLCV price bars using Decimal precision.
All calculations are deterministic and PIT-safe: only observations
available up to the current bar are used.

Thresholds are documented here for traceability:
  - RSI: overbought >= 70, oversold <= 30
  - Stochastic: overbought >= 80, oversled <= 20
  - Williams %R: overbought >= -20, oversold <= -80
  - CCI: overbought >= 100, oversold <= -100
  - MFI: overbought >= 80, oversold <= 20
  - ADX: strong trend >= 25, weak trend < 20
  - Bollinger: %B > 1 = above upper, %B < 0 = below lower
  - ATR multiplier for breakouts: 1.5x ATR
  - Gap threshold: >= 1% open vs previous close
  - 52-week: proximity within 5% of high/low
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from src.data.models import PriceBar


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

_RSI_OVERBOUGHT = Decimal("70")
_RSI_OVERSOLD = Decimal("30")
_STOCHASTIC_OVERBOUGHT = Decimal("80")
_STOCHASTIC_OVERSOLD = Decimal("20")
_WILLIAMS_OVERBOUGHT = Decimal("-20")
_WILLIAMS_OVERSOLD = Decimal("-80")
_CCI_OVERBOUGHT = Decimal("100")
_CCI_OVERSOLD = Decimal("-100")
_MFI_OVERBOUGHT = Decimal("80")
_MFI_OVERSOLD = Decimal("20")
_ADX_STRONG_TREND = Decimal("25")
_ADX_WEAK_TREND = Decimal("20")
_BOLLINGER_UPPER_THRESHOLD = Decimal("1")
_BOLLINGER_LOWER_THRESHOLD = Decimal("0")
_ATR_BREAKOUT_MULTIPLIER = Decimal("1.5")
_GAP_THRESHOLD_PCT = Decimal("1")
_PROXIMITY_52W_PCT = Decimal("5")

# SMA periods for trend structure
_SMA_PERIODS = (5, 10, 20, 50, 100, 200)

# EMA periods
_EMA_PERIODS = (9, 12, 20, 26, 50, 200)

# Multi-horizon return periods
_RETURN_PERIODS = (1, 5, 10, 20, 50, 100, 200)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _pct_change(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous <= 0:
        return None
    return ((current - previous) / previous) * Decimal("100")


def _sma(values: Sequence[Decimal], period: int) -> Decimal | None:
    if len(values) < period:
        return None
    window = values[-period:]
    return sum(window) / Decimal(period)


def _ema(
    values: Sequence[Decimal],
    period: int,
) -> list[Decimal]:
    """Return full EMA series. Empty list if insufficient data."""
    if len(values) < period:
        return []

    multiplier = Decimal("2") / (Decimal(period) + Decimal("1"))
    seed = sum(values[:period]) / Decimal(period)
    ema_values: list[Decimal] = [seed]

    for val in values[period:]:
        ema_values.append(val * multiplier + ema_values[-1] * (Decimal("1") - multiplier))

    return ema_values


def _true_range(bar: PriceBar, prev_close: Decimal) -> Decimal:
    hl = bar.high - bar.low
    hc = abs(bar.high - prev_close)
    lc = abs(bar.low - prev_close)
    return max(hl, hc, lc)


def _safe_div(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> Decimal | None:
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return numerator / denominator


def _quantize(value: Decimal, places: str = "0.01") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Signal classification helpers
# ---------------------------------------------------------------------------


def _rsi_signal(rsi: Decimal) -> str:
    if rsi >= _RSI_OVERBOUGHT:
        return "OVERBOUGHT"
    if rsi <= _RSI_OVERSOLD:
        return "OVERSOLD"
    return "NEUTRAL"


def _stochastic_signal(k: Decimal) -> str:
    if k >= _STOCHASTIC_OVERBOUGHT:
        return "OVERBOUGHT"
    if k <= _STOCHASTIC_OVERSOLD:
        return "OVERSOLD"
    return "NEUTRAL"


def _williams_signal(wr: Decimal) -> str:
    if wr >= _WILLIAMS_OVERBOUGHT:
        return "OVERBOUGHT"
    if wr <= _WILLIAMS_OVERSOLD:
        return "OVERSOLD"
    return "NEUTRAL"


def _cci_signal(cci: Decimal) -> str:
    if cci >= _CCI_OVERBOUGHT:
        return "OVERBOUGHT"
    if cci <= _CCI_OVERSOLD:
        return "OVERSOLD"
    return "NEUTRAL"


def _mfi_signal(mfi: Decimal) -> str:
    if mfi >= _MFI_OVERBOUGHT:
        return "OVERBOUGHT"
    if mfi <= _MFI_OVERSOLD:
        return "OVERSOLD"
    return "NEUTRAL"


def _adx_signal(adx: Decimal) -> str:
    if adx >= _ADX_STRONG_TREND:
        return "STRONG_TREND"
    if adx < _ADX_WEAK_TREND:
        return "WEAK_TREND"
    return "MODERATE_TREND"


def _bollinger_signal(pct_b: Decimal) -> str:
    if pct_b > _BOLLINGER_UPPER_THRESHOLD:
        return "ABOVE_UPPER"
    if pct_b < _BOLLINGER_LOWER_THRESHOLD:
        return "BELOW_LOWER"
    return "WITHIN_BANDS"


def _direction_from_value(value: Decimal | None, inverse: bool = False) -> str:
    if value is None:
        return "NEUTRAL"
    if value > 0:
        return "NEGATIVE" if inverse else "POSITIVE"
    if value < 0:
        return "POSITIVE" if inverse else "NEGATIVE"
    return "NEUTRAL"


# ---------------------------------------------------------------------------
# Indicator result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndicatorResult:
    """Base for a single indicator observation."""

    indicator: str
    period: int | None = None
    value: str | None = None
    signal: str = "INSUFFICIENT_DATA"
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class EMASet:
    """All EMA values for the latest bar."""

    ema_9: Decimal | None = None
    ema_12: Decimal | None = None
    ema_20: Decimal | None = None
    ema_26: Decimal | None = None
    ema_50: Decimal | None = None
    ema_200: Decimal | None = None


@dataclass(frozen=True)
class PriceVsEMA:
    """Price relative to each EMA."""

    price_vs_ema_9_pct: Decimal | None = None
    price_vs_ema_12_pct: Decimal | None = None
    price_vs_ema_20_pct: Decimal | None = None
    price_vs_ema_26_pct: Decimal | None = None
    price_vs_ema_50_pct: Decimal | None = None
    price_vs_ema_200_pct: Decimal | None = None


@dataclass(frozen=True)
class SMASeries:
    """SMA values for trend structure."""

    sma_5: Decimal | None = None
    sma_10: Decimal | None = None
    sma_20: Decimal | None = None
    sma_50: Decimal | None = None
    sma_100: Decimal | None = None
    sma_200: Decimal | None = None


@dataclass(frozen=True)
class PriceVsSMA:
    """Price relative to each SMA."""

    price_vs_sma_5_pct: Decimal | None = None
    price_vs_sma_10_pct: Decimal | None = None
    price_vs_sma_20_pct: Decimal | None = None
    price_vs_sma_50_pct: Decimal | None = None
    price_vs_sma_100_pct: Decimal | None = None
    price_vs_sma_200_pct: Decimal | None = None


@dataclass(frozen=True)
class MACDResult:
    """MACD indicator."""

    macd_line: Decimal | None = None
    signal_line: Decimal | None = None
    histogram: Decimal | None = None
    macd_crossover: str = "NONE"
    signal_label: str = "INSUFFICIENT_DATA"
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class RSIResult:
    """RSI indicator."""

    rsi_14: Decimal | None = None
    signal: str = "INSUFFICIENT_DATA"
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class StochasticResult:
    """Stochastic oscillator."""

    percent_k: Decimal | None = None
    percent_d: Decimal | None = None
    signal: str = "INSUFFICIENT_DATA"
    crossover: str = "NONE"
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class WilliamsRResult:
    """Williams %R."""

    williams_r_14: Decimal | None = None
    signal: str = "INSUFFICIENT_DATA"
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class ATRResult:
    """Average True Range."""

    atr_14: Decimal | None = None
    atr_pct: Decimal | None = None
    signal: str = "INSUFFICIENT_DATA"
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class BollingerResult:
    """Bollinger Bands."""

    upper: Decimal | None = None
    middle: Decimal | None = None
    lower: Decimal | None = None
    bandwidth: Decimal | None = None
    pct_b: Decimal | None = None
    signal: str = "INSUFFICIENT_DATA"
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class VolumeIndicators:
    """Volume-based indicators."""

    obv: str | None = None
    obv_change: str | None = None
    accumulation_distribution: str | None = None
    mfi_14: Decimal | None = None
    mfi_signal: str = "INSUFFICIENT_DATA"
    price_volume_divergence: str = "NONE"
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class MomentumResult:
    """Rate of change / momentum indicators."""

    roc_5: Decimal | None = None
    roc_10: Decimal | None = None
    roc_20: Decimal | None = None
    momentum_direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class ADXResult:
    """Average Directional Index."""

    adx_14: Decimal | None = None
    plus_di: Decimal | None = None
    minus_di: Decimal | None = None
    signal: str = "INSUFFICIENT_DATA"
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class CCIResult:
    """Commodity Channel Index."""

    cci_20: Decimal | None = None
    signal: str = "INSUFFICIENT_DATA"
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class PivotResult:
    """Pivot points and support/resistance."""

    pivot: Decimal | None = None
    r1: Decimal | None = None
    r2: Decimal | None = None
    r3: Decimal | None = None
    s1: Decimal | None = None
    s2: Decimal | None = None
    s3: Decimal | None = None
    explanation: str = ""


@dataclass(frozen=True)
class BreakoutResult:
    """Breakout/breakdown detection."""

    breakout_upper: bool = False
    breakout_lower: bool = False
    atr_breakout: str = "NONE"
    signal: str = "INSUFFICIENT_DATA"
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class GapResult:
    """Gap detection."""

    gap_type: str = "NO_GAP"
    gap_pct: Decimal | None = None
    signal: str = "INSUFFICIENT_DATA"
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class HighLowResult:
    """52-week high/low analysis."""

    high_52w: Decimal | None = None
    low_52w: Decimal | None = None
    pct_from_high: Decimal | None = None
    pct_from_low: Decimal | None = None
    at_52w_high: bool = False
    at_52w_low: bool = False
    signal: str = "INSUFFICIENT_DATA"
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class DrawdownResult:
    """Drawdown analysis."""

    current_drawdown: Decimal | None = None
    max_drawdown_20d: Decimal | None = None
    max_drawdown_50d: Decimal | None = None
    max_drawdown_200d: Decimal | None = None
    recovery_pct: Decimal | None = None
    explanation: str = ""


@dataclass(frozen=True)
class BenchmarkCorrelation:
    """Benchmark correlation and beta."""

    correlation_20d: Decimal | None = None
    correlation_50d: Decimal | None = None
    beta_20d: Decimal | None = None
    beta_50d: Decimal | None = None
    direction: str = "NEUTRAL"
    explanation: str = ""


@dataclass(frozen=True)
class TrendStructure:
    """Extended trend structure / regime analysis."""

    regime: str = "INSUFFICIENT_DATA"
    trend_strength: Decimal | None = None
    above_sma_count: int = 0
    below_sma_count: int = 0
    sma_alignment: str = "MIXED"
    ema_alignment: str = "MIXED"
    explanation: str = ""


# ---------------------------------------------------------------------------
# Main computation function
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TechnicalIndicatorResult:
    """
    Complete technical indicator result for one symbol.

    All fields are optional to gracefully handle insufficient data.
    """

    symbol: str
    trading_date: str
    bars_used: int = 0

    # Existing indicators (A-class, already available)
    return_1d: Decimal | None = None
    return_5d: Decimal | None = None
    return_10d: Decimal | None = None
    return_20d: Decimal | None = None
    return_50d: Decimal | None = None
    return_100d: Decimal | None = None
    return_200d: Decimal | None = None

    sma: SMASeries = field(default_factory=SMASeries)
    price_vs_sma: PriceVsSMA = field(default_factory=PriceVsSMA)

    # New indicators (B-class)
    ema: EMASet = field(default_factory=EMASet)
    price_vs_ema: PriceVsEMA = field(default_factory=PriceVsEMA)

    rsi: RSIResult = field(default_factory=RSIResult)
    macd: MACDResult = field(default_factory=MACDResult)
    stochastic: StochasticResult = field(default_factory=StochasticResult)
    williams_r: WilliamsRResult = field(default_factory=WilliamsRResult)
    momentum: MomentumResult = field(default_factory=MomentumResult)

    atr: ATRResult = field(default_factory=ATRResult)
    bollinger: BollingerResult = field(default_factory=BollingerResult)
    volume_indicators: VolumeIndicators = field(
        default_factory=VolumeIndicators
    )

    adx: ADXResult = field(default_factory=ADXResult)
    cci: CCIResult = field(default_factory=CCIResult)

    pivots: PivotResult = field(default_factory=PivotResult)
    breakout: BreakoutResult = field(default_factory=BreakoutResult)
    gaps: GapResult = field(default_factory=GapResult)
    high_low: HighLowResult = field(default_factory=HighLowResult)
    drawdowns: DrawdownResult = field(default_factory=DrawdownResult)

    trend_structure: TrendStructure = field(default_factory=TrendStructure)


def _compute_ema_set(closes: Sequence[Decimal]) -> EMASet:
    ema_series: dict[int, list[Decimal]] = {}
    for period in _EMA_PERIODS:
        ema_series[period] = _ema(closes, period)

    def _latest(series: list[Decimal]) -> Decimal | None:
        return _quantize(series[-1]) if series else None

    return EMASet(
        ema_9=_latest(ema_series[9]),
        ema_12=_latest(ema_series[12]),
        ema_20=_latest(ema_series[20]),
        ema_26=_latest(ema_series[26]),
        ema_50=_latest(ema_series[50]),
        ema_200=_latest(ema_series[200]),
    )


def _compute_price_vs_ema(
    close: Decimal,
    ema_set: EMASet,
) -> PriceVsEMA:
    def _pct(ema: Decimal | None) -> Decimal | None:
        if ema is None or ema <= 0:
            return None
        return _quantize(_pct_change(close, ema))

    return PriceVsEMA(
        price_vs_ema_9_pct=_pct(ema_set.ema_9),
        price_vs_ema_12_pct=_pct(ema_set.ema_12),
        price_vs_ema_20_pct=_pct(ema_set.ema_20),
        price_vs_ema_26_pct=_pct(ema_set.ema_26),
        price_vs_ema_50_pct=_pct(ema_set.ema_50),
        price_vs_ema_200_pct=_pct(ema_set.ema_200),
    )


def _compute_sma_set(closes: Sequence[Decimal]) -> SMASeries:
    return SMASeries(
        sma_5=_quantize(s) if (s := _sma(closes, 5)) is not None else None,
        sma_10=_quantize(s) if (s := _sma(closes, 10)) is not None else None,
        sma_20=_quantize(s) if (s := _sma(closes, 20)) is not None else None,
        sma_50=_quantize(s) if (s := _sma(closes, 50)) is not None else None,
        sma_100=_quantize(s) if (s := _sma(closes, 100)) is not None else None,
        sma_200=_quantize(s) if (s := _sma(closes, 200)) is not None else None,
    )


def _compute_price_vs_sma(
    close: Decimal,
    sma_set: SMASeries,
) -> PriceVsSMA:
    def _pct(sma: Decimal | None) -> Decimal | None:
        if sma is None or sma <= 0:
            return None
        return _quantize(_pct_change(close, sma))

    return PriceVsSMA(
        price_vs_sma_5_pct=_pct(sma_set.sma_5),
        price_vs_sma_10_pct=_pct(sma_set.sma_10),
        price_vs_sma_20_pct=_pct(sma_set.sma_20),
        price_vs_sma_50_pct=_pct(sma_set.sma_50),
        price_vs_sma_100_pct=_pct(sma_set.sma_100),
        price_vs_sma_200_pct=_pct(sma_set.sma_200),
    )


def _compute_rsi(closes: Sequence[Decimal], period: int = 14) -> RSIResult:
    if len(closes) < period + 1:
        return RSIResult()

    gains: list[Decimal] = []
    losses: list[Decimal] = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, Decimal("0")))
        losses.append(max(-change, Decimal("0")))

    if len(gains) < period:
        return RSIResult()

    avg_gain = sum(gains[:period]) / Decimal(period)
    avg_loss = sum(losses[:period]) / Decimal(period)

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (Decimal(period) - Decimal("1")) + gains[i]) / Decimal(period)
        avg_loss = (avg_loss * (Decimal(period) - Decimal("1")) + losses[i]) / Decimal(period)

    if avg_loss == 0:
        rsi = Decimal("100")
    else:
        rs = avg_gain / avg_loss
        rsi = Decimal("100") - (Decimal("100") / (Decimal("1") + rs))

    rsi = _quantize(rsi)
    signal = _rsi_signal(rsi)
    direction = _direction_from_value(rsi - Decimal("50"))

    explanation = f"RSI({period}) = {rsi}. "
    if signal == "OVERBOUGHT":
        explanation += "Above overbought threshold (>=70). "
    elif signal == "OVERSOLD":
        explanation += "Below oversold threshold (<=30). "
    else:
        explanation += "Within neutral range. "

    return RSIResult(
        rsi_14=rsi,
        signal=signal,
        direction=direction,
        explanation=explanation,
    )


def _compute_macd(closes: Sequence[Decimal]) -> MACDResult:
    if len(closes) < 26:
        return MACDResult()

    ema12 = _ema(closes, 12)
    ema26 = _ema(closes, 26)

    if not ema12 or not ema26:
        return MACDResult()

    # Align: ema12 starts at index 11, ema26 starts at index 25
    # ema12[14:] aligns with ema26[0:]
    offset = 26 - 12
    macd_line = [
        ema12[i + offset] - ema26[i]
        for i in range(len(ema26))
    ]

    if len(macd_line) < 9:
        return MACDResult()

    signal_ema = _ema(macd_line, 9)

    if not signal_ema:
        return MACDResult()

    latest_macd = _quantize(macd_line[-1])
    latest_signal = _quantize(signal_ema[-1])
    histogram = _quantize(latest_macd - latest_signal)

    # Crossover detection
    crossover = "NONE"
    if len(macd_line) >= 2 and len(signal_ema) >= 2:
        prev_macd = macd_line[-2]
        prev_signal = signal_ema[-2]
        curr_macd = macd_line[-1]
        curr_signal = signal_ema[-1]

        if prev_macd <= prev_signal and curr_macd > curr_signal:
            crossover = "BULLISH"
        elif prev_macd >= prev_signal and curr_macd < curr_signal:
            crossover = "BEARISH"

    direction = "POSITIVE" if histogram > 0 else "NEGATIVE" if histogram < 0 else "NEUTRAL"

    explanation = f"MACD line={latest_macd}, signal={latest_signal}, histogram={histogram}. "
    if crossover == "BULLISH":
        explanation += "Bullish crossover detected. "
    elif crossover == "BEARISH":
        explanation += "Bearish crossover detected. "

    return MACDResult(
        macd_line=latest_macd,
        signal_line=latest_signal,
        histogram=histogram,
        macd_crossover=crossover,
        signal_label=crossover if crossover != "NONE" else "NO_CROSSOVER",
        direction=direction,
        explanation=explanation,
    )


def _compute_stochastic(
    bars: Sequence[PriceBar],
    k_period: int = 14,
    d_period: int = 3,
) -> StochasticResult:
    if len(bars) < k_period + d_period:
        return StochasticResult()

    k_values: list[Decimal] = []

    for i in range(k_period - 1, len(bars)):
        window = bars[i - k_period + 1 : i + 1]
        highest = max(b.high for b in window)
        lowest = min(b.low for b in window)

        if highest == lowest:
            k_values.append(Decimal("50"))
        else:
            k = ((bars[i].close - lowest) / (highest - lowest)) * Decimal("100")
            k_values.append(_quantize(k))

    if len(k_values) < d_period:
        return StochasticResult()

    d_values = [
        _quantize(sum(k_values[i - d_period + 1 : i + 1]) / Decimal(d_period))
        for i in range(d_period - 1, len(k_values))
    ]

    if not d_values:
        return StochasticResult()

    latest_k = k_values[-1]
    latest_d = d_values[-1]

    crossover = "NONE"
    if len(k_values) >= 2 and len(d_values) >= 2:
        if k_values[-2] <= d_values[-2] and latest_k > latest_d:
            crossover = "BULLISH"
        elif k_values[-2] >= d_values[-2] and latest_k < latest_d:
            crossover = "BEARISH"

    signal = _stochastic_signal(latest_k)
    direction = _direction_from_value(latest_k - Decimal("50"))

    explanation = f"Stochastic %K={latest_k}, %D={latest_d}. "
    if signal == "OVERBOUGHT":
        explanation += "In overbought zone (>=80). "
    elif signal == "OVERSOLD":
        explanation += "In oversold zone (<=20). "

    return StochasticResult(
        percent_k=latest_k,
        percent_d=latest_d,
        signal=signal,
        crossover=crossover,
        direction=direction,
        explanation=explanation,
    )


def _compute_williams_r(
    bars: Sequence[PriceBar],
    period: int = 14,
) -> WilliamsRResult:
    if len(bars) < period:
        return WilliamsRResult()

    window = bars[-period:]
    highest = max(b.high for b in window)
    lowest = min(b.low for b in window)

    if highest == lowest:
        wr = Decimal("-50")
    else:
        wr = ((highest - bars[-1].close) / (highest - lowest)) * Decimal("-100")

    wr = _quantize(wr)
    signal = _williams_signal(wr)
    direction = _direction_from_value(wr + Decimal("50"))

    explanation = f"Williams %R({period}) = {wr}. "
    if signal == "OVERBOUGHT":
        explanation += "Above overbought threshold (>=-20). "
    elif signal == "OVERSOLD":
        explanation += "Below oversold threshold (<=-80). "

    return WilliamsRResult(
        williams_r_14=wr,
        signal=signal,
        direction=direction,
        explanation=explanation,
    )


def _compute_atr(
    bars: Sequence[PriceBar],
    period: int = 14,
) -> ATRResult:
    if len(bars) < period + 1:
        return ATRResult()

    true_ranges: list[Decimal] = []
    for i in range(1, len(bars)):
        tr = _true_range(bars[i], bars[i - 1].close)
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return ATRResult()

    atr = sum(true_ranges[:period]) / Decimal(period)
    for i in range(period, len(true_ranges)):
        atr = (atr * (Decimal(period) - Decimal("1")) + true_ranges[i]) / Decimal(period)

    atr = _quantize(atr)
    atr_pct = _quantize(
        (atr / bars[-1].close) * Decimal("100")
    ) if bars[-1].close > 0 else None

    explanation = f"ATR({period}) = {atr} ({atr_pct}% of price). "

    return ATRResult(
        atr_14=atr,
        atr_pct=atr_pct,
        # ATR measures volatility magnitude, not direction; the
        # no-bias token keeps the signal space directional.
        signal="NEUTRAL",
        direction="NEUTRAL",
        explanation=explanation,
    )


def _compute_bollinger(
    closes: Sequence[Decimal],
    period: int = 20,
    std_dev: Decimal = Decimal("2"),
) -> BollingerResult:
    if len(closes) < period:
        return BollingerResult()

    sma = _sma(closes, period)
    if sma is None:
        return BollingerResult()

    window = closes[-period:]
    mean = sum(window) / Decimal(period)
    variance = sum((v - mean) ** 2 for v in window) / Decimal(period)
    sd = variance.sqrt()

    upper = _quantize(sma + std_dev * sd)
    lower = _quantize(sma - std_dev * sd)
    middle = _quantize(sma)

    bandwidth = _quantize(
        ((upper - lower) / middle) * Decimal("100")
    ) if middle > 0 else None

    pct_b = _quantize(
        (closes[-1] - lower) / (upper - lower)
    ) if upper != lower else None

    signal = _bollinger_signal(pct_b) if pct_b is not None else "INSUFFICIENT_DATA"
    direction = _direction_from_value(pct_b - Decimal("0.5")) if pct_b is not None else "NEUTRAL"

    explanation = f"Bollinger: upper={upper}, middle={middle}, lower={lower}. "
    if bandwidth is not None:
        explanation += f"Bandwidth={bandwidth}%. "
    if pct_b is not None:
        explanation += f"%B={pct_b}. "

    return BollingerResult(
        upper=upper,
        middle=middle,
        lower=lower,
        bandwidth=bandwidth,
        pct_b=pct_b,
        signal=signal,
        direction=direction,
        explanation=explanation,
    )


def _compute_volume_indicators(
    bars: Sequence[PriceBar],
) -> VolumeIndicators:
    if len(bars) < 2:
        return VolumeIndicators()

    # OBV
    obv_value = Decimal("0")
    for i in range(1, len(bars)):
        if bars[i].close > bars[i - 1].close:
            obv_value += Decimal(bars[i].volume)
        elif bars[i].close < bars[i - 1].close:
            obv_value -= Decimal(bars[i].volume)

    obv_change = None
    if len(bars) >= 3:
        prev_obv = Decimal("0")
        for i in range(1, len(bars) - 1):
            if bars[i].close > bars[i - 1].close:
                prev_obv += Decimal(bars[i].volume)
            elif bars[i].close < bars[i - 1].close:
                prev_obv -= Decimal(bars[i].volume)
        if prev_obv != 0:
            obv_change = _quantize(obv_value - prev_obv)

    # A/D line
    ad_value = Decimal("0")
    for bar in bars:
        if bar.high == bar.low:
            mfm = Decimal("0")
        else:
            mfm = ((bar.close - bar.low) - (bar.high - bar.close)) / (bar.high - bar.low)
        ad_value += mfm * Decimal(bar.volume)

    # MFI (14-period)
    mfi = None
    mfi_signal = "INSUFFICIENT_DATA"
    if len(bars) >= 15:
        typical_prices = [
            (b.high + b.low + b.close) / Decimal("3") for b in bars
        ]
        raw_money_flow = [tp * Decimal(b.volume) for tp, b in zip(typical_prices, bars)]

        positive_flow = Decimal("0")
        negative_flow = Decimal("0")

        for i in range(len(bars) - 14, len(bars)):
            if typical_prices[i] > typical_prices[i - 1]:
                positive_flow += raw_money_flow[i]
            elif typical_prices[i] < typical_prices[i - 1]:
                negative_flow += raw_money_flow[i]

        if negative_flow > 0:
            mfr = positive_flow / negative_flow
            mfi = _quantize(Decimal("100") - (Decimal("100") / (Decimal("1") + mfr)))
            mfi_signal = _mfi_signal(mfi)

    # Price-volume divergence (simple: price up + volume down or vice versa)
    divergence = "NONE"
    if len(bars) >= 5:
        price_trend = bars[-1].close - bars[-5].close
        vol_trend = Decimal(bars[-1].volume) - Decimal(bars[-5].volume)
        if price_trend > 0 and vol_trend < 0:
            divergence = "BEARISH_DIVERGENCE"
        elif price_trend < 0 and vol_trend > 0:
            divergence = "BULLISH_DIVERGENCE"

    direction = "NEUTRAL"
    if divergence == "BULLISH_DIVERGENCE":
        direction = "POSITIVE"
    elif divergence == "BEARISH_DIVERGENCE":
        direction = "NEGATIVE"

    explanation = f"OBV={obv_value}. A/D={ad_value}. "
    if mfi is not None:
        explanation += f"MFI={mfi}. "
    if divergence != "NONE":
        explanation += f"Price-volume: {divergence}. "

    return VolumeIndicators(
        obv=str(obv_value),
        obv_change=str(obv_change) if obv_change is not None else None,
        accumulation_distribution=str(ad_value),
        mfi_14=mfi,
        mfi_signal=mfi_signal,
        price_volume_divergence=divergence,
        direction=direction,
        explanation=explanation,
    )


def _compute_momentum(closes: Sequence[Decimal]) -> MomentumResult:
    def _roc(period: int) -> Decimal | None:
        if len(closes) <= period:
            return None
        return _quantize(_pct_change(closes[-1], closes[-period - 1]))

    roc5 = _roc(5)
    roc10 = _roc(10)
    roc20 = _roc(20)

    direction = "NEUTRAL"
    if roc20 is not None:
        direction = "POSITIVE" if roc20 > 0 else "NEGATIVE" if roc20 < 0 else "NEUTRAL"

    explanation = "Momentum: "
    if roc5 is not None:
        explanation += f"ROC(5)={roc5}%. "
    if roc10 is not None:
        explanation += f"ROC(10)={roc10}%. "
    if roc20 is not None:
        explanation += f"ROC(20)={roc20}%. "

    return MomentumResult(
        roc_5=roc5,
        roc_10=roc10,
        roc_20=roc20,
        momentum_direction=direction,
        explanation=explanation,
    )


def _compute_adx(bars: Sequence[PriceBar], period: int = 14) -> ADXResult:
    if len(bars) < period * 2:
        return ADXResult()

    plus_dm: list[Decimal] = []
    minus_dm: list[Decimal] = []
    true_ranges: list[Decimal] = []

    for i in range(1, len(bars)):
        high_diff = bars[i].high - bars[i - 1].high
        low_diff = bars[i - 1].low - bars[i].low

        plus_dm.append(max(high_diff, Decimal("0")) if high_diff > low_diff else Decimal("0"))
        minus_dm.append(max(low_diff, Decimal("0")) if low_diff > high_diff else Decimal("0"))
        true_ranges.append(_true_range(bars[i], bars[i - 1].close))

    if len(true_ranges) < period:
        return ADXResult()

    atr = sum(true_ranges[:period]) / Decimal(period)
    smooth_plus = sum(plus_dm[:period]) / Decimal(period)
    smooth_minus = sum(minus_dm[:period]) / Decimal(period)

    dx_values: list[Decimal] = []

    for i in range(period, len(true_ranges)):
        atr = (atr * (Decimal(period) - Decimal("1")) + true_ranges[i]) / Decimal(period)
        smooth_plus = (smooth_plus * (Decimal(period) - Decimal("1")) + plus_dm[i]) / Decimal(period)
        smooth_minus = (smooth_minus * (Decimal(period) - Decimal("1")) + minus_dm[i]) / Decimal(period)

        if atr > 0:
            plus_di = (smooth_plus / atr) * Decimal("100")
            minus_di = (smooth_minus / atr) * Decimal("100")
        else:
            plus_di = Decimal("0")
            minus_di = Decimal("0")

        di_sum = plus_di + minus_di
        if di_sum > 0:
            dx = (abs(plus_di - minus_di) / di_sum) * Decimal("100")
        else:
            dx = Decimal("0")

        dx_values.append((dx, plus_di, minus_di))

    if not dx_values:
        return ADXResult()

    adx = sum(d[0] for d in dx_values[:period]) / Decimal(period)
    for i in range(period, len(dx_values)):
        adx = (adx * (Decimal(period) - Decimal("1")) + dx_values[i][0]) / Decimal(period)

    latest_plus_di = dx_values[-1][1]
    latest_minus_di = dx_values[-1][2]

    adx = _quantize(adx)
    signal = _adx_signal(adx)

    direction = "POSITIVE" if latest_plus_di > latest_minus_di else "NEGATIVE"

    explanation = f"ADX({period})={adx}, +DI={_quantize(latest_plus_di)}, -DI={_quantize(latest_minus_di)}. "
    if signal == "STRONG_TREND":
        explanation += "Strong directional trend. "
    elif signal == "WEAK_TREND":
        explanation += "Weak/no directional trend. "

    return ADXResult(
        adx_14=adx,
        plus_di=_quantize(latest_plus_di),
        minus_di=_quantize(latest_minus_di),
        signal=signal,
        direction=direction,
        explanation=explanation,
    )


def _compute_cci(bars: Sequence[PriceBar], period: int = 20) -> CCIResult:
    if len(bars) < period:
        return CCIResult()

    typical_prices = [
        (b.high + b.low + b.close) / Decimal("3") for b in bars
    ]

    window = typical_prices[-period:]
    sma_tp = sum(window) / Decimal(period)
    mean_dev = sum(abs(tp - sma_tp) for tp in window) / Decimal(period)

    if mean_dev == 0:
        return CCIResult()

    cci = (typical_prices[-1] - sma_tp) / (Decimal("0.01") * mean_dev)
    cci = _quantize(cci)
    signal = _cci_signal(cci)
    direction = _direction_from_value(cci)

    explanation = f"CCI({period})={cci}. "
    if signal == "OVERBOUGHT":
        explanation += "Above overbought threshold (>=100). "
    elif signal == "OVERSOLD":
        explanation += "Below oversold threshold (<=-100). "

    return CCIResult(
        cci_20=cci,
        signal=signal,
        direction=direction,
        explanation=explanation,
    )


def _compute_pivots(bar: PriceBar) -> PivotResult:
    pivot = (bar.high + bar.low + bar.close) / Decimal("3")
    r1 = Decimal("2") * pivot - bar.low
    r2 = pivot + (bar.high - bar.low)
    r3 = bar.high + Decimal("2") * (pivot - bar.low)
    s1 = Decimal("2") * pivot - bar.high
    s2 = pivot - (bar.high - bar.low)
    s3 = bar.low - Decimal("2") * (bar.high - pivot)

    return PivotResult(
        pivot=_quantize(pivot),
        r1=_quantize(r1),
        r2=_quantize(r2),
        r3=_quantize(r3),
        s1=_quantize(s1),
        s2=_quantize(s2),
        s3=_quantize(s3),
        explanation=f"Pivot={_quantize(pivot)}, R1={_quantize(r1)}, S1={_quantize(s1)}.",
    )


def _compute_breakout(
    bars: Sequence[PriceBar],
    atr: Decimal | None,
    lookback: int = 20,
) -> BreakoutResult:
    if len(bars) < lookback + 1:
        return BreakoutResult()

    window = bars[-(lookback + 1) : -1]
    upper = max(b.high for b in window)
    lower = min(b.low for b in window)

    latest = bars[-1]
    breakout_upper = latest.close > upper
    breakout_lower = latest.close < lower

    # ATR-based breakout
    atr_breakout = "NONE"
    if atr is not None and atr > 0:
        threshold = atr * _ATR_BREAKOUT_MULTIPLIER
        if len(bars) >= 2:
            bar_range = latest.high - latest.low
            if bar_range > threshold:
                atr_breakout = "RANGE_EXPANSION"

    signal = "INSUFFICIENT_DATA"
    direction = "NEUTRAL"
    explanation = ""

    if breakout_upper:
        signal = "BREAKOUT_UPPER"
        direction = "POSITIVE"
        explanation = f"Price broke above {lookback}-day high ({upper}). "
    elif breakout_lower:
        signal = "BREAKDOWN_LOWER"
        direction = "NEGATIVE"
        explanation = f"Price broke below {lookback}-day low ({lower}). "
    else:
        signal = "NO_BREAKOUT"
        explanation = f"Within {lookback}-day range ({lower} to {upper}). "

    if atr_breakout != "NONE":
        explanation += "ATR range expansion detected. "

    return BreakoutResult(
        breakout_upper=breakout_upper,
        breakout_lower=breakout_lower,
        atr_breakout=atr_breakout,
        signal=signal,
        direction=direction,
        explanation=explanation,
    )


def _compute_gaps(bars: Sequence[PriceBar]) -> GapResult:
    if len(bars) < 2:
        return GapResult()

    prev_close = bars[-2].close
    curr_open = bars[-1].open

    if prev_close <= 0:
        return GapResult()

    gap_pct = _quantize(_pct_change(curr_open, prev_close))

    if abs(gap_pct) < _GAP_THRESHOLD_PCT:
        return GapResult(
            gap_type="NO_GAP",
            gap_pct=gap_pct,
            signal="NO_GAP",
            direction="NEUTRAL",
            explanation=f"Open vs previous close: {gap_pct}% (below {_GAP_THRESHOLD_PCT}% threshold).",
        )

    if curr_open > prev_close:
        gap_type = "GAP_UP"
        direction = "POSITIVE"
    else:
        gap_type = "GAP_DOWN"
        direction = "NEGATIVE"

    return GapResult(
        gap_type=gap_type,
        gap_pct=gap_pct,
        signal="GAP_DETECTED",
        direction=direction,
        explanation=f"{gap_type}: open={curr_open} vs prev close={prev_close} ({gap_pct}%).",
    )


def _compute_high_low(
    bars: Sequence[PriceBar],
    lookback: int = 252,
) -> HighLowResult:
    if not bars:
        return HighLowResult()

    window = bars[-min(lookback, len(bars)) :]
    high_52w = max(b.high for b in window)
    low_52w = min(b.low for b in window)
    latest_close = bars[-1].close

    pct_from_high = _quantize(_pct_change(latest_close, high_52w)) if high_52w > 0 else None
    pct_from_low = _quantize(_pct_change(latest_close, low_52w)) if low_52w > 0 else None

    at_high = latest_close >= high_52w
    at_low = latest_close <= low_52w

    signal = "NEAR_52W_HIGH" if pct_from_high is not None and abs(pct_from_high) < _PROXIMITY_52W_PCT else \
             "NEAR_52W_LOW" if pct_from_low is not None and abs(pct_from_low) < _PROXIMITY_52W_PCT else \
             "AT_52W_HIGH" if at_high else "AT_52W_LOW" if at_low else "MID_RANGE"

    direction = "POSITIVE" if at_high or (pct_from_high is not None and abs(pct_from_high) < _PROXIMITY_52W_PCT) else \
                "NEGATIVE" if at_low or (pct_from_low is not None and abs(pct_from_low) < _PROXIMITY_52W_PCT) else "NEUTRAL"

    explanation = f"52-week: high={high_52w}, low={low_52w}. "
    if pct_from_high is not None:
        explanation += f"{pct_from_high}% from high. "

    return HighLowResult(
        high_52w=high_52w,
        low_52w=low_52w,
        pct_from_high=pct_from_high,
        pct_from_low=pct_from_low,
        at_52w_high=at_high,
        at_52w_low=at_low,
        signal=signal,
        direction=direction,
        explanation=explanation,
    )


def _compute_drawdowns(closes: Sequence[Decimal]) -> DrawdownResult:
    def _max_dd(window: list[Decimal]) -> Decimal | None:
        if not window:
            return None
        peak = window[0]
        max_dd = Decimal("0")
        for c in window:
            if c > peak:
                peak = c
            dd = ((c - peak) / peak) * Decimal("100") if peak > 0 else Decimal("0")
            if dd < max_dd:
                max_dd = dd
        return _quantize(max_dd)

    if not closes:
        return DrawdownResult()

    peak = max(closes)
    current_dd = _quantize(
        ((closes[-1] - peak) / peak) * Decimal("100")
    ) if peak > 0 else None

    recovery = None
    if current_dd is not None:
        recovery = _quantize(max(Decimal("0"), Decimal("100") + current_dd))

    return DrawdownResult(
        current_drawdown=current_dd,
        max_drawdown_20d=_max_dd(closes[-20:]) if len(closes) >= 5 else None,
        max_drawdown_50d=_max_dd(closes[-50:]) if len(closes) >= 10 else None,
        max_drawdown_200d=_max_dd(closes[-200:]) if len(closes) >= 20 else None,
        recovery_pct=recovery,
        explanation=f"Current drawdown={current_dd}%. Recovery={recovery}%.",
    )


def _compute_benchmark_correlation(
    stock_closes: Sequence[Decimal],
    benchmark_closes: Sequence[Decimal],
    period: int = 20,
) -> BenchmarkCorrelation:
    """Compute correlation and beta between stock and benchmark."""
    min_len = min(len(stock_closes), len(benchmark_closes))

    def _corr(p: int) -> tuple[Decimal | None, Decimal | None]:
        if min_len < p + 1:
            return None, None

        stock_ret = [
            _pct_change(stock_closes[i], stock_closes[i - 1])
            for i in range(-p, 0)
            if stock_closes[i - 1] > 0
        ]
        bench_ret = [
            _pct_change(benchmark_closes[i], benchmark_closes[i - 1])
            for i in range(-p, 0)
            if benchmark_closes[i - 1] > 0
        ]

        n = min(len(stock_ret), len(bench_ret))
        if n < 2:
            return None, None

        sr = stock_ret[-n:]
        br = bench_ret[-n:]

        mean_s = sum(sr) / Decimal(n)
        mean_b = sum(br) / Decimal(n)

        cov = sum((sr[i] - mean_s) * (br[i] - mean_b) for i in range(n)) / Decimal(n - 1)
        std_s = (sum((r - mean_s) ** 2 for r in sr) / Decimal(n - 1)).sqrt()
        std_b = (sum((r - mean_b) ** 2 for r in br) / Decimal(n - 1)).sqrt()

        if std_s == 0 or std_b == 0:
            return None, None

        corr = cov / (std_s * std_b)
        beta = cov / (std_b ** 2) if std_b > 0 else None

        return _quantize(corr), _quantize(beta) if beta is not None else None

    corr20, beta20 = _corr(20)
    corr50, beta50 = _corr(50)

    direction = "NEUTRAL"
    if beta20 is not None:
        direction = "POSITIVE" if beta20 > 1 else "NEGATIVE" if beta20 < 1 else "NEUTRAL"

    explanation = ""
    if corr20 is not None:
        explanation = f"Correlation(20d)={corr20}, Beta(20d)={beta20}. "
    if corr50 is not None:
        explanation += f"Correlation(50d)={corr50}, Beta(50d)={beta50}."

    return BenchmarkCorrelation(
        correlation_20d=corr20,
        correlation_50d=corr50,
        beta_20d=beta20,
        beta_50d=beta50,
        direction=direction,
        explanation=explanation,
    )


def _compute_trend_structure(
    closes: Sequence[Decimal],
    sma_set: SMASeries,
    ema_set: EMASet,
) -> TrendStructure:
    if not closes:
        return TrendStructure()

    close = closes[-1]

    above_count = 0
    below_count = 0

    for sma_val in [sma_set.sma_5, sma_set.sma_10, sma_set.sma_20, sma_set.sma_50, sma_set.sma_100, sma_set.sma_200]:
        if sma_val is not None:
            if close > sma_val:
                above_count += 1
            else:
                below_count += 1

    # SMA alignment
    sma_vals = [sma_set.sma_5, sma_set.sma_10, sma_set.sma_20, sma_set.sma_50, sma_set.sma_100, sma_set.sma_200]
    sma_vals = [v for v in sma_vals if v is not None]
    if len(sma_vals) >= 2:
        if all(sma_vals[i] >= sma_vals[i + 1] for i in range(len(sma_vals) - 1)):
            sma_alignment = "BULLISH"
        elif all(sma_vals[i] <= sma_vals[i + 1] for i in range(len(sma_vals) - 1)):
            sma_alignment = "BEARISH"
        else:
            sma_alignment = "MIXED"
    else:
        sma_alignment = "INSUFFICIENT_DATA"

    # EMA alignment
    ema_vals = [ema_set.ema_9, ema_set.ema_12, ema_set.ema_20, ema_set.ema_26, ema_set.ema_50, ema_set.ema_200]
    ema_vals = [v for v in ema_vals if v is not None]
    if len(ema_vals) >= 2:
        if all(ema_vals[i] >= ema_vals[i + 1] for i in range(len(ema_vals) - 1)):
            ema_alignment = "BULLISH"
        elif all(ema_vals[i] <= ema_vals[i + 1] for i in range(len(ema_vals) - 1)):
            ema_alignment = "BEARISH"
        else:
            ema_alignment = "MIXED"
    else:
        ema_alignment = "INSUFFICIENT_DATA"

    # Regime
    if above_count == 6:
        regime = "STRONG_BULL"
    elif above_count >= 4:
        regime = "BULL"
    elif below_count == 6:
        regime = "STRONG_BEAR"
    elif below_count >= 4:
        regime = "BEAR"
    else:
        regime = "MIXED"

    # Trend strength (0-1)
    total = above_count + below_count
    trend_strength = _quantize(Decimal(above_count) / Decimal(total)) if total > 0 else None

    explanation = f"Regime={regime}. Price above {above_count}/6 SMAs. "
    explanation += f"SMA alignment={sma_alignment}, EMA alignment={ema_alignment}."

    return TrendStructure(
        regime=regime,
        trend_strength=trend_strength,
        above_sma_count=above_count,
        below_sma_count=below_count,
        sma_alignment=sma_alignment,
        ema_alignment=ema_alignment,
        explanation=explanation,
    )


def compute_technical_indicators(
    bars: Sequence[PriceBar],
    benchmark_bars: Sequence[PriceBar] | None = None,
) -> TechnicalIndicatorResult:
    """
    Compute the full suite of technical indicators.

    Input must be ordered oldest -> newest.
    All calculations are PIT-safe.
    """
    if not bars:
        return TechnicalIndicatorResult(symbol="", trading_date="")

    ordered = list(bars)
    closes = [bar.close for bar in ordered]
    latest = ordered[-1]

    result = TechnicalIndicatorResult(
        symbol=latest.symbol,
        trading_date=str(latest.trading_date),
        bars_used=len(ordered),
    )

    # Multi-horizon returns
    def _ret(p: int) -> Decimal | None:
        if len(closes) <= p:
            return None
        return _quantize(_pct_change(closes[-1], closes[-p - 1]))

    result = TechnicalIndicatorResult(
        symbol=latest.symbol,
        trading_date=str(latest.trading_date),
        bars_used=len(ordered),
        return_1d=_ret(1),
        return_5d=_ret(5),
        return_10d=_ret(10),
        return_20d=_ret(20),
        return_50d=_ret(50),
        return_100d=_ret(100),
        return_200d=_ret(200),
    )

    # SMAs
    sma_set = _compute_sma_set(closes)
    price_vs_sma = _compute_price_vs_sma(latest.close, sma_set)

    # EMAs
    ema_set = _compute_ema_set(closes)
    price_vs_ema = _compute_price_vs_ema(latest.close, ema_set)

    # RSI
    rsi = _compute_rsi(closes)

    # MACD
    macd = _compute_macd(closes)

    # Stochastic
    stochastic = _compute_stochastic(ordered)

    # Williams %R
    williams_r = _compute_williams_r(ordered)

    # ATR
    atr_result = _compute_atr(ordered)

    # Bollinger
    bollinger = _compute_bollinger(closes)

    # Volume indicators
    volume_ind = _compute_volume_indicators(ordered)

    # Momentum
    momentum = _compute_momentum(closes)

    # ADX
    adx = _compute_adx(ordered)

    # CCI
    cci = _compute_cci(ordered)

    # Pivots
    pivots = _compute_pivots(latest)

    # Breakout
    breakout = _compute_breakout(ordered, atr_result.atr_14)

    # Gaps
    gaps = _compute_gaps(ordered)

    # 52-week high/low
    high_low = _compute_high_low(ordered)

    # Drawdowns
    drawdowns = _compute_drawdowns(closes)

    # Trend structure
    trend_structure = _compute_trend_structure(closes, sma_set, ema_set)

    # Benchmark correlation
    benchmark_corr = BenchmarkCorrelation()
    if benchmark_bars and len(benchmark_bars) > 1:
        bench_closes = [b.close for b in benchmark_bars]
        benchmark_corr = _compute_benchmark_correlation(closes, bench_closes)

    return TechnicalIndicatorResult(
        symbol=latest.symbol,
        trading_date=str(latest.trading_date),
        bars_used=len(ordered),
        return_1d=_ret(1),
        return_5d=_ret(5),
        return_10d=_ret(10),
        return_20d=_ret(20),
        return_50d=_ret(50),
        return_100d=_ret(100),
        return_200d=_ret(200),
        sma=sma_set,
        price_vs_sma=price_vs_sma,
        ema=ema_set,
        price_vs_ema=price_vs_ema,
        rsi=rsi,
        macd=macd,
        stochastic=stochastic,
        williams_r=williams_r,
        momentum=momentum,
        atr=atr_result,
        bollinger=bollinger,
        volume_indicators=volume_ind,
        adx=adx,
        cci=cci,
        pivots=pivots,
        breakout=breakout,
        gaps=gaps,
        high_low=high_low,
        drawdowns=drawdowns,
        trend_structure=trend_structure,
    )
