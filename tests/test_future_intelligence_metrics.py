from datetime import date
from decimal import Decimal

from src.validation.future_intelligence_metrics import (
    calculate_validation_metrics,
    compare_high_and_low_readiness,
    readiness_buckets,
)
from src.validation.future_intelligence_validation import (
    FutureIntelligenceValidationResult,
)


def make_result(
    readiness: str,
    outcome: str,
    *,
    valid: bool = True,
):
    return FutureIntelligenceValidationResult(
        symbol="TEST",
        observation_date=date(2025, 1, 1),
        outcome_date=date(2025, 4, 1),
        metric="revenue_growth",
        future_readiness=Decimal(readiness),
        outcome_value=Decimal(outcome),
        valid_temporal_order=valid,
    )


def test_empty_metrics_are_neutral():

    metrics = calculate_validation_metrics([])

    assert metrics.sample_count == 0
    assert metrics.average_outcome is None
    assert metrics.median_outcome is None
    assert metrics.positive_outcome_rate is None
    assert not metrics.has_sufficient_sample


def test_metrics_calculate_average_median_and_positive_rate():

    results = [
        make_result("70", "10"),
        make_result("70", "20"),
        make_result("70", "-5"),
        make_result("70", "15"),
        make_result("70", "5"),
    ]

    metrics = calculate_validation_metrics(results)

    assert metrics.sample_count == 5
    assert metrics.average_outcome == Decimal("9")
    assert metrics.median_outcome == Decimal("10")
    assert metrics.positive_outcome_rate == Decimal("0.8")
    assert metrics.minimum_outcome == Decimal("-5")
    assert metrics.maximum_outcome == Decimal("20")
    assert metrics.has_sufficient_sample


def test_invalid_results_are_not_used():

    results = [
        make_result("70", "10"),
        make_result("70", "100", valid=False),
    ]

    metrics = calculate_validation_metrics(results)

    assert metrics.sample_count == 1
    assert metrics.average_outcome == Decimal("10")


def test_readiness_buckets():

    results = [
        make_result("20", "5"),
        make_result("45", "10"),
        make_result("65", "15"),
        make_result("85", "20"),
    ]

    buckets = readiness_buckets(results)

    assert len(buckets) == 4

    assert buckets[0].bucket == "LOW"
    assert buckets[0].metrics.sample_count == 1

    assert buckets[1].bucket == "MODERATE"
    assert buckets[1].metrics.sample_count == 1

    assert buckets[2].bucket == "HIGH"
    assert buckets[2].metrics.sample_count == 1

    assert buckets[3].bucket == "VERY_HIGH"
    assert buckets[3].metrics.sample_count == 1


def test_readiness_bucket_boundary():

    results = [
        make_result("40", "10"),
        make_result("60", "20"),
        make_result("80", "30"),
    ]

    buckets = readiness_buckets(results)

    assert buckets[0].metrics.sample_count == 0
    assert buckets[1].metrics.sample_count == 1
    assert buckets[2].metrics.sample_count == 1
    assert buckets[3].metrics.sample_count == 1


def test_high_and_low_comparison():

    results = [
        make_result("20", "5"),
        make_result("30", "15"),
        make_result("70", "25"),
        make_result("90", "35"),
    ]

    comparison = compare_high_and_low_readiness(results)

    assert comparison.low_readiness.sample_count == 2
    assert comparison.high_readiness.sample_count == 2

    assert comparison.low_readiness.average_outcome == Decimal("10")
    assert comparison.high_readiness.average_outcome == Decimal("30")

    assert comparison.average_outcome_difference == Decimal("20")


def test_comparison_ignores_middle_group():

    results = [
        make_result("20", "5"),
        make_result("50", "100"),
        make_result("80", "25"),
    ]

    comparison = compare_high_and_low_readiness(results)

    assert comparison.low_readiness.average_outcome == Decimal("5")
    assert comparison.high_readiness.average_outcome == Decimal("25")


def test_insufficient_sample_is_explicit():

    results = [
        make_result("80", "10"),
        make_result("80", "20"),
    ]

    metrics = calculate_validation_metrics(results)

    assert metrics.sample_count == 2
    assert not metrics.has_sufficient_sample
