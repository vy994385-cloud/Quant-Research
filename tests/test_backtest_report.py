from datetime import date, timedelta
from decimal import Decimal

from src.backtest.engine import BacktestEngine
from src.backtest.models import (
    BacktestBar,
    BacktestSignal,
)
from src.backtest.report import build_backtest_report


def make_bars(prices: list[str]) -> list[BacktestBar]:
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
    score: str = "80",
) -> BacktestSignal:
    return BacktestSignal(
        symbol="TEST",
        trading_date=date(2026, 1, day),
        action=action,
        score=Decimal(score),
    )


def run_profitable_backtest():
    bars = make_bars(
        ["100", "110", "120"]
    )

    signals = [
        make_signal(1, "BUY"),
        make_signal(3, "SELL"),
    ]

    return BacktestEngine(
        Decimal("1000")
    ).run(
        bars,
        signals,
    )


def test_build_report_contains_performance_summary():
    result = run_profitable_backtest()

    report = build_backtest_report(result)

    assert report.initial_capital == Decimal("1000")
    assert report.final_equity == Decimal("1200")
    assert report.profit_loss == Decimal("200")
    assert report.total_return == Decimal("20")
    assert report.trade_count == 1


def test_report_contains_trade_statistics():
    result = run_profitable_backtest()

    report = build_backtest_report(result)

    assert report.winning_trades == 1
    assert report.losing_trades == 0
    assert report.win_rate == Decimal("100")
    assert report.average_winning_trade == Decimal("200")
    assert report.average_losing_trade == Decimal("0")


def test_small_sample_is_explicitly_flagged():
    result = run_profitable_backtest()

    report = build_backtest_report(result)

    assert report.sample_size_warning is not None
    assert "small" in report.sample_size_warning.lower()


def test_report_is_not_a_trade_signal():
    result = run_profitable_backtest()

    report = build_backtest_report(result)

    assert report.is_trade_signal is False


def test_report_contains_validation_limitations():
    result = run_profitable_backtest()

    report = build_backtest_report(result)

    assert len(report.limitations) >= 4

    combined = " ".join(report.limitations).lower()

    assert "historical" in combined
    assert "out-of-sample" in combined
    assert "walk-forward" in combined


def test_no_trade_backtest_reports_insufficient_data():
    result = BacktestEngine(
        Decimal("1000")
    ).run(
        make_bars(["100", "105", "110"]),
        [],
    )

    report = build_backtest_report(result)

    assert report.trade_count == 0
    assert report.research_signal == "INSUFFICIENT_DATA"
    assert report.sample_size_warning is not None
    assert report.is_trade_signal is False


def test_negative_historical_result_is_classified_descriptively():
    result = BacktestEngine(
        Decimal("1000")
    ).run(
        make_bars(["100", "90"]),
        [
            make_signal(1, "BUY"),
            make_signal(2, "SELL"),
        ],
    )

    report = build_backtest_report(result)

    assert report.profit_loss < Decimal("0")
    assert report.research_signal == "HISTORICALLY_NEGATIVE"
    assert report.is_trade_signal is False


def test_report_can_include_benchmark_comparison():
    result = run_profitable_backtest()


    from src.backtest.benchmark import calculate_benchmark_result

    benchmark = calculate_benchmark_result(
        result,
        [
            BacktestBar(
                symbol="BENCH",
                trading_date=date(2026, 1, 1),
                close=Decimal("100"),
            ),
            BacktestBar(
                symbol="BENCH",
                trading_date=date(2026, 1, 2),
                close=Decimal("105"),
            ),
            BacktestBar(
                symbol="BENCH",
                trading_date=date(2026, 1, 3),
                close=Decimal("110"),
            ),
        ],
    )

    report = build_backtest_report(
        result,
        benchmark=benchmark,
    )

    assert report.has_benchmark
    assert report.benchmark is not None
    assert report.benchmark.benchmark_symbol == "BENCH"
    assert report.benchmark.benchmark_return == Decimal("10")
    assert report.benchmark.strategy_return == Decimal("20")
    assert report.benchmark.excess_return == Decimal("10")
    assert report.outperformed_benchmark is True


def test_report_without_benchmark_remains_backward_compatible():
    result = run_profitable_backtest()

    report = build_backtest_report(result)

    assert report.benchmark is None
    assert report.has_benchmark is False
    assert report.outperformed_benchmark is None
