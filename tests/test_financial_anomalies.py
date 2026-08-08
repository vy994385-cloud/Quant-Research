from datetime import date
from decimal import Decimal

from src.analysis.financial_anomalies import (
    analyze_financial_change,
    percentage_change,
)
from src.data.company.financials import FinancialSnapshot


def make_snapshot(
    *,
    revenue: str,
    receivables: str,
    payables: str,
) -> FinancialSnapshot:

    return FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        revenue=Decimal(revenue),
        receivables=Decimal(receivables),
        payables=Decimal(payables),
    )


def test_percentage_change():
    result = percentage_change(
        Decimal("100"),
        Decimal("120"),
    )

    assert result == Decimal("20")


def test_detects_receivables_divergence():

    previous = make_snapshot(
        revenue="1000",
        receivables="100",
        payables="100",
    )

    current = make_snapshot(
        revenue="1080",
        receivables="140",
        payables="105",
    )

    anomalies = analyze_financial_change(
        previous,
        current,
    )

    assert len(anomalies) == 1

    assert anomalies[0].metric == "receivables"
    assert anomalies[0].severity == "MEDIUM"


def test_normal_receivables_growth_is_not_flagged():

    previous = make_snapshot(
        revenue="1000",
        receivables="100",
        payables="100",
    )

    current = make_snapshot(
        revenue="1200",
        receivables="120",
        payables="110",
    )

    anomalies = analyze_financial_change(
        previous,
        current,
    )

    assert anomalies == []
