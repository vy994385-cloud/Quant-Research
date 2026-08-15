from __future__ import annotations

from src.research.context import ResearchContext
from src.research.features.base import FeatureCalculationContext


def research_context_to_feature_context(
    context: ResearchContext,
    *,
    provenance_ids: tuple[str, ...] = (),
) -> FeatureCalculationContext:
    """
    Convert a point-in-time ResearchContext into the feature
    calculation boundary.

    This adapter performs no external data access and does not
    calculate features. It only exposes already-available
    observations to the feature layer.
    """

    observations: dict[str, object] = {}

    for observation in context.market:
        if isinstance(observation, dict):
            observations.update(observation)

    for observation in context.fundamentals:
        if isinstance(observation, dict):
            observations.update(observation)

    for observation in context.macro:
        if isinstance(observation, dict):
            observations.update(observation)

    for observation in context.events:
        if isinstance(observation, dict):
            observations.update(observation)

    for observation in context.corporate_actions:
        if isinstance(observation, dict):
            observations.update(observation)

    return FeatureCalculationContext(
        symbol=context.symbol,
        timestamp=context.timestamp,
        observations=observations,
        source_ids=context.source_ids,
        provenance_ids=provenance_ids,
    )


__all__ = [
    "research_context_to_feature_context",
]
