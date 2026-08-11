from datetime import date, datetime, timezone

import pytest

from src.research.features.engine import FeatureEngine
from src.research.features.market import (
    MARKET_FEATURE_DEFINITIONS,
    market_observation_to_context,
)
from src.research.features.models import FeatureStatus
from src.research.market_observations import (
    MarketObservation,
)


AS_OF = datetime(
    2026,
    8,
    10,
    10,
    tzinfo=timezone.utc,
)


def make_observation() -> MarketObservation:
    return MarketObservation(
        symbol="test",
        observation_date=date(2026, 8, 10),
        available_at=AS_OF,
        close=120.0,
        return_1d=0.02,
        return_5d=0.05,
        return_20d=0.12,
        volatility_20d=0.015,
        volume=100000.0,
        volume_ratio_20d=1.4,
        drawdown_20d=-0.08,
    )


def test_market_definitions_are_registered():
    engine = FeatureEngine(
        MARKET_FEATURE_DEFINITIONS
    )

    assert engine.feature_ids == (
        "market_close",
        "market_drawdown_20d",
        "market_return_1d",
        "market_return_20d",
        "market_return_5d",
        "market_volatility_20d",
        "market_volume_ratio_20d",
    )


def test_market_observation_becomes_feature_context():
    observation = make_observation()

    context = market_observation_to_context(
        observation
    )

    assert context.symbol == "TEST"
    assert context.timestamp == AS_OF
    assert context.observations["close"] == 120.0
    assert context.observations["return_20d"] == 0.12


def test_market_features_calculate():
    observation = make_observation()

    context = market_observation_to_context(
        observation
    )

    engine = FeatureEngine(
        MARKET_FEATURE_DEFINITIONS
    )

    results = engine.calculate(context)

    assert len(results) == 7

    by_id = {
        result.feature_id: result
        for result in results
    }

    assert by_id["market_close"].value == pytest.approx(
        120.0
    )

    assert by_id["market_return_1d"].value == pytest.approx(
        0.02
    )

    assert by_id["market_return_5d"].value == pytest.approx(
        0.05
    )

    assert by_id["market_return_20d"].value == pytest.approx(
        0.12
    )

    assert by_id["market_volatility_20d"].value == pytest.approx(
        0.015
    )

    assert by_id["market_volume_ratio_20d"].value == pytest.approx(
        1.4
    )

    assert by_id["market_drawdown_20d"].value == pytest.approx(
        -0.08
    )


def test_missing_market_history_is_explicit():
    observation = MarketObservation(
        symbol="TEST",
        observation_date=date(2026, 8, 1),
        available_at=AS_OF,
        close=100.0,
    )

    context = market_observation_to_context(
        observation
    )

    engine = FeatureEngine(
        MARKET_FEATURE_DEFINITIONS
    )

    results = engine.calculate(context)

    by_id = {
        result.feature_id: result
        for result in results
    }

    assert by_id["market_close"].status == FeatureStatus.VALID

    assert by_id["market_return_1d"].status == FeatureStatus.MISSING
    assert by_id["market_return_5d"].status == FeatureStatus.MISSING
    assert by_id["market_return_20d"].status == FeatureStatus.MISSING
    assert by_id["market_volatility_20d"].status == FeatureStatus.MISSING
    assert by_id["market_volume_ratio_20d"].status == FeatureStatus.MISSING
    assert by_id["market_drawdown_20d"].status == FeatureStatus.MISSING
