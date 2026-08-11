from __future__ import annotations

from dataclasses import dataclass

from src.research.features.models import (
    FeatureStatus,
    FeatureValue,
)
from src.research.features.snapshot import FeatureSnapshot


@dataclass(frozen=True)
class FeatureValidationResult:
    """
    Research usability assessment for one feature.
    """

    feature_id: str
    usable: bool
    status: FeatureStatus
    reason: str


@dataclass(frozen=True)
class FeatureSnapshotValidation:
    """
    Research usability assessment for a complete snapshot.
    """

    symbol: str
    timestamp: object
    results: tuple[FeatureValidationResult, ...]

    @property
    def usable_features(self) -> tuple[str, ...]:
        return tuple(
            result.feature_id
            for result in self.results
            if result.usable
        )

    @property
    def rejected_features(self) -> tuple[str, ...]:
        return tuple(
            result.feature_id
            for result in self.results
            if not result.usable
        )

    @property
    def usable_count(self) -> int:
        return len(self.usable_features)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected_features)


class FeatureSnapshotValidator:
    """
    Validate whether snapshot features are usable for research.

    This validator performs no external data access and never changes
    feature values.
    """

    def validate_feature(
        self,
        feature: FeatureValue,
    ) -> FeatureValidationResult:
        if feature.status == FeatureStatus.VALID:
            if not feature.is_point_in_time_safe:
                return FeatureValidationResult(
                    feature_id=feature.feature_id,
                    usable=False,
                    status=FeatureStatus.PIT_VIOLATION,
                    reason="observation occurs after calculation",
                )

            return FeatureValidationResult(
                feature_id=feature.feature_id,
                usable=True,
                status=feature.status,
                reason="feature is research-ready",
            )

        reasons = {
            FeatureStatus.MISSING: "required data is missing",
            FeatureStatus.INVALID: "feature calculation is invalid",
            FeatureStatus.STALE: "feature data is stale",
            FeatureStatus.PIT_VIOLATION: (
                "feature violates point-in-time safety"
            ),
        }

        return FeatureValidationResult(
            feature_id=feature.feature_id,
            usable=False,
            status=feature.status,
            reason=reasons.get(
                feature.status,
                "feature is not research-ready",
            ),
        )

    def validate(
        self,
        snapshot: FeatureSnapshot,
    ) -> FeatureSnapshotValidation:
        results = tuple(
            self.validate_feature(feature)
            for feature in snapshot.features
        )

        return FeatureSnapshotValidation(
            symbol=snapshot.symbol,
            timestamp=snapshot.timestamp,
            results=results,
        )


__all__ = [
    "FeatureValidationResult",
    "FeatureSnapshotValidation",
    "FeatureSnapshotValidator",
]
