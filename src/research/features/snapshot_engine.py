from __future__ import annotations

"""
Backward-compatible exports for the original snapshot engine API.

The canonical implementations now live in:

    base.py   -> FeatureDefinition / FeatureCalculationContext
    engine.py -> FeatureEngine

New code should import from those modules directly.
"""

from src.research.features.base import (
    FeatureCalculationContext,
    FeatureDefinition,
)
from src.research.features.engine import FeatureEngine


class FeatureSnapshotEngine(FeatureEngine):
    """
    Backward-compatible alias for the canonical FeatureEngine.

    Kept so existing research modules continue to work while the
    feature architecture is consolidated.
    """

    pass


__all__ = [
    "FeatureDefinition",
    "FeatureCalculationContext",
    "FeatureSnapshotEngine",
]
