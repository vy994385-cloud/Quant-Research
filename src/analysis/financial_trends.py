from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.data.company.financials import FinancialSnapshot


@dataclass(frozen=True)
class FinancialTrend:
    """
    Normalized financial trend used by the research and risk layers.

    The original five fields remain the stable public contract.
    Additional fields provide richer multi-period evidence.
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

    percentage_change: Decimal | None = None
    persistence: Decimal | None = None
    acceleration: Decimal | None = None


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

    Persistence and acceleration are separate attributes.
    Direction therefore remains one of:

    INCREASING
    DECREASING
    STABLE
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

    movement = (
        "increased"
        if direction == "INCREASING"
        else "decreased"
    )

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
        raise ValueError(
            "Cannot compare different symbols"
        )

    if current.period_end <= previous.period_end:
        raise ValueError(
            "Current snapshot must have a later period "
            "than previous snapshot"
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
        percentage_change=_percentage_change(
            previous_value,
            current_value,
        ),
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


def _percentage_change(
    first_value: Decimal,
    last_value: Decimal,
) -> Decimal | None:
    """
    Calculate percentage change from first to last value.

    A zero starting value has no meaningful percentage change.
    """

    if first_value == 0:
        return None

    return (
        (last_value - first_value)
        / abs(first_value)
    ) * Decimal("100")


def _average_changes(
    values: list[tuple[date, Decimal]],
) -> list[Decimal]:
    """
    Return consecutive period changes.
    """

    return [
        current_value - previous_value
        for (_, previous_value), (_, current_value)
        in zip(values, values[1:])
    ]


def _persistence(
    changes: list[Decimal],
) -> Decimal:
    """
    Percentage of period-to-period changes moving in the
    same direction as the overall trend.

    For example:
        +100, +150 -> 100%
        +100, -50  -> 50%
    """

    if not changes:
        return Decimal("0")

    positive = sum(
        change > 0
        for change in changes
    )

    negative = sum(
        change < 0
        for change in changes
    )

    if positive == len(changes) or negative == len(changes):
        return Decimal("100")

    if positive >= negative:
        matching = positive
    else:
        matching = negative

    return (
        Decimal(matching)
        / Decimal(len(changes))
    ) * Decimal("100")


def _acceleration(
    changes: list[Decimal],
) -> Decimal | None:
    """
    Measure change in the period-to-period movement.

    With changes:
        +100, +200

    acceleration = +100.

    At least two changes are required.
    """

    if len(changes) < 2:
        return None

    return changes[-1] - changes[-2]


def multi_period_trends(
    snapshots: list[FinancialSnapshot],
) -> list[FinancialTrend]:
    """
    Analyze financial metrics across multiple reporting periods.

    The snapshots may be supplied in any order.

    All snapshots must belong to the same company.
    """

    if len(snapshots) < 2:
        return []

    symbols = {
        snapshot.symbol
        for snapshot in snapshots
    }

    if len(symbols) != 1:
        raise ValueError(
            "multi_period_trends requires snapshots "
            "for exactly one symbol"
        )

    symbol = next(iter(symbols))

    ordered = sorted(
        snapshots,
        key=lambda snapshot: snapshot.period_end,
    )

    results: list[FinancialTrend] = []

    for metric in _TRACKED_METRICS:
        values: list[tuple[date, Decimal]] = []

        for snapshot in ordered:
            value = getattr(snapshot, metric)

            if value is not None:
                values.append(
                    (
                        snapshot.period_end,
                        value,
                    )
                )

        if len(values) < 2:
            continue

        changes = _average_changes(values)

        first_date, first_value = values[0]
        last_date, last_value = values[-1]

        total_change = last_value - first_value

        percentage_change = _percentage_change(
            first_value,
            last_value,
        )

        direction = _direction(
            metric,
            total_change,
        )

        persistence = _persistence(
            changes
        )

        acceleration = _acceleration(
            changes
        )

        results.append(
            FinancialTrend(
                metric=metric,
                direction=direction,
                observations=len(values),
                average_change=(
                    sum(changes)
                    / Decimal(len(changes))
                ),
                explanation=(
                    f"{metric} is "
                    f"{direction.lower()} across "
                    f"{len(values)} reporting observations "
                    f"with {persistence:.2f}% directional "
                    "persistence."
                ),
                symbol=symbol,
                previous_period=first_date,
                current_period=last_date,
                previous_value=first_value,
                current_value=last_value,
                change=total_change,
                percentage_change=percentage_change,
                persistence=persistence,
                acceleration=acceleration,
            )
        )

    return results
