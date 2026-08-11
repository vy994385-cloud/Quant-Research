from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import median

from src.validation.ranking_validation import (
    RankingValidationResult,
)


@dataclass(frozen=True)
class WalkForwardMetrics:
    """
    Aggregate performance metrics across chronological
    walk-forward validation windows.

    This layer is descriptive only. It does not optimize
    ranking weights or modify historical observations.
    """

    window_count: int
    observation_count: int

    average_forward_return: Decimal
    median_forward_return: Decimal
    positive_return_rate: Decimal

    average_excess_return: Decimal | None
    positive_excess_return_rate: Decimal | None

    average_score_return_correlation: Decimal | None

    successful_window_rate: Decimal
    weak_window_count: int


def aggregate_walk_forward_metrics(
    results: list[RankingValidationResult],
) -> WalkForwardMetrics:
    """
    Aggregate already-computed ranking validation results.

    A window is considered successful when its average
    forward return is strictly positive.

    Missing excess-return or correlation values are ignored
    rather than converted into artificial zeros.
    """

    if not results:
        raise ValueError(
            "at least one walk-forward result is required"
        )

    horizons = {
        result.horizon
        for result in results
    }

    if len(horizons) != 1:
        raise ValueError(
            "all walk-forward results must use the same horizon"
        )

    observation_count = sum(
        result.observation_count
        for result in results
    )

    if observation_count <= 0:
        raise ValueError(
            "walk-forward results must contain observations"
        )

    forward_returns = [
        result.average_forward_return
        for result in results
    ]

    average_forward_return = (
        sum(forward_returns, Decimal("0"))
        / Decimal(len(forward_returns))
    )

    median_forward_return = Decimal(
        str(median(forward_returns))
    )

    positive_return_rate = (
        sum(
            result.positive_return_rate
            for result in results
        )
        / Decimal(len(results))
    )

    excess_returns = [
        result.average_excess_return
        for result in results
        if result.average_excess_return is not None
    ]

    if excess_returns:
        average_excess_return = (
            sum(excess_returns, Decimal("0"))
            / Decimal(len(excess_returns))
        )
    else:
        average_excess_return = None

    excess_rates = [
        result.positive_excess_return_rate
        for result in results
        if result.positive_excess_return_rate is not None
    ]

    if excess_rates:
        positive_excess_return_rate = (
            sum(excess_rates, Decimal("0"))
            / Decimal(len(excess_rates))
        )
    else:
        positive_excess_return_rate = None

    correlations = [
        result.score_return_correlation
        for result in results
        if result.score_return_correlation is not None
    ]

    if correlations:
        average_score_return_correlation = (
            sum(correlations, Decimal("0"))
            / Decimal(len(correlations))
        )
    else:
        average_score_return_correlation = None

    successful_window_count = sum(
        result.average_forward_return > Decimal("0")
        for result in results
    )

    successful_window_rate = (
        Decimal(successful_window_count)
        / Decimal(len(results))
    )

    weak_window_count = sum(
        result.average_forward_return <= Decimal("0")
        for result in results
    )

    return WalkForwardMetrics(
        window_count=len(results),
        observation_count=observation_count,
        average_forward_return=average_forward_return,
        median_forward_return=median_forward_return,
        positive_return_rate=positive_return_rate,
        average_excess_return=average_excess_return,
        positive_excess_return_rate=positive_excess_return_rate,
        average_score_return_correlation=(
            average_score_return_correlation
        ),
        successful_window_rate=successful_window_rate,
        weak_window_count=weak_window_count,
    )


__all__ = [
    "WalkForwardMetrics",
    "aggregate_walk_forward_metrics",
]