from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.research.context import ResearchContext
from src.research.features.context_adapter import (
    research_context_to_feature_context,
)
from src.research.features.models import FeatureValue
from src.research.features.registry_engine import (
    ResearchFeatureEngine,
)


@dataclass(frozen=True)
class FeatureSnapshot:
    """
    Immutable complete point-in-time feature snapshot.

    A snapshot contains every registered research feature calculated
    from observations available at the ResearchContext timestamp.
    """

    symbol: str
    timestamp: datetime
    features: tuple[FeatureValue, ...]

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")

        if self.timestamp.tzinfo is None:
            raise ValueError(
                "timestamp must be timezone-aware"
            )

        ordered = tuple(
            sorted(
                self.features,
                key=lambda feature: feature.feature_id,
            )
        )

        feature_ids = [
            feature.feature_id
            for feature in ordered
        ]

        if len(feature_ids) != len(set(feature_ids)):
            raise ValueError(
                "duplicate feature ids are not allowed"
            )

        object.__setattr__(
            self,
            "symbol",
            self.symbol.strip().upper(),
        )

        object.__setattr__(
            self,
            "features",
            ordered,
        )

    @property
    def feature_count(self) -> int:
        return len(self.features)

    @property
    def feature_ids(self) -> tuple[str, ...]:
        return tuple(
            feature.feature_id
            for feature in self.features
        )

    def get(self, feature_id: str) -> FeatureValue:
        key = feature_id.strip().lower()

        for feature in self.features:
            if feature.feature_id == key:
                return feature

        raise KeyError(
            f"feature not present in snapshot: {feature_id}"
        )


class FeatureSnapshotBuilder:
    """
    Build a complete feature snapshot from ResearchContext.

    No external data access occurs here.
    """

    def __init__(
        self,
        engine: ResearchFeatureEngine | None = None,
    ) -> None:
        self._engine = (
            engine
            if engine is not None
            else ResearchFeatureEngine()
        )

    def build(
        self,
        context: ResearchContext,
        *,
        calculated_at: datetime | None = None,
    ) -> FeatureSnapshot:
        if not isinstance(
            context,
            ResearchContext,
        ):
            raise TypeError(
                "context must be a ResearchContext"
            )

        feature_context = (
            research_context_to_feature_context(
                context
            )
        )

        features = self._engine.calculate(
            feature_context,
            calculated_at=calculated_at,
        )

        return FeatureSnapshot(
            symbol=context.symbol,
            timestamp=context.timestamp,
            features=features,
        )


__all__ = [
    "FeatureSnapshot",
    "FeatureSnapshotBuilder",
]
