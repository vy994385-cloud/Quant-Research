from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.features.market_structure import MarketStructure
from src.features.relative_strength import RelativeStrength
from src.features.technical import TechnicalFeatures


@dataclass(frozen=True)
class MarketFeatureSnapshot:
    """
    Immutable, validated market-feature state for one security
    at one observation date.

    This object contains descriptive features only.
    It does not generate a trading prediction.
    """

    symbol: str
    trading_date: date

    technical: TechnicalFeatures
    structure: MarketStructure
    relative_strength: RelativeStrength

    benchmark_symbol: str


def build_market_feature_snapshot(
    technical: TechnicalFeatures,
    structure: MarketStructure,
    relative_strength: RelativeStrength,
) -> MarketFeatureSnapshot:
    """
    Assemble independent feature calculations into one validated
    market snapshot.
    """

    if technical.symbol != structure.symbol:
        raise ValueError(
            "Technical and market-structure symbols must match"
        )

    if technical.symbol != relative_strength.symbol:
        raise ValueError(
            "Technical and relative-strength symbols must match"
        )

    if structure.symbol != relative_strength.symbol:
        raise ValueError(
            "Market-structure and relative-strength symbols must match"
        )

    if technical.trading_date != structure.trading_date:
        raise ValueError(
            "Technical and market-structure dates must match"
        )

    if technical.trading_date != relative_strength.trading_date:
        raise ValueError(
            "Technical and relative-strength dates must match"
        )

    if structure.trading_date != relative_strength.trading_date:
        raise ValueError(
            "Market-structure and relative-strength dates must match"
        )

    if not relative_strength.benchmark_symbol:
        raise ValueError(
            "Benchmark symbol cannot be empty"
        )

    return MarketFeatureSnapshot(
        symbol=technical.symbol,
        trading_date=technical.trading_date,
        technical=technical,
        structure=structure,
        relative_strength=relative_strength,
        benchmark_symbol=relative_strength.benchmark_symbol,
    )
