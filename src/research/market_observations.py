from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from math import isfinite


@dataclass(frozen=True)
class MarketObservation:
    """
    Point-in-time market observation derived from validated
    historical price data.

    This is a research observation, not a trading signal.
    """

    symbol: str
    observation_date: date
    available_at: datetime

    close: float

    return_1d: float | None = None
    return_5d: float | None = None
    return_20d: float | None = None
    return_50d: float | None = None
    return_100d: float | None = None
    return_200d: float | None = None

    volatility_20d: float | None = None
    volatility_regime: str | None = None  # LOW, NORMAL, HIGH

    volume: float | None = None
    volume_ratio_20d: float | None = None
    abnormal_volume: bool = False

    drawdown_20d: float | None = None
    drawdown_50d: float | None = None

    # Trend regime
    trend_regime: str | None = None  # UPTREND, DOWNTREND, SIDEWAYS

    # Gap events
    gap_up: bool = False
    gap_down: bool = False
    gap_pct: float | None = None

    # Price-volume divergence
    price_volume_divergence: str | None = None  # CONVERGENT, DIVERGENT, NEUTRAL

    # Abnormal return events
    abnormal_return_1d: bool = False
    abnormal_return_5d: bool = False

    # 52-week context
    high_52w: float | None = None
    low_52w: float | None = None
    pct_from_52w_high: float | None = None
    pct_from_52w_low: float | None = None

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")

        if self.available_at.tzinfo is None:
            raise ValueError(
                "available_at must be timezone-aware"
            )

        if not isfinite(self.close):
            raise ValueError("close must be finite")

        for name in (
            "return_1d",
            "return_5d",
            "return_20d",
            "return_50d",
            "return_100d",
            "return_200d",
            "volatility_20d",
            "volume",
            "volume_ratio_20d",
            "drawdown_20d",
            "drawdown_50d",
            "gap_pct",
            "pct_from_52w_high",
            "pct_from_52w_low",
        ):
            value = getattr(self, name)

            if value is not None and not isfinite(value):
                raise ValueError(
                    f"{name} must be finite when provided"
                )

        object.__setattr__(
            self,
            "symbol",
            self.symbol.strip().upper(),
        )


def _return(
    current: float,
    previous: float,
) -> float:
    if previous == 0:
        raise ValueError(
            "cannot calculate return from zero price"
        )

    return current / previous - 1.0


def _mean(values: list[float]) -> float:
    if not values:
        raise ValueError(
            "cannot calculate mean from empty values"
        )

    return sum(values) / len(values)


def _sample_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0

    mean = _mean(values)

    variance = sum(
        (value - mean) ** 2
        for value in values
    ) / (len(values) - 1)

    return variance ** 0.5


