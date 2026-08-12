from datetime import date
from decimal import Decimal

from src.analysis.financial_risk_scoring import (
    financial_risk_score,
    financial_risk_signals,
)
from src.data.company.financials import FinancialSnapshot


def snapshot(
    period_end: date,
    revenue: str,
    receivables: str,
) -> FinancialSnapshot:
    return FinancialSnapshot(
        symbol="TCS",
        period_end=period_end,
        revenue=Decimal(revenue),
        net_profit=Decimal("200"),
        total_assets=Decimal("1000"),
        total_debt=Decimal("50"),
        free_cash_flow=Decimal("150"),
        receivables=Decimal(receivables),
        operating_cash_flow=Decimal("210"),
    )


def test_no_anomalies_have_high_risk_quality():
    previous = snapshot(
        date(2025, 3, 31),
        "1000",
        "100",
    )

    current = snapshot(
        date(2026, 3, 31),
        "1100",
        "105",
    )

    assert financial_risk_score(
        [previous, current]
    ) == Decimal("90")

    assert financial_risk_signals(
        [previous, current]
    ) == []


def test_receivables_divergence_creates_risk_signal():
    previous = snapshot(
        date(2025, 3, 31),
        "1000",
        "100",
    )

    current = snapshot(
        date(2026, 3, 31),
        "1050",
        "150",
    )

    signals = financial_risk_signals(
        [previous, current]
    )

    assert len(signals) == 1
    assert signals[0].metric == "receivables"
    assert signals[0].severity == "MEDIUM"


def test_anomaly_reduces_risk_quality_score():
    previous = snapshot(
        date(2025, 3, 31),
        "1000",
        "100",
    )

    current = snapshot(
        date(2026, 3, 31),
        "1050",
        "150",
    )

    score = financial_risk_score(
        [previous, current]
    )

    assert score < Decimal("90")
    assert score >= Decimal("0")


def test_insufficient_history_is_neutral():
    current = snapshot(
        date(2026, 3, 31),
        "1000",
        "100",
    )

    assert financial_risk_score(
        [current]
    ) == Decimal("50")
