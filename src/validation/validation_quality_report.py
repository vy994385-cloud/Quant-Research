from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.ranking.ranking_quality import (
    RankingQuality,
    RankingQualityAssessment,
    assess_validation_result,
)
from src.validation.ranking_validation import (
    RankingValidationResult,
)


@dataclass(frozen=True)
class ValidationQualityReport:
    """
    Human- and machine-readable quality summary for one
    historical ranking validation result.

    This report does not modify validation evidence or ranking
    parameters. It only combines existing validation statistics
    with the deterministic ranking-quality assessment.
    """

    horizon: str
    observation_count: int

    quality: RankingQuality
    score: Decimal
    confidence: Decimal

    average_forward_return: Decimal
    median_forward_return: Decimal
    positive_return_rate: Decimal

    average_excess_return: Decimal | None
    positive_excess_return_rate: Decimal | None

    score_return_correlation: Decimal | None

    reasons: tuple[str, ...]

    @classmethod
    def from_validation_result(
        cls,
        validation_result: RankingValidationResult,
    ) -> ValidationQualityReport:
        """
        Build a quality report from an existing validation result.

        The input validation result is treated as immutable evidence.
        """

        if not isinstance(
            validation_result,
            RankingValidationResult,
        ):
            raise TypeError(
                "validation_result must be a RankingValidationResult"
            )

        assessment = assess_validation_result(
            validation_result
        )

        return cls.from_assessment(
            validation_result=validation_result,
            assessment=assessment,
        )

    @classmethod
    def from_assessment(
        cls,
        *,
        validation_result: RankingValidationResult,
        assessment: RankingQualityAssessment,
    ) -> ValidationQualityReport:
        """
        Build a report from an existing validation result and
        matching quality assessment.
        """

        if not isinstance(
            validation_result,
            RankingValidationResult,
        ):
            raise TypeError(
                "validation_result must be a RankingValidationResult"
            )

        if not isinstance(
            assessment,
            RankingQualityAssessment,
        ):
            raise TypeError(
                "assessment must be a RankingQualityAssessment"
            )

        if (
            assessment.observation_count
            != validation_result.observation_count
        ):
            raise ValueError(
                "assessment observation count does not match "
                "validation result"
            )

        return cls(
            horizon=validation_result.horizon,
            observation_count=validation_result.observation_count,
            quality=assessment.quality,
            score=assessment.score,
            confidence=assessment.confidence,
            average_forward_return=(
                validation_result.average_forward_return
            ),
            median_forward_return=(
                validation_result.median_forward_return
            ),
            positive_return_rate=(
                validation_result.positive_return_rate
            ),
            average_excess_return=(
                validation_result.average_excess_return
            ),
            positive_excess_return_rate=(
                validation_result.positive_excess_return_rate
            ),
            score_return_correlation=(
                validation_result.score_return_correlation
            ),
            reasons=assessment.reasons,
        )

    @property
    def is_actionable(self) -> bool:
        """
        Whether the evidence is strong enough to be considered
        actionable by downstream research consumers.

        This is intentionally conservative: insufficient and weak
        validation results are not actionable.
        """

        return self.quality in {
            RankingQuality.MODERATE,
            RankingQuality.STRONG,
        }

    @property
    def is_strong(self) -> bool:
        """
        Whether the ranking demonstrates strong historical quality.
        """

        return self.quality == RankingQuality.STRONG

    @property
    def is_insufficient(self) -> bool:
        """
        Whether the validation sample is insufficient.
        """

        return self.quality == RankingQuality.INSUFFICIENT_DATA

    def to_dict(self) -> dict[str, object]:
        """
        Convert the report into a deterministic serializable mapping.
        """

        return {
            "horizon": self.horizon,
            "observation_count": self.observation_count,
            "quality": self.quality.value,
            "score": self.score,
            "confidence": self.confidence,
            "average_forward_return": (
                self.average_forward_return
            ),
            "median_forward_return": (
                self.median_forward_return
            ),
            "positive_return_rate": (
                self.positive_return_rate
            ),
            "average_excess_return": (
                self.average_excess_return
            ),
            "positive_excess_return_rate": (
                self.positive_excess_return_rate
            ),
            "score_return_correlation": (
                self.score_return_correlation
            ),
            "reasons": self.reasons,
            "is_actionable": self.is_actionable,
            "is_strong": self.is_strong,
            "is_insufficient": self.is_insufficient,
        }


def build_validation_quality_report(
    validation_result: RankingValidationResult,
) -> ValidationQualityReport:
    """
    Convenience adapter for creating a validation-quality report.
    """

    return ValidationQualityReport.from_validation_result(
        validation_result
    )


__all__ = [
    "ValidationQualityReport",
    "build_validation_quality_report",
]