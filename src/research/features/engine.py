from __future__ import annotations

from datetime import datetime
from typing import Iterable

from src.research.features.base import (
    FeatureCalculationContext,
    FeatureDefinition,
)
from src.research.features.models import (
    FeatureStatus,
    FeatureValue,
)


class FeatureEngine:
    """
    Deterministic point-in-time feature calculation engine.

    Architecture:

        ResearchContext
              ↓
        FeatureCalculationContext
              ↓
        FeatureDefinition
              ↓
        FeatureValue

    This engine never fetches external data.

    Missing, invalid and point-in-time-invalid results are represented
    explicitly instead of being silently discarded.
    """

    def __init__(
        self,
        definitions: Iterable[FeatureDefinition],
    ) -> None:
        registry: dict[str, FeatureDefinition] = {}

        for definition in definitions:
            feature_id = definition.feature_id

            if feature_id in registry:
                raise ValueError(
                    f"feature already registered: {feature_id}"
                )

            registry[feature_id] = definition

        self._definitions = registry

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
            calculated_at
            if calculated_at is not None
            else context.timestamp
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

        return tuple(
            self._calculate_one(
                definition,
                context,
                calculation_time,
            )
            for definition in self._definitions.values()
        )

    def calculate_one(
        self,
        feature_id: str,
        context: FeatureCalculationContext,
        *,
        calculated_at: datetime | None = None,
    ) -> FeatureValue:
        key = feature_id.strip().lower()

        if key not in self._definitions:
            raise KeyError(
                f"feature not registered: {feature_id}"
            )

        calculation_time = (
            calculated_at
            if calculated_at is not None
            else context.timestamp
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

        return self._calculate_one(
            self._definitions[key],
            context,
            calculation_time,
        )

    def _calculate_one(
        self,
        definition: FeatureDefinition,
        context: FeatureCalculationContext,
        calculated_at: datetime,
    ) -> FeatureValue:
        missing = tuple(
            field
            for field in definition.required_inputs
            if (
                field not in context.observations
                or context.observations[field] is None
            )
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
                    (
                        "missing_inputs",
                        ",".join(missing),
                    ),
                ),
            )

        if context.timestamp > calculated_at:
            return FeatureValue(
                feature_id=definition.feature_id,
                feature_version=definition.feature_version,
                symbol=context.symbol,
                value=None,
                unit=definition.unit,
                observation_at=context.timestamp,
                calculated_at=calculated_at,
                status=FeatureStatus.PIT_VIOLATION,
                source_ids=context.source_ids,
                provenance_ids=context.provenance_ids,
                metadata=(
                    (
                        "reason",
                        "observation_after_calculation",
                    ),
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


__all__ = [
    "FeatureEngine",
]
