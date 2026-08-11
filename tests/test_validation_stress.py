from decimal import Decimal

import pytest

from src.validation.ranking_validation import (
    RankingValidationResult,
)
from src.validation.validation_stress import (
    ValidationStressResult,
    stress_test_validation,
)


def make_result(
    *,
    average_return: str = "0.10",
    excess_return: str | None = "0.05",
    correlation: str | None = "0.50",
    horizon: str = "LONG_TERM",
) -> RankingValidationResult:
    return RankingValidationResult(
        horizon=horizon,
        observation_count=2,
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


def test_stress_test_passes_valid_scenarios():
    result = stress_test_validation(
        {
            "positive": [
                make_result(),
                make_result(),
                make_result(),
            ],
            "negative": [
                make_result(average_return="-0.10"),
                make_result(average_return="-0.05"),
                make_result(average_return="-0.20"),
            ],
            "missing_benchmark": [
                make_result(excess_return=None),
                make_result(excess_return=None),
                make_result(excess_return=None),
            ],
        }
    )

    assert isinstance(
        result,
        ValidationStressResult,
    )
    assert result.scenario_count == 3
    assert result.passed_count == 3
    assert result.failed_count == 0
    assert result.pass_rate == Decimal("1")
    assert result.all_passed is True


def test_empty_scenarios_are_rejected():
    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        stress_test_validation({})


def test_invalid_empty_scenario_is_reported():
    result = stress_test_validation(
        {
            "empty": [],
        }
    )

    assert result.scenario_count == 1
    assert result.failed_count == 1
    assert result.passed_count == 0
    assert result.all_passed is False
    assert "empty" in result.failures[0]


def test_mixed_horizons_are_detected():
    result = stress_test_validation(
        {
            "mixed": [
                make_result(horizon="LONG_TERM"),
                make_result(horizon="SWING"),
            ]
        }
    )

    assert result.failed_count == 1
    assert result.all_passed is False
    assert "mixed" in result.failures[0]


def test_multiple_scenarios_are_evaluated_independently():
    result = stress_test_validation(
        {
            "valid": [
                make_result(),
                make_result(),
                make_result(),
            ],
            "invalid": [],
        }
    )

    assert result.scenario_count == 2
    assert result.passed_count == 1
    assert result.failed_count == 1
    assert result.pass_rate == Decimal("0.5")


def test_missing_correlation_is_allowed():
    result = stress_test_validation(
        {
            "no_correlation": [
                make_result(correlation=None),
                make_result(correlation=None),
                make_result(correlation=None),
            ]
        }
    )

    assert result.all_passed is True


def test_extreme_decimal_values_are_handled():
    result = stress_test_validation(
        {
            "extreme": [
                make_result(
                    average_return="999999999999.999999",
                    excess_return="999999999999.999999",
                    correlation="1",
                ),
                make_result(
                    average_return="-999999999999.999999",
                    excess_return="-999999999999.999999",
                    correlation="-1",
                ),
                make_result(
                    average_return="0",
                    excess_return="0",
                    correlation="0",
                ),
            ]
        }
    )

    assert result.all_passed is True


def test_failure_count_tracks_unique_scenarios():
    result = stress_test_validation(
        {
            "bad": [],
        }
    )

    assert result.failed_count == 1
    assert result.passed_count == 0