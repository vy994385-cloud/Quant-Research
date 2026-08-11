from __future__ import annotations

from src.research.features.base import FeatureCalculationContext
from src.research.features.engine import FeatureEngine
from src.research.features.registry import feature_definitions
from src.research.features.models import FeatureValue


class ResearchFeatureEngine:
    """
    Unified research feature engine.

    Uses the canonical feature registry and delegates deterministic
    calculation to FeatureEngine.

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
    ) -> tuple[FeatureValue, ...]:
        return self._engine.calculate(context)

    def calculate_one(
        self,
        feature_id: str,
        context: FeatureCalculationContext,
    ) -> FeatureValue:
        return self._engine.calculate_one(
            feature_id,
            context,
        )


__all__ = [
    "ResearchFeatureEngine",
]
