from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Sequence

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
    test_bars: tuple[BacktestBar, ...]

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

    @property
    def train_count(self) -> int:
        return len(self.train_bars)

    @property
    def test_count(self) -> int:
        return len(self.test_bars)


@dataclass(frozen=True)
class WalkForwardWindowMetadata:
    """
    Research metadata for one walk-forward window.

    This describes the information boundary around the experiment.
    It does not represent a trading instruction.
    """

    index: int

    train_start: Any
    train_end: Any
    test_start: Any
    test_end: Any

    train_observations: int
    test_observations: int

    parameters: Any = None
    combinations_tested: int | None = None

    @property
    def has_parameters(self) -> bool:
        return self.parameters is not None


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

    window_metadata: tuple[
        WalkForwardWindowMetadata,
        ...
    ] = ()

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
    def flat_windows(self) -> int:
        return sum(
            run.result.profit_loss == Decimal("0")
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
    def median_window_return(self) -> Decimal:
        if not self.windows:
            return Decimal("0")

        values = sorted(
            run.result.return_percent
            for run in self.windows
        )

        middle = len(values) // 2

        if len(values) % 2:
            return values[middle]

        return (
            values[middle - 1]
            + values[middle]
        ) / Decimal("2")

    @property
    def best_window_return(self) -> Decimal:
        if not self.windows:
            return Decimal("0")

        return max(
            run.result.return_percent
            for run in self.windows
        )

    @property
    def worst_window_return(self) -> Decimal:
        if not self.windows:
            return Decimal("0")

        return min(
            run.result.return_percent
            for run in self.windows
        )

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

    @property
    def total_test_observations(self) -> int:
        return sum(
            metadata.test_observations
            for metadata in self.window_metadata
        )

    @property
    def total_train_observations(self) -> int:
        return sum(
            metadata.train_observations
            for metadata in self.window_metadata
        )

    @property
    def profitable_window_ratio(self) -> Decimal:
        if not self.windows:
            return Decimal("0")

        return (
            Decimal(self.profitable_windows)
            / Decimal(self.window_count)
        )

    @property
    def parameterized_window_count(self) -> int:
        return sum(
            metadata.has_parameters
            for metadata in self.window_metadata
        )

    @property
    def parameter_stability_percent(self) -> Decimal:
        """
        Percentage of adjacent parameterized windows that selected
        exactly the same parameter set.

        A high value indicates parameter stability.

        A low value is a research warning, not automatically a failure.
        """

        parameterized = [
            metadata
            for metadata in self.window_metadata
            if metadata.has_parameters
        ]

        if len(parameterized) < 2:
            return Decimal("0")

        stable = 0
        comparisons = 0

        for previous, current in zip(
            parameterized,
            parameterized[1:],
        ):
            comparisons += 1

            if previous.parameters == current.parameters:
                stable += 1

        if comparisons == 0:
            return Decimal("0")

        return (
            Decimal(stable)
            / Decimal(comparisons)
        ) * Decimal("100")


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


def _metadata_for_window(
    window: WalkForwardWindow,
    *,
    parameters: Any = None,
    combinations_tested: int | None = None,
) -> WalkForwardWindowMetadata:
    """
    Build immutable research metadata for a window.
    """

    return WalkForwardWindowMetadata(
        index=window.index,
        train_start=window.train_start,
        train_end=window.train_end,
        test_start=window.test_start,
        test_end=window.test_end,
        train_observations=window.train_count,
        test_observations=window.test_count,
        parameters=parameters,
        combinations_tested=combinations_tested,
    )


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

    The deterministic strategy is evaluated only on test_bars.

    train_bars remain isolated so that future observations cannot
    accidentally enter signal generation.
    """

    windows = build_walk_forward_windows(
        bars,
        train_size=train_size,
        test_size=test_size,
        step_size=step_size,
    )

    runs: list[BacktestRun] = []
    metadata: list[WalkForwardWindowMetadata] = []

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
        # Only the test observations enter the strategy.
        #
        # The train observations are retained solely as the
        # chronological research boundary.
        run = runner.run_strategy(
            window.test_bars,
            strategy,
        )

        runs.append(run)

        metadata.append(
            _metadata_for_window(window)
        )

    return WalkForwardResult(
        windows=tuple(runs),
        initial_capital=initial_capital,
        window_metadata=tuple(metadata),
    )


def run_trainable_walk_forward(
    bars: Sequence[BacktestBar],
    strategy_factory: Callable[
        [],
        TrainableBacktestStrategy,
    ],
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
        3. Generate signals only from test_bars.
        4. Execute the test signals.
        5. Store only the out-of-sample result.

    Test observations are never supplied to fit().

    The fitted parameter state is captured in window_metadata when
    the strategy exposes a parameter-like state through the common
    buy_threshold/sell_threshold attributes.
    """

    windows = build_walk_forward_windows(
        bars,
        train_size=train_size,
        test_size=test_size,
        step_size=step_size,
    )

    runs: list[BacktestRun] = []
    metadata: list[WalkForwardWindowMetadata] = []

    for window in windows:
        strategy = strategy_factory()

        # HARD INFORMATION BOUNDARY:
        # fit() receives train_bars and nothing else.
        strategy.fit(window.train_bars)

        runner = BacktestRunner(
            initial_capital,
            allocation=allocation,
            transaction_cost_rate=transaction_cost_rate,
            minimum_bars=minimum_bars,
            minimum_trades=minimum_trades,
        )

        # HARD INFORMATION BOUNDARY:
        # test_bars are supplied only after fitting is complete.
        run = runner.run_strategy(
            window.test_bars,
            strategy,
        )

        runs.append(run)

        parameters = None

        if hasattr(strategy, "buy_threshold") and hasattr(
            strategy,
            "sell_threshold",
        ):
            parameters = {
                "buy_threshold": strategy.buy_threshold,
                "sell_threshold": strategy.sell_threshold,
            }

        metadata.append(
            _metadata_for_window(
                window,
                parameters=parameters,
            )
        )

    return WalkForwardResult(
        windows=tuple(runs),
        initial_capital=initial_capital,
        window_metadata=tuple(metadata),
    )
