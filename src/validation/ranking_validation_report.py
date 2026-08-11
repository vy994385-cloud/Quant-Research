from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.validation.ranking_validation import RankingValidationResult
from src.validation.walk_forward_evaluation import (
    WalkForwardEvaluation,
    evaluate_walk_forward,
)


@dataclass(frozen=True)
class RankingValidationReport:
    """
    Auditable research report for out-of-sample ranking validation.

    Descriptive only. It does not optimize weights, predict returns,
    or produce BUY/SELL instructions.
    """

    horizon: str
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

    robust: bool

    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    unknowns: tuple[str, ...]

    minimum_window_count: int
    minimum_successful_window_rate: Decimal


def build_ranking_validation_report(
    results: list[RankingValidationResult],
    *,
    minimum_window_count: int = 3,
    minimum_successful_window_rate: Decimal = Decimal("0.50"),
) -> RankingValidationReport:
    """
    Convert chronological validation results into one auditable
    research report.

    No optimization or ranking-weight adjustment occurs here.
    """

    evaluation: WalkForwardEvaluation = evaluate_walk_forward(
        results,
        minimum_window_count=minimum_window_count,
        minimum_successful_window_rate=(
            minimum_successful_window_rate
        ),
    )

    metrics = evaluation.metrics

    strengths: list[str] = []
    weaknesses: list[str] = []
    unknowns: list[str] = []

    if metrics.average_forward_return > Decimal("0"):
        strengths.append(
            "Average forward return was positive across "
            "the validation windows."
        )
    else:
        weaknesses.append(
            "Average forward return was not positive across "
            "the validation windows."
        )

    if evaluation.consistency_rate >= Decimal("0.50"):
        strengths.append(
            "At least half of the validation windows produced "
            "positive average forward returns."
        )
    else:
        weaknesses.append(
            "Fewer than half of the validation windows produced "
            "positive average forward returns."
        )

    if (
        metrics.average_excess_return is not None
        and metrics.average_excess_return > Decimal("0")
    ):
        strengths.append(
            "Average excess return versus the supplied benchmark "
            "was positive."
        )
    elif metrics.average_excess_return is not None:
        weaknesses.append(
            "Average excess return versus the supplied benchmark "
            "was not positive."
        )
    else:
        unknowns.append(
            "Benchmark-relative performance could not be evaluated "
            "because excess-return data was unavailable."
        )

    if metrics.average_score_return_correlation is not None:
        if (
            metrics.average_score_return_correlation
            > Decimal("0")
        ):
            strengths.append(
                "Ranking score and realized forward return showed "
                "positive average correlation."
            )
        else:
            weaknesses.append(
                "Ranking score and realized forward return did not "
                "show positive average correlation."
            )
    else:
        unknowns.append(
            "Score-return correlation could not be evaluated."
        )

    if evaluation.robust:
        strengths.append(
            "The ranking passed the configured walk-forward "
            "robustness criteria."
        )
    else:
        weaknesses.append(
            "The ranking did not pass the configured walk-forward "
            "robustness criteria."
        )

    if metrics.weak_window_count > 0:
        weaknesses.append(
            f"{metrics.weak_window_count} validation window(s) "
            "had non-positive average forward returns."
        )

    if metrics.window_count < minimum_window_count:
        unknowns.append(
            "The number of validation windows is below the "
            "configured minimum for robustness assessment."
        )

    return RankingValidationReport(
        horizon=evaluation.horizon,
        window_count=metrics.window_count,
        observation_count=metrics.observation_count,
        average_forward_return=metrics.average_forward_return,
        median_forward_return=metrics.median_forward_return,
        positive_return_rate=metrics.positive_return_rate,
        average_excess_return=metrics.average_excess_return,
        positive_excess_return_rate=(
            metrics.positive_excess_return_rate
        ),
        average_score_return_correlation=(
            metrics.average_score_return_correlation
        ),
        successful_window_rate=(
            metrics.successful_window_rate
        ),
        weak_window_count=metrics.weak_window_count,
        robust=evaluation.robust,
        strengths=tuple(strengths),
        weaknesses=tuple(weaknesses),
        unknowns=tuple(unknowns),
        minimum_window_count=minimum_window_count,
        minimum_successful_window_rate=(
            minimum_successful_window_rate
        ),
    )


__all__ = [
    "RankingValidationReport",
    "build_ranking_validation_report",
]