def build_market_observations(
    *,
    symbol: str,
    bars,
    available_at: datetime,
) -> list[MarketObservation]:
    """
    Build deterministic point-in-time market observations.

    All rolling features use only information available at the
    current observation date.

    The function does not use future observations.
    """

    if available_at.tzinfo is None:
        raise ValueError(
            "available_at must be timezone-aware"
        )

    normalized_symbol = symbol.strip().upper()

    if not normalized_symbol:
        raise ValueError(
            "symbol cannot be empty"
        )

    ordered = sorted(
        bars,
        key=lambda bar: bar.trading_date,
    )

    observations: list[MarketObservation] = []

    closes: list[float] = []
    volumes: list[float | None] = []
    highs: list[float] = []
    lows: list[float] = []
    opens: list[float] = []

    # Thresholds for classification
    _VOLATILITY_HIGH = 0.03  # 3% daily std
    _VOLATILITY_LOW = 0.01  # 1% daily std
    _ABNORMAL_VOLUME_MULT = 2.0  # 2x average
    _ABNORMAL_RETURN_1D = 0.03  # 3% daily move
    _ABNORMAL_RETURN_5D = 0.05  # 5% weekly move
    _GAP_THRESHOLD = 0.01  # 1% gap

    for index, bar in enumerate(ordered):

        close = float(bar.close)
        high = float(bar.high) if bar.high else close
        low = float(bar.low) if bar.low else close
        opn = float(bar.open) if bar.open else close

        volume = (
            float(bar.volume)
            if bar.volume is not None
            else None
        )

        # --------------------------------------------------
        # Point-in-time returns (extended)
        # --------------------------------------------------

        return_1d = None
        if index >= 1:
            return_1d = _return(close, closes[index - 1])

        return_5d = None
        if index >= 5:
            return_5d = _return(close, closes[index - 5])

        return_20d = None
        if index >= 20:
            return_20d = _return(close, closes[index - 20])

        return_50d = None
        if index >= 50:
            return_50d = _return(close, closes[index - 50])

        return_100d = None
        if index >= 100:
            return_100d = _return(close, closes[index - 100])

        return_200d = None
        if index >= 200:
            return_200d = _return(close, closes[index - 200])

        # --------------------------------------------------
        # 20-session volatility
        # --------------------------------------------------

        volatility_20d = None
        if index >= 20:
            daily_returns = [
                _return(closes[position], closes[position - 1])
                for position in range(index - 19, index)
            ]
            daily_returns.append(_return(close, closes[index - 1]))
            volatility_20d = _sample_std(daily_returns)

        # --------------------------------------------------
        # Volatility regime classification
        # --------------------------------------------------

        volatility_regime = None
        if volatility_20d is not None:
            if volatility_20d >= _VOLATILITY_HIGH:
                volatility_regime = "HIGH"
            elif volatility_20d <= _VOLATILITY_LOW:
                volatility_regime = "LOW"
            else:
                volatility_regime = "NORMAL"

        # --------------------------------------------------
        # Volume ratio and abnormal volume detection
        # --------------------------------------------------

        volume_ratio_20d = None
        abnormal_volume = False

        if (
            volume is not None
            and index >= 20
            and all(
                item is not None
                for item in volumes[index - 20:index]
            )
        ):
            historical_volume = [
                item
                for item in volumes[index - 20:index]
                if item is not None
            ]
            average_volume = _mean(historical_volume)

            if average_volume != 0:
                volume_ratio_20d = volume / average_volume
                abnormal_volume = (
                    volume_ratio_20d >= _ABNORMAL_VOLUME_MULT
                )

        # --------------------------------------------------
        # Drawdown (20d and 50d)
        # --------------------------------------------------

        drawdown_20d = None
        if index >= 20:
            window = closes[index - 20:index] + [close]
            peak = max(window)
            if peak != 0:
                drawdown_20d = (close / peak) - 1.0

        drawdown_50d = None
        if index >= 50:
            window = closes[index - 50:index] + [close]
            peak = max(window)
            if peak != 0:
                drawdown_50d = (close / peak) - 1.0

        # --------------------------------------------------
        # Trend regime (SMA-based)
        # --------------------------------------------------

        trend_regime = None
        if index >= 50:
            sma_20 = _mean(closes[index - 19:index] + [close])
            sma_50 = _mean(closes[index - 49:index] + [close])

            if close > sma_20 > sma_50:
                trend_regime = "UPTREND"
            elif close < sma_20 < sma_50:
                trend_regime = "DOWNTREND"
            else:
                trend_regime = "SIDEWAYS"

        # --------------------------------------------------
        # Gap events
        # --------------------------------------------------

        gap_up = False
        gap_down = False
        gap_pct = None

        if index >= 1:
            prev_close = closes[index - 1]
            if prev_close != 0:
                gap_pct = (opn - prev_close) / prev_close
                if gap_pct >= _GAP_THRESHOLD:
                    gap_up = True
                elif gap_pct <= -_GAP_THRESHOLD:
                    gap_down = True

        # --------------------------------------------------
        # Price-volume divergence
        # --------------------------------------------------

        price_volume_divergence = None
        if index >= 5 and volume is not None:
            # Compare recent price trend with volume trend
            price_change_5d = _return(close, closes[index - 5])

            recent_volumes = [
                v for v in volumes[index - 5:index] if v is not None
            ]
            if len(recent_volumes) >= 3 and volume is not None:
                avg_recent_vol = _mean(recent_volumes)
                if avg_recent_vol != 0:
                    vol_change = volume / avg_recent_vol - 1.0

                    # Price up + volume up = convergent
                    # Price up + volume down = divergent
                    if price_change_5d > 0 and vol_change > 0:
                        price_volume_divergence = "CONVERGENT"
                    elif price_change_5d > 0 and vol_change < -0.2:
                        price_volume_divergence = "DIVERGENT"
                    elif price_change_5d < 0 and vol_change > 0:
                        price_volume_divergence = "CONVERGENT"
                    elif price_change_5d < 0 and vol_change < -0.2:
                        price_volume_divergence = "DIVERGENT"
                    else:
                        price_volume_divergence = "NEUTRAL"

        # --------------------------------------------------
        # Abnormal return events
        # --------------------------------------------------

        abnormal_return_1d = False
        if return_1d is not None:
            abnormal_return_1d = (
                abs(return_1d) >= _ABNORMAL_RETURN_1D
            )

        abnormal_return_5d = False
        if return_5d is not None:
            abnormal_return_5d = (
                abs(return_5d) >= _ABNORMAL_RETURN_5D
            )

        # --------------------------------------------------
        # 52-week context
        # --------------------------------------------------

        high_52w = None
        low_52w = None
        pct_from_52w_high = None
        pct_from_52w_low = None

        if index >= 250:  # ~1 trading year
            window_52w = highs[index - 250:index + 1]
            high_52w = max(window_52w)
            low_52w = min(
                l for l in lows[index - 250:index + 1]
                if l > 0
            )

            if high_52w != 0:
                pct_from_52w_high = (close / high_52w) - 1.0
            if low_52w != 0:
                pct_from_52w_low = (close / low_52w) - 1.0
        elif index >= 1:
            high_52w = max(highs[:index + 1])
            valid_lows = [l for l in lows[:index + 1] if l > 0]
            if valid_lows:
                low_52w = min(valid_lows)

            if high_52w != 0:
                pct_from_52w_high = (close / high_52w) - 1.0
            if low_52w and low_52w != 0:
                pct_from_52w_low = (close / low_52w) - 1.0

        # --------------------------------------------------
        # Build observation
        # --------------------------------------------------

        observations.append(
            MarketObservation(
                symbol=normalized_symbol,
                observation_date=bar.trading_date,
                available_at=available_at,
                close=close,
                return_1d=return_1d,
                return_5d=return_5d,
                return_20d=return_20d,
                return_50d=return_50d,
                return_100d=return_100d,
                return_200d=return_200d,
                volatility_20d=volatility_20d,
                volatility_regime=volatility_regime,
                volume=volume,
                volume_ratio_20d=volume_ratio_20d,
                abnormal_volume=abnormal_volume,
                drawdown_20d=drawdown_20d,
                drawdown_50d=drawdown_50d,
                trend_regime=trend_regime,
                gap_up=gap_up,
                gap_down=gap_down,
                gap_pct=gap_pct,
                price_volume_divergence=price_volume_divergence,
                abnormal_return_1d=abnormal_return_1d,
                abnormal_return_5d=abnormal_return_5d,
                high_52w=high_52w,
                low_52w=low_52w,
                pct_from_52w_high=pct_from_52w_high,
                pct_from_52w_low=pct_from_52w_low,
            )
        )

        # --------------------------------------------------
        # Only now expose the current observation to future
        # iterations.
        # --------------------------------------------------

        closes.append(close)
        volumes.append(volume)
        highs.append(high)
        lows.append(low)
        opens.append(opn)

    return observations