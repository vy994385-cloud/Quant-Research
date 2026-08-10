from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from itertools import product
from typing import Callable, Mapping, Sequence

from src.backtest.models import BacktestBar
from src.backtest.runner import BacktestRunner
from src.backtest.strategy import BacktestStrategy
from src.backtest.strategy_spec import (
    ParameterRange,
    ParameterSet,
)


@dataclass(frozen=True)
class OptimizationResult:
    """
    Result of a deterministic in-sample parameter search.

    This object describes the best historical configuration found
    on the supplied training data.

    It must never be interpreted as an out-of-sample result.
    """

    best_parameters: ParameterSet
    best_run_return: Decimal
    best_run_profit_loss: Decimal
    combinations_tested: int

    @property
    def is_profitable(self) -> bool:
        return self.best_run_profit_loss > Decimal("0")


class GridSearchOptimizer:
    """
    Deterministic exhaustive parameter search.

    Every parameter combination is evaluated independently.

    The optimizer is intentionally simple and transparent. More
    advanced optimizers can later be added behind the same interface.
    """

    def __init__(
        self,
        parameter_ranges: Mapping[
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
        objective: Callable[
            [Decimal, Decimal],
            Decimal,
        ]
        | None = None,
    ) -> None:
        if not parameter_ranges:
            raise ValueError(
                "parameter_ranges cannot be empty"
            )

        self.parameter_ranges = dict(
            parameter_ranges
        )

        self.strategy_factory = strategy_factory
        self.initial_capital = initial_capital
        self.allocation = allocation
        self.transaction_cost_rate = (
            transaction_cost_rate
        )
        self.minimum_bars = minimum_bars
        self.minimum_trades = minimum_trades

        self.objective = (
            objective
            if objective is not None
            else self._default_objective
        )

    @staticmethod
    def _default_objective(
        total_return: Decimal,
        profit_loss: Decimal,
    ) -> Decimal:
        """
        Default optimization objective.

        Total historical return is maximized.
        """
        return total_return

    def _parameter_sets(
        self,
    ) -> tuple[ParameterSet, ...]:
        names = tuple(
            self.parameter_ranges.keys()
        )

        value_lists = tuple(
            self.parameter_ranges[name].values()
            for name in names
        )

        return tuple(
            ParameterSet(
                dict(
                    zip(
                        names,
                        values,
                    )
                )
            )
            for values in product(
                *value_lists
            )
        )

    def optimize(
        self,
        bars: Sequence[BacktestBar],
    ) -> OptimizationResult:
        if not bars:
            raise ValueError(
                "bars cannot be empty"
            )

        parameter_sets = self._parameter_sets()

        if not parameter_sets:
            raise ValueError(
                "parameter search produced no combinations"
            )

        best_parameters: ParameterSet | None = None
        best_score: Decimal | None = None
        best_return = Decimal("0")
        best_profit_loss = Decimal("0")

        for parameters in parameter_sets:
            strategy = self.strategy_factory(
                parameters
            )

            runner = BacktestRunner(
                self.initial_capital,
                allocation=self.allocation,
                transaction_cost_rate=(
                    self.transaction_cost_rate
                ),
                minimum_bars=self.minimum_bars,
                minimum_trades=self.minimum_trades,
            )

            run = runner.run_strategy(
                bars,
                strategy,
            )

            score = self.objective(
                run.metrics.total_return,
                run.metrics.profit_loss,
            )

            if (
                best_score is None
                or score > best_score
            ):
                best_score = score
                best_parameters = parameters
                best_return = (
                    run.metrics.total_return
                )
                best_profit_loss = (
                    run.metrics.profit_loss
                )

        assert best_parameters is not None

        return OptimizationResult(
            best_parameters=best_parameters,
            best_run_return=best_return,
            best_run_profit_loss=best_profit_loss,
            combinations_tested=len(
                parameter_sets
            ),
        )
