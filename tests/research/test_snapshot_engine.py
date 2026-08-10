from datetime import datetime, timedelta, timezone

import pytest

from src.research.features.models import FeatureStatus
from src.research.features.snapshot_engine import (
    FeatureCalculationContext,
    FeatureDefinition,
    FeatureSnapshotEngine,
)


UTC = timezone.utc


def test_calculates_feature_deterministically():
    definition = FeatureDefinition(
        feature_id="gross_margin",
        feature_version="1.0.0",
        unit="ratio",
        required_inputs=("revenue", "cost"),
        calculator=lambda x: (
            (x["revenue"] - x["cost"])
            / x["revenue"]
        ),
    )

    engine = FeatureSnapshotEngine([definition])

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=datetime(
            2026, 8, 8, tzinfo=UTC
        ),
        observations={
            "revenue": 100.0,
            "cost": 60.0,
        },
        source_ids=("SEC_EDGAR",),
        provenance_ids=("filing-123",),
    )

    results = engine.calculate(context)

    assert len(results) == 1
    assert results[0].feature_id == "gross_margin"
    assert results[0].value == 0.4
    assert results[0].is_usable
    assert results[0].source_ids == ("sec_edgar",)
    assert results[0].provenance_ids == ("filing-123",)


def test_missing_required_input_does_not_become_zero():
    definition = FeatureDefinition(
        feature_id="margin",
        feature_version="1.0.0",
        unit="ratio",
        required_inputs=("revenue", "profit"),
        calculator=lambda x: x["profit"] / x["revenue"],
    )

    engine = FeatureSnapshotEngine([definition])

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=datetime(
            2026, 8, 8, tzinfo=UTC
        ),
        observations={"revenue": 100.0},
    )

    result = engine.calculate(context)[0]

    assert result.status == FeatureStatus.MISSING
    assert result.value is None
    assert not result.is_usable


def test_calculator_failure_becomes_invalid_feature():
    definition = FeatureDefinition(
        feature_id="bad_feature",
        feature_version="1.0.0",
        unit="ratio",
        calculator=lambda _: 1 / 0,
    )

    engine = FeatureSnapshotEngine([definition])

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=datetime(
            2026, 8, 8, tzinfo=UTC
        ),
        observations={},
    )

    result = engine.calculate(context)[0]

    assert result.status == FeatureStatus.INVALID
    assert result.value is None


def test_calculator_returning_none_is_missing():
    definition = FeatureDefinition(
        feature_id="optional_feature",
        feature_version="1.0.0",
        unit="ratio",
        calculator=lambda _: None,
    )

    engine = FeatureSnapshotEngine([definition])

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=datetime(
            2026, 8, 8, tzinfo=UTC
        ),
        observations={},
    )

    result = engine.calculate(context)[0]

    assert result.status == FeatureStatus.MISSING
    assert result.value is None


def test_naive_context_timestamp_is_rejected():
    with pytest.raises(
        ValueError,
        match="timestamp must be timezone-aware",
    ):
        FeatureCalculationContext(
            symbol="TEST",
            timestamp=datetime(2026, 8, 8),
            observations={},
        )


def test_naive_calculation_timestamp_is_rejected():
    definition = FeatureDefinition(
        feature_id="test",
        feature_version="1.0.0",
        unit="value",
        calculator=lambda _: 1.0,
    )

    engine = FeatureSnapshotEngine([definition])

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=datetime(
            2026, 8, 8, tzinfo=UTC
        ),
        observations={},
    )

    with pytest.raises(
        ValueError,
        match="calculated_at must be timezone-aware",
    ):
        engine.calculate(
            context,
            calculated_at=datetime(2026, 8, 8),
        )


def test_calculation_cannot_precede_context_timestamp():
    definition = FeatureDefinition(
        feature_id="test",
        feature_version="1.0.0",
        unit="value",
        calculator=lambda _: 1.0,
    )

    engine = FeatureSnapshotEngine([definition])

    timestamp = datetime(
        2026, 8, 8, tzinfo=UTC
    )

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=timestamp,
        observations={},
    )

    with pytest.raises(
        ValueError,
        match="cannot be earlier",
    ):
        engine.calculate(
            context,
            calculated_at=timestamp - timedelta(seconds=1),
        )


def test_duplicate_feature_ids_are_rejected():
    definition = FeatureDefinition(
        feature_id="ROIC",
        feature_version="1.0.0",
        unit="ratio",
        calculator=lambda _: 1.0,
    )

    duplicate = FeatureDefinition(
        feature_id="roic",
        feature_version="2.0.0",
        unit="ratio",
        calculator=lambda _: 2.0,
    )

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        FeatureSnapshotEngine(
            [definition, duplicate]
        )


def test_feature_ids_are_sorted():
    engine = FeatureSnapshotEngine(
        [
            FeatureDefinition(
                feature_id="z_feature",
                feature_version="1.0.0",
                unit="value",
                calculator=lambda _: 1.0,
            ),
            FeatureDefinition(
                feature_id="a_feature",
                feature_version="1.0.0",
                unit="value",
                calculator=lambda _: 1.0,
            ),
        ]
    )

    assert engine.feature_ids == (
        "a_feature",
        "z_feature",
    )


def test_feature_version_is_preserved():
    definition = FeatureDefinition(
        feature_id="roic",
        feature_version="2.1.0",
        unit="ratio",
        calculator=lambda _: 0.2,
    )

    engine = FeatureSnapshotEngine([definition])

    context = FeatureCalculationContext(
        symbol="TEST",
        timestamp=datetime(
            2026, 8, 8, tzinfo=UTC
        ),
        observations={},
    )

    result = engine.calculate(context)[0]

    assert result.feature_version == "2.1.0"
