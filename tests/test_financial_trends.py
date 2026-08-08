from datetime import date
from decimal import Decimal

from src.analysis.financial_trends import (
    compare_snapshots,
    compare_snapshot_series,
)
from src.data.company.financials import FinancialSnapshot


def make_snapshot(
    period_end,
    revenue,
    net_profit,
    operating_cash_flow,
    total_debt,
    receivables,
    payables,
):
    return FinancialSnapshot(
        symbol="TEST",
        period_end=period_end,
        revenue=Decimal(revenue),
        net_profit=Decimal(net_profit),
        operating_cash_flow=Decimal(operating_cash_flow),
        total_debt=Decimal(total_debt),
        receivables=Decimal(receivables),
        payables=Decimal(payables),
    )


def test_compare_snapshots_detects_revenue_growth():
    previous = make_snapshot(
        date(2025, 3, 31),
        "1000",
        "100",
        "120",
        "500",
        "100",
        "80",
    )

    current = make_snapshot(
        date(2026, 3, 31),
        "1200",
        "130",
        "140",
        "450",
        "110",
        "85",
    )

    trends = compare_snapshots(previous, current)

    revenue = next(
        trend for trend in trends
        if trend.metric == "revenue"
    )

    assert revenue.direction == "INCREASING"
    assert revenue.change == Decimal("200")


def test_compare_snapshots_detects_debt_reduction():
    previous = make_snapshot(
        date(2025, 3, 31),
        "1000",
        "100",
        "120",
        "500",
        "100",
        "80",
    )

    current = make_snapshot(
        date(2026, 3, 31),
        "1100",
        "120",
        "130",
        "400",
        "105",
        "85",
    )

    trends = compare_snapshots(previous, current)

    debt = next(
        trend for trend in trends
        if trend.metric == "total_debt"
    )

    assert debt.direction == "DECREASING"
    assert debt.change == Decimal("-100")


def test_compare_snapshots_detects_receivables_growth():
    previous = make_snapshot(
        date(2025, 3, 31),
        "1000",
        "100",
        "120",
        "500",
        "100",
        "80",
    )

    current = make_snapshot(
        date(2026, 3, 31),
        "1100",
        "120",
        "130",
        "500",
        "180",
        "85",
    )

    trends = compare_snapshots(previous, current)

    receivables = next(
        trend for trend in trends
        if trend.metric == "receivables"
    )

    assert receivables.direction == "INCREASING"
    assert receivables.change == Decimal("80")


def test_compare_snapshot_series_is_ordered():
    snapshots = [
        make_snapshot(
            date(2024, 3, 31),
            "800",
            "70",
            "90",
            "600",
            "90",
            "70",
        ),
        make_snapshot(
            date(2025, 3, 31),
            "1000",
            "100",
            "120",
            "500",
            "100",
            "80",
        ),
        make_snapshot(
            date(2026, 3, 31),
            "1200",
            "130",
            "140",
            "400",
            "110",
            "85",
        ),
    ]

    trends = compare_snapshot_series(snapshots)

    assert len(trends) > 0

    dates = [
        trend.current_period
        for trend in trends
    ]

    assert dates == sorted(dates)


def test_compare_snapshot_series_does_not_mutate_input():
    first = make_snapshot(
        date(2025, 3, 31),
        "1000",
        "100",
        "120",
        "500",
        "100",
        "80",
    )

    second = make_snapshot(
        date(2026, 3, 31),
        "1200",
        "130",
        "140",
        "400",
        "110",
        "85",
    )

    snapshots = [second, first]

    compare_snapshot_series(snapshots)

    assert snapshots == [second, first]
