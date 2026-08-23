"""
Typed research-observation model for technical analysis.

Converts indicator results into a unified observation format
with full provenance, PIT metadata, direction, severity, and
data-quality status.

Every observation is descriptive only -- it flags evidence worth
noting, not predictions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Sequence

from src.analysis.technical_indicators import (
    TechnicalIndicatorResult,
)


class TObservationDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class TObservationSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TObservationStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class TechnicalObservation:
    """
    A single technical research observation.

    Full provenance traceability.
    """

    observation_id: str
    symbol: str
    category: str
    observation_type: str

    period: str
    indicator: str
    value: str | None = None
    previous_value: str | None = None
    change: str | None = None

    signal: str = "INSUFFICIENT_DATA"
    direction: str = "NEUTRAL"
    severity: str = "LOW"

    calculation_method: str = ""
    source: str = "OHLCV"

    available_at: str | None = None
    as_of: str | None = None

    status: str = "AVAILABLE"

    explanation: str = ""
    related_indicators: tuple[str, ...] = ()
    supporting_data: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TechnicalObservationSet:
    """
    Complete set of technical observations for one symbol.
    """

    symbol: str
    as_of: str
    trading_date: str

    indicator_observations: tuple[TechnicalObservation, ...] = ()
    signal_observations: tuple[TechnicalObservation, ...] = ()

    total_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0

    available_indicators: tuple[str, ...] = ()
    missing_indicators: tuple[str, ...] = ()

    notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Builder: converts TechnicalIndicatorResult -> observations
# ---------------------------------------------------------------------------


def _obs_id(symbol: str, indicator: str, idx: int) -> str:
    return f"{symbol}-TECH-{indicator.upper()}-{idx:03d}"


def _build_return_observations(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    obs: list[TechnicalObservation] = []
    for period, value in [
        ("1d", result.return_1d),
        ("5d", result.return_5d),
        ("10d", result.return_10d),
        ("20d", result.return_20d),
        ("50d", result.return_50d),
        ("100d", result.return_100d),
        ("200d", result.return_200d),
    ]:
        if value is not None:
            direction = "POSITIVE" if value > 0 else "NEGATIVE" if value < 0 else "NEUTRAL"
            severity = "HIGH" if abs(value) > 10 else "MEDIUM" if abs(value) > 5 else "LOW"
            obs.append(TechnicalObservation(
                observation_id=_obs_id(result.symbol, f"return_{period}", idx),
                symbol=result.symbol,
                category="MOMENTUM",
                observation_type=f"return_{period}",
                period=period,
                indicator=f"return_{period}",
                value=str(value),
                signal=direction,
                direction=direction,
                severity=severity,
                explanation=f"{period} return: {value}%.",
            ))
    return obs


def _build_rsi_observation(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    if result.rsi.rsi_14 is None:
        return []
    severity = "HIGH" if result.rsi.signal in ("OVERBOUGHT", "OVERSOLD") else "LOW"
    return [TechnicalObservation(
        observation_id=_obs_id(result.symbol, "RSI_14", idx),
        symbol=result.symbol,
        category="MOMENTUM",
        observation_type="rsi",
        period="14",
        indicator="rsi_14",
        value=str(result.rsi.rsi_14),
        signal=result.rsi.signal,
        direction=result.rsi.direction,
        severity=severity,
        explanation=result.rsi.explanation,
    )]


def _build_macd_observation(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    if result.macd.macd_line is None:
        return []
    severity = "HIGH" if result.macd.macd_crossover != "NONE" else "MEDIUM"
    return [TechnicalObservation(
        observation_id=_obs_id(result.symbol, "MACD", idx),
        symbol=result.symbol,
        category="MOMENTUM",
        observation_type="macd",
        period="12/26/9",
        indicator="macd",
        value=str(result.macd.macd_line),
        signal=result.macd.signal_label,
        direction=result.macd.direction,
        severity=severity,
        explanation=result.macd.explanation,
        supporting_data={
            "signal_line": str(result.macd.signal_line) if result.macd.signal_line else None,
            "histogram": str(result.macd.histogram) if result.macd.histogram else None,
            "crossover": result.macd.macd_crossover,
        },
    )]


def _build_stochastic_observation(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    if result.stochastic.percent_k is None:
        return []
    severity = "HIGH" if result.stochastic.signal in ("OVERBOUGHT", "OVERSOLD") else "LOW"
    return [TechnicalObservation(
        observation_id=_obs_id(result.symbol, "STOCHASTIC", idx),
        symbol=result.symbol,
        category="MOMENTUM",
        observation_type="stochastic",
        period="14",
        indicator="stochastic",
        value=str(result.stochastic.percent_k),
        signal=result.stochastic.signal,
        direction=result.stochastic.direction,
        severity=severity,
        explanation=result.stochastic.explanation,
        supporting_data={
            "percent_d": str(result.stochastic.percent_d) if result.stochastic.percent_d else None,
            "crossover": result.stochastic.crossover,
        },
    )]


def _build_williams_observation(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    if result.williams_r.williams_r_14 is None:
        return []
    severity = "HIGH" if result.williams_r.signal in ("OVERBOUGHT", "OVERSOLD") else "LOW"
    return [TechnicalObservation(
        observation_id=_obs_id(result.symbol, "WILLIAMS_R", idx),
        symbol=result.symbol,
        category="MOMENTUM",
        observation_type="williams_r",
        period="14",
        indicator="williams_r",
        value=str(result.williams_r.williams_r_14),
        signal=result.williams_r.signal,
        direction=result.williams_r.direction,
        severity=severity,
        explanation=result.williams_r.explanation,
    )]


def _build_adx_observation(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    if result.adx.adx_14 is None:
        return []
    severity = "HIGH" if result.adx.signal == "STRONG_TREND" else "MEDIUM"
    return [TechnicalObservation(
        observation_id=_obs_id(result.symbol, "ADX", idx),
        symbol=result.symbol,
        category="TREND",
        observation_type="adx",
        period="14",
        indicator="adx_14",
        value=str(result.adx.adx_14),
        signal=result.adx.signal,
        direction=result.adx.direction,
        severity=severity,
        explanation=result.adx.explanation,
        supporting_data={
            "plus_di": str(result.adx.plus_di) if result.adx.plus_di else None,
            "minus_di": str(result.adx.minus_di) if result.adx.minus_di else None,
        },
    )]


def _build_cci_observation(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    if result.cci.cci_20 is None:
        return []
    severity = "HIGH" if result.cci.signal in ("OVERBOUGHT", "OVERSOLD") else "LOW"
    return [TechnicalObservation(
        observation_id=_obs_id(result.symbol, "CCI", idx),
        symbol=result.symbol,
        category="MOMENTUM",
        observation_type="cci",
        period="20",
        indicator="cci_20",
        value=str(result.cci.cci_20),
        signal=result.cci.signal,
        direction=result.cci.direction,
        severity=severity,
        explanation=result.cci.explanation,
    )]


def _build_bollinger_observation(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    if result.bollinger.upper is None:
        return []
    severity = "HIGH" if result.bollinger.signal in ("ABOVE_UPPER", "BELOW_LOWER") else "LOW"
    return [TechnicalObservation(
        observation_id=_obs_id(result.symbol, "BOLLINGER", idx),
        symbol=result.symbol,
        category="VOLATILITY",
        observation_type="bollinger",
        period="20",
        indicator="bollinger",
        value=str(result.bollinger.pct_b) if result.bollinger.pct_b else None,
        signal=result.bollinger.signal,
        direction=result.bollinger.direction,
        severity=severity,
        explanation=result.bollinger.explanation,
        supporting_data={
            "upper": str(result.bollinger.upper),
            "middle": str(result.bollinger.middle),
            "lower": str(result.bollinger.lower),
            "bandwidth": str(result.bollinger.bandwidth) if result.bollinger.bandwidth else None,
        },
    )]


def _build_volume_observation(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    obs: list[TechnicalObservation] = []
    vi = result.volume_indicators

    if vi.mfi_14 is not None:
        severity = "HIGH" if vi.mfi_signal in ("OVERBOUGHT", "OVERSOLD") else "LOW"
        obs.append(TechnicalObservation(
            observation_id=_obs_id(result.symbol, "MFI", idx),
            symbol=result.symbol,
            category="VOLUME",
            observation_type="mfi",
            period="14",
            indicator="mfi_14",
            value=str(vi.mfi_14),
            signal=vi.mfi_signal,
            direction=vi.direction,
            severity=severity,
            explanation=f"MFI(14)={vi.mfi_14}.",
        ))

    if vi.price_volume_divergence != "NONE":
        severity = "MEDIUM"
        obs.append(TechnicalObservation(
            observation_id=_obs_id(result.symbol, "PV_DIVERGENCE", idx),
            symbol=result.symbol,
            category="VOLUME",
            observation_type="price_volume_divergence",
            period="5d",
            indicator="price_volume_divergence",
            signal=vi.price_volume_divergence,
            direction=vi.direction,
            severity=severity,
            explanation=f"Price-volume: {vi.price_volume_divergence}.",
        ))

    return obs


def _build_atr_observation(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    if result.atr.atr_14 is None:
        return []
    return [TechnicalObservation(
        observation_id=_obs_id(result.symbol, "ATR", idx),
        symbol=result.symbol,
        category="VOLATILITY",
        observation_type="atr",
        period="14",
        indicator="atr_14",
        value=str(result.atr.atr_14),
        signal=result.atr.signal,
        direction="NEUTRAL",
        severity="LOW",
        explanation=result.atr.explanation,
        supporting_data={"atr_pct": str(result.atr.atr_pct) if result.atr.atr_pct else None},
    )]


def _build_breakout_observation(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    if result.breakout.signal == "INSUFFICIENT_DATA":
        return []
    severity = "HIGH" if result.breakout.signal in ("BREAKOUT_UPPER", "BREAKDOWN_LOWER") else "LOW"
    return [TechnicalObservation(
        observation_id=_obs_id(result.symbol, "BREAKOUT", idx),
        symbol=result.symbol,
        category="STRUCTURE",
        observation_type="breakout",
        period="20d",
        indicator="breakout",
        signal=result.breakout.signal,
        direction=result.breakout.direction,
        severity=severity,
        explanation=result.breakout.explanation,
    )]


def _build_gap_observation(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    if result.gaps.signal == "INSUFFICIENT_DATA" or result.gaps.gap_type == "NO_GAP":
        return []
    return [TechnicalObservation(
        observation_id=_obs_id(result.symbol, "GAP", idx),
        symbol=result.symbol,
        category="STRUCTURE",
        observation_type="gap",
        period="1d",
        indicator="gap",
        value=str(result.gaps.gap_pct) if result.gaps.gap_pct else None,
        signal=result.gaps.signal,
        direction=result.gaps.direction,
        severity="MEDIUM",
        explanation=result.gaps.explanation,
    )]


def _build_high_low_observation(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    hl = result.high_low
    if hl.pct_from_high is None:
        return []
    severity = "HIGH" if hl.signal in ("AT_52W_HIGH", "AT_52W_LOW") else "MEDIUM" if "NEAR" in hl.signal else "LOW"
    return [TechnicalObservation(
        observation_id=_obs_id(result.symbol, "HIGH_LOW", idx),
        symbol=result.symbol,
        category="STRUCTURE",
        observation_type="52w_high_low",
        period="252d",
        indicator="52w_high_low",
        signal=hl.signal,
        direction=hl.direction,
        severity=severity,
        explanation=hl.explanation,
        supporting_data={
            "high_52w": str(hl.high_52w) if hl.high_52w else None,
            "low_52w": str(hl.low_52w) if hl.low_52w else None,
            "pct_from_high": str(hl.pct_from_high) if hl.pct_from_high else None,
            "pct_from_low": str(hl.pct_from_low) if hl.pct_from_low else None,
        },
    )]


def _build_trend_structure_observation(
    result: TechnicalIndicatorResult,
    idx: int,
) -> list[TechnicalObservation]:
    ts = result.trend_structure
    if ts.regime == "INSUFFICIENT_DATA":
        return []
    severity = "HIGH" if ts.regime in ("STRONG_BULL", "STRONG_BEAR") else "MEDIUM"
    return [TechnicalObservation(
        observation_id=_obs_id(result.symbol, "TREND_REGIME", idx),
        symbol=result.symbol,
        category="TREND",
        observation_type="trend_structure",
        period="200d",
        indicator="trend_structure",
        signal=ts.regime,
        direction="POSITIVE" if "BULL" in ts.regime else "NEGATIVE" if "BEAR" in ts.regime else "NEUTRAL",
        severity=severity,
        explanation=ts.explanation,
        supporting_data={
            "sma_alignment": ts.sma_alignment,
            "ema_alignment": ts.ema_alignment,
            "above_sma_count": str(ts.above_sma_count),
            "below_sma_count": str(ts.below_sma_count),
        },
    )]


def build_technical_observations(
    result: TechnicalIndicatorResult,
    as_of: datetime,
) -> TechnicalObservationSet:
    """
    Build the complete observation set from indicator results.
    """
    idx = 0
    indicator_obs: list[TechnicalObservation] = []

    # Returns
    indicator_obs.extend(_build_return_observations(result, idx))
    idx += 1

    # RSI
    indicator_obs.extend(_build_rsi_observation(result, idx))
    idx += 1

    # MACD
    indicator_obs.extend(_build_macd_observation(result, idx))
    idx += 1

    # Stochastic
    indicator_obs.extend(_build_stochastic_observation(result, idx))
    idx += 1

    # Williams %R
    indicator_obs.extend(_build_williams_observation(result, idx))
    idx += 1

    # ADX
    indicator_obs.extend(_build_adx_observation(result, idx))
    idx += 1

    # CCI
    indicator_obs.extend(_build_cci_observation(result, idx))
    idx += 1

    # Bollinger
    indicator_obs.extend(_build_bollinger_observation(result, idx))
    idx += 1

    # Volume
    indicator_obs.extend(_build_volume_observation(result, idx))
    idx += 1

    # ATR
    indicator_obs.extend(_build_atr_observation(result, idx))
    idx += 1

    # Breakout
    indicator_obs.extend(_build_breakout_observation(result, idx))
    idx += 1

    # Gaps
    indicator_obs.extend(_build_gap_observation(result, idx))
    idx += 1

    # 52-week
    indicator_obs.extend(_build_high_low_observation(result, idx))
    idx += 1

    # Trend structure
    indicator_obs.extend(_build_trend_structure_observation(result, idx))
    idx += 1

    # Signal-level observations (composite)
    signal_obs: list[TechnicalObservation] = []

    # Trend signal
    if result.trend_structure.regime != "INSUFFICIENT_DATA":
        signal_obs.append(TechnicalObservation(
            observation_id=_obs_id(result.symbol, "TREND_SIGNAL", 0),
            symbol=result.symbol,
            category="SIGNAL",
            observation_type="composite_trend",
            period="composite",
            indicator="trend_structure",
            signal=result.trend_structure.regime,
            direction="POSITIVE" if "BULL" in result.trend_structure.regime else "NEGATIVE" if "BEAR" in result.trend_structure.regime else "NEUTRAL",
            severity="HIGH",
            explanation=f"Trend regime: {result.trend_structure.regime}.",
        ))

    # Momentum signal
    if result.rsi.rsi_14 is not None and result.macd.macd_line is not None:
        combined_signal = "NEUTRAL"
        if result.rsi.signal == "OVERBOUGHT" and result.macd.direction == "NEGATIVE":
            combined_signal = "BEARISH"
        elif result.rsi.signal == "OVERSOLD" and result.macd.direction == "POSITIVE":
            combined_signal = "BULLISH"

        if combined_signal != "NEUTRAL":
            signal_obs.append(TechnicalObservation(
                observation_id=_obs_id(result.symbol, "MOMENTUM_SIGNAL", 0),
                symbol=result.symbol,
                category="SIGNAL",
                observation_type="composite_momentum",
                period="composite",
                indicator="rsi+macd",
                signal=combined_signal,
                direction="NEGATIVE" if combined_signal == "BEARISH" else "POSITIVE",
                severity="HIGH",
                explanation=f"Combined RSI({result.rsi.rsi_14}) + MACD signal: {combined_signal}.",
            ))

    positive = sum(1 for o in indicator_obs if o.direction == "POSITIVE")
    negative = sum(1 for o in indicator_obs if o.direction == "NEGATIVE")
    neutral = len(indicator_obs) - positive - negative

    available = []
    missing = []
    for name in [
        "return_1d", "return_5d", "return_20d", "rsi", "macd",
        "stochastic", "williams_r", "adx", "cci", "bollinger",
        "mfi", "atr", "breakout", "gaps", "52w_high_low", "trend_structure",
    ]:
        has_value = any(
            o.indicator == name or name in o.observation_type
            for o in indicator_obs
        )
        if has_value:
            available.append(name)
        else:
            missing.append(name)

    return TechnicalObservationSet(
        symbol=result.symbol,
        as_of=as_of.isoformat(),
        trading_date=result.trading_date,
        indicator_observations=tuple(indicator_obs),
        signal_observations=tuple(signal_obs),
        total_count=len(indicator_obs) + len(signal_obs),
        positive_count=positive + sum(1 for o in signal_obs if o.direction == "POSITIVE"),
        negative_count=negative + sum(1 for o in signal_obs if o.direction == "NEGATIVE"),
        neutral_count=neutral + sum(1 for o in signal_obs if o.direction == "NEUTRAL"),
        available_indicators=tuple(available),
        missing_indicators=tuple(missing),
        notes=[],
    )
