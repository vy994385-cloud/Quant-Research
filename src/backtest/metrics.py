from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.backtest.models import BacktestResult


@dataclass(frozen=True)
class BacktestMetrics:
    """
    Performance statistics for a completed historical backtest.

    These metrics describe historical performance only.
    They do not predict future returns.
    """

    total_return: Decimal
    profit_loss: Decimal

    max_drawdown: Decimal
    max_drawdown_percent: Decimal

    trade_count: int
    winning_trades: int
    losing_trades: int
    win_rate: Decimal

    average_winning_trade: Decimal
    average_losing_trade: Decimal

    profit_factor: Decimal | None

    exposure_percent: Decimal

    cagr: Decimal | None


def calculate_max_drawdown(
    result: BacktestResult,
) -> tuple[Decimal, Decimal]:
    """
    Return maximum drawdown in currency and percentage.

    Drawdown is measured from each historical equity peak to the
    subsequent equity value.
    """

    if not result.equity_curve:
        return Decimal("0"), Decimal("0")

    peak = result.equity_curve[0].equity

    max_drawdown = Decimal("0")
    max_drawdown_percent = Decimal("0")

    for point in result.equity_curve:
        equity = point.equity

        if equity > peak:
            peak = equity

        if peak <= Decimal("0"):
            continue

        drawdown = peak - equity
        drawdown_percent = (
            drawdown / peak
        ) * Decimal("100")

        if drawdown > max_drawdown:
            max_drawdown = drawdown

        if drawdown_percent > max_drawdown_percent:
            max_drawdown_percent = drawdown_percent

    return (
        max_drawdown,
        max_drawdown_percent,
    )


def _trade_returns(
    result: BacktestResult,
) -> list[Decimal]:
    """
    Calculate realized percentage return for each completed long trade.

    Trades are expected to occur in LONG entry/exit pairs.
    """

    returns: list[Decimal] = []
    entry_value: Decimal | None = None

    for trade in result.trades:
        value = trade.gross_value

        if entry_value is None:
            entry_value = value
            continue

        if entry_value <= Decimal("0"):
            entry_value = None
            continue

        returns.append(
            (
                (value - entry_value)
                / entry_value
            ) * Decimal("100")
        )

        entry_value = None

    return returns


def _trade_profit_losses(
    result: BacktestResult,
) -> list[Decimal]:
    """
    Calculate realized P/L for each completed trade pair.

    Transaction costs are included.
    """

    values: list[Decimal] = []

    entry_total: Decimal | None = None

    for trade in result.trades:
        if entry_total is None:
            entry_total = trade.total_cost
            continue

        exit_value = (
            trade.gross_value
            - trade.transaction_cost
        )

        values.append(
            exit_value - entry_total
        )

        entry_total = None

    return values


def _calculate_cagr(
    result: BacktestResult,
) -> Decimal | None:
    if len(result.equity_curve) < 2:
        return None

    initial = result.initial_capital
    final = result.final_equity

    if initial <= Decimal("0") or final <= Decimal("0"):
        return None

    start = result.equity_curve[0].trading_date
    end = result.equity_curve[-1].trading_date

    days = (end - start).days

    if days <= 0:
        return None

    years = Decimal(days) / Decimal("365")

    if years <= 0:
        return None

    return (
        (
            final / initial
        ) ** (
            Decimal("1") / years
        )
        - Decimal("1")
    ) * Decimal("100")


def _calculate_exposure(
    result: BacktestResult,
) -> Decimal:
    """
    Approximate time-in-market percentage.

    A trading observation is considered exposed when positions_value
    is greater than zero.
    """

    if not result.equity_curve:
        return Decimal("0")

    exposed = sum(
        point.positions_value > Decimal("0")
        for point in result.equity_curve
    )

    return (
        Decimal(exposed)
        / Decimal(len(result.equity_curve))
    ) * Decimal("100")


def calculate_backtest_metrics(
    result: BacktestResult,
) -> BacktestMetrics:
    """
    Calculate the standard historical performance metrics.
    """

    profit_loss = result.profit_loss
    total_return = result.return_percent

    (
        max_drawdown,
        max_drawdown_percent,
    ) = calculate_max_drawdown(result)

    trade_profits = _trade_profit_losses(result)

    winning = [
        value
        for value in trade_profits
        if value > Decimal("0")
    ]

    losing = [
        value
        for value in trade_profits
        if value < Decimal("0")
    ]

    trade_count = len(trade_profits)

    if trade_count:
        win_rate = (
            Decimal(len(winning))
            / Decimal(trade_count)
        ) * Decimal("100")
    else:
        win_rate = Decimal("0")

    if winning:
        average_winning = (
            sum(winning)
            / Decimal(len(winning))
        )
    else:
        average_winning = Decimal("0")

    if losing:
        average_losing = (
            sum(losing)
            / Decimal(len(losing))
        )
    else:
        average_losing = Decimal("0")

    gross_profit = sum(winning)
    gross_loss = abs(sum(losing))

    if gross_loss > Decimal("0"):
        profit_factor = (
            gross_profit / gross_loss
        )
    elif gross_profit > Decimal("0"):
        profit_factor = None
    else:
        profit_factor = Decimal("0")

    return BacktestMetrics(
        total_return=total_return,
        profit_loss=profit_loss,
        max_drawdown=max_drawdown,
        max_drawdown_percent=max_drawdown_percent,
        trade_count=trade_count,
        winning_trades=len(winning),
        losing_trades=len(losing),
        win_rate=win_rate,
        average_winning_trade=average_winning,
        average_losing_trade=average_losing,
        profit_factor=profit_factor,
        exposure_percent=_calculate_exposure(result),
        cagr=_calculate_cagr(result),
    )
