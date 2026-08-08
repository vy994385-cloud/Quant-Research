from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.backtest.models import BacktestBar
from src.backtest.runner import BacktestRunner
from src.backtest.strategy import ThresholdStrategy


def make_bars(
    prices: list[str],
    scores: list[str] | None = None,
) -> list[BacktestBar]:
    start = date(2026, 1, 1)

    if scores is not None:
        assert len(prices) == len(scores)

    return [
        BacktestBar(
            symbol="TEST",
            trading_date=start + timedelta(days=index),
            close=Decimal(price),
            score=(
                Decimal(scores[index])
                if scores is not None
                else None
            ),
        )
        for index, price in enumerate(prices)
    ]


def test_run_strategy_generates_and_executes_signals():
    runner = BacktestRunner(
        Decimal("1000"),
        minimum_bars=3,
        minimum_trades=1,
    )

    strategy = ThresholdStrategy(
        buy_threshold=Decimal("70"),
        sell_threshold=Decimal("40"),
    )

    run = runner.run_strategy(
        make_bars(
            ["100", "110", "120"],
            ["80", "60", "30"],
        ),
        strategy,
    )

    assert run.is_valid
    assert run.result.trade_count == 2
    assert run.result.final_equity == Decimal("1200")


def test_run_strategy_uses_same_validation_pipeline():
    runner = BacktestRunner(
        Decimal("1000"),
        minimum_bars=30,
        minimum_trades=10,
    )

    strategy = ThresholdStrategy()

    run = runner.run_strategy(
        make_bars(
            ["100", "110", "120"],
            ["80", "60", "30"],
        ),
        strategy,
    )

    assert run.is_valid
    assert run.requires_review
    assert run.validation.status == "NEEDS_REVIEW"


def test_run_strategy_produces_metrics_and_report():
    runner = BacktestRunner(
        Decimal("1000"),
        minimum_bars=3,
        minimum_trades=1,
    )

    strategy = ThresholdStrategy()

    run = runner.run_strategy(
        make_bars(
            ["100", "110", "120"],
            ["80", "60", "30"],
        ),
        strategy,
    )

    assert run.metrics is not None
    assert run.report is not None
    assert run.report.initial_capital == Decimal("1000")


def test_run_strategy_preserves_transaction_costs():
    runner = BacktestRunner(
        Decimal("1000"),
        transaction_cost_rate=Decimal("0.01"),
        minimum_bars=3,
        minimum_trades=1,
    )

    strategy = ThresholdStrategy()

    run = runner.run_strategy(
        make_bars(
            ["100", "110", "120"],
            ["80", "60", "30"],
        ),
        strategy,
    )

    assert run.result.final_equity < Decimal("1200")


def test_run_strategy_rejects_empty_bars():
    runner = BacktestRunner(
        Decimal("1000"),
        minimum_bars=1,
        minimum_trades=1,
    )

    strategy = ThresholdStrategy()

    with pytest.raises(ValueError):
        runner.run_strategy(
            [],
            strategy,
        )


def test_manual_signal_api_still_works():
    runner = BacktestRunner(
        Decimal("1000"),
        minimum_bars=3,
        minimum_trades=1,
    )

    strategy = ThresholdStrategy()

    bars = make_bars(
        ["100", "110", "120"],
        ["80", "60", "30"],
    )

    signals = strategy.generate_signals(bars)

    run = runner.run(
        bars,
        signals,
    )

    assert run.is_valid
    assert run.result.trade_count == 2
    assert run.result.final_equity == Decimal("1200")


def test_strategy_runner_does_not_create_trade_signal():
    runner = BacktestRunner(
        Decimal("1000"),
        minimum_bars=3,
        minimum_trades=1,
    )

    strategy = ThresholdStrategy()

    run = runner.run_strategy(
        make_bars(
            ["100", "110", "120"],
            ["80", "60", "30"],
        ),
        strategy,
    )

    assert run.is_trade_signal is False
    assert run.report.is_trade_signal is False
