from decimal import Decimal

import pytest

from src.validation.ranking_validation import (
    RankingValidationResult,
)
from src.validation.walk_forward_metrics import (
    WalkForwardMetrics,
    aggregate_walk_forward_metrics,
)


def make_result(
    *,
    horizon: str = "LONG_TERM",
    observations: int = 2,
    average_return: str = "0.10",
    median_return: str = "0.10",
    positive_rate: str = "0.50",
    excess_return: str | None = "0.05",
    positive_excess_rate: str | None = "0.50",
    correlation: str | None = "0.80",
) -> RankingValidationResult:
    return RankingValidationResult(
        horizon=horizon,
        observation_count=observations,
        average_forward_return=Decimal(average_return),
        median_forward_return=Decimal(median_return),
        positive_return_rate=Decimal(positive_rate),
        average_excess_return=(
            Decimal(excess_return)
            if excess_return is not None
            else None
        ),
        positive_excess_return_rate=(
            Decimal(positive_excess_rate)
            if positive_excess_rate is not None
            else None
        ),
        score_return_correlation=(
            Decimal(correlation)
            if correlation is not None
            else None
        ),
    )


def test_aggregates_basic_metrics():
    result = aggregate_walk_forward_metrics(
        [
            make_result(
                observations=2,
                average_return="0.10",
                median_return="0.10",
                positive_rate="1",
            ),
            make_result(
                observations=4,
                average_return="0.20",
                median_return="0.20",
                positive_rate="0.50",
            ),
        ]
    )

    assert isinstance(result, WalkForwardMetrics)
    assert result.window_count == 2
    assert result.observation_count == 6
    assert result.average_forward_return == Decimal("0.15")
    assert result.median_forward_return == Decimal("0.15")
    assert result.positive_return_rate == Decimal("0.75")


def test_aggregates_excess_return_metrics():
    result = aggregate_walk_forward_metrics(
        [
            make_result(
                excess_return="0.10",
                positive_excess_rate="1",
            ),
            make_result(
                excess_return="-0.02",
                positive_excess_rate="0",
            ),
        ]
    )

    assert result.average_excess_return == Decimal("0.04")
    assert result.positive_excess_return_rate == Decimal("0.5")


def test_aggregates_correlations():
    result = aggregate_walk_forward_metrics(
        [
            make_result(correlation="1"),
            make_result(correlation="0.5"),
        ]
    )

    assert result.average_score_return_correlation == Decimal("0.75")


def test_missing_excess_returns_remain_none():
    result = aggregate_walk_forward_metrics(
        [
            make_result(
                excess_return=None,
                positive_excess_rate=None,
            ),
            make_result(
                excess_return=None,
                positive_excess_rate=None,
            ),
        ]
    )

    assert result.average_excess_return is None
    assert result.positive_excess_return_rate is None


def test_missing_correlations_remain_none():
    result = aggregate_walk_forward_metrics(
        [
            make_result(correlation=None),
            make_result(correlation=None),
        ]
    )

    assert result.average_score_return_correlation is None


def test_successful_and_weak_windows_are_counted():
    result = aggregate_walk_forward_metrics(
        [
            make_result(average_return="0.10"),
            make_result(average_return="-0.05"),
            make_result(average_return="0"),
            make_result(average_return="0.20"),
        ]
    )

    assert result.successful_window_rate == Decimal("0.5")
    assert result.weak_window_count == 2


def test_empty_results_are_rejected():
    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        aggregate_walk_forward_metrics([])


def test_mixed_horizons_are_rejected():
    with pytest.raises(
        ValueError,
        match="same horizon",
    ):
        aggregate_walk_forward_metrics(
            [
                make_result(horizon="LONG_TERM"),
                make_result(horizon="SWING"),
            ]
        )


def test_zero_observation_results_are_rejected():
    with pytest.raises(
        ValueError,
        match="observations",
    ):
        aggregate_walk_forward_metrics(
            [
                make_result(observations=0),
            ]
        )