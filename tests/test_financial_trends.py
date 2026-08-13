from datetime import date
from decimal import Decimal

from src.analysis.financial_trends import (
    compare_snapshots,
    compare_snapshot_series,
)
from src.data.company.financials import FinancialSnapshot

import pytest

from src.analysis.financial_trends import (
    FinancialTrend,
    compare_snapshots,
    compare_snapshot_series,
    multi_period_trends,
)

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


def test_pairwise_trend_calculates_percentage_change():
    previous = FinancialSnapshot(
        symbol="TCS",
        period_end=date(2025, 3, 31),
        revenue=Decimal("1000"),
    )

    current = FinancialSnapshot(
        symbol="TCS",
        period_end=date(2026, 3, 31),
        revenue=Decimal("1200"),
    )

    trends = compare_snapshots(
        previous,
        current,
    )

    revenue = next(
        trend
        for trend in trends
        if trend.metric == "revenue"
    )

    assert revenue.direction == "INCREASING"
    assert revenue.change == Decimal("200")
    assert revenue.percentage_change == Decimal("20")


def test_zero_base_does_not_create_fake_percentage():
    previous = FinancialSnapshot(
        symbol="TCS",
        period_end=date(2025, 3, 31),
        revenue=Decimal("0"),
    )

    current = FinancialSnapshot(
        symbol="TCS",
        period_end=date(2026, 3, 31),
        revenue=Decimal("100"),
    )

    trends = compare_snapshots(
        previous,
        current,
    )

    revenue = next(
        trend
        for trend in trends
        if trend.metric == "revenue"
    )

    assert revenue.percentage_change is None


def test_multi_period_trend_measures_persistence():
    snapshots = [
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2024, 3, 31),
            revenue=Decimal("800"),
        ),
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2025, 3, 31),
            revenue=Decimal("900"),
        ),
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2026, 3, 31),
            revenue=Decimal("1050"),
        ),
    ]

    trends = multi_period_trends(
        snapshots
    )

    revenue = next(
        trend
        for trend in trends
        if trend.metric == "revenue"
    )

    assert revenue.observations == 3
    assert revenue.direction == "INCREASING"
    assert revenue.persistence == Decimal("100")
    assert revenue.change == Decimal("250")


def test_multi_period_trend_measures_acceleration():
    snapshots = [
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2024, 3, 31),
            revenue=Decimal("800"),
        ),
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2025, 3, 31),
            revenue=Decimal("900"),
        ),
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2026, 3, 31),
            revenue=Decimal("1100"),
        ),
    ]

    trends = multi_period_trends(
        snapshots
    )

    revenue = next(
        trend
        for trend in trends
        if trend.metric == "revenue"
    )

    assert revenue.acceleration == Decimal("100")


def test_multi_period_trend_rejects_multiple_symbols():
    snapshots = [
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2025, 3, 31),
            revenue=Decimal("1000"),
        ),
        FinancialSnapshot(
            symbol="INFY",
            period_end=date(2026, 3, 31),
            revenue=Decimal("1200"),
        ),
    ]

    with pytest.raises(ValueError):
        multi_period_trends(
            snapshots
        )


def test_pairwise_trend_calculates_percentage_change():
    previous = FinancialSnapshot(
        symbol="TCS",
        period_end=date(2025, 3, 31),
        revenue=Decimal("1000"),
    )

    current = FinancialSnapshot(
        symbol="TCS",
        period_end=date(2026, 3, 31),
        revenue=Decimal("1200"),
    )

    trends = compare_snapshots(
        previous,
        current,
    )

    revenue = next(
        trend
        for trend in trends
        if trend.metric == "revenue"
    )

    assert revenue.direction == "INCREASING"
    assert revenue.change == Decimal("200")
    assert revenue.percentage_change == Decimal("20")


def test_zero_base_does_not_create_fake_percentage():
    previous = FinancialSnapshot(
        symbol="TCS",
        period_end=date(2025, 3, 31),
        revenue=Decimal("0"),
    )

    current = FinancialSnapshot(
        symbol="TCS",
        period_end=date(2026, 3, 31),
        revenue=Decimal("100"),
    )

    trends = compare_snapshots(
        previous,
        current,
    )

    revenue = next(
        trend
        for trend in trends
        if trend.metric == "revenue"
    )

    assert revenue.percentage_change is None


def test_multi_period_trend_measures_persistence():
    snapshots = [
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2024, 3, 31),
            revenue=Decimal("800"),
        ),
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2025, 3, 31),
            revenue=Decimal("900"),
        ),
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2026, 3, 31),
            revenue=Decimal("1050"),
        ),
    ]

    trends = multi_period_trends(
        snapshots
    )

    revenue = next(
        trend
        for trend in trends
        if trend.metric == "revenue"
    )

    assert revenue.observations == 3
    assert revenue.direction == "INCREASING"
    assert revenue.persistence == Decimal("100")
    assert revenue.change == Decimal("250")


def test_multi_period_trend_measures_acceleration():
    snapshots = [
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2024, 3, 31),
            revenue=Decimal("800"),
        ),
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2025, 3, 31),
            revenue=Decimal("900"),
        ),
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2026, 3, 31),
            revenue=Decimal("1100"),
        ),
    ]

    trends = multi_period_trends(
        snapshots
    )

    revenue = next(
        trend
        for trend in trends
        if trend.metric == "revenue"
    )

    assert revenue.acceleration == Decimal("100")


def test_multi_period_trend_rejects_multiple_symbols():
    snapshots = [
        FinancialSnapshot(
            symbol="TCS",
            period_end=date(2025, 3, 31),
            revenue=Decimal("1000"),
        ),
        FinancialSnapshot(
            symbol="INFY",
            period_end=date(2026, 3, 31),
            revenue=Decimal("1200"),
        ),
    ]

    with pytest.raises(ValueError):
        multi_period_trends(
            snapshots
        )
