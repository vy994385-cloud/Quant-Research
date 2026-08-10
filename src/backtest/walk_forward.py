from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Sequence

from src.backtest.models import BacktestBar
from src.backtest.runner import BacktestRun, BacktestRunner

from src.backtest.strategy import (
    BacktestStrategy,
    TrainableBacktestStrategy,
)

@dataclass(frozen=True)
class WalkForwardWindow:
    """
    One chronological train/test window.

    The training period always occurs before the test period.
    """

    index: int
    train_bars: tuple[BacktestBar, ...]
    test_bars: tuple[BacktestBar,
     ...]

    @property
    def train_start(self):
        return self.train_bars[0].trading_date

    @property
    def train_end(self):
        return self.train_bars[-1].trading_date

    @property
    def test_start(self):
        return self.test_bars[0].trading_date

    @property
    def test_end(self):
        return self.test_bars[-1].trading_date


@dataclass(frozen=True)
class WalkForwardResult:
    """
    Complete out-of-sample walk-forward experiment.

    Results are evaluated only on test windows.

    This object is for historical research and validation only.
    It does not generate live trading instructions.
    """

    windows: tuple[BacktestRun, ...]
    initial_capital: Decimal

    @property
    def window_count(self) -> int:
        return len(self.windows)

    @property
    def profitable_windows(self) -> int:
        return sum(
            run.result.profit_loss > Decimal("0")
            for run in self.windows
        )

    @property
    def losing_windows(self) -> int:
        return sum(
            run.result.profit_loss < Decimal("0")
            for run in self.windows
        )

    @property
    def total_profit_loss(self) -> Decimal:
        return sum(
            (
                run.result.profit_loss
                for run in self.windows
            ),
            Decimal("0"),
        )

    @property
    def average_window_return(self) -> Decimal:
        if not self.windows:
            return Decimal("0")

        total = sum(
            (
                run.result.return_percent
                for run in self.windows
            ),
            Decimal("0"),
        )

        return total / Decimal(len(self.windows))

    @property
    def consistency_percent(self) -> Decimal:
        if not self.windows:
            return Decimal("0")

        return (
            Decimal(self.profitable_windows)
            / Decimal(self.window_count)
        ) * Decimal("100")

    @property
    def all_windows_valid(self) -> bool:
        return all(
            run.is_valid
            for run in self.windows
        )

    @property
    def requires_review(self) -> bool:
        return any(
            run.requires_review
            for run in self.windows
        )


def build_walk_forward_windows(
    bars: Sequence[BacktestBar],
    *,
    train_size: int,
    test_size: int,
    step_size: int | None = None,
) -> tuple[WalkForwardWindow, ...]:
    """
    Build chronological rolling train/test windows.

    Example:

        train_size = 60
        test_size = 20
        step_size = 20

        [train 60][test 20]
                 [train 60][test 20]
                          [train 60][test 20]

    No future observation can enter a training window.

    Bars must already be sorted chronologically.
    """

    ordered = list(bars)

    if not ordered:
        raise ValueError("bars cannot be empty")

    if train_size <= 0:
        raise ValueError(
            "train_size must be greater than zero"
        )

    if test_size <= 0:
        raise ValueError(
            "test_size must be greater than zero"
        )

    if step_size is None:
        step_size = test_size

    if step_size <= 0:
        raise ValueError(
            "step_size must be greater than zero"
        )

    for previous, current in zip(
        ordered,
        ordered[1:],
    ):
        if current.trading_date <= previous.trading_date:
            raise ValueError(
                "bars must be strictly ordered by trading_date"
            )

    windows: list[WalkForwardWindow] = []

    start = 0
    index = 0

    while (
        start + train_size + test_size
        <= len(ordered)
    ):
        train = tuple(
            ordered[
                start : start + train_size
            ]
        )

        test_start = start + train_size

        test = tuple(
            ordered[
                test_start : test_start + test_size
            ]
        )

        windows.append(
            WalkForwardWindow(
                index=index,
                train_bars=train,
                test_bars=test,
            )
        )

        start += step_size
        index += 1

    if not windows:
        raise ValueError(
            "insufficient bars for the requested "
            "train/test window sizes"
        )

    return tuple(windows)


