from decimal import Decimal

import pytest

from src.validation.ranking_validation import (
    RankingValidationResult,
)
from src.validation.ranking_validation_report import (
    RankingValidationReport,
    build_ranking_validation_report,
)


def make_result(
    *,
    horizon: str = "LONG_TERM",
    average_return: str = "0.10",
    excess_return: str | None = "0.05",
    correlation: str | None = "0.50",
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
        score_return_correlation=(
            Decimal(correlation)
            if correlation is not None
            else None
        ),
    )


def test_builds_report():
    result = build_ranking_validation_report(
        [
            make_result(average_return="0.10"),
            make_result(average_return="0.20"),
            make_result(average_return="0.05"),
        ]
    )

    assert isinstance(result, RankingValidationReport)
    assert result.horizon == "LONG_TERM"
    assert result.window_count == 3
    assert result.observation_count == 6
    assert result.average_forward_return == Decimal(
        "0.1166666666666666666666666667"
    )
    assert result.robust is True


def test_positive_performance_creates_strengths():
    result = build_ranking_validation_report(
        [
            make_result(average_return="0.10"),
            make_result(average_return="0.20"),
            make_result(average_return="0.05"),
        ]
    )

    assert len(result.strengths) >= 3
    assert any(
        "positive" in item.lower()
        for item in result.strengths
    )


def test_negative_performance_creates_weaknesses():
    result = build_ranking_validation_report(
        [
            make_result(
                average_return="-0.10",
                excess_return="-0.05",
                correlation="-0.20",
            ),
            make_result(
                average_return="-0.20",
                excess_return="-0.10",
                correlation="-0.10",
            ),
            make_result(
                average_return="-0.05",
                excess_return="-0.02",
                correlation="-0.05",
            ),
        ]
    )

    assert result.robust is False
    assert len(result.weaknesses) >= 3


def test_missing_benchmark_is_unknown():
    result = build_ranking_validation_report(
        [
            make_result(
                excess_return=None,
            ),
            make_result(
                excess_return=None,
            ),
            make_result(
                excess_return=None,
            ),
        ]
    )

    assert result.average_excess_return is None
    assert any(
        "benchmark" in item.lower()
        for item in result.unknowns
    )


def test_missing_correlation_is_unknown():
    result = build_ranking_validation_report(
        [
            make_result(correlation=None),
            make_result(correlation=None),
            make_result(correlation=None),
        ]
    )

    assert result.average_score_return_correlation is None
    assert any(
        "correlation" in item.lower()
        for item in result.unknowns
    )


def test_insufficient_windows_are_reported():
    result = build_ranking_validation_report(
        [
            make_result(average_return="0.10"),
        ],
        minimum_window_count=3,
    )

    assert result.robust is False
    assert result.window_count == 1
    assert any(
        "minimum" in item.lower()
        for item in result.unknowns
    )


def test_weak_windows_are_reported():
    result = build_ranking_validation_report(
        [
            make_result(average_return="0.10"),
            make_result(average_return="-0.10"),
            make_result(average_return="0.20"),
        ]
    )

    assert result.weak_window_count == 1
    assert any(
        "window" in item.lower()
        for item in result.weaknesses
    )


def test_mixed_horizons_are_rejected():
    with pytest.raises(
        ValueError,
        match="same horizon",
    ):
        build_ranking_validation_report(
            [
                make_result(horizon="LONG_TERM"),
                make_result(horizon="SWING"),
            ]
        )


def test_empty_results_are_rejected():
    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        build_ranking_validation_report([])