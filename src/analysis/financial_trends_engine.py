from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.analysis.financial_trends import (
    FinancialTrend,
    compare_snapshot_series,
)
from src.data.company.financials import FinancialSnapshot


@dataclass(frozen=True)
class FinancialTrendSummary:
    """
    Multi-period summary of one financial metric.

    This is descriptive research evidence only.
    It does not predict future returns.
    """

    metric: str
    direction: str
    observations: int
    average_change: Decimal
    positive_periods: int
    negative_periods: int
    stable_periods: int
    consistency: Decimal
    explanation: str


def _direction_from_average(
    average_change: Decimal,
) -> str:
    if average_change > 0:
        return "INCREASING"

    if average_change < 0:
        return "DECREASING"

    return "STABLE"


def _consistency(
    positive_periods: int,
    negative_periods: int,
    stable_periods: int,
) -> Decimal:
    total = (
        positive_periods
        + negative_periods
        + stable_periods
    )

    if total == 0:
        return Decimal("0")

    directional_periods = max(
        positive_periods,
        negative_periods,
    )

    return (
        Decimal(directional_periods)
        / Decimal(total)
    ) * Decimal("100")


def _summary_explanation(
    metric: str,
    direction: str,
    average_change: Decimal,
    consistency: Decimal,
    observations: int,
) -> str:
    if direction == "STABLE":
        return (
            f"{metric} remained broadly stable across "
            f"{observations} reporting observations."
        )

    movement = (
        "increased"
        if direction == "INCREASING"
        else "decreased"
    )

    return (
        f"{metric} {movement} by an average of "
        f"{abs(average_change)} per reporting interval "
        f"across {observations} observations, with "
        f"{consistency}% directional consistency."
    )


def summarize_trends(
    trends: list[FinancialTrend],
) -> list[FinancialTrendSummary]:
    """
    Aggregate pairwise financial trends by metric.

    The supplied list is never modified.
    """

    grouped: dict[str, list[FinancialTrend]] = {}

    for trend in trends:
        grouped.setdefault(
            trend.metric,
            [],
        ).append(trend)

    summaries: list[FinancialTrendSummary] = []

    for metric, metric_trends in grouped.items():
        changes = [
            trend.change
            if trend.change is not None
            else trend.average_change
            for trend in metric_trends
        ]

        average_change = (
            sum(changes)
            / Decimal(len(changes))
        )

        positive_periods = sum(
            change > 0
            for change in changes
        )

        negative_periods = sum(
            change < 0
            for change in changes
        )

        stable_periods = sum(
            change == 0
            for change in changes
        )

        direction = _direction_from_average(
            average_change,
        )

        consistency = _consistency(
            positive_periods,
            negative_periods,
            stable_periods,
        )

        summaries.append(
            FinancialTrendSummary(
                metric=metric,
                direction=direction,
                observations=len(changes) + 1,
                average_change=average_change,
                positive_periods=positive_periods,
                negative_periods=negative_periods,
                stable_periods=stable_periods,
                consistency=consistency,
                explanation=_summary_explanation(
                    metric,
                    direction,
                    average_change,
                    consistency,
                    len(changes) + 1,
                ),
            )
        )

    return summaries


def analyze_financial_trends(
    snapshots: list[FinancialSnapshot],
) -> list[FinancialTrendSummary]:
    """
    Analyze financial trends across multiple reporting periods.

    At least two snapshots are required to establish a change.
    """

    if len(snapshots) < 2:
        return []

    trends = compare_snapshot_series(
        snapshots,
    )

    if not trends:
        return []

    return summarize_trends(
        trends,
    )
