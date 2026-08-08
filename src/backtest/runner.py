from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from src.backtest.engine import BacktestEngine
from src.backtest.metrics import BacktestMetrics, calculate_backtest_metrics
from src.backtest.models import (
    BacktestBar,
    BacktestResult,
    BacktestSignal,
)
from src.backtest.report import BacktestReport, build_backtest_report
from src.backtest.validation import (
    BacktestValidation,
    validate_backtest_inputs,
)


@dataclass(frozen=True)
class BacktestRun:
    """
    Complete output of one validated historical backtest.

    This object combines validation, execution, metrics, and
    research reporting into one deterministic result.

    It does not make live trading decisions.
    """

    result: BacktestResult
    metrics: BacktestMetrics
    report: BacktestReport
    validation: BacktestValidation

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

    Pipeline:

        validation
            ↓
        execution
            ↓
        metrics
            ↓
        report

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
    ) -> BacktestRun:
        """
        Run one complete historical experiment.

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

        metrics = calculate_backtest_metrics(
            result
        )

        report = build_backtest_report(
            result
        )

        return BacktestRun(
            result=result,
            metrics=metrics,
            report=report,
            validation=validation,
        )
