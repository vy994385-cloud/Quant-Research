from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from src.backtest.models import BacktestBar, BacktestResult


@dataclass(frozen=True)
class BenchmarkResult:
    """
    Historical buy-and-hold benchmark comparison.

    The benchmark uses the first and last available closing prices
    from the supplied historical bars.

    This is a research comparison only. It does not generate
    trading or investment instructions.
    """

    benchmark_symbol: str

    initial_value: Decimal
    final_value: Decimal

    benchmark_return: Decimal
    strategy_return: Decimal
    excess_return: Decimal

    benchmark_max_drawdown: Decimal
    benchmark_max_drawdown_percent: Decimal

    strategy_max_drawdown: Decimal
    strategy_max_drawdown_percent: Decimal

    outperforming: bool


def _validate_bars(
    bars: Sequence[BacktestBar],
) -> list[BacktestBar]:
    """
    Validate benchmark observations.

    Bars must be non-empty and strictly ordered by date.
    """

    if not bars:
        raise ValueError("benchmark bars cannot be empty")

    ordered = list(bars)

    for previous, current in zip(
        ordered,
        ordered[1:],
    ):
        if current.trading_date <= previous.trading_date:
            raise ValueError(
                "benchmark bars must be strictly ordered by "
                "trading_date"
            )

    symbols = {
        bar.symbol
        for bar in ordered
    }

    if len(symbols) != 1:
        raise ValueError(
            "benchmark bars must contain exactly one symbol"
        )

    return ordered


def _calculate_benchmark_drawdown(
    bars: Sequence[BacktestBar],
) -> tuple[Decimal, Decimal]:
    """
    Calculate maximum drawdown of a buy-and-hold benchmark.

    The benchmark is normalized to 1.0 at the first observation.
    """

    if not bars:
        return Decimal("0"), Decimal("0")

    first_price = bars[0].close

    if first_price <= Decimal("0"):
        raise ValueError(
            "benchmark starting price must be greater than zero"
        )

    peak_value = Decimal("1")

    max_drawdown = Decimal("0")
    max_drawdown_percent = Decimal("0")

    for bar in bars:
        normalized_value = (
            bar.close / first_price
        )

        if normalized_value > peak_value:
            peak_value = normalized_value

        drawdown = (
            peak_value - normalized_value
        )

        if drawdown > max_drawdown:
            max_drawdown = drawdown

        if peak_value > Decimal("0"):
            drawdown_percent = (
                drawdown / peak_value
            ) * Decimal("100")

            if drawdown_percent > max_drawdown_percent:
                max_drawdown_percent = drawdown_percent

    return (
        max_drawdown,
        max_drawdown_percent,
    )


def calculate_benchmark_result(
    result: BacktestResult,
    benchmark_bars: Sequence[BacktestBar],
) -> BenchmarkResult:
    """
    Compare a completed strategy backtest against a
    buy-and-hold benchmark over the same historical observations.

    The benchmark receives the same initial capital as the strategy.

    Benchmark return:

        final benchmark price / initial benchmark price - 1

    Excess return:

        strategy return - benchmark return
    """

    if result.initial_capital <= Decimal("0"):
        raise ValueError(
            "backtest initial capital must be greater than zero"
        )

    ordered = _validate_bars(benchmark_bars)

    benchmark_symbol = ordered[0].symbol

    first_price = ordered[0].close
    final_price = ordered[-1].close

    if first_price <= Decimal("0"):
        raise ValueError(
            "benchmark starting price must be greater than zero"
        )

    benchmark_return = (
        (
            final_price / first_price
        ) - Decimal("1")
    ) * Decimal("100")

    initial_value = result.initial_capital

    final_value = (
        initial_value
        * (
            final_price / first_price
        )
    )

    strategy_return = result.return_percent

    excess_return = (
        strategy_return
        - benchmark_return
    )

    (
        benchmark_max_drawdown_normalized,
        benchmark_max_drawdown_percent,
    ) = _calculate_benchmark_drawdown(
        ordered
    )

    benchmark_max_drawdown = (
        initial_value
        * benchmark_max_drawdown_normalized
    )

    from src.backtest.metrics import calculate_max_drawdown

    (
        strategy_max_drawdown,
        strategy_max_drawdown_percent,
    ) = calculate_max_drawdown(result)

    return BenchmarkResult(
        benchmark_symbol=benchmark_symbol,
        initial_value=initial_value,
        final_value=final_value,
        benchmark_return=benchmark_return,
        strategy_return=strategy_return,
        excess_return=excess_return,
        benchmark_max_drawdown=benchmark_max_drawdown,
        benchmark_max_drawdown_percent=(
            benchmark_max_drawdown_percent
        ),
        strategy_max_drawdown=strategy_max_drawdown,
        strategy_max_drawdown_percent=(
            strategy_max_drawdown_percent
        ),
        outperforming=excess_return > Decimal("0"),
    )
