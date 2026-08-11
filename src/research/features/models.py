from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from enum import Enum
from typing import Any


class FeatureStatus(str, Enum):
    VALID = "VALID"
    MISSING = "MISSING"
    INVALID = "INVALID"
    STALE = "STALE"
    PIT_VIOLATION = "PIT_VIOLATION"


@dataclass(frozen=True)
class FeatureValue:
    """
    Immutable, point-in-time-safe research feature.

    A feature is only useful for research when its value,
    timing, provenance and calculation identity are explicit.
    """

    feature_id: str
    feature_version: str
    symbol: str

    value: float | None
    unit: str

    observation_at: datetime
    calculated_at: datetime

    status: FeatureStatus = FeatureStatus.VALID

    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()

    confidence: float = 1.0
    metadata: tuple[tuple[str, Any], ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "feature_id",
            "feature_version",
            "symbol",
            "unit",
        ):
            value = getattr(self, field_name)

            if not value.strip():
                raise ValueError(
                    f"{field_name} cannot be empty"
                )

        if self.observation_at.tzinfo is None:
            raise ValueError(
                "observation_at must be timezone-aware"
            )

        if self.calculated_at.tzinfo is None:
            raise ValueError(
                "calculated_at must be timezone-aware"
            )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                "confidence must be between 0 and 1"
            )

        if self.value is not None and not isfinite(
            self.value
        ):
            raise ValueError(
                "feature value must be finite"
            )

        if (
            self.status == FeatureStatus.VALID
            and self.value is None
        ):
            raise ValueError(
                "VALID feature cannot have a missing value"
            )

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

        normalized_metadata = tuple(
            sorted(
                self.metadata,
                key=lambda item: item[0],
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
            "symbol",
            self.symbol.strip().upper(),
        )

        object.__setattr__(
            self,
            "unit",
            self.unit.strip(),
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

        object.__setattr__(
            self,
            "metadata",
            normalized_metadata,
        )

    @property
    def is_usable(self) -> bool:
        return self.status == FeatureStatus.VALID

    @property
    def is_point_in_time_safe(self) -> bool:
        return (
            self.is_usable
            and self.observation_at <= self.calculated_at
        )
