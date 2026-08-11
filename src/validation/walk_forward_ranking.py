from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.validation.ranking_validation import (
    RankingObservation,
    RankingValidationResult,
    validate_rankings,
)


@dataclass(frozen=True)
class WalkForwardWindow:
    """
    One chronological walk-forward evaluation window.

    Training observations must occur before the validation
    observations. No future validation outcome may enter the
    historical training period.
    """

    training_start: date
    training_end: date
    validation_start: date
    validation_end: date

    def __post_init__(self) -> None:
        if self.training_start > self.training_end:
            raise ValueError(
                "training_start cannot be after training_end"
            )

        if self.validation_start > self.validation_end:
            raise ValueError(
                "validation_start cannot be after validation_end"
            )

        if self.training_end >= self.validation_start:
            raise ValueError(
                "training period must end before validation period"
            )


@dataclass(frozen=True)
class WalkForwardResult:
    """
    Aggregate result of chronological out-of-sample validation.
    """

    window_count: int
    observation_count: int
    window_results: tuple[RankingValidationResult, ...]

    @property
    def average_forward_return(self) -> Decimal:
        if not self.window_results:
            return Decimal("0")

        total = sum(
            (
                result.average_forward_return
                for result in self.window_results
            ),
            Decimal("0"),
        )

        return total / Decimal(len(self.window_results))

    @property
    def average_excess_return(self) -> Decimal | None:
        values = [
            result.average_excess_return
            for result in self.window_results
            if result.average_excess_return is not None
        ]

        if not values:
            return None

        return sum(values, Decimal("0")) / Decimal(len(values))


def validate_walk_forward(
    observations: list[RankingObservation],
    windows: list[WalkForwardWindow],
) -> WalkForwardResult:
    """
    Evaluate ranking observations using strictly chronological
    walk-forward validation.

    Each observation is assigned to exactly one validation window.

    Observations outside validation windows are ignored.

    No observation from a later validation period can be included
    in an earlier validation result.
    """

    if not windows:
        raise ValueError(
            "at least one walk-forward window is required"
        )

    ordered_windows = sorted(
        windows,
        key=lambda window: window.validation_start,
    )

    for previous, current in zip(
        ordered_windows,
        ordered_windows[1:],
    ):
        if previous.validation_end >= current.validation_start:
            raise ValueError(
                "walk-forward validation windows cannot overlap"
            )

    selected: list[RankingValidationResult] = []
    used_observation_ids: set[int] = set()

    for window in ordered_windows:
        window_observations: list[RankingObservation] = []

        for observation in observations:
            ranking_date = observation.ranking_date

            if (
                window.validation_start
                <= ranking_date
                <= window.validation_end
            ):
                observation_id = id(observation)

                if observation_id in used_observation_ids:
                    raise ValueError(
                        "observation belongs to multiple validation windows"
                    )

                used_observation_ids.add(observation_id)
                window_observations.append(observation)

        if not window_observations:
            continue

        selected.append(
            validate_rankings(window_observations)
        )

    return WalkForwardResult(
        window_count=len(selected),
        observation_count=sum(
            result.observation_count
            for result in selected
        ),
        window_results=tuple(selected),
    )


__all__ = [
    "WalkForwardWindow",
    "WalkForwardResult",
    "validate_walk_forward",
]