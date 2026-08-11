from datetime import datetime, timezone

import pytest

from src.research.features.models import (
    FeatureStatus,
    FeatureValue,
)


def timestamp():
    return datetime(
        2026,
        8,
        10,
        10,
        tzinfo=timezone.utc,
    )


def test_feature_value_normalizes_identity_fields():
    feature = FeatureValue(
        feature_id=" Revenue_Growth ",
        feature_version=" 1.0 ",
        symbol=" test ",
        value=12.5,
        unit=" percent ",
        observation_at=timestamp(),
        calculated_at=timestamp(),
        source_ids=(" BSE ", "bse"),
        provenance_ids=(" record-2 ", "record-1"),
    )

    assert feature.feature_id == "revenue_growth"
    assert feature.feature_version == "1.0"
    assert feature.symbol == "TEST"
    assert feature.unit == "percent"
    assert feature.source_ids == ("bse",)
    assert feature.provenance_ids == (
        "record-1",
        "record-2",
    )


def test_valid_feature_requires_value():
    with pytest.raises(ValueError):
        FeatureValue(
            feature_id="test",
            feature_version="1.0",
            symbol="TEST",
            value=None,
            unit="ratio",
            observation_at=timestamp(),
            calculated_at=timestamp(),
            status=FeatureStatus.VALID,
        )


def test_feature_value_rejects_naive_timestamps():
    naive = datetime(2026, 8, 10)

    with pytest.raises(ValueError):
        FeatureValue(
            feature_id="test",
            feature_version="1.0",
            symbol="TEST",
            value=1.0,
            unit="ratio",
            observation_at=naive,
            calculated_at=timestamp(),
        )


def test_feature_value_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        FeatureValue(
            feature_id="test",
            feature_version="1.0",
            symbol="TEST",
            value=1.0,
            unit="ratio",
            observation_at=timestamp(),
            calculated_at=timestamp(),
            confidence=1.5,
        )


def test_missing_feature_is_not_usable():
    feature = FeatureValue(
        feature_id="test",
        feature_version="1.0",
        symbol="TEST",
        value=None,
        unit="ratio",
        observation_at=timestamp(),
        calculated_at=timestamp(),
        status=FeatureStatus.MISSING,
    )

    assert not feature.is_usable
    assert not feature.is_point_in_time_safe


def test_valid_feature_is_point_in_time_safe():
    feature = FeatureValue(
        feature_id="test",
        feature_version="1.0",
        symbol="TEST",
        value=1.0,
        unit="ratio",
        observation_at=timestamp(),
        calculated_at=timestamp(),
    )

    assert feature.is_usable
    assert feature.is_point_in_time_safe
