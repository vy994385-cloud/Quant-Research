from datetime import datetime, timedelta, timezone

import pytest

from src.research.features.models import (
    FeatureStatus,
    FeatureValue,
)
from src.research.features.quality import (
    FeatureQualityEvaluator,
)


UTC = timezone.utc


def make_feature(
    *,
    value: float | None = 10.0,
    status: FeatureStatus = FeatureStatus.VALID,
    observation_at: datetime | None = None,
    calculated_at: datetime | None = None,
    confidence: float = 1.0,
) -> FeatureValue:
    observed = observation_at or datetime(
        2026,
        1,
        1,
        tzinfo=UTC,
    )

    calculated = calculated_at or datetime(
        2026,
        1,
        2,
        tzinfo=UTC,
    )

    return FeatureValue(
        feature_id="revenue_growth",
        feature_version="1.0",
        symbol="TEST",
        value=value,
        unit="percent",
        observation_at=observed,
        calculated_at=calculated,
        status=status,
        confidence=confidence,
    )


def test_valid_feature_passes() -> None:
    evaluator = FeatureQualityEvaluator()

    result = evaluator.evaluate(
        make_feature()
    )

    assert result.usable is True
    assert result.passed is True
    assert result.status == FeatureStatus.VALID
    assert result.reasons == ()


def test_missing_feature_fails() -> None:
    evaluator = FeatureQualityEvaluator()

    result = evaluator.evaluate(
        make_feature(
            value=None,
            status=FeatureStatus.MISSING,
        )
    )

    assert result.usable is False
    assert result.status == FeatureStatus.MISSING
    assert "status:MISSING" in result.reasons
    assert "missing_value" in result.reasons


def test_invalid_feature_fails() -> None:
    evaluator = FeatureQualityEvaluator()

    result = evaluator.evaluate(
        make_feature(
            value=None,
            status=FeatureStatus.INVALID,
        )
    )

    assert result.usable is False
    assert result.status == FeatureStatus.INVALID


def test_existing_point_in_time_violation_is_rejected() -> None:
    evaluator = FeatureQualityEvaluator()

    result = evaluator.evaluate(
        make_feature(
            status=FeatureStatus.PIT_VIOLATION,
        )
    )

    assert result.usable is False
    assert result.status == FeatureStatus.PIT_VIOLATION


def test_observation_after_calculation_is_point_in_time_violation() -> None:
    evaluator = FeatureQualityEvaluator()

    result = evaluator.evaluate(
        make_feature(
            observation_at=datetime(
                2026,
                1,
                3,
                tzinfo=UTC,
            ),
            calculated_at=datetime(
                2026,
                1,
                2,
                tzinfo=UTC,
            ),
        )
    )

    assert result.usable is False
    assert result.status == FeatureStatus.PIT_VIOLATION
    assert "observation_after_calculation" in result.reasons


def test_as_of_rejects_future_observation() -> None:
    evaluator = FeatureQualityEvaluator()

    result = evaluator.evaluate(
        make_feature(
            observation_at=datetime(
                2026,
                1,
                10,
                tzinfo=UTC,
            )
        ),
        as_of=datetime(
            2026,
            1,
            5,
            tzinfo=UTC,
        ),
    )

    assert result.usable is False
    assert result.status == FeatureStatus.PIT_VIOLATION
    assert "observation_after_as_of" in result.reasons


def test_as_of_rejects_future_calculation() -> None:
    evaluator = FeatureQualityEvaluator()

    result = evaluator.evaluate(
        make_feature(
            calculated_at=datetime(
                2026,
                1,
                10,
                tzinfo=UTC,
            )
        ),
        as_of=datetime(
            2026,
            1,
            5,
            tzinfo=UTC,
        ),
    )

    assert result.usable is False
    assert result.status == FeatureStatus.PIT_VIOLATION
    assert "calculation_after_as_of" in result.reasons


def test_stale_feature_is_rejected() -> None:
    evaluator = FeatureQualityEvaluator(
        max_age=timedelta(days=30),
    )

    result = evaluator.evaluate(
        make_feature(
            observation_at=datetime(
                2026,
                1,
                1,
                tzinfo=UTC,
            )
        ),
        as_of=datetime(
            2026,
            2,
                15,
                tzinfo=UTC,
        ),
    )

    assert result.usable is False
    assert result.status == FeatureStatus.STALE
    assert "stale" in result.reasons


def test_confidence_threshold_is_enforced() -> None:
    evaluator = FeatureQualityEvaluator(
        minimum_confidence=0.8,
    )

    result = evaluator.evaluate(
        make_feature(
            confidence=0.79,
        )
    )

    assert result.usable is False
    assert result.status == FeatureStatus.INVALID
    assert "low_confidence" in result.reasons


def test_evaluate_many_preserves_feature_order() -> None:
    evaluator = FeatureQualityEvaluator()

    first = make_feature()
    second = FeatureValue(
        feature_id="margin",
        feature_version="1.0",
        symbol="TEST",
        value=20.0,
        unit="percent",
        observation_at=datetime(
            2026,
            1,
            1,
            tzinfo=UTC,
        ),
        calculated_at=datetime(
            2026,
            1,
            2,
            tzinfo=UTC,
        ),
    )

    results = evaluator.evaluate_many(
        [first, second]
    )

    assert len(results) == 2
    assert results[0].feature_id == "revenue_growth"
    assert results[1].feature_id == "margin"


def test_as_of_must_be_timezone_aware() -> None:
    evaluator = FeatureQualityEvaluator()

    with pytest.raises(ValueError, match="timezone-aware"):
        evaluator.evaluate(
            make_feature(),
            as_of=datetime(
                2026,
                1,
                5,
            ),
        )


def test_invalid_constructor_configuration_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="minimum_confidence",
    ):
        FeatureQualityEvaluator(
            minimum_confidence=1.5
        )