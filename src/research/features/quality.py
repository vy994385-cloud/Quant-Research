from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from src.research.features.models import (
    FeatureStatus,
    FeatureValue,
)


@dataclass(frozen=True)
class FeatureQualityResult:
    """
    Deterministic quality assessment for one FeatureValue.

    The evaluator does not calculate features and does not fetch data.
    It only evaluates whether an already-calculated feature is safe
    and usable for downstream research.
    """

    feature_id: str
    symbol: str
    usable: bool
    status: FeatureStatus
    reasons: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.usable


class FeatureQualityEvaluator:
    """
    Validates individual point-in-time feature values.

    The quality layer deliberately sits after the snapshot engine:

        observations
            ↓
        snapshot engine
            ↓
        FeatureValue
            ↓
        FeatureQualityEvaluator
            ↓
        quality result

    It does not modify FeatureValue objects.
    """

    def __init__(
        self,
        *,
        max_age: object | None = None,
        minimum_confidence: float = 0.0,
    ) -> None:
        if max_age is not None and not hasattr(
            max_age,
            "total_seconds",
        ):
            raise TypeError(
                "max_age must be a timedelta or None"
            )

        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError(
                "minimum_confidence must be between 0 and 1"
            )

        self._max_age = max_age
        self._minimum_confidence = minimum_confidence

    def evaluate(
        self,
        feature: FeatureValue,
        *,
        as_of: datetime | None = None,
    ) -> FeatureQualityResult:
        reasons: list[str] = []

        if feature.status != FeatureStatus.VALID:
            reasons.append(
                f"status:{feature.status.value}"
            )

        if feature.value is None:
            reasons.append("missing_value")

        if feature.confidence < self._minimum_confidence:
            reasons.append("low_confidence")

        if feature.observation_at > feature.calculated_at:
            reasons.append("observation_after_calculation")

        if as_of is not None:
            if as_of.tzinfo is None:
                raise ValueError(
                    "as_of must be timezone-aware"
                )

            if feature.observation_at > as_of:
                reasons.append(
                    "observation_after_as_of"
                )

            if feature.calculated_at > as_of:
                reasons.append(
                    "calculation_after_as_of"
                )

            if self._max_age is not None:
                age = as_of - feature.observation_at

                if age > self._max_age:
                    reasons.append("stale")

        usable = not reasons

        status = (
            FeatureStatus.VALID
            if usable
            else self._derive_status(
                feature,
                reasons,
            )
        )

        return FeatureQualityResult(
            feature_id=feature.feature_id,
            symbol=feature.symbol,
            usable=usable,
            status=status,
            reasons=tuple(reasons),
        )

    def evaluate_many(
        self,
        features: Iterable[FeatureValue],
        *,
        as_of: datetime | None = None,
    ) -> tuple[FeatureQualityResult, ...]:
        return tuple(
            self.evaluate(
                feature,
                as_of=as_of,
            )
            for feature in features
        )

    @staticmethod
    def _derive_status(
        feature: FeatureValue,
        reasons: list[str],
    ) -> FeatureStatus:
        if feature.status == FeatureStatus.PIT_VIOLATION:
            return FeatureStatus.PIT_VIOLATION

        if (
            "observation_after_as_of" in reasons
            or "calculation_after_as_of" in reasons
            or "observation_after_calculation" in reasons
        ):
            return FeatureStatus.PIT_VIOLATION

        if "stale" in reasons:
            return FeatureStatus.STALE

        if feature.status == FeatureStatus.MISSING:
            return FeatureStatus.MISSING

        return FeatureStatus.INVALID