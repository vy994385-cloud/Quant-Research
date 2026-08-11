from datetime import date
from decimal import Decimal

import pytest

from src.validation.ranking_outcomes import (
    build_ranking_outcome,
)
from src.validation.ranking_validation import (
    RankingObservation,
)
from src.validation.walk_forward_ranking import (
    WalkForwardWindow,
    validate_walk_forward,
)


def make_observation(
    symbol: str,
    ranking_date: date,
    score: str,
    entry: str,
    outcome: str,
) -> RankingObservation:
    outcome_date = date(
        ranking_date.year,
        ranking_date.month + 3
        if ranking_date.month <= 9
        else 12,
        1,
    )

    result = build_ranking_outcome(
        symbol=symbol,
        ranking_date=ranking_date,
        outcome_date=outcome_date,
        horizon="LONG_TERM",
        entry_price=Decimal(entry),
        outcome_price=Decimal(outcome),
    )

    return RankingObservation(
        symbol=symbol,
        ranking_date=ranking_date,
        horizon="LONG_TERM",
        score=Decimal(score),
        outcome=result,
    )


def test_window_requires_chronological_order():
    with pytest.raises(
        ValueError,
        match="training_start",
    ):
        WalkForwardWindow(
            training_start=date(2024, 4, 1),
            training_end=date(2024, 1, 1),
            validation_start=date(2024, 5, 1),
            validation_end=date(2024, 6, 1),
        )


def test_validation_period_must_follow_training_period():
    with pytest.raises(
        ValueError,
        match="training period",
    ):
        WalkForwardWindow(
            training_start=date(2024, 1, 1),
            training_end=date(2024, 6, 1),
            validation_start=date(2024, 5, 1),
            validation_end=date(2024, 7, 1),
        )


def test_overlapping_windows_are_rejected():
    observations = [
        make_observation(
            "AAA",
            date(2024, 4, 1),
            "90",
            "100",
            "110",
        )
    ]

    windows = [
        WalkForwardWindow(
            training_start=date(2023, 1, 1),
            training_end=date(2024, 2, 1),
            validation_start=date(2024, 3, 1),
            validation_end=date(2024, 5, 1),
        ),
        WalkForwardWindow(
            training_start=date(2024, 2, 1),
            training_end=date(2024, 3, 1),
            validation_start=date(2024, 5, 1),
            validation_end=date(2024, 7, 1),
        ),
    ]

    with pytest.raises(
        ValueError,
        match="overlap",
    ):
        validate_walk_forward(
            observations,
            windows,
        )


def test_only_validation_period_observations_are_evaluated():
    observations = [
        make_observation(
            "AAA",
            date(2024, 2, 1),
            "90",
            "100",
            "150",
        ),
        make_observation(
            "BBB",
            date(2024, 4, 1),
            "80",
            "100",
            "110",
        ),
    ]

    windows = [
        WalkForwardWindow(
            training_start=date(2023, 1, 1),
            training_end=date(2024, 1, 31),
            validation_start=date(2024, 3, 1),
            validation_end=date(2024, 5, 1),
        )
    ]

    result = validate_walk_forward(
        observations,
        windows,
    )

    assert result.window_count == 1
    assert result.observation_count == 1
    assert result.window_results[0].observation_count == 1


def test_multiple_windows_are_aggregated():
    observations = [
        make_observation(
            "AAA",
            date(2024, 4, 1),
            "90",
            "100",
            "110",
        ),
        make_observation(
            "BBB",
            date(2024, 7, 1),
            "80",
            "100",
            "120",
        ),
    ]

    windows = [
        WalkForwardWindow(
            training_start=date(2023, 1, 1),
            training_end=date(2024, 3, 1),
            validation_start=date(2024, 4, 1),
            validation_end=date(2024, 5, 1),
        ),
        WalkForwardWindow(
            training_start=date(2024, 5, 2),
            training_end=date(2024, 6, 1),
            validation_start=date(2024, 7, 1),
            validation_end=date(2024, 8, 1),
        ),
    ]

    result = validate_walk_forward(
        observations,
        windows,
    )

    assert result.window_count == 2
    assert result.observation_count == 2
    assert result.average_forward_return == Decimal("0.15")


def test_empty_validation_windows_are_ignored():
    observations = [
        make_observation(
            "AAA",
            date(2024, 7, 1),
            "90",
            "100",
            "110",
        )
    ]

    windows = [
        WalkForwardWindow(
            training_start=date(2023, 1, 1),
            training_end=date(2024, 1, 1),
            validation_start=date(2024, 2, 1),
            validation_end=date(2024, 3, 1),
        ),
        WalkForwardWindow(
            training_start=date(2024, 3, 2),
            training_end=date(2024, 6, 1),
            validation_start=date(2024, 7, 1),
            validation_end=date(2024, 8, 1),
        ),
    ]

    result = validate_walk_forward(
        observations,
        windows,
    )

    assert result.window_count == 1
    assert result.observation_count == 1


def test_no_windows_are_rejected():
    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        validate_walk_forward([], [])