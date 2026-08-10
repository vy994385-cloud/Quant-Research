from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.backtest.models import BacktestBar
from src.backtest.strategy import ThresholdStrategy
from src.backtest.walk_forward import (
    build_walk_forward_windows,
    run_walk_forward,
)


def make_bars(
    count: int,
    *,
    start_price: int = 100,
) -> list[BacktestBar]:
    start = date(2026, 1, 1)

    return [
        BacktestBar(
            symbol="TEST",
            trading_date=start + timedelta(days=index),
            close=Decimal(
                str(start_price + index)
            ),
            score=Decimal("80"),
        )
        for index in range(count)
    ]


def test_builds_chronological_train_test_windows():
    bars = make_bars(10)

    windows = build_walk_forward_windows(
        bars,
        train_size=4,
        test_size=2,
    )

    assert len(windows) == 3

    assert windows[0].train_start == date(2026, 1, 1)
    assert windows[0].train_end == date(2026, 1, 4)

    assert windows[0].test_start == date(2026, 1, 5)
    assert windows[0].test_end == date(2026, 1, 6)

    assert windows[1].train_start == date(2026, 1, 3)
    assert windows[1].train_end == date(2026, 1, 6)

    assert windows[1].test_start == date(2026, 1, 7)
    assert windows[1].test_end == date(2026, 1, 8)


def test_step_size_controls_window_movement():
    bars = make_bars(12)

    windows = build_walk_forward_windows(
        bars,
        train_size=4,
        test_size=2,
        step_size=2,
    )

    assert len(windows) == 4

    assert windows[0].test_start == date(2026, 1, 5)
    assert windows[1].test_start == date(2026, 1, 7)
    assert windows[2].test_start == date(2026, 1, 9)
    assert windows[3].test_start == date(2026, 1, 11)


def test_train_and_test_periods_do_not_overlap():
    bars = make_bars(12)

    windows = build_walk_forward_windows(
        bars,
        train_size=5,
        test_size=3,
    )

    for window in windows:
        train_dates = {
            bar.trading_date
            for bar in window.train_bars
        }

        test_dates = {
            bar.trading_date
            for bar in window.test_bars
        }

        assert train_dates.isdisjoint(test_dates)

        assert (
            window.train_end
            < window.test_start
        )


def test_insufficient_data_is_rejected():
    bars = make_bars(5)

    with pytest.raises(ValueError):
        build_walk_forward_windows(
            bars,
            train_size=4,
            test_size=2,
        )


def test_empty_bars_are_rejected():
    with pytest.raises(ValueError):
        build_walk_forward_windows(
            [],
            train_size=2,
            test_size=1,
        )


def test_invalid_window_sizes_are_rejected():
    bars = make_bars(10)

    with pytest.raises(ValueError):
        build_walk_forward_windows(
            bars,
            train_size=0,
            test_size=2,
        )

    with pytest.raises(ValueError):
        build_walk_forward_windows(
            bars,
            train_size=2,
            test_size=0,
        )


def test_invalid_step_size_is_rejected():
    bars = make_bars(10)

    with pytest.raises(ValueError):
        build_walk_forward_windows(
            bars,
            train_size=2,
            test_size=2,
            step_size=0,
        )


def test_non_chronological_data_is_rejected():
    bars = make_bars(6)

    bars[1], bars[2] = bars[2], bars[1]

    with pytest.raises(ValueError):
        build_walk_forward_windows(
            bars,
            train_size=2,
            test_size=2,
        )


def test_walk_forward_runs_only_test_windows():
    bars = make_bars(
        12,
        start_price=100,
    )

    result = run_walk_forward(
        bars,
        lambda: ThresholdStrategy(
            buy_threshold=Decimal("70"),
            sell_threshold=Decimal("40"),
        ),
        initial_capital=Decimal("1000"),
        train_size=4,
        test_size=2,
        minimum_bars=2,
        minimum_trades=0,
    )

    assert result.window_count == 4
    assert result.all_windows_valid

    for run in result.windows:
        assert len(run.result.equity_curve) == 2


def test_walk_forward_returns_consistency_metrics():
    bars = make_bars(12)

    result = run_walk_forward(
        bars,
        ThresholdStrategy,
        initial_capital=Decimal("1000"),
        train_size=4,
        test_size=2,
        minimum_bars=2,
        minimum_trades=0,
    )

    assert result.window_count == 4
    assert result.profitable_windows >= 0
    assert result.losing_windows >= 0

    assert (
        result.consistency_percent
        >= Decimal("0")
    )

    assert (
        result.consistency_percent
        <= Decimal("100")
    )


def test_walk_forward_creates_fresh_strategy_per_window():
    created = []

    def factory():
        strategy = ThresholdStrategy()
        created.append(strategy)
        return strategy

    result = run_walk_forward(
        make_bars(10),
        factory,
        initial_capital=Decimal("1000"),
        train_size=4,
        test_size=2,
        minimum_bars=2,
        minimum_trades=0,
    )

    assert len(created) == result.window_count
    assert len({
        id(strategy)
        for strategy in created
    }) == result.window_count


def test_walk_forward_preserves_transaction_costs():
    result = run_walk_forward(
        make_bars(10),
        ThresholdStrategy,
        initial_capital=Decimal("1000"),
        train_size=4,
        test_size=2,
        transaction_cost_rate=Decimal("0.01"),
        minimum_bars=2,
        minimum_trades=0,
    )

    assert result.window_count > 0

    for run in result.windows:
        assert (
            run.result.final_equity
            <= Decimal("1000")
        )


def test_walk_forward_is_not_a_trade_signal():
    result = run_walk_forward(
        make_bars(10),
        ThresholdStrategy,
        initial_capital=Decimal("1000"),
        train_size=4,
        test_size=2,
        minimum_bars=2,
        minimum_trades=0,
    )

    for run in result.windows:
        assert run.is_trade_signal is False
        assert run.report.is_trade_signal is False
