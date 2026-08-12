from __future__ import annotations

from decimal import Decimal

from src.analysis.financial_anomalies import (
    FinancialAnomaly,
    analyze_financial_change,
)
from src.data.company.financials import FinancialSnapshot


def _clamp(value: Decimal) -> Decimal:
    return max(
        Decimal("0"),
        min(Decimal("100"), value),
    )


def _severity_penalty(severity: str) -> Decimal:
    penalties = {
        "LOW": Decimal("5"),
        "MEDIUM": Decimal("15"),
        "HIGH": Decimal("30"),
        "CRITICAL": Decimal("45"),
    }

    return penalties.get(
        severity.upper(),
        Decimal("0"),
    )


def financial_risk_score(
    snapshots: list[FinancialSnapshot],
) -> Decimal:
    """
    Convert observed financial anomalies into a normalized
    0-100 risk-quality score.

    Higher score = lower observed financial risk.

    This does not claim that an anomaly is fraud or misconduct.
    It only measures currently observed financial warning signals.
    """

    if len(snapshots) < 2:
        return Decimal("50")

    ordered = sorted(
        snapshots,
        key=lambda snapshot: snapshot.period_end,
    )

    penalty = Decimal("0")
    anomaly_count = 0

    for previous, current in zip(
        ordered,
        ordered[1:],
    ):
        anomalies = analyze_financial_change(
            previous,
            current,
        )

        anomaly_count += len(anomalies)

        for anomaly in anomalies:
            penalty += _severity_penalty(
                anomaly.severity
            )

    if anomaly_count == 0:
        return Decimal("90")

    return _clamp(
        Decimal("90") - penalty
    )


def financial_risk_signals(
    snapshots: list[FinancialSnapshot],
) -> list[FinancialAnomaly]:
    """
    Return the actual underlying financial anomalies so the
    research report can expose the evidence behind the score.
    """

    if len(snapshots) < 2:
        return []

    ordered = sorted(
        snapshots,
        key=lambda snapshot: snapshot.period_end,
    )

    signals: list[FinancialAnomaly] = []

    for previous, current in zip(
        ordered,
        ordered[1:],
    ):
        signals.extend(
            analyze_financial_change(
                previous,
                current,
            )
        )

    return signals
