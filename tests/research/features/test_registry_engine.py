from datetime import datetime, timezone

import pytest

from src.research.features.base import FeatureCalculationContext
from src.research.features.registry import feature_ids
from src.research.features.registry_engine import ResearchFeatureEngine
from src.research.features.models import FeatureStatus


AS_OF = datetime(
    2026,
    8,
    10,
    10,
    tzinfo=timezone.utc,
)


def test_registry_engine_uses_canonical_registry():
    engine = ResearchFeatureEngine()

    assert engine.feature_ids == tuple(
        sorted(feature_ids())
    )


def test_registry_engine_calculates_registered_features():
    engine = ResearchFeatureEngine()

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=AS_OF,
        observations={
            "revenue": 120,
            "previous_revenue": 100,
            "net_profit": 12,
            "operating_cash_flow": 18,
            "free_cash_flow": 10,
            "receivables": 20,
            "payables": 15,
            "total_debt": 30,
            "cash_and_equivalents": 60,
            "previous_operating_profit": 8,
            "operating_profit": 10,
            "previous_net_profit": 10,
            "previous_operating_cash_flow": 15,
            "previous_free_cash_flow": 8,
            "previous_total_debt": 35,
            "previous_cash_and_equivalents": 50,
            "previous_receivables": 18,
            "previous_payables": 12,
            "close": 100,
            "return_1d": 0.02,
            "return_5d": 0.05,
            "return_20d": 0.10,
            "volatility_20d": 0.03,
            "volume_ratio_20d": 1.2,
            "drawdown_20d": -0.04,
        },
    )

    results = engine.calculate(context)

    assert len(results) == len(engine.feature_ids)

    revenue_growth = next(
        item
        for item in results
        if item.feature_id == "revenue_growth"
    )

    assert revenue_growth.value == pytest.approx(20.0)
    assert revenue_growth.status == FeatureStatus.VALID


def test_registry_engine_calculate_one():
    engine = ResearchFeatureEngine()

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=AS_OF,
        observations={
            "close": 250,
        },
    )

    result = engine.calculate_one(
        "market_close",
        context,
    )

    assert result.feature_id == "market_close"
    assert result.value == pytest.approx(250.0)
    assert result.status == FeatureStatus.VALID


def test_registry_engine_rejects_unknown_feature():
    engine = ResearchFeatureEngine()

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=AS_OF,
        observations={},
    )

    with pytest.raises(KeyError):
        engine.calculate_one(
            "does_not_exist",
            context,
        )
