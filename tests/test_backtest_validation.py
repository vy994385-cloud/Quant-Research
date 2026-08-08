from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.backtest.models import (
    BacktestBar,
    BacktestSignal,
)
from src.backtest.validation import validate_backtest_inputs


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


def test_valid_structure_with_small_sample_needs_review():
    result = validate_backtest_inputs(
        make_bars(["100", "101", "102"]),
        [
            make_signal(1, "BUY"),
            make_signal(3, "SELL"),
        ],
        minimum_bars=3,
        minimum_trades=10,
    )

    assert result.status == "NEEDS_REVIEW"
    assert result.needs_review
    assert not result.is_rejected


def test_empty_bars_are_rejected():
    result = validate_backtest_inputs(
        [],
        [],
    )

    assert result.status == "REJECT"
    assert result.is_rejected
    assert any(
        "bars cannot be empty" in error
        for error in result.errors
    )


def test_duplicate_bar_dates_are_rejected():
    bars = make_bars(["100", "101"])

    bars = [
        bars[0],
        BacktestBar(
            symbol="TEST",
            trading_date=bars[0].trading_date,
            close=Decimal("102"),
        ),
    ]

    result = validate_backtest_inputs(
        bars,
        [],
    )

    assert result.status == "REJECT"
    assert any(
        "duplicate trading dates" in error
        for error in result.errors
    )


def test_non_chronological_bars_are_rejected():
    bars = make_bars(["100", "101", "102"])

    result = validate_backtest_inputs(
        [
            bars[1],
            bars[0],
            bars[2],
        ],
        [],
    )

    assert result.status == "REJECT"
    assert any(
        "strictly ordered" in error
        for error in result.errors
    )


def test_duplicate_signal_dates_are_rejected():
    result = validate_backtest_inputs(
        make_bars(["100", "101", "102"]),
        [
            make_signal(1, "BUY"),
            make_signal(1, "SELL"),
        ],
    )

    assert result.status == "REJECT"
    assert any(
        "signals contain duplicate" in error
        for error in result.errors
    )


def test_signal_without_matching_bar_is_rejected():
    result = validate_backtest_inputs(
        make_bars(["100", "101"]),
        [
            make_signal(3, "BUY"),
        ],
    )

    assert result.status == "REJECT"
    assert any(
        "no matching historical price bar" in error
        for error in result.errors
    )


def test_signal_before_history_is_rejected():
    result = validate_backtest_inputs(
        make_bars(["100", "101", "102"]),
        [
            BacktestSignal(
                symbol="TEST",
                trading_date=date(2025, 12, 31),
                action="BUY",
                score=Decimal("80"),
            )
        ],
    )

    assert result.status == "REJECT"
    assert any(
        "before the available historical data" in error
        for error in result.errors
    )


def test_signal_after_history_is_rejected():
    result = validate_backtest_inputs(
        make_bars(["100", "101", "102"]),
        [
            make_signal(4, "BUY"),
        ],
    )

    assert result.status == "REJECT"
    assert any(
        "after the available historical data" in error
        for error in result.errors
    )


def test_multiple_symbols_are_rejected():
    bars = make_bars(["100", "101"])

    bars.append(
        BacktestBar(
            symbol="OTHER",
            trading_date=date(2026, 1, 3),
            close=Decimal("200"),
        )
    )

    result = validate_backtest_inputs(
        bars,
        [],
    )

    assert result.status == "REJECT"
    assert any(
        "one symbol per backtest" in error
        for error in result.errors
    )


def test_large_clean_sample_can_be_accepted():
    bars = make_bars(
        [str(100 + index) for index in range(30)]
    )

    signals = [
        make_signal(1, "BUY"),
        make_signal(2, "SELL"),
        make_signal(3, "BUY"),
        make_signal(4, "SELL"),
        make_signal(5, "BUY"),
        make_signal(6, "SELL"),
        make_signal(7, "BUY"),
        make_signal(8, "SELL"),
        make_signal(9, "BUY"),
        make_signal(10, "SELL"),
    ]

    result = validate_backtest_inputs(
        bars,
        signals,
        minimum_bars=30,
        minimum_trades=5,
    )

    assert result.status == "ACCEPT"
    assert result.is_accepted
    assert not result.errors
    assert not result.warnings


def test_invalid_minimum_bars_is_rejected_by_configuration():
    with pytest.raises(ValueError):
        validate_backtest_inputs(
            make_bars(["100"]),
            [],
            minimum_bars=0,
        )


def test_invalid_minimum_trades_is_rejected_by_configuration():
    with pytest.raises(ValueError):
        validate_backtest_inputs(
            make_bars(["100"]),
            [],
            minimum_trades=-1,
        )
