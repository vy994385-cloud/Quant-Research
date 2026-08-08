from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.data.company.financials import FinancialSnapshot


@dataclass(frozen=True)
class FinancialTrend:
    """
    Normalized financial trend used by the research and risk layers.

    The first five fields are the stable public contract used by
    risk_signals.py and company_report.py.

    Additional period/value fields provide richer evidence for
    the research engine.
    """

    metric: str
    direction: str
    observations: int
    average_change: Decimal
    explanation: str

    symbol: str | None = None
    previous_period: date | None = None
    current_period: date | None = None
    previous_value: Decimal | None = None
    current_value: Decimal | None = None
    change: Decimal | None = None


_TRACKED_METRICS = (
    "revenue",
    "operating_profit",
    "net_profit",
    "operating_cash_flow",
    "free_cash_flow",
    "total_assets",
    "total_debt",
    "cash_and_equivalents",
    "receivables",
    "payables",
)


def _direction(metric: str, change: Decimal) -> str:
    """
    Describe the raw movement of a financial metric.

    We deliberately distinguish movement from interpretation.

    Increasing receivables, for example, are not automatically bad.
    Their significance depends on revenue growth, cash flow, margins,
    payment terms and the company's business model.
    """

    if change > 0:
        return "INCREASING"

    if change < 0:
        return "DECREASING"

    return "STABLE"


def _explanation(
    metric: str,
    direction: str,
    change: Decimal,
) -> str:
    if direction == "STABLE":
        return f"{metric} remained stable."

    movement = "increased" if direction == "INCREASING" else "decreased"

    return (
        f"{metric} {movement} by {abs(change)} "
        "between the two reporting periods."
    )


def compare_snapshots(
    previous: FinancialSnapshot,
    current: FinancialSnapshot,
) -> list[FinancialTrend]:
    """
    Compare two consecutive financial snapshots.

    Missing metrics are skipped rather than fabricated.
    """

    if previous.symbol != current.symbol:
        raise ValueError("Cannot compare different symbols")

    if current.period_end <= previous.period_end:
        raise ValueError(
            "Current snapshot must have a later period than previous snapshot"
        )

    trends: list[FinancialTrend] = []

    for metric in _TRACKED_METRICS:
        previous_value = getattr(previous, metric)
        current_value = getattr(current, metric)

        if previous_value is None or current_value is None:
            continue

        change = current_value - previous_value
        direction = _direction(metric, change)

        trends.append(
            FinancialTrend(
                metric=metric,
                direction=direction,
                observations=2,
                average_change=change,
                explanation=_explanation(
                    metric,
                    direction,
                    change,
                ),
                symbol=current.symbol,
                previous_period=previous.period_end,
                current_period=current.period_end,
                previous_value=previous_value,
                current_value=current_value,
                change=change,
            )
        )

    return trends


def compare_snapshot_series(
    snapshots: list[FinancialSnapshot],
) -> list[FinancialTrend]:
    """
    Compare consecutive financial snapshots chronologically.

    The caller's list is never modified.
    """

    if len(snapshots) < 2:
        return []

    ordered = sorted(
        snapshots,
        key=lambda snapshot: snapshot.period_end,
    )

    trends: list[FinancialTrend] = []

    for previous, current in zip(
        ordered,
        ordered[1:],
    ):
        trends.extend(
            compare_snapshots(
                previous,
                current,
            )
        )

    return trends
