from math import isclose

from src.research.features.financial_quality import (
    FINANCIAL_FEATURE_DEFINITIONS,
    cash_conversion_ratio,
    cash_to_debt,
    debt_to_revenue,
    free_cash_flow_margin,
    net_profit_margin,
    operating_cash_flow_margin,
    payables_to_revenue,
    receivables_to_revenue,
    revenue_growth,
)

from datetime import datetime, timezone

from src.research.features.snapshot_engine import (
    FeatureCalculationContext,
    FeatureSnapshotEngine,
)


def test_financial_features_integrate_with_snapshot_engine() -> None:
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
        provenance_ids=("financial-test-001",),
    )

    engine = FeatureSnapshotEngine(
        FINANCIAL_FEATURE_DEFINITIONS
    )

    results = engine.calculate(context)

    assert len(results) == 9

    revenue_growth_feature = next(
        feature
        for feature in results
        if feature.feature_id == "revenue_growth"
    )

    assert revenue_growth_feature.value == 20.0
    assert revenue_growth_feature.unit == "percent"
    assert revenue_growth_feature.status.value == "VALID"
    assert revenue_growth_feature.source_ids == (
        "test_source",
    )
    assert revenue_growth_feature.provenance_ids == (
        "financial-test-001",
    )

OBSERVATIONS = {
    "revenue": 1200.0,
    "previous_revenue": 1000.0,
    "net_profit": 120.0,
    "operating_cash_flow": 180.0,
    "free_cash_flow": 150.0,
    "receivables": 240.0,
    "payables": 180.0,
    "total_debt": 300.0,
    "cash_and_equivalents": 150.0,
}


def test_revenue_growth() -> None:
    assert isclose(
        revenue_growth(OBSERVATIONS),
        20.0,
    )


def test_net_profit_margin() -> None:
    assert isclose(
        net_profit_margin(OBSERVATIONS),
        10.0,
    )


def test_operating_cash_flow_margin() -> None:
    assert isclose(
        operating_cash_flow_margin(OBSERVATIONS),
        15.0,
    )


def test_free_cash_flow_margin() -> None:
    assert isclose(
        free_cash_flow_margin(OBSERVATIONS),
        12.5,
    )


def test_receivables_to_revenue() -> None:
    assert isclose(
        receivables_to_revenue(OBSERVATIONS),
        20.0,
    )


def test_payables_to_revenue() -> None:
    assert isclose(
        payables_to_revenue(OBSERVATIONS),
        15.0,
    )


def test_debt_to_revenue() -> None:
    assert isclose(
        debt_to_revenue(OBSERVATIONS),
        0.25,
    )


def test_cash_to_debt() -> None:
    assert isclose(
        cash_to_debt(OBSERVATIONS),
        0.5,
    )


def test_cash_conversion_ratio() -> None:
    assert isclose(
        cash_conversion_ratio(OBSERVATIONS),
        150.0,
    )


def test_zero_denominator_returns_none() -> None:
    observations = {
        **OBSERVATIONS,
        "revenue": 0.0,
    }

    assert net_profit_margin(observations) is None
    assert debt_to_revenue(observations) is None


def test_zero_previous_revenue_returns_none() -> None:
    observations = {
        **OBSERVATIONS,
        "previous_revenue": 0.0,
    }

    assert revenue_growth(observations) is None


def test_missing_inputs_return_none() -> None:
    observations = {
        "revenue": 1200.0,
    }

    assert net_profit_margin(observations) is None
    assert revenue_growth(observations) is None


def test_negative_revenue_growth_is_supported() -> None:
    observations = {
        **OBSERVATIONS,
        "previous_revenue": 1000.0,
        "revenue": 800.0,
    }

    assert isclose(
        revenue_growth(observations),
        -20.0,
    )


def test_financial_feature_definitions_are_registered() -> None:
    ids = tuple(
        definition.feature_id
        for definition in FINANCIAL_FEATURE_DEFINITIONS
    )

    assert ids == (
        "revenue_growth",
        "net_profit_margin",
        "operating_cash_flow_margin",
        "free_cash_flow_margin",
        "receivables_to_revenue",
        "payables_to_revenue",
        "debt_to_revenue",
        "cash_to_debt",
        "cash_conversion_ratio",
    )


def test_all_definitions_have_required_inputs() -> None:
    for definition in FINANCIAL_FEATURE_DEFINITIONS:
        assert definition.feature_id
        assert definition.feature_version
        assert definition.unit
        assert definition.required_inputs