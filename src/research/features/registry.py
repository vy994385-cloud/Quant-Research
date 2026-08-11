from __future__ import annotations

from src.research.features.base import FeatureDefinition
from src.research.features.financial_quality import (
    FINANCIAL_FEATURE_DEFINITIONS,
)
from src.research.features.financial_trends import (
    FINANCIAL_TREND_FEATURE_DEFINITIONS,
)
from src.research.features.market import (
    MARKET_FEATURE_DEFINITIONS,
)


ALL_FEATURE_DEFINITIONS: tuple[FeatureDefinition, ...] = (
    FINANCIAL_FEATURE_DEFINITIONS
    + FINANCIAL_TREND_FEATURE_DEFINITIONS
    + MARKET_FEATURE_DEFINITIONS
)


def feature_definitions() -> tuple[FeatureDefinition, ...]:
    """
    Return the complete research feature registry.

    Feature calculation remains deterministic and external-data-free.
    """
    return ALL_FEATURE_DEFINITIONS


def feature_ids() -> tuple[str, ...]:
    return tuple(
        definition.feature_id
        for definition in ALL_FEATURE_DEFINITIONS
    )


def get_feature_definition(
    feature_id: str,
) -> FeatureDefinition:
    key = feature_id.strip().lower()

    for definition in ALL_FEATURE_DEFINITIONS:
        if definition.feature_id == key:
            return definition

    raise KeyError(
        f"feature not registered: {feature_id}"
    )


__all__ = [
    "ALL_FEATURE_DEFINITIONS",
    "feature_definitions",
    "feature_ids",
    "get_feature_definition",
]
