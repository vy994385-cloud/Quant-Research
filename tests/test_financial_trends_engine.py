from datetime import date
from decimal import Decimal

from src.analysis.financial_trends import FinancialTrend
from src.analysis.financial_trends_engine import (
    analyze_financial_trends,
    summarize_trends,
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


def test_summarize_trends_groups_same_metric():
    trends = [
        FinancialTrend(
            metric="revenue",
            direction="INCREASING",
            observations=2,
            average_change=Decimal("100"),
            explanation="Revenue increased.",
            change=Decimal("100"),
        ),
        FinancialTrend(
            metric="revenue",
            direction="INCREASING",
            observations=2,
            average_change=Decimal("200"),
            explanation="Revenue increased.",
            change=Decimal("200"),
        ),
    ]

    summaries = summarize_trends(trends)

    assert len(summaries) == 1

    revenue = summaries[0]

    assert revenue.metric == "revenue"
    assert revenue.direction == "INCREASING"
    assert revenue.observations == 3
    assert revenue.average_change == Decimal("150")
    assert revenue.positive_periods == 2
    assert revenue.negative_periods == 0
    assert revenue.stable_periods == 0
    assert revenue.consistency == Decimal("100")


def test_summarize_trends_detects_mixed_direction():
    trends = [
        FinancialTrend(
            metric="revenue",
            direction="INCREASING",
            observations=2,
            average_change=Decimal("100"),
            explanation="Revenue increased.",
            change=Decimal("100"),
        ),
        FinancialTrend(
            metric="revenue",
            direction="DECREASING",
            observations=2,
            average_change=Decimal("-20"),
            explanation="Revenue decreased.",
            change=Decimal("-20"),
        ),
    ]

    summaries = summarize_trends(trends)

    revenue = summaries[0]

    assert revenue.direction == "INCREASING"
    assert revenue.average_change == Decimal("40")
    assert revenue.positive_periods == 1
    assert revenue.negative_periods == 1
    assert revenue.consistency == Decimal("50")


def test_summarize_trends_detects_stable_metric():
    trends = [
        FinancialTrend(
            metric="cash_and_equivalents",
            direction="STABLE",
            observations=2,
            average_change=Decimal("0"),
            explanation="Cash remained stable.",
            change=Decimal("0"),
        ),
        FinancialTrend(
            metric="cash_and_equivalents",
            direction="STABLE",
            observations=2,
            average_change=Decimal("0"),
            explanation="Cash remained stable.",
            change=Decimal("0"),
        ),
    ]

    summaries = summarize_trends(trends)

    cash = summaries[0]

    assert cash.direction == "STABLE"
    assert cash.average_change == Decimal("0")
    assert cash.stable_periods == 2
    assert cash.consistency == Decimal("0")


def test_analyze_financial_trends_uses_multiple_periods():
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

    summaries = analyze_financial_trends(
        snapshots,
    )

    revenue = next(
        summary
        for summary in summaries
        if summary.metric == "revenue"
    )

    assert revenue.direction == "INCREASING"
    assert revenue.average_change == Decimal("200")
    assert revenue.observations == 3
    assert revenue.consistency == Decimal("100")


def test_analyze_financial_trends_handles_insufficient_data():
    snapshot = make_snapshot(
        date(2026, 3, 31),
        "1200",
        "130",
        "140",
        "400",
        "110",
        "85",
    )

    assert analyze_financial_trends(
        [snapshot],
    ) == []


def test_analyze_financial_trends_does_not_mutate_input():
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

    analyze_financial_trends(
        snapshots,
    )

    assert snapshots == [second, first]
