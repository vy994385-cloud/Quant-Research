from datetime import date
from decimal import Decimal

from src.backtest.metrics import (
    calculate_backtest_metrics,
    calculate_max_drawdown,
)
from src.backtest.models import (
    BacktestResult,
    BacktestTrade,
    EquityPoint,
)


def make_equity(
    values: list[str],
) -> tuple[EquityPoint, ...]:
    return tuple(
        EquityPoint(
            trading_date=date(2026, 1, index + 1),
            cash=Decimal(value),
            positions_value=Decimal("0"),
            equity=Decimal(value),
        )
        for index, value in enumerate(values)
    )


def test_max_drawdown_is_calculated():
    result = BacktestResult(
        initial_capital=Decimal("1000"),
        final_equity=Decimal("1100"),
        trades=(),
        equity_curve=make_equity(
            ["1000", "1200", "900", "1100"]
        ),
    )

    drawdown, drawdown_percent = calculate_max_drawdown(
        result
    )

    assert drawdown == Decimal("300")
    assert drawdown_percent == Decimal("25")


def test_profit_and_return_are_reported():
    result = BacktestResult(
        initial_capital=Decimal("1000"),
        final_equity=Decimal("1200"),
        trades=(),
        equity_curve=make_equity(
            ["1000", "1100", "1200"]
        ),
    )

    metrics = calculate_backtest_metrics(result)

    assert metrics.profit_loss == Decimal("200")
    assert metrics.total_return == Decimal("20")


def test_trade_statistics_are_calculated():
    trades = (
        BacktestTrade(
            symbol="TEST",
            trading_date=date(2026, 1, 1),
            side="LONG",
            quantity=Decimal("10"),
            price=Decimal("100"),
            transaction_cost=Decimal("0"),
        ),
        BacktestTrade(
            symbol="TEST",
            trading_date=date(2026, 1, 2),
            side="LONG",
            quantity=Decimal("10"),
            price=Decimal("120"),
            transaction_cost=Decimal("0"),
        ),
        BacktestTrade(
            symbol="TEST",
            trading_date=date(2026, 1, 3),
            side="LONG",
            quantity=Decimal("10"),
            price=Decimal("120"),
            transaction_cost=Decimal("0"),
        ),
        BacktestTrade(
            symbol="TEST",
            trading_date=date(2026, 1, 4),
            side="LONG",
            quantity=Decimal("10"),
            price=Decimal("110"),
            transaction_cost=Decimal("0"),
        ),
    )

    result = BacktestResult(
        initial_capital=Decimal("1000"),
        final_equity=Decimal("1100"),
        trades=trades,
        equity_curve=make_equity(
            ["1000", "1020", "1010", "1100"]
        ),
    )

    metrics = calculate_backtest_metrics(result)

    assert metrics.trade_count == 2
    assert metrics.winning_trades == 1
    assert metrics.losing_trades == 1
    assert metrics.win_rate == Decimal("50")
    assert metrics.profit_factor == Decimal("2")


def test_empty_trade_history_is_safe():
    result = BacktestResult(
        initial_capital=Decimal("1000"),
        final_equity=Decimal("1000"),
        trades=(),
        equity_curve=make_equity(
            ["1000", "1000"]
        ),
    )

    metrics = calculate_backtest_metrics(result)

    assert metrics.trade_count == 0
    assert metrics.win_rate == Decimal("0")
    assert metrics.average_winning_trade == Decimal("0")
    assert metrics.average_losing_trade == Decimal("0")
    assert metrics.profit_factor == Decimal("0")


def test_exposure_is_calculated():
    equity_curve = (
        EquityPoint(
            trading_date=date(2026, 1, 1),
            cash=Decimal("1000"),
            positions_value=Decimal("0"),
            equity=Decimal("1000"),
        ),
        EquityPoint(
            trading_date=date(2026, 1, 2),
            cash=Decimal("0"),
            positions_value=Decimal("1000"),
            equity=Decimal("1000"),
        ),
        EquityPoint(
            trading_date=date(2026, 1, 3),
            cash=Decimal("0"),
            positions_value=Decimal("1100"),
            equity=Decimal("1100"),
        ),
    )

    result = BacktestResult(
        initial_capital=Decimal("1000"),
        final_equity=Decimal("1100"),
        trades=(),
        equity_curve=equity_curve,
    )

    metrics = calculate_backtest_metrics(result)

    assert metrics.exposure_percent == (
        Decimal("200")
        / Decimal("3")
    )
