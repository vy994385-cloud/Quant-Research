from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from src.data.models import PriceBar


@dataclass(frozen=True)
class MarketStructure:
    """
    Describes the current market structure using information available
    at the latest supplied observation.

    This module does not predict future returns.
    """

    symbol: str
    trading_date: object

    price_vs_sma_5_pct: Decimal | None
    price_vs_sma_20_pct: Decimal | None

    sma_5_vs_sma_20_pct: Decimal | None

    momentum_acceleration: Decimal | None

    trend_persistence: Decimal | None

    volume_confirmation: Decimal | None

    recovery_from_drawdown_pct: Decimal | None

    regime: str


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

    symbols = {bar.symbol for bar in ordered}

    if len(symbols) != 1:
        raise ValueError(
            "Market structure requires bars for one symbol only"
        )

    for bar in ordered:
        if not bar.is_valid_ohlc:
            raise ValueError(
                f"Invalid OHLC data for {bar.symbol} "
                f"on {bar.trading_date}"
            )

    return ordered


def _sma(
    values: Sequence[Decimal],
    period: int,
) -> Decimal | None:
    if len(values) < period:
        return None

    return sum(values[-period:]) / Decimal(period)


def _percentage_difference(
    current: Decimal,
    reference: Decimal,
) -> Decimal:
    if reference <= 0:
        raise ValueError(
            "Reference value must be greater than zero"
        )

    return (
        (current - reference)
        / reference
    ) * Decimal("100")


def _trend_persistence(
    closes: Sequence[Decimal],
) -> Decimal | None:
    """
    Percentage of recent daily observations that moved in the same
    direction as the overall move.

    Returns 0-100.

    A value near 100 means the recent move was persistent.
    A value near 50 means the path was mixed.
    """

    if len(closes) < 2:
        return None

    changes = [
        current - previous
        for previous, current in zip(
            closes[-20:],
            closes[-19:],
        )
    ]

    if not changes:
        return None

    # The changes were calculated from the latest window.
    # Determine the corresponding starting close safely.
    window_start = max(0, len(closes) - 20)
    window_closes = closes[window_start:]

    if len(window_closes) < 2:
        return None

    overall_change = (
        window_closes[-1] - window_closes[0]
    )

    if overall_change > 0:
        favorable = sum(
            change > 0
            for change in changes
        )
    elif overall_change < 0:
        favorable = sum(
            change < 0
            for change in changes
        )
    else:
        favorable = sum(
            change == 0
            for change in changes
        )

    return (
        Decimal(favorable)
        / Decimal(len(changes))
    ) * Decimal("100")


def _regime(
    price_vs_sma_5: Decimal | None,
    price_vs_sma_20: Decimal | None,
    sma_5_vs_sma_20: Decimal | None,
) -> str:
    """
    Classify observed trend structure.

    This is descriptive, not predictive.
    """

    if (
        price_vs_sma_5 is None
        or price_vs_sma_20 is None
        or sma_5_vs_sma_20 is None
    ):
        return "INSUFFICIENT_DATA"

    if (
        price_vs_sma_5 > 0
        and price_vs_sma_20 > 0
        and sma_5_vs_sma_20 > 0
    ):
        return "BULLISH"

    if (
        price_vs_sma_5 < 0
        and price_vs_sma_20 < 0
        and sma_5_vs_sma_20 < 0
    ):
        return "BEARISH"

    return "MIXED"


def calculate_market_structure(
    bars: Sequence[PriceBar],
) -> MarketStructure:
    """
    Calculate market-structure features for the latest bar.

    Input must be ordered oldest -> newest.
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

    sma_5 = _sma(closes, 5)
    sma_20 = _sma(closes, 20)

    price_vs_sma_5_pct = None
    price_vs_sma_20_pct = None
    sma_5_vs_sma_20_pct = None

    if sma_5 is not None:
        price_vs_sma_5_pct = _percentage_difference(
            latest.close,
            sma_5,
        )

    if sma_20 is not None:
        price_vs_sma_20_pct = _percentage_difference(
            latest.close,
            sma_20,
        )

    if (
        sma_5 is not None
        and sma_20 is not None
    ):
        sma_5_vs_sma_20_pct = _percentage_difference(
            sma_5,
            sma_20,
        )

    momentum_acceleration = None

    if len(closes) >= 21:
        current_20d = _percentage_difference(
            closes[-1],
            closes[-21],
        )

        previous_20d = _percentage_difference(
            closes[-2],
            closes[-22],
        )

        momentum_acceleration = (
            current_20d - previous_20d
        )

    persistence = _trend_persistence(closes)

    volume_confirmation = None

    if len(volumes) >= 20:
        average_volume = _sma(
            volumes,
            20,
        )

        if average_volume is not None and average_volume > 0:
            volume_confirmation = (
                Decimal(latest.volume)
                / average_volume
            )

    recovery_from_drawdown_pct = None

    if len(closes) >= 20:
        window = closes[-20:]
        peak = max(window)

        if peak > 0:
            drawdown = (
                (latest.close - peak)
                / peak
            ) * Decimal("100")

            recovery_from_drawdown_pct = max(
                Decimal("0"),
                Decimal("100") + drawdown,
            )

    regime = _regime(
        price_vs_sma_5_pct,
        price_vs_sma_20_pct,
        sma_5_vs_sma_20_pct,
    )

    return MarketStructure(
        symbol=latest.symbol,
        trading_date=latest.trading_date,
        price_vs_sma_5_pct=price_vs_sma_5_pct,
        price_vs_sma_20_pct=price_vs_sma_20_pct,
        sma_5_vs_sma_20_pct=sma_5_vs_sma_20_pct,
        momentum_acceleration=momentum_acceleration,
        trend_persistence=persistence,
        volume_confirmation=volume_confirmation,
        recovery_from_drawdown_pct=recovery_from_drawdown_pct,
        regime=regime,
    )
