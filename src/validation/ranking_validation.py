from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import median

from src.validation.ranking_outcomes import RankingOutcome


@dataclass(frozen=True)
class RankingObservation:
    """
    A historical ranking paired with its realized future outcome.

    The ranking score must have been produced at ranking_date.
    The outcome must occur strictly after ranking_date.
    """

    symbol: str
    ranking_date: object
    horizon: str
    score: Decimal
    outcome: RankingOutcome

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        horizon = self.horizon.strip().upper()

        if not symbol:
            raise ValueError("symbol cannot be empty")

        if not horizon:
            raise ValueError("horizon cannot be empty")

        if self.outcome.symbol != symbol:
            raise ValueError(
                "ranking observation symbol does not match outcome symbol"
            )

        if self.outcome.ranking_date != self.ranking_date:
            raise ValueError(
                "ranking date does not match outcome ranking date"
            )

        if self.outcome.horizon != horizon:
            raise ValueError(
                "ranking horizon does not match outcome horizon"
            )

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "horizon", horizon)


@dataclass(frozen=True)
class RankingValidationResult:
    """
    Aggregate out-of-sample statistics for a set of ranking
    observations sharing the same horizon.
    """

    horizon: str
    observation_count: int
    average_forward_return: Decimal
    median_forward_return: Decimal
    positive_return_rate: Decimal
    average_excess_return: Decimal | None
    positive_excess_return_rate: Decimal | None
    score_return_correlation: Decimal | None


def _pearson_correlation(
    scores: list[Decimal],
    returns: list[Decimal],
) -> Decimal | None:
    if len(scores) != len(returns):
        raise ValueError(
            "scores and returns must have equal length"
        )

    if len(scores) < 2:
        return None

    mean_score = sum(scores, Decimal("0")) / Decimal(len(scores))
    mean_return = sum(returns, Decimal("0")) / Decimal(len(returns))

    numerator = sum(
        (score - mean_score) * (value - mean_return)
        for score, value in zip(scores, returns)
    )

    score_variance = sum(
        (score - mean_score) ** 2
        for score in scores
    )

    return_variance = sum(
        (value - mean_return) ** 2
        for value in returns
    )

    denominator = (
        score_variance * return_variance
    ) ** Decimal("0.5")

    if denominator == Decimal("0"):
        return None

    return numerator / denominator


def validate_rankings(
    observations: list[RankingObservation],
) -> RankingValidationResult:
    """
    Evaluate realized outcomes associated with historical rankings.

    This function does not modify scores or optimize weights.
    It only measures what happened after each ranking observation.
    """

    if not observations:
        raise ValueError(
            "at least one ranking observation is required"
        )

    horizons = {
        observation.horizon
        for observation in observations
    }

    if len(horizons) != 1:
        raise ValueError(
            "all observations must use the same horizon"
        )

    for observation in observations:
        if observation.outcome.outcome_date <= observation.ranking_date:
            raise ValueError(
                "outcome must occur after ranking date"
            )

    horizon = observations[0].horizon

    forward_returns = [
        observation.outcome.forward_return
        for observation in observations
    ]

    average_forward_return = (
        sum(forward_returns, Decimal("0"))
        / Decimal(len(forward_returns))
    )

    median_forward_return = Decimal(
        str(median(forward_returns))
    )

    positive_return_rate = (
        Decimal(
            sum(
                value > Decimal("0")
                for value in forward_returns
            )
        )
        / Decimal(len(forward_returns))
    )

    excess_returns = [
        observation.outcome.excess_return
        for observation in observations
        if observation.outcome.excess_return is not None
    ]

    if excess_returns:
        average_excess_return = (
            sum(excess_returns, Decimal("0"))
            / Decimal(len(excess_returns))
        )

        positive_excess_return_rate = (
            Decimal(
                sum(
                    value > Decimal("0")
                    for value in excess_returns
                )
            )
            / Decimal(len(excess_returns))
        )
    else:
        average_excess_return = None
        positive_excess_return_rate = None

    score_return_correlation = _pearson_correlation(
        [
            observation.score
            for observation in observations
        ],
        forward_returns,
    )

    return RankingValidationResult(
        horizon=horizon,
        observation_count=len(observations),
        average_forward_return=average_forward_return,
        median_forward_return=median_forward_return,
        positive_return_rate=positive_return_rate,
        average_excess_return=average_excess_return,
        positive_excess_return_rate=positive_excess_return_rate,
        score_return_correlation=score_return_correlation,
    )


__all__ = [
    "RankingObservation",
    "RankingValidationResult",
    "validate_rankings",
]