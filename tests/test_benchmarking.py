from datetime import date
from decimal import Decimal

from src.analysis.benchmarking import (
    benchmark_metric,
    benchmark_standard_metrics,
    median,
    percentile_rank,
)
from src.data.company.financials import FinancialSnapshot


def make_snapshot(
    revenue: str,
    debt: str,
) -> FinancialSnapshot:

    return FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        revenue=Decimal(revenue),
        total_debt=Decimal(debt),
    )


def test_median_odd_values():

    values = [
        Decimal("10"),
        Decimal("30"),
        Decimal("20"),
    ]

    assert median(values) == Decimal("20")


def test_median_even_values():

    values = [
        Decimal("10"),
        Decimal("20"),
        Decimal("30"),
        Decimal("40"),
    ]

    assert median(values) == Decimal("25")


def test_percentile_rank():

    values = [
        Decimal("10"),
        Decimal("20"),
        Decimal("30"),
        Decimal("40"),
    ]

    assert percentile_rank(
        Decimal("30"),
        values,
    ) == Decimal("75")


def test_benchmark_above_peer_median():

    company = make_snapshot(
        revenue="200",
        debt="50",
    )

    peers = [
        make_snapshot(
            revenue="100",
            debt="30",
        ),
        make_snapshot(
            revenue="120",
            debt="35",
        ),
        make_snapshot(
            revenue="140",
            debt="40",
        ),
    ]

    result = benchmark_metric(
        company,
        peers,
        "revenue",
    )

    assert result is not None
    assert result.peer_median == Decimal("120")
    assert result.relative_to_peers == "ABOVE_PEER_MEDIAN"


def test_benchmark_below_peer_median():

    company = make_snapshot(
        revenue="50",
        debt="50",
    )

    peers = [
        make_snapshot(
            revenue="100",
            debt="30",
        ),
        make_snapshot(
            revenue="120",
            debt="35",
        ),
        make_snapshot(
            revenue="140",
            debt="40",
        ),
    ]

    result = benchmark_metric(
        company,
        peers,
        "revenue",
    )

    assert result is not None
    assert result.relative_to_peers == "BELOW_PEER_MEDIAN"


def test_standard_benchmarking():

    company = make_snapshot(
        revenue="200",
        debt="50",
    )

    peers = [
        make_snapshot(
            revenue="100",
            debt="30",
        ),
        make_snapshot(
            revenue="120",
            debt="35",
        ),
        make_snapshot(
            revenue="140",
            debt="40",
        ),
    ]

    results = benchmark_standard_metrics(
        company,
        peers,
    )

    metrics = {
        result.metric
        for result in results
    }

    assert "revenue" in metrics
    assert "total_debt" in metrics
