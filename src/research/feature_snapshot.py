from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Any, Mapping

from src.research.context import ResearchContext


@dataclass(frozen=True)
class FeatureValue:
    """
    One deterministic, point-in-time feature.

    Every feature records the source observations that produced it,
    making downstream ranking and backtesting auditable.
    """

    name: str
    value: float
    source_ids: tuple[str, ...] = ()
    observation_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("feature name cannot be empty")

        if not isfinite(self.value):
            raise ValueError(
                f"feature value must be finite: {self.name}"
            )

        object.__setattr__(
            self,
            "name",
            self.name.strip().lower(),
        )

        object.__setattr__(
            self,
            "source_ids",
            tuple(sorted({
                source.strip().lower()
                for source in self.source_ids
                if source.strip()
            })),
        )

        object.__setattr__(
            self,
            "observation_ids",
            tuple(sorted({
                observation.strip()
                for observation in self.observation_ids
                if observation.strip()
            })),
        )


@dataclass(frozen=True)
class FeatureSnapshot:
    """
    Immutable point-in-time feature snapshot.

    Downstream ranking, ML and backtesting should consume this object
    instead of directly accessing raw observations.
    """

    symbol: str
    timestamp: datetime
    features: tuple[FeatureValue, ...] = ()

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
                key=lambda feature: feature.name,
            )
        )

        names = [feature.name for feature in ordered]

        if len(names) != len(set(names)):
            raise ValueError(
                "duplicate feature names are not allowed"
            )

        object.__setattr__(
            self,
            "symbol",
            self.symbol.strip(),
        )
        object.__setattr__(
            self,
            "features",
            ordered,
        )

    @property
    def feature_count(self) -> int:
        return len(self.features)

    def get(self, name: str) -> FeatureValue:
        key = name.strip().lower()

        for feature in self.features:
            if feature.name == key:
                return feature

        raise KeyError(
            f"feature not found: {name}"
        )

    def as_dict(self) -> dict[str, float]:
        return {
            feature.name: feature.value
            for feature in self.features
        }


class PITFeatureBuilder:
    """
    Build an immutable feature snapshot from an already validated
    ResearchContext.

    This layer intentionally does not fetch external data.

    Architecture:

        external data
            ↓
        provenance
            ↓
        ResearchContext
            ↓
        PITFeatureBuilder
            ↓
        FeatureSnapshot
            ↓
        ranking / ML / backtest
    """

    def build(
        self,
        context: ResearchContext,
        features: Mapping[
            str,
            float | int | FeatureValue,
        ],
    ) -> FeatureSnapshot:
        if not isinstance(
            context,
            ResearchContext,
        ):
            raise TypeError(
                "context must be a ResearchContext"
            )

        built: list[FeatureValue] = []

        for name, value in features.items():
            if isinstance(value, FeatureValue):
                if value.name != name.strip().lower():
                    raise ValueError(
                        "feature key does not match "
                        "FeatureValue.name"
                    )

                built.append(value)
                continue

            try:
                numeric_value = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"feature value must be numeric: {name}"
                ) from exc

            built.append(
                FeatureValue(
                    name=name,
                    value=numeric_value,
                    source_ids=context.source_ids,
                )
            )

        return FeatureSnapshot(
            symbol=context.symbol,
            timestamp=context.timestamp,
            features=tuple(built),
        )


def build_feature_snapshot(
    context: ResearchContext,
    features: Mapping[
        str,
        float | int | FeatureValue,
    ],
) -> FeatureSnapshot:
    """
    Functional convenience wrapper.
    """

    return PITFeatureBuilder().build(
        context,
        features,
    )
