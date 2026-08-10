from datetime import datetime, timezone

import pytest

from src.research.features.models import (
    FeatureStatus,
    FeatureValue,
)


UTC = timezone.utc


def make_feature(**overrides):
    values = {
        "feature_id": "roic",
        "feature_version": "1.0.0",
        "symbol": "TEST",
        "value": 0.25,
        "unit": "ratio",
        "observation_at": datetime(
            2026, 8, 1, tzinfo=UTC
        ),
        "calculated_at": datetime(
            2026, 8, 8, tzinfo=UTC
        ),
    }

    values.update(overrides)
    return FeatureValue(**values)


def test_valid_feature_is_usable():
    feature = make_feature()

    assert feature.is_usable
    assert feature.is_point_in_time_safe


def test_empty_feature_id_is_rejected():
    with pytest.raises(ValueError, match="feature_id"):
        make_feature(feature_id="")


def test_naive_observation_datetime_is_rejected():
    with pytest.raises(
        ValueError,
        match="observation_at must be timezone-aware",
    ):
        make_feature(
            observation_at=datetime(2026, 8, 1)
        )


def test_naive_calculation_datetime_is_rejected():
    with pytest.raises(
        ValueError,
        match="calculated_at must be timezone-aware",
    ):
        make_feature(
            calculated_at=datetime(2026, 8, 8)
        )


def test_non_finite_value_is_rejected():
    with pytest.raises(
        ValueError,
        match="feature value must be finite",
    ):
        make_feature(value=float("nan"))


def test_confidence_must_be_between_zero_and_one():
    with pytest.raises(
        ValueError,
        match="confidence",
    ):
        make_feature(confidence=1.1)


def test_valid_feature_requires_value():
    with pytest.raises(
        ValueError,
        match="VALID feature",
    ):
        make_feature(
            value=None,
            status=FeatureStatus.VALID,
        )


def test_missing_feature_can_have_no_value():
    feature = make_feature(
        value=None,
        status=FeatureStatus.MISSING,
    )

    assert not feature.is_usable


def test_source_ids_are_normalized():
    feature = make_feature(
        source_ids=(" NSE_INDIA ", "sec_edgar", "nse_india")
    )

    assert feature.source_ids == (
        "nse_india",
        "sec_edgar",
    )


def test_observation_cannot_be_after_calculation():
    feature = make_feature(
        observation_at=datetime(
            2026, 8, 9, tzinfo=UTC
        ),
        calculated_at=datetime(
            2026, 8, 8, tzinfo=UTC
        ),
    )

    assert not feature.is_point_in_time_safe


def test_feature_is_immutable():
    feature = make_feature()

    with pytest.raises(Exception):
        feature.value = 100
