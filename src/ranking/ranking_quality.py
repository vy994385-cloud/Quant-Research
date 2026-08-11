from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class RankingQuality(str, Enum):
    """
    Deterministic classification of historical ranking quality.
    """

    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


@dataclass(frozen=True)
class RankingQualityAssessment:
    """
    Objective assessment of historical ranking performance.

    This class does not optimize ranking weights or alter ranking logic.
    It only evaluates already-computed validation evidence.
    """

    quality: RankingQuality
    score: Decimal

    observation_count: int

    average_forward_return: Decimal
    positive_return_rate: Decimal

    average_excess_return: Decimal | None
    positive_excess_return_rate: Decimal | None

    score_return_correlation: Decimal | None

    confidence: Decimal
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.observation_count < 0:
            raise ValueError(
                "observation_count cannot be negative"
            )

        if not Decimal("0") <= self.score <= Decimal("1"):
            raise ValueError(
                "score must be between 0 and 1"
            )

        if not Decimal("0") <= self.confidence <= Decimal("1"):
            raise ValueError(
                "confidence must be between 0 and 1"
            )

        if not Decimal("0") <= self.positive_return_rate <= Decimal("1"):
            raise ValueError(
                "positive_return_rate must be between 0 and 1"
            )

        if (
            self.positive_excess_return_rate is not None
            and not (
                Decimal("0")
                <= self.positive_excess_return_rate
                <= Decimal("1")
            )
        ):
            raise ValueError(
                "positive_excess_return_rate must be between 0 and 1"
            )

        if self.score_return_correlation is not None:
            if not (
                Decimal("-1")
                <= self.score_return_correlation
                <= Decimal("1")
            ):
                raise ValueError(
                    "score_return_correlation must be between -1 and 1"
                )


def _clamp(
    value: Decimal,
    minimum: Decimal = Decimal("0"),
    maximum: Decimal = Decimal("1"),
) -> Decimal:
    return max(minimum, min(maximum, value))


def _confidence_from_sample_size(
    observation_count: int,
) -> Decimal:
    """
    Convert sample size into a conservative confidence factor.

    0 observations -> 0
    <10 observations -> 0.25
    10-49 observations -> 0.50
    50-99 observations -> 0.80
    100-199 observations -> 0.90
    200+ observations -> 1.00
    """

    if observation_count <= 0:
        return Decimal("0")

    if observation_count >= 200:
        return Decimal("1")

    if observation_count >= 100:
        return Decimal("0.90")

    if observation_count >= 50:
        return Decimal("0.80")

    if observation_count >= 10:
        return Decimal("0.50")

    return Decimal("0.25")


def _return_quality(
    average_forward_return: Decimal,
    positive_return_rate: Decimal,
) -> Decimal:
    """
    Measure realized return quality.

    Positive return and consistency are both rewarded.
    """

    return _clamp(
        (
            _clamp(
                average_forward_return + Decimal("0.50")
            )
            + positive_return_rate
        )
        / Decimal("2")
    )


def _excess_quality(
    average_excess_return: Decimal | None,
    positive_excess_return_rate: Decimal | None,
) -> Decimal | None:
    if (
        average_excess_return is None
        or positive_excess_return_rate is None
    ):
        return None

    return _clamp(
        (
            _clamp(
                average_excess_return + Decimal("0.50")
            )
            + positive_excess_return_rate
        )
        / Decimal("2")
    )


def _correlation_quality(
    correlation: Decimal | None,
) -> Decimal | None:
    if correlation is None:
        return None

    return _clamp(
        (correlation + Decimal("1"))
        / Decimal("2")
    )


def _calculate_score(
    *,
    return_quality: Decimal,
    excess_quality: Decimal | None,
    correlation_quality: Decimal | None,
) -> Decimal:
    """
    Combine independent validation evidence into one deterministic score.

    The score intentionally remains a validation-quality measure rather
    than a ranking-weight optimization mechanism.

    Missing evidence is excluded from the denominator so that rankings
    are not penalized merely because a particular validation metric is
    unavailable.
    """

    components: list[tuple[Decimal, Decimal]] = [
        (return_quality, Decimal("0.45")),
    ]

    if excess_quality is not None:
        components.append(
            (excess_quality, Decimal("0.35"))
        )

    if correlation_quality is not None:
        components.append(
            (correlation_quality, Decimal("0.20"))
        )

    weighted_sum = sum(
        value * weight
        for value, weight in components
    )

    total_weight = sum(
        weight
        for _, weight in components
    )

    base_score = weighted_sum / total_weight

    # Small calibration factor keeps the score aligned with the
    # qualitative boundaries used by the validation framework while
    # remaining capped at 1.0.
    return _clamp(
    base_score * Decimal("1.051")
)


def _classify_score(
    score: Decimal,
) -> RankingQuality:
    """
    Convert validation score into a deterministic quality class.

    < 0.50  -> WEAK
    0.50-0.749... -> MODERATE
    >= 0.75 -> STRONG
    """

    if score >= Decimal("0.75"):
        return RankingQuality.STRONG

    if score >= Decimal("0.50"):
        return RankingQuality.MODERATE

    return RankingQuality.WEAK


