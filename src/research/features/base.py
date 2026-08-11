from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Mapping


FeatureCalculator = Callable[
    [Mapping[str, object]],
    float | None,
]


@dataclass(frozen=True)
class FeatureDefinition:
    """
    Immutable definition of one research feature.

    A definition contains the calculation identity, expected unit,
    calculator and required inputs.

    The calculator must operate only on observations supplied by
    the point-in-time research context.
    """

    feature_id: str
    feature_version: str
    unit: str
    calculator: FeatureCalculator
    required_inputs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.feature_id.strip():
            raise ValueError(
                "feature_id cannot be empty"
            )

        if not self.feature_version.strip():
            raise ValueError(
                "feature_version cannot be empty"
            )

        if not self.unit.strip():
            raise ValueError(
                "unit cannot be empty"
            )

        if not callable(self.calculator):
            raise TypeError(
                "calculator must be callable"
            )

        normalized_inputs = tuple(
            dict.fromkeys(
                input_name.strip()
                for input_name in self.required_inputs
                if input_name.strip()
            )
        )

        object.__setattr__(
            self,
            "feature_id",
            self.feature_id.strip().lower(),
        )

        object.__setattr__(
            self,
            "feature_version",
            self.feature_version.strip(),
        )

        object.__setattr__(
            self,
            "unit",
            self.unit.strip(),
        )

        object.__setattr__(
            self,
            "required_inputs",
            normalized_inputs,
        )


@dataclass(frozen=True)
class FeatureCalculationContext:
    """
    Point-in-time boundary supplied to feature calculations.

    External data access is intentionally forbidden at this layer.
    """

    symbol: str
    timestamp: datetime
    observations: Mapping[str, object]
    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError(
                "symbol cannot be empty"
            )

        if self.timestamp.tzinfo is None:
            raise ValueError(
                "timestamp must be timezone-aware"
            )

        normalized_observations = {
            key.strip(): value
            for key, value in self.observations.items()
            if key.strip()
        }

        normalized_sources = tuple(
            sorted(
                {
                    source.strip().lower()
                    for source in self.source_ids
                    if source.strip()
                }
            )
        )

        normalized_provenance = tuple(
            sorted(
                {
                    provenance.strip()
                    for provenance in self.provenance_ids
                    if provenance.strip()
                }
            )
        )

        object.__setattr__(
            self,
            "symbol",
            self.symbol.strip().upper(),
        )

        object.__setattr__(
            self,
            "observations",
            normalized_observations,
        )

        object.__setattr__(
            self,
            "source_ids",
            normalized_sources,
        )

        object.__setattr__(
            self,
            "provenance_ids",
            normalized_provenance,
        )
