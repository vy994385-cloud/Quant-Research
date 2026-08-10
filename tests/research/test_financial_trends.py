from math import isclose

from src.research.features.financial_trends import (
    FINANCIAL_TREND_FEATURE_DEFINITIONS,
    cash_change,
    free_cash_flow_change,
    net_profit_change,
    operating_cash_flow_change,
    operating_profit_change,
    payables_change,
    receivables_change,
    revenue_change,
    revenue_growth_change,
    total_debt_change,
)

from datetime import datetime, timezone

from src.research.features.snapshot_engine import (
    FeatureCalculationContext,
    FeatureSnapshotEngine,
)

OBSERVATIONS = {
    "revenue": 1200.0,
    "previous_revenue": 1000.0,
    "operating_profit": 180.0,
    "previous_operating_profit": 150.0,
    "net_profit": 120.0,
    "previous_net_profit": 100.0,
    "operating_cash_flow": 200.0,
    "previous_operating_cash_flow": 160.0,
    "free_cash_flow": 150.0,
    "previous_free_cash_flow": 120.0,
    "total_debt": 300.0,
    "previous_total_debt": 250.0,
    "cash_and_equivalents": 180.0,
    "previous_cash_and_equivalents": 150.0,
    "receivables": 240.0,
    "previous_receivables": 200.0,
    "payables": 180.0,
    "previous_payables": 150.0,
}


def test_revenue_change() -> None:
    assert revenue_change(OBSERVATIONS) == 200.0


def test_revenue_growth_change() -> None:
    assert isclose(
        revenue_growth_change(OBSERVATIONS),
        20.0,
    )


def test_operating_profit_change() -> None:
    assert operating_profit_change(
        OBSERVATIONS
    ) == 30.0


def test_net_profit_change() -> None:
    assert net_profit_change(
        OBSERVATIONS
    ) == 20.0


def test_operating_cash_flow_change() -> None:
    assert operating_cash_flow_change(
        OBSERVATIONS
    ) == 40.0


def test_free_cash_flow_change() -> None:
    assert free_cash_flow_change(
        OBSERVATIONS
    ) == 30.0


def test_total_debt_change() -> None:
    assert total_debt_change(
        OBSERVATIONS
    ) == 50.0


def test_cash_change() -> None:
    assert cash_change(
        OBSERVATIONS
    ) == 30.0


def test_receivables_change() -> None:
    assert receivables_change(
        OBSERVATIONS
    ) == 40.0


def test_payables_change() -> None:
    assert payables_change(
        OBSERVATIONS
    ) == 30.0


def test_missing_previous_value_returns_none() -> None:
    observations = {
        "revenue": 1200.0,
    }

    assert revenue_change(observations) is None


def test_zero_previous_value_returns_none_for_percentage_change() -> None:
    observations = {
        "revenue": 1200.0,
        "previous_revenue": 0.0,
    }

    assert revenue_growth_change(observations) is None


def test_negative_change_is_preserved() -> None:
    observations = {
        "revenue": 800.0,
        "previous_revenue": 1000.0,
    }

    assert revenue_change(observations) == -200.0

    assert isclose(
        revenue_growth_change(observations),
        -20.0,
    )


def test_trend_definitions_are_complete() -> None:
    ids = tuple(
        definition.feature_id
        for definition in FINANCIAL_TREND_FEATURE_DEFINITIONS
    )

    assert ids == (
        "revenue_change",
        "revenue_growth_change",
        "operating_profit_change",
        "net_profit_change",
        "operating_cash_flow_change",
        "free_cash_flow_change",
        "total_debt_change",
        "cash_change",
        "receivables_change",
        "payables_change",
    )


def test_trend_definitions_have_required_inputs() -> None:
    for definition in FINANCIAL_TREND_FEATURE_DEFINITIONS:
        assert definition.feature_id
        assert definition.feature_version
        assert definition.unit
        assert definition.required_inputs

def test_financial_trends_integrate_with_snapshot_engine() -> None:
    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=datetime(
            2026,
            8,
            10,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        observations=OBSERVATIONS,
        source_ids=("TEST_SOURCE",),
        provenance_ids=("financial-trend-001",),
    )

    engine = FeatureSnapshotEngine(
        FINANCIAL_TREND_FEATURE_DEFINITIONS
    )

    results = engine.calculate(context)

    assert len(results) == 10

    revenue_change_feature = next(
        feature
        for feature in results
        if feature.feature_id == "revenue_change"
    )

    assert revenue_change_feature.value == 200.0
    assert revenue_change_feature.unit == "absolute"
    assert revenue_change_feature.status.value == "VALID"
    assert revenue_change_feature.source_ids == (
        "test_source",
    )
    assert revenue_change_feature.provenance_ids == (
        "financial-trend-001",
    )