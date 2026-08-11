from __future__ import annotations

from dataclasses import dataclass
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

    volatility_20d: float | None = None

    volume: float | None = None
    volume_ratio_20d: float | None = None

    drawdown_20d: float | None = None

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
            "volatility_20d",
            "volume",
            "volume_ratio_20d",
            "drawdown_20d",
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

    for index, bar in enumerate(ordered):

        close = float(bar.close)

        volume = (
            float(bar.volume)
            if bar.volume is not None
            else None
        )

        # --------------------------------------------------
        # Point-in-time returns
        # --------------------------------------------------

        return_1d = None

        if index >= 1:
            return_1d = _return(
                close,
                closes[index - 1],
            )

        return_5d = None

        if index >= 5:
            return_5d = _return(
                close,
                closes[index - 5],
            )

        return_20d = None

        if index >= 20:
            return_20d = _return(
                close,
                closes[index - 20],
            )

        # --------------------------------------------------
        # 20-session volatility
        #
        # At index T:
        #
        # returns are:
        # T-19 -> T-18
        # ...
        # T-1  -> T
        #
        # Exactly 20 daily returns.
        # --------------------------------------------------

        volatility_20d = None

        if index >= 20:

            daily_returns = [
                _return(
                    closes[position],
                    closes[position - 1],
                )
                for position in range(
                    index - 19,
                    index,
                )
            ]

            daily_returns.append(
                _return(
                    close,
                    closes[index - 1],
                )
            )

            volatility_20d = _sample_std(
                daily_returns
            )

        # --------------------------------------------------
        # Volume ratio
        #
        # Current volume compared with the previous
        # 20 completed sessions.
        # --------------------------------------------------

        volume_ratio_20d = None

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

            average_volume = _mean(
                historical_volume
            )

            if average_volume != 0:
                volume_ratio_20d = (
                    volume / average_volume
                )

        # --------------------------------------------------
        # 20-session drawdown
        #
        # Includes the current observation.
        # --------------------------------------------------

        drawdown_20d = None

        if index >= 20:

            window = (
                closes[index - 20:index]
                + [close]
            )

            peak = max(window)

            if peak != 0:
                drawdown_20d = (
                    close / peak
                ) - 1.0

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
                volatility_20d=volatility_20d,
                volume=volume,
                volume_ratio_20d=volume_ratio_20d,
                drawdown_20d=drawdown_20d,
            )
        )

        # --------------------------------------------------
        # Only now expose the current observation to future
        # iterations.
        # --------------------------------------------------

        closes.append(close)
        volumes.append(volume)

    return observations