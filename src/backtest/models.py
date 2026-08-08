from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal


Side = Literal["LONG", "SHORT"]
Action = Literal["BUY", "SELL", "HOLD"]


@dataclass(frozen=True)
class BacktestBar:
    """
    Normalized historical market observation.

    close:
        Actual historical market price used by the execution engine.

    score:
        Optional research/strategy score available at this date.
        It is deliberately separate from the market price so a
        strategy cannot accidentally use price as its signal score.

    The backtest must only use information available at or before
    this trading date.
    """

    symbol: str
    trading_date: date
    close: Decimal
    score: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol cannot be empty")

        if self.close <= Decimal("0"):
            raise ValueError("close must be greater than zero")

        if self.score is not None:
            if (
                self.score < Decimal("0")
                or self.score > Decimal("100")
            ):
                raise ValueError(
                    "score must be between 0 and 100"
                )


@dataclass(frozen=True)
class BacktestSignal:
    """
    Historical strategy decision for one security and date.

    This is deliberately separate from the research score/ranker
    so the backtest can evaluate different strategies.
    """

    symbol: str
    trading_date: date
    action: Action
    score: Decimal

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol cannot be empty")

        if self.score < Decimal("0") or self.score > Decimal("100"):
            raise ValueError("score must be between 0 and 100")


@dataclass(frozen=True)
class BacktestTrade:
    """
    Executed historical trade.

    Prices are assumed to include the execution convention selected
    by the backtest engine.
    """

    symbol: str
    trading_date: date
    side: Side
    quantity: Decimal
    price: Decimal
    transaction_cost: Decimal

    @property
    def gross_value(self) -> Decimal:
        return self.quantity * self.price

    @property
    def total_cost(self) -> Decimal:
        return self.gross_value + self.transaction_cost


@dataclass(frozen=True)
class BacktestPosition:
    """
    Position held after processing a trading date.
    """

    symbol: str
    quantity: Decimal
    average_price: Decimal

    @property
    def market_value(self) -> Decimal:
        return self.quantity * self.average_price


@dataclass(frozen=True)
class EquityPoint:
    """
    Portfolio value at the end of a historical observation date.
    """

    trading_date: date
    cash: Decimal
    positions_value: Decimal
    equity: Decimal


@dataclass(frozen=True)
class BacktestResult:
    """
    Complete deterministic output of one backtest run.

    Metrics are calculated from historical observations only.
    """

    initial_capital: Decimal
    final_equity: Decimal
    trades: tuple[BacktestTrade, ...]
    equity_curve: tuple[EquityPoint, ...]

    @property
    def profit_loss(self) -> Decimal:
        return self.final_equity - self.initial_capital

    @property
    def return_percent(self) -> Decimal:
        if self.initial_capital <= Decimal("0"):
            return Decimal("0")

        return (
            self.profit_loss
            / self.initial_capital
        ) * Decimal("100")

    @property
    def trade_count(self) -> int:
        return len(self.trades)
