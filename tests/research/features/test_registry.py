import pytest

from src.research.features.registry import (
    ALL_FEATURE_DEFINITIONS,
    feature_definitions,
    feature_ids,
    get_feature_definition,
)


def test_registry_contains_features():
    definitions = feature_definitions()

    assert definitions == ALL_FEATURE_DEFINITIONS
    assert len(definitions) > 20


def test_registry_feature_ids_are_unique():
    ids = feature_ids()

    assert len(ids) == len(set(ids))
    assert ids == tuple(
        definition.feature_id
        for definition in ALL_FEATURE_DEFINITIONS
    )


def test_registry_contains_financial_features():
    ids = set(feature_ids())

    assert "revenue_growth" in ids
    assert "net_profit_margin" in ids
    assert "cash_conversion_ratio" in ids


def test_registry_contains_trend_features():
    ids = set(feature_ids())

    assert "revenue_change" in ids
    assert "operating_profit_change" in ids
    assert "total_debt_change" in ids


def test_registry_contains_market_features():
    ids = set(feature_ids())

    assert "market_close" in ids
    assert "market_return_20d" in ids
    assert "market_volatility_20d" in ids
    assert "market_drawdown_20d" in ids


def test_get_feature_definition():
    definition = get_feature_definition(
        "NET_PROFIT_MARGIN"
    )

    assert definition.feature_id == "net_profit_margin"
    assert definition.unit == "percent"


def test_unknown_feature_is_rejected():
    with pytest.raises(KeyError):
        get_feature_definition("does_not_exist")
