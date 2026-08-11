from decimal import Decimal

import pytest

from src.ranking.ranking_quality import (
    RankingQuality,
    RankingQualityAssessment,
    assess_ranking_quality,
    assess_validation_result,
)


def test_small_sample_is_insufficient():
    result = assess_ranking_quality(
        observation_count=5,
        average_forward_return=Decimal("0.20"),
        positive_return_rate=Decimal("0.80"),
    )

    assert result.quality == RankingQuality.INSUFFICIENT_DATA
    assert result.score == Decimal("0")
    assert result.confidence == Decimal("0.25")


def test_zero_observations_are_insufficient():
    result = assess_ranking_quality(
        observation_count=0,
        average_forward_return=Decimal("0"),
        positive_return_rate=Decimal("0"),
    )

    assert result.quality == RankingQuality.INSUFFICIENT_DATA
    assert result.confidence == Decimal("0")


def test_strong_ranking_quality():
    result = assess_ranking_quality(
        observation_count=200,
        average_forward_return=Decimal("0.20"),
        positive_return_rate=Decimal("0.70"),
        average_excess_return=Decimal("0.10"),
        positive_excess_return_rate=Decimal("0.65"),
        score_return_correlation=Decimal("0.80"),
    )

    assert result.quality == RankingQuality.STRONG
    assert result.score > Decimal("0.75")
    assert result.confidence == Decimal("1")


def test_weak_ranking_quality():
    result = assess_ranking_quality(
        observation_count=100,
        average_forward_return=Decimal("-0.20"),
        positive_return_rate=Decimal("0.30"),
        average_excess_return=Decimal("-0.10"),
        positive_excess_return_rate=Decimal("0.25"),
        score_return_correlation=Decimal("-0.50"),
    )

    assert result.quality == RankingQuality.WEAK
    assert result.score < Decimal("0.55")


def test_moderate_ranking_quality():
    result = assess_ranking_quality(
        observation_count=100,
        average_forward_return=Decimal("0.05"),
        positive_return_rate=Decimal("0.55"),
        average_excess_return=Decimal("0.02"),
        positive_excess_return_rate=Decimal("0.52"),
        score_return_correlation=Decimal("0.20"),
    )

    assert result.quality == RankingQuality.MODERATE
    assert Decimal("0.55") <= result.score < Decimal("0.75")


def test_missing_excess_return_is_supported():
    result = assess_ranking_quality(
        observation_count=50,
        average_forward_return=Decimal("0.10"),
        positive_return_rate=Decimal("0.60"),
    )

    assert result.average_excess_return is None
    assert result.positive_excess_return_rate is None
    assert result.quality != RankingQuality.INSUFFICIENT_DATA


def test_missing_correlation_is_supported():
    result = assess_ranking_quality(
        observation_count=50,
        average_forward_return=Decimal("0.10"),
        positive_return_rate=Decimal("0.60"),
        average_excess_return=Decimal("0.05"),
        positive_excess_return_rate=Decimal("0.55"),
    )

    assert result.score_return_correlation is None


def test_validation_result_adapter():
    class FakeValidationResult:
        observation_count = 100
        average_forward_return = Decimal("0.10")
        positive_return_rate = Decimal("0.60")
        average_excess_return = Decimal("0.05")
        positive_excess_return_rate = Decimal("0.55")
        score_return_correlation = Decimal("0.50")

    result = assess_validation_result(
        FakeValidationResult()
    )

    assert result.observation_count == 100
    assert result.average_forward_return == Decimal("0.10")
    assert result.average_excess_return == Decimal("0.05")


def test_invalid_positive_return_rate_is_rejected():
    with pytest.raises(
        ValueError,
        match="positive_return_rate",
    ):
        assess_ranking_quality(
            observation_count=20,
            average_forward_return=Decimal("0.10"),
            positive_return_rate=Decimal("1.20"),
        )


def test_invalid_correlation_is_rejected():
    with pytest.raises(
        ValueError,
        match="score_return_correlation",
    ):
        assess_ranking_quality(
            observation_count=20,
            average_forward_return=Decimal("0.10"),
            positive_return_rate=Decimal("0.60"),
            score_return_correlation=Decimal("2"),
        )


def test_assessment_is_immutable():
    result = assess_ranking_quality(
        observation_count=20,
        average_forward_return=Decimal("0.10"),
        positive_return_rate=Decimal("0.60"),
    )

    with pytest.raises(
        AttributeError,
    ):
        result.score = Decimal("0.90")


def test_reasons_are_generated():
    result = assess_ranking_quality(
        observation_count=50,
        average_forward_return=Decimal("0.10"),
        positive_return_rate=Decimal("0.60"),
        average_excess_return=Decimal("0.05"),
        positive_excess_return_rate=Decimal("0.60"),
        score_return_correlation=Decimal("0.50"),
    )

    assert len(result.reasons) >= 3
    assert any(
        "positive average forward returns" in reason
        for reason in result.reasons
    )


def test_sample_confidence_progresses():
    small = assess_ranking_quality(
        observation_count=10,
        average_forward_return=Decimal("0.10"),
        positive_return_rate=Decimal("0.60"),
    )

    medium = assess_ranking_quality(
        observation_count=50,
        average_forward_return=Decimal("0.10"),
        positive_return_rate=Decimal("0.60"),
    )

    large = assess_ranking_quality(
        observation_count=100,
        average_forward_return=Decimal("0.10"),
        positive_return_rate=Decimal("0.60"),
    )

    assert small.confidence < medium.confidence
    assert medium.confidence < large.confidence


def test_assessment_fields_are_preserved():
    result = assess_ranking_quality(
        observation_count=50,
        average_forward_return=Decimal("0.12"),
        positive_return_rate=Decimal("0.62"),
        average_excess_return=Decimal("0.04"),
        positive_excess_return_rate=Decimal("0.58"),
        score_return_correlation=Decimal("0.40"),
    )

    assert isinstance(result, RankingQualityAssessment)
    assert result.observation_count == 50
    assert result.average_forward_return == Decimal("0.12")
    assert result.positive_return_rate == Decimal("0.62")
    assert result.average_excess_return == Decimal("0.04")
    assert result.positive_excess_return_rate == Decimal("0.58")
    assert result.score_return_correlation == Decimal("0.40")