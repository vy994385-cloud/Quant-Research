from __future__ import annotations

from decimal import Decimal
from typing import Literal, Sequence

from src.backtest.models import (
    BacktestBar,
    BacktestResult,
    BacktestSignal,
    BacktestTrade,
    EquityPoint,
)

ExecutionTiming = Literal["SAME_CLOSE", "NEXT_BAR"]


class BacktestEngine:
    """
    Deterministic long-only historical backtest engine.

    Execution timing is explicit:

    SAME_CLOSE:
        A signal for date T executes at the close of date T.
        This is appropriate only when the signal was known before
        that close.

    NEXT_BAR:
        A signal generated from date T information executes using
        the next available historical bar, T+1.
        This is the safer convention when signals use the current
        bar's closing information.

    Position rules:
    - Long-only.
    - One position may be held at a time.
    - BUY opens a position.
    - SELL closes a position.
    - Position size is determined by allocation.
    """

    def __init__(
        self,
        initial_capital: Decimal,
        *,
        allocation: Decimal = Decimal("1"),
        transaction_cost_rate: Decimal = Decimal("0"),
        execution_timing: ExecutionTiming = "SAME_CLOSE",
    ) -> None:
        if initial_capital <= Decimal("0"):
            raise ValueError(
                "initial_capital must be greater than zero"
            )

        if allocation <= Decimal("0") or allocation > Decimal("1"):
            raise ValueError(
                "allocation must be between 0 and 1"
            )

        if transaction_cost_rate < Decimal("0"):
            raise ValueError(
                "transaction_cost_rate cannot be negative"
            )

        if execution_timing not in {
            "SAME_CLOSE",
            "NEXT_BAR",
        }:
            raise ValueError(
                "execution_timing must be SAME_CLOSE or NEXT_BAR"
            )

        self.initial_capital = Decimal(initial_capital)
        self.allocation = Decimal(allocation)
        self.transaction_cost_rate = Decimal(
            transaction_cost_rate
        )
        self.execution_timing = execution_timing

    def run(
        self,
        bars: Sequence[BacktestBar],
        signals: Sequence[BacktestSignal],
    ) -> BacktestResult:
        """
        Execute a historical backtest.

        Bars and signals must be chronologically ordered.

        Every signal must correspond to a historical observation.

        With SAME_CLOSE, the signal executes on its own bar.

        With NEXT_BAR, the signal generated on bar T executes on
        the next available bar. A signal on the final bar therefore
        has no execution opportunity and is not executed.
        """

        ordered_bars = self._validate_bars(bars)
        ordered_signals = self._validate_signals(signals)

        prices = {
            (bar.symbol, bar.trading_date): bar.close
            for bar in ordered_bars
        }

        for signal in ordered_signals:
            key = (
                signal.symbol,
                signal.trading_date,
            )

            if key not in prices:
                raise ValueError(
                    "Signal has no matching price bar: "
                    f"{signal.symbol} {signal.trading_date}"
                )

        cash = self.initial_capital
        quantity = Decimal("0")
        position_symbol: str | None = None

        trades: list[BacktestTrade] = []
        equity_curve: list[EquityPoint] = []

        signals_by_date = {
            signal.trading_date: signal
            for signal in ordered_signals
        }

        for index, bar in enumerate(ordered_bars):
            signal = self._signal_for_execution(
                ordered_bars=ordered_bars,
                signals_by_date=signals_by_date,
                index=index,
            )

            price = bar.close

            if signal is not None and signal.symbol == bar.symbol:
                if signal.action == "BUY":
                    if quantity == Decimal("0"):
                        quantity = self._buy_quantity(
                            cash,
                            price,
                        )

                        if quantity > Decimal("0"):
                            gross_value = quantity * price
                            cost = (
                                gross_value
                                * self.transaction_cost_rate
                            )

                            cash -= gross_value + cost

                            trades.append(
                                BacktestTrade(
                                    symbol=bar.symbol,
                                    trading_date=bar.trading_date,
                                    side="LONG",
                                    quantity=quantity,
                                    price=price,
                                    transaction_cost=cost,
                                )
                            )

                            position_symbol = bar.symbol

                elif signal.action == "SELL":
                    if (
                        quantity > Decimal("0")
                        and position_symbol == bar.symbol
                    ):
                        gross_value = quantity * price
                        cost = (
                            gross_value
                            * self.transaction_cost_rate
                        )

                        cash += gross_value - cost

                        trades.append(
                            BacktestTrade(
                                symbol=bar.symbol,
                                trading_date=bar.trading_date,
                                side="LONG",
                                quantity=quantity,
                                price=price,
                                transaction_cost=cost,
                            )
                        )

                        quantity = Decimal("0")
                        position_symbol = None

            positions_value = (
                quantity * price
                if position_symbol == bar.symbol
                else Decimal("0")
            )

            equity = cash + positions_value

            equity_curve.append(
                EquityPoint(
                    trading_date=bar.trading_date,
                    cash=cash,
                    positions_value=positions_value,
                    equity=equity,
                )
            )

        final_equity = (
            equity_curve[-1].equity
            if equity_curve
            else self.initial_capital
        )

        return BacktestResult(
            initial_capital=self.initial_capital,
            final_equity=final_equity,
            trades=tuple(trades),
            equity_curve=tuple(equity_curve),
        )

    def _signal_for_execution(
        self,
        *,
        ordered_bars: Sequence[BacktestBar],
        signals_by_date: dict,
        index: int,
    ) -> BacktestSignal | None:
        """
        Resolve the signal that is allowed to execute on this bar.

        SAME_CLOSE:
            Execute the signal attached to this bar.

        NEXT_BAR:
            Execute the signal attached to the immediately previous
            historical bar.
        """

        if self.execution_timing == "SAME_CLOSE":
            signal_date = ordered_bars[index].trading_date

        else:
            if index == 0:
                return None

            signal_date = ordered_bars[index - 1].trading_date

        return signals_by_date.get(signal_date)

    @staticmethod
    def _validate_bars(
        bars: Sequence[BacktestBar],
    ) -> list[BacktestBar]:
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

        return ordered

    @staticmethod
    def _validate_signals(
        signals: Sequence[BacktestSignal],
    ) -> list[BacktestSignal]:
        ordered = list(signals)

        for previous, current in zip(
            ordered,
            ordered[1:],
        ):
            if current.trading_date <= previous.trading_date:
                raise ValueError(
                    "signals must be strictly ordered by trading_date"
                )

        return ordered

    def _buy_quantity(
        self,
        cash: Decimal,
        price: Decimal,
    ) -> Decimal:
        if cash <= Decimal("0"):
            return Decimal("0")

        allocation_cash = cash * self.allocation

        denominator = (
            price
            * (
                Decimal("1")
                + self.transaction_cost_rate
            )
        )

        if denominator <= Decimal("0"):
            return Decimal("0")

        return allocation_cash / denominator
