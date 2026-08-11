from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import median

from src.validation.future_intelligence_validation import (
    FutureIntelligenceValidationResult,
)


@dataclass(frozen=True)
class ValidationMetrics:
    """
    Descriptive historical validation statistics.

    These metrics evaluate whether an existing research signal
    contains useful information. They do not create a trading
    recommendation or modify the ranking model.
    """

    sample_count: int
    average_outcome: Decimal | None
    median_outcome: Decimal | None
    positive_outcome_rate: Decimal | None
    minimum_outcome: Decimal | None
    maximum_outcome: Decimal | None

    @property
    def has_sufficient_sample(self) -> bool:
        return self.sample_count >= 5


@dataclass(frozen=True)
class ReadinessBucketMetrics:
    """
    Outcome statistics for one future-readiness bucket.
    """

    bucket: str
    minimum_score: Decimal
    maximum_score: Decimal
    metrics: ValidationMetrics


@dataclass(frozen=True)
class ValidationComparison:
    """
    Comparison between high-readiness and low-readiness groups.

    This is descriptive validation only.
    """

    high_readiness: ValidationMetrics
    low_readiness: ValidationMetrics

    @property
    def average_outcome_difference(self) -> Decimal | None:
        if (
            self.high_readiness.average_outcome is None
            or self.low_readiness.average_outcome is None
        ):
            return None

        return (
            self.high_readiness.average_outcome
            - self.low_readiness.average_outcome
        )


def _metrics(
    values: list[Decimal],
) -> ValidationMetrics:
    if not values:
        return ValidationMetrics(
            sample_count=0,
            average_outcome=None,
            median_outcome=None,
            positive_outcome_rate=None,
            minimum_outcome=None,
            maximum_outcome=None,
        )

    positive_count = sum(
        value > 0
        for value in values
    )

    return ValidationMetrics(
        sample_count=len(values),
        average_outcome=(
            sum(values, Decimal("0"))
            / Decimal(len(values))
        ),
        median_outcome=Decimal(
            str(median(values))
        ),
        positive_outcome_rate=(
            Decimal(positive_count)
            / Decimal(len(values))
        ),
        minimum_outcome=min(values),
        maximum_outcome=max(values),
    )


def calculate_validation_metrics(
    results: list[FutureIntelligenceValidationResult],
) -> ValidationMetrics:
    """
    Calculate descriptive statistics across validated outcomes.

    Invalid temporal observations are ignored rather than repaired.
    """

    values = [
        result.outcome_value
        for result in results
        if result.is_valid
    ]

    return _metrics(values)


def readiness_buckets(
    results: list[FutureIntelligenceValidationResult],
) -> list[ReadinessBucketMetrics]:
    """
    Group validated observations into conservative readiness buckets.

        LOW       < 40
        MODERATE  40-59.99
        HIGH      60-79.99
        VERY_HIGH >= 80

    Bucket boundaries are descriptive and are not ranking weights.
    """

    definitions = (
        (
            "LOW",
            Decimal("0"),
            Decimal("40"),
        ),
        (
            "MODERATE",
            Decimal("40"),
            Decimal("60"),
        ),
        (
            "HIGH",
            Decimal("60"),
            Decimal("80"),
        ),
        (
            "VERY_HIGH",
            Decimal("80"),
            Decimal("100.000001"),
        ),
    )

    output: list[ReadinessBucketMetrics] = []

    valid_results = [
        result
        for result in results
        if result.is_valid
    ]

    for name, minimum, maximum in definitions:

        values = [
            result.outcome_value
            for result in valid_results
            if (
                result.future_readiness >= minimum
                and result.future_readiness < maximum
            )
        ]

        output.append(
            ReadinessBucketMetrics(
                bucket=name,
                minimum_score=minimum,
                maximum_score=(
                    Decimal("100")
                    if name == "VERY_HIGH"
                    else maximum
                ),
                metrics=_metrics(values),
            )
        )

    return output


def compare_high_and_low_readiness(
    results: list[FutureIntelligenceValidationResult],
    *,
    low_maximum: Decimal = Decimal("40"),
    high_minimum: Decimal = Decimal("60"),
) -> ValidationComparison:
    """
    Compare low-readiness and high-readiness observations.

    The caller can override thresholds for research experiments.
    """

    valid_results = [
        result
        for result in results
        if result.is_valid
    ]

    low_values = [
        result.outcome_value
        for result in valid_results
        if result.future_readiness < low_maximum
    ]

    high_values = [
        result.outcome_value
        for result in valid_results
        if result.future_readiness >= high_minimum
    ]

    return ValidationComparison(
        high_readiness=_metrics(high_values),
        low_readiness=_metrics(low_values),
    )
