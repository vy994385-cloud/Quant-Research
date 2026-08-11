from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Iterable

from src.analysis.future_intelligence import (
    FutureTechnologyProfile,
    future_readiness_score,
)


@dataclass(frozen=True)
class FutureIntelligenceObservation:
    """
    Point-in-time future-intelligence observation.

    The profile represents information available on `as_of_date`.
    Outcomes must occur strictly after that date.
    """

    symbol: str
    as_of_date: date
    profile: FutureTechnologyProfile


@dataclass(frozen=True)
class FutureIntelligenceOutcome:
    """
    Historical outcome observed after a research snapshot.

    This layer intentionally stores outcomes separately from the
    research signal so validation cannot accidentally use future
    information when constructing the original profile.
    """

    symbol: str
    outcome_date: date
    metric: str
    value: Decimal


@dataclass(frozen=True)
class FutureIntelligenceValidationResult:
    """
    Descriptive validation result.

    This does not create a trading recommendation or ranking weight.
    """

    symbol: str
    observation_date: date
    outcome_date: date

    metric: str
    future_readiness: Decimal
    outcome_value: Decimal

    valid_temporal_order: bool

    @property
    def is_valid(self) -> bool:
        return (
            self.valid_temporal_order
            and self.observation_date < self.outcome_date
        )


def validate_temporal_order(
    *,
    observation_date: date,
    outcome_date: date,
) -> bool:
    """
    Require the outcome to occur strictly after the observation.

    Same-day outcomes are rejected because the available information
    ordering cannot safely be assumed from dates alone.
    """

    return observation_date < outcome_date


def validate_observation(
    observation: FutureIntelligenceObservation,
    outcome: FutureIntelligenceOutcome,
) -> FutureIntelligenceValidationResult:
    """
    Validate one point-in-time intelligence observation against
    one later historical outcome.

    Symbol matching and strict temporal ordering are mandatory.
    """

    observation_symbol = observation.symbol.strip().upper()
    outcome_symbol = outcome.symbol.strip().upper()

    if not observation_symbol:
        raise ValueError("observation symbol cannot be empty")

    if not outcome_symbol:
        raise ValueError("outcome symbol cannot be empty")

    if observation_symbol != outcome_symbol:
        raise ValueError(
            "observation and outcome symbols must match"
        )

    valid_temporal_order = validate_temporal_order(
        observation_date=observation.as_of_date,
        outcome_date=outcome.outcome_date,
    )

    return FutureIntelligenceValidationResult(
        symbol=observation_symbol,
        observation_date=observation.as_of_date,
        outcome_date=outcome.outcome_date,
        metric=outcome.metric,
        future_readiness=future_readiness_score(
            observation.profile
        ),
        outcome_value=outcome.value,
        valid_temporal_order=valid_temporal_order,
    )


def validate_observations(
    *,
    observations: Iterable[FutureIntelligenceObservation],
    outcomes: Iterable[FutureIntelligenceOutcome],
) -> list[FutureIntelligenceValidationResult]:
    """
    Match historical observations to later outcomes.

    Only observations with a strictly later outcome date are returned.

    The input iterables are never modified.
    """

    observation_list = list(observations)
    outcome_list = list(outcomes)

    results: list[FutureIntelligenceValidationResult] = []

    for observation in observation_list:
        for outcome in outcome_list:
            if (
                observation.symbol.strip().upper()
                != outcome.symbol.strip().upper()
            ):
                continue

            if outcome.outcome_date <= observation.as_of_date:
                continue

            results.append(
                validate_observation(
                    observation,
                    outcome,
                )
            )

    return sorted(
        results,
        key=lambda result: (
            result.symbol,
            result.observation_date,
            result.outcome_date,
            result.metric,
        ),
    )