def run_walk_forward(
    bars: Sequence[BacktestBar],
    strategy_factory: Callable[[], BacktestStrategy],
    *,
    initial_capital: Decimal,
    train_size: int,
    test_size: int,
    step_size: int | None = None,
    allocation: Decimal = Decimal("1"),
    transaction_cost_rate: Decimal = Decimal("0"),
    minimum_bars: int = 1,
    minimum_trades: int = 0,
) -> WalkForwardResult:
    """
    Execute a rolling out-of-sample historical experiment.

    A fresh strategy instance is created for every window.

    The current strategy interface is deterministic rather than
    trainable, so the train window is intentionally kept separate
    from the test window. This prevents test observations from being
    passed to signal generation.

    A future trainable strategy interface can later use the same
    window structure for fitting parameters exclusively on train_bars.
    """

    windows = build_walk_forward_windows(
        bars,
        train_size=train_size,
        test_size=test_size,
        step_size=step_size,
    )

    runs: list[BacktestRun] = []

    for window in windows:
        strategy = strategy_factory()

        runner = BacktestRunner(
            initial_capital,
            allocation=allocation,
            transaction_cost_rate=transaction_cost_rate,
            minimum_bars=minimum_bars,
            minimum_trades=minimum_trades,
        )

        # IMPORTANT:
        # The strategy is evaluated only against the test window.
        #
        # The train window remains isolated and is not supplied to
        # generate_signals. This prevents accidental look-ahead.
        run = runner.run_strategy(
            window.test_bars,
            strategy,
        )

        runs.append(run)

    return WalkForwardResult(
        windows=tuple(runs),
        initial_capital=initial_capital,
    )

def run_trainable_walk_forward(
    bars: Sequence[BacktestBar],
    strategy_factory: Callable[[], TrainableBacktestStrategy],
    *,
    initial_capital: Decimal,
    train_size: int,
    test_size: int,
    step_size: int | None = None,
    allocation: Decimal = Decimal("1"),
    transaction_cost_rate: Decimal = Decimal("0"),
    minimum_bars: int = 1,
    minimum_trades: int = 0,
) -> WalkForwardResult:
    """
    Execute genuine train -> fit -> test walk-forward validation.

    For every window:

        1. Create a fresh strategy.
        2. Fit only on train_bars.
        3. Freeze the fitted strategy.
        4. Generate signals only from test_bars.
        5. Execute the test signals.
        6. Store only the out-of-sample result.

    Test observations are never supplied to fit().
    """

    windows = build_walk_forward_windows(
        bars,
        train_size=train_size,
        test_size=test_size,
        step_size=step_size,
    )

    runs: list[BacktestRun] = []

    for window in windows:
        strategy = strategy_factory()

        strategy.fit(
            window.train_bars
        )

        runner = BacktestRunner(
            initial_capital,
            allocation=allocation,
            transaction_cost_rate=(
                transaction_cost_rate
            ),
            minimum_bars=minimum_bars,
            minimum_trades=minimum_trades,
        )

        run = runner.run_strategy(
            window.test_bars,
            strategy,
        )

        runs.append(run)

    return WalkForwardResult(
        windows=tuple(runs),
        initial_capital=initial_capital,
    )

def run_optimized_walk_forward(
    bars: Sequence[BacktestBar],
    parameter_ranges,
    strategy_factory,
    *,
    initial_capital: Decimal,
    train_size: int,
    test_size: int,
    step_size: int | None = None,
    allocation: Decimal = Decimal("1"),
    transaction_cost_rate: Decimal = Decimal("0"),
    minimum_bars: int = 1,
    minimum_trades: int = 0,
) -> WalkForwardResult:
    """
    Perform genuine walk-forward optimization.

    For each chronological window:

        TRAIN
          ↓
        optimize parameters
          ↓
        construct fresh strategy using best parameters
          ↓
        TEST
          ↓
        record only out-of-sample result

    Test observations never participate in optimization.
    """

    from src.backtest.training import StrategyTrainer

    windows = build_walk_forward_windows(
        bars,
        train_size=train_size,
        test_size=test_size,
        step_size=step_size,
    )

    runs: list[BacktestRun] = []

    for window in windows:
        trainer = StrategyTrainer(
            parameter_ranges,
            strategy_factory,
            initial_capital=initial_capital,
            allocation=allocation,
            transaction_cost_rate=transaction_cost_rate,
            minimum_bars=minimum_bars,
            minimum_trades=minimum_trades,
        )

        training_result = trainer.fit(
            window.train_bars
        )

        strategy = strategy_factory(
            training_result.parameters
        )

        runner = BacktestRunner(
            initial_capital,
            allocation=allocation,
            transaction_cost_rate=transaction_cost_rate,
            minimum_bars=minimum_bars,
            minimum_trades=minimum_trades,
        )

        run = runner.run_strategy(
            window.test_bars,
            strategy,
        )

        runs.append(run)

    return WalkForwardResult(
        windows=tuple(runs),
        initial_capital=initial_capital,
    )