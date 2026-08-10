from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Iterable, Mapping

from src.research.features.models import FeatureValue, FeatureStatus


@dataclass(frozen=True)
class FeatureDefinition:
    """
    Immutable definition of one research feature.

    The calculator receives only observations that were already
    known at the requested research timestamp.
    """

    feature_id: str
    feature_version: str
    unit: str
    calculator: Callable[[Mapping[str, object]], float | None]
    required_inputs: tuple[str, ...] = ()


@dataclass(frozen=True)
class FeatureCalculationContext:
    """
    Point-in-time boundary supplied to feature calculations.
    """

    symbol: str
    timestamp: datetime
    observations: Mapping[str, object]
    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")

        if self.timestamp.tzinfo is None:
            raise ValueError(
                "timestamp must be timezone-aware"
            )


class FeatureSnapshotEngine:
    """
    Deterministic point-in-time feature calculation engine.

    This engine deliberately does not fetch external data.

    Its responsibility is:

        point-in-time observations
                ↓
        feature definitions
                ↓
        validated FeatureValue objects

    Data acquisition and point-in-time filtering remain upstream.
    """

    def __init__(
        self,
        definitions: Iterable[FeatureDefinition],
    ) -> None:
        self._definitions: dict[str, FeatureDefinition] = {}

        for definition in definitions:
            key = definition.feature_id.strip().lower()

            if not key:
                raise ValueError(
                    "feature_id cannot be empty"
                )

            if key in self._definitions:
                raise ValueError(
                    f"feature already registered: {key}"
                )

            self._definitions[key] = definition

    @property
    def feature_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._definitions))

    def calculate(
        self,
        context: FeatureCalculationContext,
        *,
        calculated_at: datetime | None = None,
    ) -> tuple[FeatureValue, ...]:
        calculation_time = (
            calculated_at or context.timestamp
        )

        if calculation_time.tzinfo is None:
            raise ValueError(
                "calculated_at must be timezone-aware"
            )

        if calculation_time < context.timestamp:
            raise ValueError(
                "calculated_at cannot be earlier than "
                "context timestamp"
            )

        results: list[FeatureValue] = []

        for definition in self._definitions.values():
            results.append(
                self._calculate_one(
                    definition,
                    context,
                    calculation_time,
                )
            )

        return tuple(results)

    def _calculate_one(
        self,
        definition: FeatureDefinition,
        context: FeatureCalculationContext,
        calculated_at: datetime,
    ) -> FeatureValue:
        missing = tuple(
            field
            for field in definition.required_inputs
            if field not in context.observations
            or context.observations[field] is None
        )

        if missing:
            return FeatureValue(
                feature_id=definition.feature_id,
                feature_version=definition.feature_version,
                symbol=context.symbol,
                value=None,
                unit=definition.unit,
                observation_at=context.timestamp,
                calculated_at=calculated_at,
                status=FeatureStatus.MISSING,
                source_ids=context.source_ids,
                provenance_ids=context.provenance_ids,
                metadata=(
                    ("missing_inputs", ",".join(missing)),
                ),
            )

        try:
            value = definition.calculator(
                context.observations
            )
        except (TypeError, ValueError, ArithmeticError):
            return FeatureValue(
                feature_id=definition.feature_id,
                feature_version=definition.feature_version,
                symbol=context.symbol,
                value=None,
                unit=definition.unit,
                observation_at=context.timestamp,
                calculated_at=calculated_at,
                status=FeatureStatus.INVALID,
                source_ids=context.source_ids,
                provenance_ids=context.provenance_ids,
            )

        if value is None:
            return FeatureValue(
                feature_id=definition.feature_id,
                feature_version=definition.feature_version,
                symbol=context.symbol,
                value=None,
                unit=definition.unit,
                observation_at=context.timestamp,
                calculated_at=calculated_at,
                status=FeatureStatus.MISSING,
                source_ids=context.source_ids,
                provenance_ids=context.provenance_ids,
            )

        return FeatureValue(
            feature_id=definition.feature_id,
            feature_version=definition.feature_version,
            symbol=context.symbol,
            value=float(value),
            unit=definition.unit,
            observation_at=context.timestamp,
            calculated_at=calculated_at,
            status=FeatureStatus.VALID,
            source_ids=context.source_ids,
            provenance_ids=context.provenance_ids,
        )
