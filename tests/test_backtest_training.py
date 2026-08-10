from datetime import date, timedelta
from decimal import Decimal

from src.backtest.models import BacktestBar
from src.backtest.training import StrategyTrainer
from src.backtest.strategy import ThresholdStrategy
from src.backtest.strategy_spec import ParameterRange, ParameterSet


def make_bars(count: int = 12):
    start = date(2026, 1, 1)

    scores = [
        "80",
        "75",
        "65",
        "55",
        "45",
        "35",
        "80",
        "75",
        "65",
        "55",
        "45",
        "35",
    ]

    return [
        BacktestBar(
            symbol="TEST",
            trading_date=start + timedelta(days=index),
            close=Decimal(str(100 + index)),
            score=Decimal(scores[index]),
        )
        for index in range(count)
    ]


def strategy_factory(
    parameters: ParameterSet,
):
    return ThresholdStrategy(
        buy_threshold=parameters.get(
            "buy_threshold"
        ),
        sell_threshold=parameters.get(
            "sell_threshold"
        ),
    )


def test_trainer_uses_only_training_data():
    trainer = StrategyTrainer(
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
        strategy_factory,
        initial_capital=Decimal("1000"),
        minimum_bars=4,
        minimum_trades=0,
    )

    result = trainer.fit(
        make_bars()[:6]
    )

    assert result.combinations_tested == 4

    assert (
        result.parameters.get(
            "buy_threshold"
        )
        in {
            Decimal("70"),
            Decimal("80"),
        }
    )

    assert (
        result.parameters.get(
            "sell_threshold"
        )
        in {
            Decimal("30"),
            Decimal("40"),
        }
    )
