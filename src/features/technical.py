from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from src.data.models import PriceBar


@dataclass(frozen=True)
class TechnicalFeatures:
    """
    Deterministic technical features calculated only from historical
    OHLCV observations available up to the current bar.
    """

    symbol: str
    trading_date: object

    return_1d: Decimal | None
    return_5d: Decimal | None
    return_20d: Decimal | None

    sma_5: Decimal | None
    sma_20: Decimal | None

    momentum: Decimal | None
    volatility_20d: Decimal | None

    average_volume_20d: Decimal | None
    volume_ratio: Decimal | None

    drawdown_20d: Decimal | None


def _validate_bars(
    bars: Sequence[PriceBar],
) -> list[PriceBar]:
    if not bars:
        raise ValueError("At least one price bar is required")

    ordered = list(bars)

    for previous, current in zip(
        ordered,
        ordered[1:],
    ):
        if current.trading_date <= previous.trading_date:
            raise ValueError(
                "Price bars must be strictly ordered by trading_date"
            )

    for bar in ordered:
        if not bar.is_valid_ohlc:
            raise ValueError(
                f"Invalid OHLC data for {bar.symbol} "
                f"on {bar.trading_date}"
            )

    symbols = {bar.symbol for bar in ordered}

    if len(symbols) != 1:
        raise ValueError(
            "Technical features require bars for one symbol only"
        )

    return ordered


def _percentage_change(
    current: Decimal,
    previous: Decimal,
) -> Decimal:
    if previous <= 0:
        raise ValueError(
            "Previous price must be greater than zero"
        )

    return (
        (current - previous)
        / previous
    ) * Decimal("100")


def _sma(
    values: Sequence[Decimal],
    period: int,
) -> Decimal | None:
    if len(values) < period:
        return None

    window = values[-period:]

    return sum(window) / Decimal(period)


def _returns(
    closes: Sequence[Decimal],
    period: int,
) -> Decimal | None:
    if len(closes) <= period:
        return None

    return _percentage_change(
        closes[-1],
        closes[-period - 1],
    )


def _sample_std(
    values: Sequence[Decimal],
) -> Decimal | None:
    if len(values) < 2:
        return None

    mean = sum(values) / Decimal(len(values))

    variance = sum(
        (value - mean) ** 2
        for value in values
    ) / Decimal(len(values) - 1)

    # Decimal does not expose sqrt in every Python version through
    # the same convenient interface, so use the Decimal sqrt method.
    return variance.sqrt()


def calculate_technical_features(
    bars: Sequence[PriceBar],
) -> TechnicalFeatures:
    """
    Calculate technical features for the latest supplied bar.

    No future observations are accessed.

    The input must be ordered oldest -> newest.
    """

    ordered = _validate_bars(bars)

    closes = [
        bar.close
        for bar in ordered
    ]

    volumes = [
        Decimal(bar.volume)
        for bar in ordered
    ]

    latest = ordered[-1]

    return_1d = _returns(closes, 1)
    return_5d = _returns(closes, 5)
    return_20d = _returns(closes, 20)

    sma_5 = _sma(closes, 5)
    sma_20 = _sma(closes, 20)

    momentum = return_20d

    daily_returns: list[Decimal] = []

    for previous, current in zip(
        closes,
        closes[1:],
    ):
        daily_returns.append(
            _percentage_change(
                current,
                previous,
            )
        )

    volatility_window = daily_returns[-20:]

    volatility_20d = _sample_std(
        volatility_window
    )

    average_volume_20d = _sma(
        volumes,
        20,
    )

    volume_ratio = None

    if (
        average_volume_20d is not None
        and average_volume_20d > 0
    ):
        volume_ratio = (
            Decimal(latest.volume)
            / average_volume_20d
        )

    drawdown_20d = None

    if len(closes) >= 20:
        window = closes[-20:]
        peak = max(window)

        if peak > 0:
            drawdown_20d = (
                (latest.close - peak)
                / peak
            ) * Decimal("100")

    return TechnicalFeatures(
        symbol=latest.symbol,
        trading_date=latest.trading_date,
        return_1d=return_1d,
        return_5d=return_5d,
        return_20d=return_20d,
        sma_5=sma_5,
        sma_20=sma_20,
        momentum=momentum,
        volatility_20d=volatility_20d,
        average_volume_20d=average_volume_20d,
        volume_ratio=volume_ratio,
        drawdown_20d=drawdown_20d,
    )
