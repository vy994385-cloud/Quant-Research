from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.backtest.models import (
    BacktestBar,
    BacktestSignal,
)
from src.backtest.runner import BacktestRunner


def make_bars(
    prices: list[str],
) -> list[BacktestBar]:
    start = date(2026, 1, 1)

    return [
        BacktestBar(
            symbol="TEST",
            trading_date=start + timedelta(days=index),
            close=Decimal(price),
        )
        for index, price in enumerate(prices)
    ]


def make_signal(
    day: int,
    action: str,
) -> BacktestSignal:
    return BacktestSignal(
        symbol="TEST",
        trading_date=date(2026, 1, day),
        action=action,
        score=Decimal("80"),
    )


def test_runner_executes_complete_pipeline():
    runner = BacktestRunner(
        Decimal("1000"),
        minimum_bars=3,
        minimum_trades=1,
    )

    run = runner.run(
        make_bars(["100", "110", "120"]),
        [
            make_signal(1, "BUY"),
            make_signal(3, "SELL"),
        ],
    )

    assert run.is_valid
    assert not run.requires_review

    assert run.result.final_equity == Decimal("1200")
    assert run.metrics.total_return == Decimal("20")
    assert run.report.profit_loss == Decimal("200")


def test_runner_preserves_needs_review_status():
    runner = BacktestRunner(
        Decimal("1000"),
        minimum_bars=30,
        minimum_trades=10,
    )

    run = runner.run(
        make_bars(["100", "110", "120"]),
        [
            make_signal(1, "BUY"),
            make_signal(3, "SELL"),
        ],
    )

    assert run.is_valid
    assert run.requires_review
    assert run.validation.status == "NEEDS_REVIEW"


def test_runner_rejects_invalid_backtest():
    runner = BacktestRunner(
        Decimal("1000"),
        minimum_bars=3,
        minimum_trades=1,
    )

    with pytest.raises(ValueError):
        runner.run(
            make_bars(["100", "110"]),
            [
                make_signal(3, "BUY"),
            ],
        )


def test_runner_exposes_validation_warnings():
    runner = BacktestRunner(
        Decimal("1000"),
        minimum_bars=3,
        minimum_trades=5,
    )

    run = runner.run(
        make_bars(["100", "110", "120"]),
        [
            make_signal(1, "BUY"),
            make_signal(3, "SELL"),
        ],
    )

    assert run.validation.warnings
    assert run.report.sample_size_warning is not None


def test_runner_does_not_create_trade_signal():
    runner = BacktestRunner(
        Decimal("1000"),
        minimum_bars=3,
        minimum_trades=1,
    )

    run = runner.run(
        make_bars(["100", "110", "120"]),
        [
            make_signal(1, "BUY"),
            make_signal(3, "SELL"),
        ],
    )

    assert run.is_trade_signal is False
    assert run.report.is_trade_signal is False


def test_runner_respects_transaction_costs():
    runner = BacktestRunner(
        Decimal("1000"),
        transaction_cost_rate=Decimal("0.01"),
        minimum_bars=2,
        minimum_trades=1,
    )

    run = runner.run(
        make_bars(["100", "120"]),
        [
            make_signal(1, "BUY"),
            make_signal(2, "SELL"),
        ],
    )

    assert run.result.final_equity < Decimal("1200")
    assert run.metrics.total_return < Decimal("20")
