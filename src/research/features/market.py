from __future__ import annotations

from typing import Mapping

from src.research.features.base import FeatureDefinition
from src.research.market_observations import MarketObservation


def _value(
    observations: Mapping[str, object],
    key: str,
) -> float | None:
    value = observations.get(key)

    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def market_close(
    observations: Mapping[str, object],
) -> float | None:
    return _value(observations, "close")


def market_return_1d(
    observations: Mapping[str, object],
) -> float | None:
    return _value(observations, "return_1d")


def market_return_5d(
    observations: Mapping[str, object],
) -> float | None:
    return _value(observations, "return_5d")


def market_return_20d(
    observations: Mapping[str, object],
) -> float | None:
    return _value(observations, "return_20d")


def market_volatility_20d(
    observations: Mapping[str, object],
) -> float | None:
    return _value(observations, "volatility_20d")


def market_volume_ratio_20d(
    observations: Mapping[str, object],
) -> float | None:
    return _value(observations, "volume_ratio_20d")


def market_drawdown_20d(
    observations: Mapping[str, object],
) -> float | None:
    return _value(observations, "drawdown_20d")


MARKET_FEATURE_DEFINITIONS = (
    FeatureDefinition(
        feature_id="market_close",
        feature_version="1.0",
        unit="price",
        calculator=market_close,
        required_inputs=("close",),
    ),
    FeatureDefinition(
        feature_id="market_return_1d",
        feature_version="1.0",
        unit="decimal_return",
        calculator=market_return_1d,
        required_inputs=("return_1d",),
    ),
    FeatureDefinition(
        feature_id="market_return_5d",
        feature_version="1.0",
        unit="decimal_return",
        calculator=market_return_5d,
        required_inputs=("return_5d",),
    ),
    FeatureDefinition(
        feature_id="market_return_20d",
        feature_version="1.0",
        unit="decimal_return",
        calculator=market_return_20d,
        required_inputs=("return_20d",),
    ),
    FeatureDefinition(
        feature_id="market_volatility_20d",
        feature_version="1.0",
        unit="decimal_volatility",
        calculator=market_volatility_20d,
        required_inputs=("volatility_20d",),
    ),
    FeatureDefinition(
        feature_id="market_volume_ratio_20d",
        feature_version="1.0",
        unit="ratio",
        calculator=market_volume_ratio_20d,
        required_inputs=("volume_ratio_20d",),
    ),
    FeatureDefinition(
        feature_id="market_drawdown_20d",
        feature_version="1.0",
        unit="decimal_drawdown",
        calculator=market_drawdown_20d,
        required_inputs=("drawdown_20d",),
    ),
)


def market_observation_to_context(
    observation: MarketObservation,
) -> object:
    """
    Convert one point-in-time MarketObservation into the
    FeatureEngine calculation boundary.

    No external data is fetched here.
    """

    from src.research.features.base import (
        FeatureCalculationContext,
    )

    return FeatureCalculationContext(
        symbol=observation.symbol,
        timestamp=observation.available_at,
        observations={
            "close": observation.close,
            "return_1d": observation.return_1d,
            "return_5d": observation.return_5d,
            "return_20d": observation.return_20d,
            "volatility_20d": observation.volatility_20d,
            "volume": observation.volume,
            "volume_ratio_20d": observation.volume_ratio_20d,
            "drawdown_20d": observation.drawdown_20d,
        },
    )


__all__ = [
    "MARKET_FEATURE_DEFINITIONS",
    "market_observation_to_context",
]
