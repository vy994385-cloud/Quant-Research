from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Sequence

from src.backtest.models import BacktestBar
from src.backtest.optimization import (
    GridSearchOptimizer,
    OptimizationResult,
)
from src.backtest.strategy import (
    BacktestStrategy,
)
from src.backtest.strategy_spec import (
    ParameterRange,
    ParameterSet,
)


@dataclass(frozen=True)
class TrainingResult:
    """
    Result of fitting a strategy on a historical training set.

    This result represents in-sample research only.

    It must never be presented as out-of-sample performance.
    """

    parameters: ParameterSet
    in_sample_return: Decimal
    in_sample_profit_loss: Decimal
    combinations_tested: int

    @property
    def is_profitable(self) -> bool:
        return (
            self.in_sample_profit_loss
            > Decimal("0")
        )


class StrategyTrainer:
    """
    Deterministic strategy trainer.

    The trainer searches parameter space using only the
    supplied training observations.
    """

    def __init__(
        self,
        parameter_ranges: dict[
            str,
            ParameterRange,
        ],
        strategy_factory: Callable[
            [ParameterSet],
            BacktestStrategy,
        ],
        *,
        initial_capital: Decimal,
        allocation: Decimal = Decimal("1"),
        transaction_cost_rate: Decimal = Decimal("0"),
        minimum_bars: int = 1,
        minimum_trades: int = 0,
    ) -> None:
        self.optimizer = GridSearchOptimizer(
            parameter_ranges,
            strategy_factory,
            initial_capital=initial_capital,
            allocation=allocation,
            transaction_cost_rate=transaction_cost_rate,
            minimum_bars=minimum_bars,
            minimum_trades=minimum_trades,
        )

    def fit(
        self,
        train_bars: Sequence[BacktestBar],
    ) -> TrainingResult:
        if not train_bars:
            raise ValueError(
                "train_bars cannot be empty"
            )

        result: OptimizationResult = (
            self.optimizer.optimize(train_bars)
        )

        return TrainingResult(
            parameters=result.best_parameters,
            in_sample_return=result.best_run_return,
            in_sample_profit_loss=(
                result.best_run_profit_loss
            ),
            combinations_tested=(
                result.combinations_tested
            ),
        )
