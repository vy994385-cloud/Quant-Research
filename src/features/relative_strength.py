from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

from src.data.models import PriceBar


@dataclass(frozen=True)
class RelativeStrength:
    """
    Measures a security's historical performance relative to a
    benchmark over the same observation dates.

    This is descriptive. It does not predict future returns.
    """

    symbol: str
    benchmark_symbol: str
    trading_date: date

    stock_return_1d: Decimal | None
    benchmark_return_1d: Decimal | None
    relative_return_1d: Decimal | None

    stock_return_5d: Decimal | None
    benchmark_return_5d: Decimal | None
    relative_return_5d: Decimal | None

    stock_return_20d: Decimal | None
    benchmark_return_20d: Decimal | None
    relative_return_20d: Decimal | None

    relative_momentum: Decimal | None


def _validate_series(
    bars: Sequence[PriceBar],
    name: str,
) -> list[PriceBar]:
    if not bars:
        raise ValueError(
            f"{name} price series cannot be empty"
        )

    ordered = list(bars)

    for previous, current in zip(
        ordered,
        ordered[1:],
    ):
        if current.trading_date <= previous.trading_date:
            raise ValueError(
                f"{name} price bars must be strictly "
                "ordered by trading_date"
            )

    for bar in ordered:
        if not bar.is_valid_ohlc:
            raise ValueError(
                f"Invalid OHLC data for {bar.symbol} "
                f"on {bar.trading_date}"
            )

    return ordered


def _returns(
    closes: Sequence[Decimal],
    period: int,
) -> Decimal | None:
    if len(closes) <= period:
        return None

    previous = closes[-period - 1]
    current = closes[-1]

    if previous <= 0:
        raise ValueError(
            "Previous closing price must be greater than zero"
        )

    return (
        (current - previous)
        / previous
    ) * Decimal("100")


def _relative(
    stock_return: Decimal | None,
    benchmark_return: Decimal | None,
) -> Decimal | None:
    if (
        stock_return is None
        or benchmark_return is None
    ):
        return None

    return stock_return - benchmark_return


def _align_dates(
    stock_bars: Sequence[PriceBar],
    benchmark_bars: Sequence[PriceBar],
) -> tuple[list[PriceBar], list[PriceBar]]:
    """
    Align both series to their common trading dates.

    We deliberately use exact date intersections instead of assuming
    that the two markets have identical calendars.
    """

    benchmark_by_date = {
        bar.trading_date: bar
        for bar in benchmark_bars
    }

    stock_aligned = []
    benchmark_aligned = []

    for stock_bar in stock_bars:
        benchmark_bar = benchmark_by_date.get(
            stock_bar.trading_date
        )

        if benchmark_bar is None:
            continue

        stock_aligned.append(stock_bar)
        benchmark_aligned.append(benchmark_bar)

    if not stock_aligned:
        raise ValueError(
            "Stock and benchmark have no common trading dates"
        )

    return stock_aligned, benchmark_aligned


def calculate_relative_strength(
    stock_bars: Sequence[PriceBar],
    benchmark_bars: Sequence[PriceBar],
) -> RelativeStrength:
    """
    Calculate historical relative strength for the latest common
    observation date.

    The two input series may have different trading calendars.

    Only observations available on or before the latest common date
    are used.
    """

    stock = _validate_series(
        stock_bars,
        "Stock",
    )

    benchmark = _validate_series(
        benchmark_bars,
        "Benchmark",
    )

    stock, benchmark = _align_dates(
        stock,
        benchmark,
    )

    if stock[-1].trading_date != benchmark[-1].trading_date:
        raise ValueError(
            "Aligned series must end on the same date"
        )

    stock_closes = [
        bar.close
        for bar in stock
    ]

    benchmark_closes = [
        bar.close
        for bar in benchmark
    ]

    stock_return_1d = _returns(
        stock_closes,
        1,
    )
    benchmark_return_1d = _returns(
        benchmark_closes,
        1,
    )

    stock_return_5d = _returns(
        stock_closes,
        5,
    )
    benchmark_return_5d = _returns(
        benchmark_closes,
        5,
    )

    stock_return_20d = _returns(
        stock_closes,
        20,
    )
    benchmark_return_20d = _returns(
        benchmark_closes,
        20,
    )

    relative_return_1d = _relative(
        stock_return_1d,
        benchmark_return_1d,
    )

    relative_return_5d = _relative(
        stock_return_5d,
        benchmark_return_5d,
    )

    relative_return_20d = _relative(
        stock_return_20d,
        benchmark_return_20d,
    )

    relative_momentum = None

    if (
        relative_return_5d is not None
        and relative_return_20d is not None
    ):
        relative_momentum = (
            relative_return_5d
            + relative_return_20d
        ) / Decimal("2")

    return RelativeStrength(
        symbol=stock[-1].symbol,
        benchmark_symbol=benchmark[-1].symbol,
        trading_date=stock[-1].trading_date,
        stock_return_1d=stock_return_1d,
        benchmark_return_1d=benchmark_return_1d,
        relative_return_1d=relative_return_1d,
        stock_return_5d=stock_return_5d,
        benchmark_return_5d=benchmark_return_5d,
        relative_return_5d=relative_return_5d,
        stock_return_20d=stock_return_20d,
        benchmark_return_20d=benchmark_return_20d,
        relative_return_20d=relative_return_20d,
        relative_momentum=relative_momentum,
    )
