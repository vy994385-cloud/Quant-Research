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


class TrainableBacktestStrategy(BacktestStrategy, Protocol):
    """
    Strategy capable of fitting parameters exclusively on
    historical training observations.

    The fitted strategy must then generate signals only from
    observations supplied to generate_signals().
    """

    def fit(
        self,
        bars: Sequence[BacktestBar],
    ) -> None:
        ...


@dataclass(frozen=True)
class ThresholdStrategy:
    """
    Transparent score-threshold baseline strategy.

    Rules:

        score >= buy_threshold  -> BUY
        score <= sell_threshold -> SELL
        otherwise                -> HOLD

    For backward compatibility with older research fixtures,
    bars without an explicit score use close as the score.

    New experiments should provide score explicitly.
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
            score = (
                bar.score
                if bar.score is not None
                else bar.close
            )

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


@dataclass
class TrainableThresholdStrategy:
    """
    Trainable threshold strategy.

    This class is intentionally simple for the first training
    pipeline. It can be fitted on historical training data and
    subsequently evaluated on completely separate test data.

    The test observations are never used by fit().
    """

    buy_threshold: Decimal = Decimal("70")
    sell_threshold: Decimal = Decimal("40")

    def __post_init__(self) -> None:
        self.buy_threshold = Decimal(
            self.buy_threshold
        )
        self.sell_threshold = Decimal(
            self.sell_threshold
        )

        self._validate()

    def _validate(self) -> None:
        if (
            self.buy_threshold < Decimal("0")
            or self.buy_threshold > Decimal("100")
        ):
            raise ValueError(
                "buy_threshold must be between 0 and 100"
            )

        if (
            self.sell_threshold < Decimal("0")
            or self.sell_threshold > Decimal("100")
        ):
            raise ValueError(
                "sell_threshold must be between 0 and 100"
            )

        if self.sell_threshold >= self.buy_threshold:
            raise ValueError(
                "sell_threshold must be lower than buy_threshold"
            )

    def fit(
        self,
        bars: Sequence[BacktestBar],
    ) -> None:
        """
        Fit thresholds using training observations only.

        This baseline uses the median training score as its
        central reference and places symmetric thresholds around it.
        """

        if not bars:
            raise ValueError(
                "bars cannot be empty"
            )

        ordered = list(bars)

        for previous, current in zip(
            ordered,
            ordered[1:],
        ):
            if current.trading_date <= previous.trading_date:
                raise ValueError(
                    "bars must be strictly ordered by trading_date"
                )

        scores = [
            bar.score
            for bar in ordered
            if bar.score is not None
        ]

        if not scores:
            raise ValueError(
                "training bars must contain explicit scores"
            )

        sorted_scores = sorted(scores)

        middle = len(sorted_scores) // 2

        median = sorted_scores[middle]

        self.buy_threshold = min(
            Decimal("100"),
            median + Decimal("10"),
        )

        self.sell_threshold = max(
            Decimal("0"),
            median - Decimal("10"),
        )

        if self.sell_threshold >= self.buy_threshold:
            raise ValueError(
                "fitted thresholds are invalid"
            )

        self._validate()

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
            if bar.score is None:
                raise ValueError(
                    "trainable threshold strategy requires "
                    "an explicit score"
                )

            if bar.score >= self.buy_threshold:
                action = "BUY"
            elif bar.score <= self.sell_threshold:
                action = "SELL"
            else:
                action = "HOLD"

            signals.append(
                BacktestSignal(
                    symbol=bar.symbol,
                    trading_date=bar.trading_date,
                    action=action,
                    score=bar.score,
                )
            )

        return signals


@dataclass(frozen=True)
class SignalSequenceStrategy:
    """
    Deterministic strategy backed by a precomputed signal sequence.

    Useful for testing and for plugging research-generated signals
    into the backtest engine.

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
