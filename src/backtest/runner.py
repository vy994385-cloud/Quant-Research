from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from src.backtest.benchmark import (
    BenchmarkResult,
    calculate_benchmark_result,
)
from src.backtest.engine import BacktestEngine
from src.backtest.metrics import (
    BacktestMetrics,
    calculate_backtest_metrics,
)
from src.backtest.models import (
    BacktestBar,
    BacktestResult,
    BacktestSignal,
)
from src.backtest.report import (
    BacktestReport,
    build_backtest_report,
)
from src.backtest.strategy import (
    BacktestStrategy,
    generate_strategy_signals,
)
from src.backtest.validation import (
    BacktestValidation,
    validate_backtest_inputs,
)


@dataclass(frozen=True)
class BacktestRun:
    """
    Complete output of one validated historical backtest.

    The benchmark comparison is optional and describes historical
    relative performance only.

    It does not make a live trading decision.
    """

    result: BacktestResult
    metrics: BacktestMetrics
    report: BacktestReport
    validation: BacktestValidation
    benchmark: BenchmarkResult | None = None

    @property
    def is_valid(self) -> bool:
        return not self.validation.is_rejected

    @property
    def requires_review(self) -> bool:
        return self.validation.needs_review

    @property
    def is_trade_signal(self) -> bool:
        return False


class BacktestRunner:
    """
    Orchestrates the complete historical backtest pipeline.

    Manual signal pipeline:

        signals
            ↓
        validation
            ↓
        execution
            ↓
        metrics
            ↓
        report
            ↓
        optional benchmark

    Strategy pipeline:

        bars
            ↓
        strategy
            ↓
        signals
            ↓
        validation
            ↓
        execution
            ↓
        metrics
            ↓
        report
            ↓
        optional benchmark

    The runner never converts a historical result into a live
    execution instruction.
    """

    def __init__(
        self,
        initial_capital: Decimal,
        *,
        allocation: Decimal = Decimal("1"),
        transaction_cost_rate: Decimal = Decimal("0"),
        minimum_bars: int = 30,
        minimum_trades: int = 10,
    ) -> None:
        self.engine = BacktestEngine(
            initial_capital,
            allocation=allocation,
            transaction_cost_rate=transaction_cost_rate,
        )

        self.minimum_bars = minimum_bars
        self.minimum_trades = minimum_trades

    def run(
        self,
        bars: Sequence[BacktestBar],
        signals: Sequence[BacktestSignal],
        *,
        benchmark_bars: Sequence[BacktestBar] | None = None,
    ) -> BacktestRun:
        """
        Run one complete historical experiment using
        precomputed signals.

        If benchmark_bars are supplied, the benchmark is calculated
        against the same initial capital as the strategy.

        REJECT:
            Validation errors stop execution.

        NEEDS_REVIEW:
            Warnings are preserved, but the historical experiment
            continues.

        ACCEPT:
            The experiment runs normally.
        """

        validation = validate_backtest_inputs(
            bars,
            signals,
            minimum_bars=self.minimum_bars,
            minimum_trades=self.minimum_trades,
        )

        if validation.is_rejected:
            raise ValueError(
                "Backtest validation failed: "
                + "; ".join(validation.errors)
            )

        result = self.engine.run(
            bars,
            signals,
        )

        return self._build_run(
            result,
            validation,
            benchmark_bars=benchmark_bars,
        )

    def run_strategy(
        self,
        bars: Sequence[BacktestBar],
        strategy: BacktestStrategy,
        *,
        benchmark_bars: Sequence[BacktestBar] | None = None,
    ) -> BacktestRun:
        """
        Run a complete historical experiment from a strategy.

        The strategy receives only the supplied historical bars.
        It generates historical signals, which are then passed
        through the same validation and execution pipeline used
        by the manual-signal API.

        Benchmark evaluation is optional and remains separate from
        strategy signal generation.
        """

        signals = generate_strategy_signals(
            strategy,
            bars,
        )

        return self.run(
            bars,
            signals,
            benchmark_bars=benchmark_bars,
        )

    def _build_run(
        self,
        result: BacktestResult,
        validation: BacktestValidation,
        *,
        benchmark_bars: Sequence[BacktestBar] | None = None,
    ) -> BacktestRun:
        """
        Build the common metrics/report output for both runner paths.
        """

        metrics = calculate_backtest_metrics(
            result
        )

        report = build_backtest_report(
            result
        )

        benchmark: BenchmarkResult | None = None

        if benchmark_bars is not None:
            benchmark = calculate_benchmark_result(
                result,
                benchmark_bars,
            )

        return BacktestRun(
            result=result,
            metrics=metrics,
            report=report,
            validation=validation,
            benchmark=benchmark,
        )
