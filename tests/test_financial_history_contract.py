"""Tests for the financial history API contract and router."""

from datetime import date, datetime, timezone
from decimal import Decimal

from src.api.fundamentals_router import (
    build_financial_history,
)
from src.data.company.financials import FinancialSnapshot


def make_snapshot(
    period_end: str = "2026-03-31",
    revenue: str = "1000",
    net_profit: str = "100",
    operating_profit: str = "150",
    total_assets: str = "2000",
    total_debt: str = "500",
    shareholders_equity: str = "800",
    current_assets: str = "600",
    current_liabilities: str = "300",
    inventory: str = "100",
    operating_cash_flow: str = "120",
    free_cash_flow: str = "80",
    cash_and_equivalents: str = "200",
    receivables: str = "150",
    payables: str = "100",
) -> FinancialSnapshot:

    return FinancialSnapshot(
        symbol="TEST",
        period_end=date.fromisoformat(period_end),
        revenue=Decimal(revenue),
        net_profit=Decimal(net_profit),
        operating_profit=Decimal(operating_profit),
        total_assets=Decimal(total_assets),
        total_debt=Decimal(total_debt),
        shareholders_equity=Decimal(shareholders_equity),
        current_assets=Decimal(current_assets),
        current_liabilities=Decimal(current_liabilities),
        inventory=Decimal(inventory),
        operating_cash_flow=Decimal(operating_cash_flow),
        free_cash_flow=Decimal(free_cash_flow),
        cash_and_equivalents=Decimal(cash_and_equivalents),
        receivables=Decimal(receivables),
        payables=Decimal(payables),
    )


def test_build_financial_history_empty():
    as_of = datetime(2026, 8, 15, tzinfo=timezone.utc)
    history = build_financial_history(
        snapshots=[],
        symbol="TEST",
        as_of=as_of,
    )
    assert history.period_count == 0
    assert history.periods == []
    assert history.symbol == "TEST"
    assert len(history.notes) > 0


def test_build_financial_history_single_period():
    as_of = datetime(2026, 8, 15, tzinfo=timezone.utc)
    snapshot = make_snapshot()

    history = build_financial_history(
        snapshots=[snapshot],
        symbol="TEST",
        as_of=as_of,
    )

    assert history.period_count == 1
    assert len(history.periods) == 1

    period = history.periods[0]
    assert period.symbol == "TEST"
    assert period.period_end == "2026-03-31"

    metrics_by_name = {m.metric: m for m in period.metrics}
    assert "revenue" in metrics_by_name
    assert metrics_by_name["revenue"].available is True
    assert metrics_by_name["revenue"].value == "1000"

    assert "total_equity" in metrics_by_name
    assert metrics_by_name["total_equity"].available is False

    ratios_by_name = {r.ratio: r for r in period.ratios}
    assert "net_profit_margin" in ratios_by_name
    assert ratios_by_name["net_profit_margin"].available is True
    assert ratios_by_name["net_profit_margin"].value == "10.0"

    assert "return_on_equity" in ratios_by_name
    assert ratios_by_name["return_on_equity"].available is True


def test_build_financial_history_multi_period():
    as_of = datetime(2026, 8, 15, tzinfo=timezone.utc)

    snapshots = [
        make_snapshot(
            period_end="2025-03-31",
            revenue="900",
            net_profit="90",
        ),
        make_snapshot(
            period_end="2026-03-31",
            revenue="1000",
            net_profit="100",
        ),
    ]

    history = build_financial_history(
        snapshots=snapshots,
        symbol="TEST",
        as_of=as_of,
    )

    assert history.period_count == 2
    assert len(history.periods) == 2

    assert history.periods[0].period_end == "2025-03-31"
    assert history.periods[1].period_end == "2026-03-31"


def test_build_financial_history_coverage():
    as_of = datetime(2026, 8, 15, tzinfo=timezone.utc)
    snapshot = make_snapshot()

    history = build_financial_history(
        snapshots=[snapshot],
        symbol="TEST",
        as_of=as_of,
    )

    assert "revenue" in history.coverage
    assert history.coverage["revenue"] == 1
    assert "net_profit_margin" in history.coverage
    assert history.coverage["net_profit_margin"] == 1


def test_build_financial_history_missing_metrics():
    as_of = datetime(2026, 8, 15, tzinfo=timezone.utc)

    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        revenue=Decimal("1000"),
    )

    history = build_financial_history(
        snapshots=[snapshot],
        symbol="TEST",
        as_of=as_of,
    )

    assert "total_equity" in history.missing_metrics
    assert "current_assets" in history.missing_metrics
    assert "revenue" not in history.missing_metrics


def test_build_financial_history_as_of_serialization():
    as_of = datetime(2026, 8, 15, 10, 30, 0, tzinfo=timezone.utc)
    snapshot = make_snapshot()

    history = build_financial_history(
        snapshots=[snapshot],
        symbol="TEST",
        as_of=as_of,
    )

    assert "2026-08-15T10:30:00+00:00" in history.as_of


def test_build_financial_history_provenance():
    as_of = datetime(2026, 8, 15, tzinfo=timezone.utc)

    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        revenue=Decimal("1000"),
        source_name="Yahoo Finance",
        source_type="PROVIDER",
        available_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )

    history = build_financial_history(
        snapshots=[snapshot],
        symbol="TEST",
        as_of=as_of,
    )

    period = history.periods[0]
    assert period.source_name == "Yahoo Finance"
    assert period.source_type == "PROVIDER"
    assert period.available_at == "2026-07-01T00:00:00+00:00"

    metric = period.metrics[0]
    assert metric.as_of == "2026-07-01T00:00:00+00:00"