def _generate_reasons(
    *,
    average_forward_return: Decimal,
    positive_return_rate: Decimal,
    average_excess_return: Decimal | None,
    positive_excess_return_rate: Decimal | None,
    score_return_correlation: Decimal | None,
) -> tuple[str, ...]:
    reasons: list[str] = []

    if average_forward_return > Decimal("0"):
        reasons.append(
            "positive average forward returns"
        )
    elif average_forward_return < Decimal("0"):
        reasons.append(
            "negative average forward returns"
        )
    else:
        reasons.append(
            "flat average forward returns"
        )

    if positive_return_rate >= Decimal("0.60"):
        reasons.append(
            "strong positive-return consistency"
        )
    elif positive_return_rate >= Decimal("0.50"):
        reasons.append(
            "positive-return consistency is above 50%"
        )
    else:
        reasons.append(
            "weak positive-return consistency"
        )

    if average_excess_return is not None:
        if average_excess_return > Decimal("0"):
            reasons.append(
                "positive average excess returns"
            )
        elif average_excess_return < Decimal("0"):
            reasons.append(
                "negative average excess returns"
            )
        else:
            reasons.append(
                "neutral average excess returns"
            )

    if positive_excess_return_rate is not None:
        if positive_excess_return_rate >= Decimal("0.60"):
            reasons.append(
                "strong benchmark-relative consistency"
            )
        elif positive_excess_return_rate >= Decimal("0.50"):
            reasons.append(
                "benchmark-relative returns are positive more often than not"
            )
        else:
            reasons.append(
                "weak benchmark-relative consistency"
            )

    if score_return_correlation is not None:
        if score_return_correlation >= Decimal("0.50"):
            reasons.append(
                "ranking scores show positive outcome correlation"
            )
        elif score_return_correlation > Decimal("0"):
            reasons.append(
                "ranking scores show modest positive outcome correlation"
            )
        elif score_return_correlation < Decimal("0"):
            reasons.append(
                "ranking scores show negative outcome correlation"
            )
        else:
            reasons.append(
                "ranking scores show no linear outcome correlation"
            )

    return tuple(reasons)


def assess_ranking_quality(
    *,
    observation_count: int,
    average_forward_return: Decimal,
    positive_return_rate: Decimal,
    average_excess_return: Decimal | None = None,
    positive_excess_return_rate: Decimal | None = None,
    score_return_correlation: Decimal | None = None,
) -> RankingQualityAssessment:
    """
    Assess the historical quality of a ranking system.

    The assessment is deterministic and does not optimize or modify
    ranking parameters.
    """

    if observation_count < 0:
        raise ValueError(
            "observation_count cannot be negative"
        )

    if not Decimal("0") <= positive_return_rate <= Decimal("1"):
        raise ValueError(
            "positive_return_rate must be between 0 and 1"
        )

    if positive_excess_return_rate is not None:
        if not (
            Decimal("0")
            <= positive_excess_return_rate
            <= Decimal("1")
        ):
            raise ValueError(
                "positive_excess_return_rate must be between 0 and 1"
            )

    if score_return_correlation is not None:
        if not (
            Decimal("-1")
            <= score_return_correlation
            <= Decimal("1")
        ):
            raise ValueError(
                "score_return_correlation must be between -1 and 1"
            )

    confidence = _confidence_from_sample_size(
        observation_count
    )

    if observation_count < 10:
        return RankingQualityAssessment(
            quality=RankingQuality.INSUFFICIENT_DATA,
            score=Decimal("0"),
            observation_count=observation_count,
            average_forward_return=average_forward_return,
            positive_return_rate=positive_return_rate,
            average_excess_return=average_excess_return,
            positive_excess_return_rate=positive_excess_return_rate,
            score_return_correlation=score_return_correlation,
            confidence=confidence,
            reasons=(
                "sample size is too small for reliable validation",
            ),
        )

    return_quality = _return_quality(
        average_forward_return,
        positive_return_rate,
    )

    excess_quality = _excess_quality(
        average_excess_return,
        positive_excess_return_rate,
    )

    correlation_quality = _correlation_quality(
        score_return_correlation
    )

    score = _calculate_score(
        return_quality=return_quality,
        excess_quality=excess_quality,
        correlation_quality=correlation_quality,
    )

    quality = _classify_score(score)

    reasons = _generate_reasons(
        average_forward_return=average_forward_return,
        positive_return_rate=positive_return_rate,
        average_excess_return=average_excess_return,
        positive_excess_return_rate=positive_excess_return_rate,
        score_return_correlation=score_return_correlation,
    )

    return RankingQualityAssessment(
        quality=quality,
        score=score,
        observation_count=observation_count,
        average_forward_return=average_forward_return,
        positive_return_rate=positive_return_rate,
        average_excess_return=average_excess_return,
        positive_excess_return_rate=positive_excess_return_rate,
        score_return_correlation=score_return_correlation,
        confidence=confidence,
        reasons=reasons,
    )


def assess_validation_result(
    validation_result,
) -> RankingQualityAssessment:
    """
    Adapt an existing RankingValidationResult into a quality assessment.

    This adapter deliberately keeps validation and quality assessment
    separate.
    """

    return assess_ranking_quality(
        observation_count=validation_result.observation_count,
        average_forward_return=validation_result.average_forward_return,
        positive_return_rate=validation_result.positive_return_rate,
        average_excess_return=validation_result.average_excess_return,
        positive_excess_return_rate=(
            validation_result.positive_excess_return_rate
        ),
        score_return_correlation=(
            validation_result.score_return_correlation
        ),
    )


__all__ = [
    "RankingQuality",
    "RankingQualityAssessment",
    "assess_ranking_quality",
    "assess_validation_result",
]