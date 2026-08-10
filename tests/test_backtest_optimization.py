from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.backtest.models import BacktestBar
from src.backtest.optimization import (
    GridSearchOptimizer,
    OptimizationResult,
)
from src.backtest.strategy import ThresholdStrategy
from src.backtest.strategy_spec import (
    ParameterRange,
    ParameterSet,
)


def make_bars(
    prices: list[str],
    scores: list[str],
) -> list[BacktestBar]:
    assert len(prices) == len(scores)

    start = date(2026, 1, 1)

    return [
        BacktestBar(
            symbol="TEST",
            trading_date=start + timedelta(days=index),
            close=Decimal(prices[index]),
            score=Decimal(scores[index]),
        )
        for index in range(len(prices))
    ]


def test_parameter_range_generates_inclusive_values():
    parameter_range = ParameterRange(
        minimum=Decimal("40"),
        maximum=Decimal("60"),
        step=Decimal("10"),
    )

    assert parameter_range.values() == (
        Decimal("40"),
        Decimal("50"),
        Decimal("60"),
    )


def test_parameter_range_rejects_invalid_step():
    with pytest.raises(ValueError):
        ParameterRange(
            minimum=Decimal("40"),
            maximum=Decimal("60"),
            step=Decimal("0"),
        )


def test_parameter_range_rejects_reversed_range():
    with pytest.raises(ValueError):
        ParameterRange(
            minimum=Decimal("60"),
            maximum=Decimal("40"),
            step=Decimal("10"),
        )


def test_parameter_set_normalizes_decimal_values():
    parameters = ParameterSet(
        {
            "buy_threshold": "70",
            "sell_threshold": "40",
        }
    )

    assert parameters.get("buy_threshold") == Decimal("70")
    assert parameters.get("sell_threshold") == Decimal("40")

    assert parameters.as_dict() == {
        "buy_threshold": Decimal("70"),
        "sell_threshold": Decimal("40"),
    }


def test_parameter_set_rejects_empty_values():
    with pytest.raises(ValueError):
        ParameterSet({})


def test_parameter_set_rejects_unknown_parameter():
    parameters = ParameterSet(
        {
            "buy_threshold": Decimal("70"),
        }
    )

    with pytest.raises(KeyError):
        parameters.get("sell_threshold")


def test_grid_search_generates_cartesian_parameter_combinations():
    optimizer = GridSearchOptimizer(
        {
            "buy_threshold": ParameterRange(
                Decimal("70"),
                Decimal("80"),
                Decimal("10"),
            ),
            "sell_threshold": ParameterRange(
                Decimal("30"),
                Decimal("40"),
                Decimal("10"),
            ),
        },
        lambda parameters: ThresholdStrategy(
            buy_threshold=parameters.get(
                "buy_threshold"
            ),
            sell_threshold=parameters.get(
                "sell_threshold"
            ),
        ),
        initial_capital=Decimal("1000"),
    )

    parameter_sets = optimizer._parameter_sets()

    assert len(parameter_sets) == 4


def test_grid_search_finds_best_historical_configuration():
    bars = make_bars(
        prices=[
            "100",
            "110",
            "120",
            "100",
        ],
        scores=[
            "80",
            "60",
            "30",
            "80",
        ],
    )

    optimizer = GridSearchOptimizer(
        {
            "buy_threshold": ParameterRange(
                Decimal("70"),
                Decimal("80"),
                Decimal("10"),
            ),
            "sell_threshold": ParameterRange(
                Decimal("20"),
                Decimal("40"),
                Decimal("10"),
            ),
        },
        lambda parameters: ThresholdStrategy(
            buy_threshold=parameters.get(
                "buy_threshold"
            ),
            sell_threshold=parameters.get(
                "sell_threshold"
            ),
        ),
        initial_capital=Decimal("1000"),
        minimum_bars=4,
        minimum_trades=1,
    )

    result = optimizer.optimize(bars)

    assert isinstance(result, OptimizationResult)
    assert result.combinations_tested == 6
    assert result.best_parameters is not None


def test_grid_search_rejects_empty_bars():
    optimizer = GridSearchOptimizer(
        {
            "buy_threshold": ParameterRange(
                Decimal("70"),
                Decimal("70"),
                Decimal("1"),
            ),
        },
        lambda parameters: ThresholdStrategy(
            buy_threshold=parameters.get(
                "buy_threshold"
            ),
            sell_threshold=Decimal("40"),
        ),
        initial_capital=Decimal("1000"),
    )

    with pytest.raises(ValueError):
        optimizer.optimize([])


def test_grid_search_requires_parameter_ranges():
    with pytest.raises(ValueError):
        GridSearchOptimizer(
            {},
            lambda parameters: ThresholdStrategy(),
            initial_capital=Decimal("1000"),
        )


def test_grid_search_reports_profitability():
    bars = make_bars(
        prices=[
            "100",
            "110",
            "120",
        ],
        scores=[
            "80",
            "60",
            "30",
        ],
    )

    optimizer = GridSearchOptimizer(
        {
            "buy_threshold": ParameterRange(
                Decimal("70"),
                Decimal("70"),
                Decimal("1"),
            ),
            "sell_threshold": ParameterRange(
                Decimal("40"),
                Decimal("40"),
                Decimal("1"),
            ),
        },
        lambda parameters: ThresholdStrategy(
            buy_threshold=parameters.get(
                "buy_threshold"
            ),
            sell_threshold=parameters.get(
                "sell_threshold"
            ),
        ),
        initial_capital=Decimal("1000"),
        minimum_bars=3,
        minimum_trades=1,
    )

    result = optimizer.optimize(bars)

    assert result.best_run_profit_loss > Decimal("0")
    assert result.best_run_return > Decimal("0")
    assert result.is_profitable is True


def test_grid_search_supports_custom_objective():
    bars = make_bars(
        prices=[
            "100",
            "110",
            "120",
        ],
        scores=[
            "80",
            "60",
            "30",
        ],
    )

    calls = []

    def objective(
        total_return: Decimal,
        profit_loss: Decimal,
    ) -> Decimal:
        calls.append(
            (
                total_return,
                profit_loss,
            )
        )
        return profit_loss

    optimizer = GridSearchOptimizer(
        {
            "buy_threshold": ParameterRange(
                Decimal("70"),
                Decimal("70"),
                Decimal("1"),
            ),
            "sell_threshold": ParameterRange(
                Decimal("40"),
                Decimal("40"),
                Decimal("1"),
            ),
        },
        lambda parameters: ThresholdStrategy(
            buy_threshold=parameters.get(
                "buy_threshold"
            ),
            sell_threshold=parameters.get(
                "sell_threshold"
            ),
        ),
        initial_capital=Decimal("1000"),
        objective=objective,
        minimum_bars=3,
        minimum_trades=1,
    )

    result = optimizer.optimize(bars)

    assert len(calls) == 1
    assert result.best_run_profit_loss == Decimal("200")
