from datetime import datetime, timedelta, timezone

import pytest

from src.research.features.base import (
    FeatureCalculationContext,
    FeatureDefinition,
)
from src.research.features.engine import FeatureEngine
from src.research.features.models import FeatureStatus


AS_OF = datetime(
    2026,
    8,
    10,
    10,
    tzinfo=timezone.utc,
)


def revenue_growth(observations):
    return (
        observations["revenue"]
        / observations["previous_revenue"]
        - 1
    ) * 100


def test_engine_registers_features():
    engine = FeatureEngine(
        [
            FeatureDefinition(
                feature_id="revenue_growth",
                feature_version="1.0",
                unit="percent",
                calculator=revenue_growth,
                required_inputs=(
                    "revenue",
                    "previous_revenue",
                ),
            )
        ]
    )

    assert engine.feature_ids == (
        "revenue_growth",
    )


def test_duplicate_feature_ids_are_rejected():
    definition = FeatureDefinition(
        feature_id="test",
        feature_version="1.0",
        unit="ratio",
        calculator=lambda observations: 1.0,
    )

    with pytest.raises(ValueError):
        FeatureEngine(
            [
                definition,
                definition,
            ]
        )


def test_engine_calculates_valid_feature():
    engine = FeatureEngine(
        [
            FeatureDefinition(
                feature_id="revenue_growth",
                feature_version="1.0",
                unit="percent",
                calculator=revenue_growth,
                required_inputs=(
                    "revenue",
                    "previous_revenue",
                ),
            )
        ]
    )

    context = FeatureCalculationContext(
        symbol="test",
        timestamp=AS_OF,
        observations={
            "revenue": 120,
            "previous_revenue": 100,
        },
        source_ids=("Annual Report",),
        provenance_ids=("record-1",),
    )

    result = engine.calculate(context)

    assert len(result) == 1
    assert result[0].feature_id == "revenue_growth"
    assert result[0].value == pytest.approx(20.0)
    assert result[0].status == FeatureStatus.VALID
    assert result[0].source_ids == ("annual report",)
    assert result[0].provenance_ids == ("record-1",)


def test_missing_required_input_is_explicit():
    engine = FeatureEngine(
        [
            FeatureDefinition(
                feature_id="revenue_growth",
                feature_version="1.0",
                unit="percent",
                calculator=revenue_growth,
                required_inputs=(
                    "revenue",
                    "previous_revenue",
                ),
            )
        ]
    )

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=AS_OF,
        observations={
            "revenue": 120,
        },
    )

    result = engine.calculate(context)[0]

    assert result.status == FeatureStatus.MISSING
    assert result.value is None
    assert result.metadata == (
        ("missing_inputs", "previous_revenue"),
    )


def test_calculator_returning_none_is_missing():
    engine = FeatureEngine(
        [
            FeatureDefinition(
                feature_id="test",
                feature_version="1.0",
                unit="ratio",
                calculator=lambda observations: None,
            )
        ]
    )

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=AS_OF,
        observations={},
    )

    result = engine.calculate(context)[0]

    assert result.status == FeatureStatus.MISSING
    assert result.value is None


def test_calculator_error_becomes_invalid_feature():
    def broken(_):
        raise ValueError("bad input")

    engine = FeatureEngine(
        [
            FeatureDefinition(
                feature_id="broken",
                feature_version="1.0",
                unit="ratio",
                calculator=broken,
            )
        ]
    )

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=AS_OF,
        observations={},
    )

    result = engine.calculate(context)[0]

    assert result.status == FeatureStatus.INVALID
    assert result.value is None


def test_calculated_at_cannot_precede_context():
    engine = FeatureEngine(
        [
            FeatureDefinition(
                feature_id="test",
                feature_version="1.0",
                unit="ratio",
                calculator=lambda _: 1.0,
            )
        ]
    )

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=AS_OF,
        observations={},
    )

    with pytest.raises(ValueError):
        engine.calculate(
            context,
            calculated_at=AS_OF - timedelta(minutes=1),
        )


def test_calculate_one_unknown_feature_is_rejected():
    engine = FeatureEngine([])

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=AS_OF,
        observations={},
    )

    with pytest.raises(KeyError):
        engine.calculate_one(
            "unknown",
            context,
        )


def test_calculate_one_matches_batch_calculation():
    definition = FeatureDefinition(
        feature_id="test",
        feature_version="1.0",
        unit="ratio",
        calculator=lambda observations: 42.0,
    )

    engine = FeatureEngine([definition])

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=AS_OF,
        observations={},
    )

    batch = engine.calculate(context)[0]
    single = engine.calculate_one(
        "TEST",
        context,
    )

    assert single == batch
