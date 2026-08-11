from __future__ import annotations

from datetime import datetime

from src.research.features.base import FeatureCalculationContext
from src.research.features.engine import FeatureEngine
from src.research.features.models import FeatureValue
from src.research.features.registry import feature_definitions


class ResearchFeatureEngine:
    """
    Unified research feature engine.

    Uses the canonical feature registry and delegates all
    deterministic calculation to FeatureEngine.

    No external data access occurs here.
    """

    def __init__(self) -> None:
        self._engine = FeatureEngine(
            feature_definitions()
        )

    @property
    def feature_ids(self) -> tuple[str, ...]:
        return self._engine.feature_ids

    def calculate(
        self,
        context: FeatureCalculationContext,
        *,
        calculated_at: datetime | None = None,
    ) -> tuple[FeatureValue, ...]:
        return self._engine.calculate(
            context,
            calculated_at=calculated_at,
        )

    def calculate_one(
        self,
        feature_id: str,
        context: FeatureCalculationContext,
        *,
        calculated_at: datetime | None = None,
    ) -> FeatureValue:
        return self._engine.calculate_one(
            feature_id,
            context,
            calculated_at=calculated_at,
        )


__all__ = [
    "ResearchFeatureEngine",
]
