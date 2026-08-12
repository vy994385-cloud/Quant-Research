from __future__ import annotations

from datetime import date

from src.data.providers.base import MarketDataProvider
from src.features.market_snapshot import (
    MarketFeatureSnapshot,
    build_market_feature_snapshot,
)
from src.features.market_structure import calculate_market_structure
from src.features.relative_strength import calculate_relative_strength
from src.features.technical import calculate_technical_features


def build_market_feature_snapshot_from_provider(
    *,
    provider: MarketDataProvider,
    symbol: str,
    benchmark_symbol: str,
    start_date: date,
    end_date: date,
) -> MarketFeatureSnapshot:
    """
    Build a complete market-feature snapshot directly from
    a provider.

    Pipeline:

        MarketDataProvider
            -> PriceBar[]
            -> technical features
            -> market structure
            -> relative strength
            -> MarketFeatureSnapshot

    No future observations are accessed by the feature engines.
    """

    normalized_symbol = symbol.strip().upper()
    normalized_benchmark = benchmark_symbol.strip().upper()

    if not normalized_symbol:
        raise ValueError("symbol cannot be empty")

    if not normalized_benchmark:
        raise ValueError("benchmark_symbol cannot be empty")

    stock_bars = provider.get_daily_prices(
        symbol=normalized_symbol,
        start_date=start_date,
        end_date=end_date,
    )

    benchmark_bars = provider.get_daily_prices(
        symbol=normalized_benchmark,
        start_date=start_date,
        end_date=end_date,
    )

    if not stock_bars:
        raise ValueError(
            f"No market data available for {normalized_symbol}"
        )

    if not benchmark_bars:
        raise ValueError(
            f"No market data available for {normalized_benchmark}"
        )

    technical = calculate_technical_features(stock_bars)

    structure = calculate_market_structure(stock_bars)

    relative_strength = calculate_relative_strength(
        stock_bars,
        benchmark_bars,
    )

    return build_market_feature_snapshot(
        technical=technical,
        structure=structure,
        relative_strength=relative_strength,
    )
