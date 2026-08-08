from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, Sequence

from src.backtest.models import (
    BacktestBar,
    BacktestSignal,
)


class BacktestStrategy(Protocol):
    """
    Interface for a deterministic historical strategy.

    A strategy converts information available at a trading date
    into a historical decision.

    It must not access future observations.
    """

    def generate_signals(
        self,
        bars: Sequence[BacktestBar],
    ) -> list[BacktestSignal]:
        ...


@dataclass(frozen=True)
class ThresholdStrategy:
    """
    Transparent score-threshold baseline strategy.

    The strategy expects each BacktestBar.close to represent a
    normalized score between 0 and 100.

    Rules:

        score >= buy_threshold  -> BUY
        score <= sell_threshold -> SELL
        otherwise                -> HOLD

    This is intentionally simple. It exists as a baseline for
    validating the backtesting infrastructure, not as a claimed
    profitable trading strategy.
    """

    buy_threshold: Decimal = Decimal("70")
    sell_threshold: Decimal = Decimal("40")

    def __post_init__(self) -> None:
        buy = Decimal(self.buy_threshold)
        sell = Decimal(self.sell_threshold)

        if buy < Decimal("0") or buy > Decimal("100"):
            raise ValueError(
                "buy_threshold must be between 0 and 100"
            )

        if sell < Decimal("0") or sell > Decimal("100"):
            raise ValueError(
                "sell_threshold must be between 0 and 100"
            )

        if sell >= buy:
            raise ValueError(
                "sell_threshold must be lower than buy_threshold"
            )

    def generate_signals(
        self,
        bars: Sequence[BacktestBar],
    ) -> list[BacktestSignal]:
        ordered = list(bars)

        for previous, current in zip(
            ordered,
            ordered[1:],
        ):
            if current.trading_date <= previous.trading_date:
                raise ValueError(
                    "bars must be strictly ordered by trading_date"
                )

        signals: list[BacktestSignal] = []

        for bar in ordered:
            score = bar.close

            if score >= self.buy_threshold:
                action = "BUY"
            elif score <= self.sell_threshold:
                action = "SELL"
            else:
                action = "HOLD"

            signals.append(
                BacktestSignal(
                    symbol=bar.symbol,
                    trading_date=bar.trading_date,
                    action=action,
                    score=score,
                )
            )

        return signals


@dataclass(frozen=True)
class SignalSequenceStrategy:
    """
    Deterministic strategy backed by a precomputed signal sequence.

    Useful for testing and later for plugging research-generated
    signals into the backtest engine.

    The strategy validates that signals are ordered and correspond
    exactly to the supplied bars.
    """

    signals: tuple[BacktestSignal, ...]

    def generate_signals(
        self,
        bars: Sequence[BacktestBar],
    ) -> list[BacktestSignal]:
        ordered_bars = list(bars)
        ordered_signals = list(self.signals)

        if len(ordered_bars) != len(ordered_signals):
            raise ValueError(
                "signals and bars must contain the same number "
                "of observations"
            )

        for index, (bar, signal) in enumerate(
            zip(
                ordered_bars,
                ordered_signals,
            )
        ):
            if bar.symbol != signal.symbol:
                raise ValueError(
                    f"Symbol mismatch at index {index}"
                )

            if bar.trading_date != signal.trading_date:
                raise ValueError(
                    f"Trading date mismatch at index {index}"
                )

        for previous, current in zip(
            ordered_signals,
            ordered_signals[1:],
        ):
            if current.trading_date <= previous.trading_date:
                raise ValueError(
                    "signals must be strictly ordered by trading_date"
                )

        return ordered_signals.copy()


def generate_strategy_signals(
    strategy: BacktestStrategy,
    bars: Sequence[BacktestBar],
) -> list[BacktestSignal]:
    """
    Generate signals through the strategy interface.

    This helper keeps strategy execution separate from the
    BacktestEngine and makes the dependency explicit.
    """

    if not bars:
        raise ValueError(
            "bars cannot be empty"
        )

    signals = strategy.generate_signals(bars)

    for signal in signals:
        if signal.trading_date > bars[-1].trading_date:
            raise ValueError(
                "strategy generated a signal after the final "
                "available market observation"
            )

    return signals
