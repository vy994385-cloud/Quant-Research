from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.validation.ranking_validation import RankingValidationResult
from src.validation.walk_forward_metrics import (
    WalkForwardMetrics,
    aggregate_walk_forward_metrics,
)


@dataclass(frozen=True)
class WalkForwardEvaluation:
    """
    Research-level evaluation of chronological walk-forward
    validation results.

    This layer is descriptive. It does not optimize weights,
    alter observations, or generate trading instructions.
    """

    horizon: str
    metrics: WalkForwardMetrics

    robust: bool
    consistency_rate: Decimal
    positive_excess_window_rate: Decimal | None

    minimum_window_count: int = 3
    minimum_successful_window_rate: Decimal = Decimal("0.50")

    @property
    def window_count(self) -> int:
        return self.metrics.window_count

    @property
    def observation_count(self) -> int:
        return self.metrics.observation_count

    @property
    def average_forward_return(self) -> Decimal:
        return self.metrics.average_forward_return

    @property
    def average_excess_return(self) -> Decimal | None:
        return self.metrics.average_excess_return


def evaluate_walk_forward(
    results: list[RankingValidationResult],
    *,
    minimum_window_count: int = 3,
    minimum_successful_window_rate: Decimal = Decimal("0.50"),
) -> WalkForwardEvaluation:
    """
    Evaluate whether ranking performance is reasonably consistent
    across chronological validation windows.

    Robustness requires:

    1. At least the configured number of windows.
    2. At least the configured proportion of windows having
       positive average forward returns.

    This is deliberately conservative. It is a research-quality
    classification, not proof of predictive power.
    """

    if minimum_window_count <= 0:
        raise ValueError(
            "minimum_window_count must be positive"
        )

    if not (
        Decimal("0")
        <= minimum_successful_window_rate
        <= Decimal("1")
    ):
        raise ValueError(
            "minimum_successful_window_rate must be between 0 and 1"
        )

    if not results:
        raise ValueError(
            "at least one walk-forward result is required"
        )

    metrics = aggregate_walk_forward_metrics(results)

    successful_window_rate = (
        metrics.successful_window_rate
    )

    robust = (
        metrics.window_count >= minimum_window_count
        and successful_window_rate
        >= minimum_successful_window_rate
    )

    excess_results = [
        result.average_excess_return
        for result in results
        if result.average_excess_return is not None
    ]

    if excess_results:
        positive_excess_windows = sum(
            value > Decimal("0")
            for value in excess_results
        )

        positive_excess_window_rate = (
            Decimal(positive_excess_windows)
            / Decimal(len(excess_results))
        )
    else:
        positive_excess_window_rate = None

    return WalkForwardEvaluation(
        horizon=results[0].horizon,
        metrics=metrics,
        robust=robust,
        consistency_rate=successful_window_rate,
        positive_excess_window_rate=positive_excess_window_rate,
        minimum_window_count=minimum_window_count,
        minimum_successful_window_rate=(
            minimum_successful_window_rate
        ),
    )


__all__ = [
    "WalkForwardEvaluation",
    "evaluate_walk_forward",
]