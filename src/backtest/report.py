from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.backtest.benchmark import BenchmarkResult
from src.backtest.metrics import (
    BacktestMetrics,
    calculate_backtest_metrics,
)
from src.backtest.models import BacktestResult


@dataclass(frozen=True)
class BacktestReport:
    """
    Human-readable research summary of a completed backtest.

    This report describes historical strategy behaviour only.

    It does not predict future returns and does not produce
    a live BUY/SELL instruction.

    Benchmark information is optional and, when present,
    describes historical relative performance.
    """

    initial_capital: Decimal
    final_equity: Decimal
    profit_loss: Decimal
    total_return: Decimal

    trade_count: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal

    average_winning_trade: Decimal
    average_losing_trade: Decimal
    profit_factor: Decimal | None

    max_drawdown: Decimal
    max_drawdown_percent: Decimal

    exposure_percent: Decimal
    cagr: Decimal | None

    sample_size_warning: str | None

    research_signal: str
    limitations: tuple[str, ...]

    benchmark: BenchmarkResult | None = None

    @property
    def is_profitable(self) -> bool:
        return self.profit_loss > Decimal("0")

    @property
    def has_drawdown(self) -> bool:
        return self.max_drawdown > Decimal("0")

    @property
    def has_sufficient_trade_sample(self) -> bool:
        return self.trade_count >= 30

    @property
    def is_trade_signal(self) -> bool:
        """
        Explicitly prevents the report from being interpreted
        as an execution instruction.
        """
        return False

    @property
    def has_benchmark(self) -> bool:
        return self.benchmark is not None

    @property
    def outperformed_benchmark(self) -> bool | None:
        """
        Return historical benchmark-relative performance.

        None means no benchmark was supplied.
        """
        if self.benchmark is None:
            return None

        return self.benchmark.outperforming


def _sample_warning(
    metrics: BacktestMetrics,
) -> str | None:
    if metrics.trade_count == 0:
        return "No completed trades were available for evaluation."

    if metrics.trade_count < 10:
        return (
            "Very small trade sample. Historical performance "
            "statistics may be unstable."
        )

    if metrics.trade_count < 30:
        return (
            "Small trade sample. Results should not be treated "
            "as statistically reliable without further validation."
        )

    return None


def _research_signal(
    metrics: BacktestMetrics,
) -> str:
    """
    Classify the historical result descriptively.

    This is deliberately conservative and is NOT a prediction.
    """

    if metrics.trade_count == 0:
        return "INSUFFICIENT_DATA"

    if metrics.total_return <= Decimal("0"):
        return "HISTORICALLY_NEGATIVE"

    if metrics.max_drawdown_percent >= Decimal("30"):
        return "HIGH_DRAWDOWN"

    if metrics.trade_count < 10:
        return "INSUFFICIENT_SAMPLE"

    if metrics.total_return > Decimal("0"):
        return "HISTORICALLY_POSITIVE"

    return "NEUTRAL"


def build_backtest_report(
    result: BacktestResult,
    benchmark: BenchmarkResult | None = None,
) -> BacktestReport:
    """
    Build a structured research report from a completed backtest.

    All strategy calculations are delegated to the existing
    metrics layer.

    Benchmark calculations are performed by the benchmark layer
    and only attached here for reporting.
    """

    metrics = calculate_backtest_metrics(result)

    limitations = (
        "Historical backtest results do not guarantee future performance.",
        "Transaction costs and execution assumptions may differ from live markets.",
        "The quality of the result depends on the quality and completeness of historical data.",
        "Signals must be generated only from information available at the corresponding historical date.",
        "Out-of-sample and walk-forward validation are required before paper or live trading.",
    )

    return BacktestReport(
        initial_capital=result.initial_capital,
        final_equity=result.final_equity,
        profit_loss=metrics.profit_loss,
        total_return=metrics.total_return,
        trade_count=metrics.trade_count,
        winning_trades=metrics.winning_trades,
        losing_trades=metrics.losing_trades,
        win_rate=metrics.win_rate,
        average_winning_trade=metrics.average_winning_trade,
        average_losing_trade=metrics.average_losing_trade,
        profit_factor=metrics.profit_factor,
        max_drawdown=metrics.max_drawdown,
        max_drawdown_percent=metrics.max_drawdown_percent,
        exposure_percent=metrics.exposure_percent,
        cagr=metrics.cagr,
        sample_size_warning=_sample_warning(metrics),
        research_signal=_research_signal(metrics),
        limitations=limitations,
        benchmark=benchmark,
    )
