from decimal import Decimal

import pytest

from src.validation.ranking_validation import (
    RankingValidationResult,
)
from src.validation.walk_forward_evaluation import (
    WalkForwardEvaluation,
    evaluate_walk_forward,
)


def make_result(
    *,
    horizon: str = "LONG_TERM",
    average_return: str = "0.10",
    excess_return: str | None = "0.05",
    observations: int = 2,
) -> RankingValidationResult:
    return RankingValidationResult(
        horizon=horizon,
        observation_count=observations,
        average_forward_return=Decimal(average_return),
        median_forward_return=Decimal(average_return),
        positive_return_rate=Decimal("0.50"),
        average_excess_return=(
            Decimal(excess_return)
            if excess_return is not None
            else None
        ),
        positive_excess_return_rate=(
            Decimal("0.50")
            if excess_return is not None
            else None
        ),
        score_return_correlation=Decimal("0.50"),
    )


def test_evaluation_returns_metrics():
    result = evaluate_walk_forward(
        [
            make_result(average_return="0.10"),
            make_result(average_return="0.20"),
            make_result(average_return="0.05"),
        ]
    )

    assert isinstance(result, WalkForwardEvaluation)
    assert result.horizon == "LONG_TERM"
    assert result.window_count == 3
    assert result.observation_count == 6
    assert result.average_forward_return == Decimal(
        "0.1166666666666666666666666667"
    )


def test_consistent_positive_windows_are_robust():
    result = evaluate_walk_forward(
        [
            make_result(average_return="0.10"),
            make_result(average_return="0.20"),
            make_result(average_return="0.05"),
        ]
    )

    assert result.robust is True
    assert result.consistency_rate == Decimal("1")


def test_mostly_negative_windows_are_not_robust():
    result = evaluate_walk_forward(
        [
            make_result(average_return="0.10"),
            make_result(average_return="-0.20"),
            make_result(average_return="-0.05"),
        ]
    )

    assert result.robust is False
    assert result.consistency_rate == Decimal(
        "0.3333333333333333333333333333"
    )


def test_insufficient_windows_are_not_robust():
    result = evaluate_walk_forward(
        [
            make_result(average_return="0.10"),
            make_result(average_return="0.20"),
        ]
    )

    assert result.robust is False
    assert result.window_count == 2


def test_positive_excess_window_rate():
    result = evaluate_walk_forward(
        [
            make_result(excess_return="0.10"),
            make_result(excess_return="-0.05"),
            make_result(excess_return="0.02"),
        ]
    )

    assert result.positive_excess_window_rate == Decimal(
        "0.6666666666666666666666666667"
    )


def test_missing_excess_returns_remain_none():
    result = evaluate_walk_forward(
        [
            make_result(excess_return=None),
            make_result(excess_return=None),
            make_result(excess_return=None),
        ]
    )

    assert result.positive_excess_window_rate is None


def test_custom_robustness_threshold():
    result = evaluate_walk_forward(
        [
            make_result(average_return="0.10"),
            make_result(average_return="-0.05"),
            make_result(average_return="0.20"),
        ],
        minimum_successful_window_rate=Decimal("0.75"),
    )

    assert result.robust is False


def test_empty_results_are_rejected():
    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        evaluate_walk_forward([])


def test_invalid_window_count_is_rejected():
    with pytest.raises(
        ValueError,
        match="minimum_window_count",
    ):
        evaluate_walk_forward(
            [make_result()],
            minimum_window_count=0,
        )


def test_invalid_success_threshold_is_rejected():
    with pytest.raises(
        ValueError,
        match="between 0 and 1",
    ):
        evaluate_walk_forward(
            [make_result()],
            minimum_successful_window_rate=Decimal("1.1"),
        )


def test_mixed_horizons_are_rejected():
    with pytest.raises(
        ValueError,
        match="same horizon",
    ):
        evaluate_walk_forward(
            [
                make_result(horizon="LONG_TERM"),
                make_result(horizon="SWING"),
            ]
        )