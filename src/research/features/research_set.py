from __future__ import annotations

from dataclasses import dataclass

from src.research.features.models import FeatureValue
from src.research.features.snapshot import FeatureSnapshot
from src.research.features.validation import (
    FeatureSnapshotValidation,
)


@dataclass(frozen=True)
class ResearchFeatureSet:
    """
    Research-ready subset of a FeatureSnapshot.

    Usable features are exposed for downstream ranking, modelling,
    and intelligence calculations. Rejected features remain recorded
    through rejected_feature_ids for auditability.
    """

    symbol: str
    timestamp: object
    features: tuple[FeatureValue, ...]
    rejected_feature_ids: tuple[str, ...] = ()

    @property
    def feature_ids(self) -> tuple[str, ...]:
        return tuple(
            feature.feature_id
            for feature in self.features
        )

    @property
    def feature_count(self) -> int:
        return len(self.features)

    @property
    def rejected_count(self) -> int:
        return len(self.rejected_feature_ids)

    def get(self, feature_id: str) -> FeatureValue:
        key = feature_id.strip().lower()

        for feature in self.features:
            if feature.feature_id == key:
                return feature

        raise KeyError(
            f"research feature not present: {feature_id}"
        )


class ResearchFeatureSetBuilder:
    """
    Convert a validated FeatureSnapshot into research-ready features.

    No external data access occurs here.
    """

    def build(
        self,
        snapshot: FeatureSnapshot,
        validation: FeatureSnapshotValidation,
    ) -> ResearchFeatureSet:
        if snapshot.symbol != validation.symbol:
            raise ValueError(
                "snapshot and validation symbols do not match"
            )

        if snapshot.timestamp != validation.timestamp:
            raise ValueError(
                "snapshot and validation timestamps do not match"
            )

        usable_ids = set(
            validation.usable_features
        )

        features = tuple(
            feature
            for feature in snapshot.features
            if feature.feature_id in usable_ids
        )

        rejected_ids = tuple(
            result.feature_id
            for result in validation.results
            if not result.usable
        )

        return ResearchFeatureSet(
            symbol=snapshot.symbol,
            timestamp=snapshot.timestamp,
            features=features,
            rejected_feature_ids=rejected_ids,
        )


__all__ = [
    "ResearchFeatureSet",
    "ResearchFeatureSetBuilder",
]
