from datetime import date, timedelta
from decimal import Decimal

import pytest

from src.backtest.models import (
    BacktestBar,
    BacktestSignal,
)
from src.backtest.strategy import (
    SignalSequenceStrategy,
    ThresholdStrategy,
    generate_strategy_signals,
)


def make_bars(
    values: list[str],
) -> list[BacktestBar]:
    start = date(2026, 1, 1)

    return [
        BacktestBar(
            symbol="TEST",
            trading_date=start + timedelta(days=index),
            close=Decimal(value),
        )
        for index, value in enumerate(values)
    ]


def test_threshold_strategy_generates_buy_hold_sell():
    strategy = ThresholdStrategy(
        buy_threshold=Decimal("70"),
        sell_threshold=Decimal("40"),
    )

    signals = strategy.generate_signals(
        make_bars(["80", "60", "30"])
    )

    assert [signal.action for signal in signals] == [
        "BUY",
        "HOLD",
        "SELL",
    ]


def test_threshold_strategy_preserves_dates_and_symbols():
    bars = make_bars(["80", "60"])

    strategy = ThresholdStrategy()

    signals = strategy.generate_signals(bars)

    assert signals[0].symbol == "TEST"
    assert signals[0].trading_date == date(2026, 1, 1)
    assert signals[1].trading_date == date(2026, 1, 2)


def test_threshold_strategy_rejects_invalid_thresholds():
    with pytest.raises(ValueError):
        ThresholdStrategy(
            buy_threshold=Decimal("101")
        )

    with pytest.raises(ValueError):
        ThresholdStrategy(
            sell_threshold=Decimal("-1")
        )

    with pytest.raises(ValueError):
        ThresholdStrategy(
            buy_threshold=Decimal("50"),
            sell_threshold=Decimal("50"),
        )


def test_threshold_strategy_rejects_unordered_bars():
    bars = make_bars(["80", "60"])

    bars[1] = BacktestBar(
        symbol="TEST",
        trading_date=date(2025, 12, 31),
        close=Decimal("60"),
    )

    strategy = ThresholdStrategy()

    with pytest.raises(ValueError):
        strategy.generate_signals(bars)


def test_signal_sequence_strategy_accepts_matching_data():
    bars = make_bars(["100", "110"])

    signals = (
        BacktestSignal(
            symbol="TEST",
            trading_date=date(2026, 1, 1),
            action="BUY",
            score=Decimal("80"),
        ),
        BacktestSignal(
            symbol="TEST",
            trading_date=date(2026, 1, 2),
            action="SELL",
            score=Decimal("30"),
        ),
    )

    strategy = SignalSequenceStrategy(signals)

    result = strategy.generate_signals(bars)

    assert result == list(signals)


def test_signal_sequence_strategy_rejects_length_mismatch():
    bars = make_bars(["100", "110"])

    strategy = SignalSequenceStrategy(
        (
            BacktestSignal(
                symbol="TEST",
                trading_date=date(2026, 1, 1),
                action="BUY",
                score=Decimal("80"),
            ),
        )
    )

    with pytest.raises(ValueError):
        strategy.generate_signals(bars)


def test_signal_sequence_strategy_rejects_symbol_mismatch():
    bars = make_bars(["100"])

    strategy = SignalSequenceStrategy(
        (
            BacktestSignal(
                symbol="OTHER",
                trading_date=date(2026, 1, 1),
                action="BUY",
                score=Decimal("80"),
            ),
        )
    )

    with pytest.raises(ValueError):
        strategy.generate_signals(bars)


def test_signal_sequence_strategy_rejects_date_mismatch():
    bars = make_bars(["100"])

    strategy = SignalSequenceStrategy(
        (
            BacktestSignal(
                symbol="TEST",
                trading_date=date(2026, 1, 2),
                action="BUY",
                score=Decimal("80"),
            ),
        )
    )

    with pytest.raises(ValueError):
        strategy.generate_signals(bars)


def test_signal_sequence_strategy_rejects_unordered_signals():
    bars = make_bars(["100", "110"])

    strategy = SignalSequenceStrategy(
        (
            BacktestSignal(
                symbol="TEST",
                trading_date=date(2026, 1, 2),
                action="BUY",
                score=Decimal("80"),
            ),
            BacktestSignal(
                symbol="TEST",
                trading_date=date(2026, 1, 1),
                action="SELL",
                score=Decimal("30"),
            ),
        )
    )

    with pytest.raises(ValueError):
        strategy.generate_signals(bars)


def test_generate_strategy_signals_uses_strategy():
    bars = make_bars(["80", "30"])

    strategy = ThresholdStrategy()

    signals = generate_strategy_signals(
        strategy,
        bars,
    )

    assert len(signals) == 2
    assert signals[0].action == "BUY"
    assert signals[1].action == "SELL"


def test_generate_strategy_signals_rejects_empty_bars():
    strategy = ThresholdStrategy()

    with pytest.raises(ValueError):
        generate_strategy_signals(
            strategy,
            [],
        )
