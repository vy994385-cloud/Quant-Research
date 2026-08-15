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


# Backward-compatible alias for the canonical feature engine.
FeatureSnapshotEngine = FeatureEngine


__all__ = [
    "FeatureDefinition",
    "FeatureCalculationContext",
    "FeatureSnapshotEngine",
]
