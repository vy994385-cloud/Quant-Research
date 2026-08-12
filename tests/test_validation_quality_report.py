from datetime import date
from decimal import Decimal

import pytest

from src.ranking.ranking_quality import RankingQuality
from src.validation.ranking_outcomes import (
    build_ranking_outcome,
)
from src.validation.ranking_validation import (
    RankingObservation,
    validate_rankings,
)
from src.validation.validation_quality_report import (
    ValidationQualityReport,
    build_validation_quality_report,
)


def make_observation(
    symbol: str,
    score: str,
    entry: str,
    outcome: str,
    *,
    benchmark: str | None = None,
    horizon: str = "LONG_TERM",
) -> RankingObservation:
    ranking_date = date(2024, 1, 1)
    outcome_date = date(2024, 4, 1)

    result = build_ranking_outcome(
        symbol=symbol,
        ranking_date=ranking_date,
        outcome_date=outcome_date,
        horizon=horizon,
        entry_price=Decimal(entry),
        outcome_price=Decimal(outcome),
        benchmark_return=(
            Decimal(benchmark)
            if benchmark is not None
            else None
        ),
    )

    return RankingObservation(
        symbol=symbol,
        ranking_date=ranking_date,
        horizon=horizon,
        score=Decimal(score),
        outcome=result,
    )


def make_validation_result(
    *,
    benchmark: bool = True,
):
    observations = [
        make_observation(
            "AAA",
            "100",
            "100",
            "130",
            benchmark="0.10" if benchmark else None,
        ),
        make_observation(
            "BBB",
            "80",
            "100",
            "120",
            benchmark="0.10" if benchmark else None,
        ),
        make_observation(
            "CCC",
            "60",
            "100",
            "110",
            benchmark="0.10" if benchmark else None,
        ),
    ]

    return validate_rankings(observations)


def test_builds_quality_report():
    validation = make_validation_result()

    report = build_validation_quality_report(
        validation
    )

    assert isinstance(
        report,
        ValidationQualityReport,
    )

    assert report.horizon == "LONG_TERM"
    assert report.observation_count == 3
    assert report.average_forward_return == Decimal("0.20")
    assert report.median_forward_return == Decimal("0.20")
    assert report.positive_return_rate == Decimal("1")


def test_report_preserves_quality_assessment():
    validation = make_validation_result()

    report = ValidationQualityReport.from_validation_result(
        validation
    )

    assert report.quality == RankingQuality.INSUFFICIENT_DATA
    assert report.score == Decimal("0")
    assert report.confidence == Decimal("0.25")


def test_small_sample_is_not_actionable():
    validation = make_validation_result()

    report = build_validation_quality_report(
        validation
    )

    assert report.is_insufficient is True
    assert report.is_actionable is False
    assert report.is_strong is False


def test_report_preserves_excess_return_data():
    validation = make_validation_result()

    report = build_validation_quality_report(
        validation
    )

    assert report.average_excess_return == Decimal("0.10")
    assert report.positive_excess_return_rate == Decimal("1")


def test_report_preserves_correlation():
    validation = make_validation_result()

    report = build_validation_quality_report(
        validation
    )

    assert (
        report.score_return_correlation
        is not None
    )

    assert report.score_return_correlation > Decimal("0")


def test_reasons_are_preserved():
    validation = make_validation_result()

    report = build_validation_quality_report(
        validation
    )

    assert report.reasons
    assert report.reasons == tuple(report.reasons)


def test_to_dict_contains_quality_metadata():
    validation = make_validation_result()

    report = build_validation_quality_report(
        validation
    )

    data = report.to_dict()

    assert data["horizon"] == "LONG_TERM"
    assert data["observation_count"] == 3
    assert data["quality"] == "INSUFFICIENT_DATA"
    assert data["score"] == Decimal("0")
    assert data["confidence"] == Decimal("0.25")
    assert data["is_actionable"] is False
    assert data["is_strong"] is False
    assert data["is_insufficient"] is True


def test_from_assessment_rejects_mismatched_observation_count():
    validation = make_validation_result()

    assessment = (
        ValidationQualityReport
        .from_validation_result(validation)
    )

    with pytest.raises(
        TypeError,
    ):
        ValidationQualityReport.from_assessment(
            validation_result=validation,
            assessment=object(),
        )


def test_wrong_validation_result_type_is_rejected():
    with pytest.raises(
        TypeError,
        match="RankingValidationResult",
    ):
        build_validation_quality_report(
            object()
        )


def test_report_is_immutable():
    validation = make_validation_result()

    report = build_validation_quality_report(
        validation
    )

    with pytest.raises(
        AttributeError,
    ):
        report.score = Decimal("1")


def test_missing_benchmark_data_is_supported():
    validation = make_validation_result(
        benchmark=False,
    )

    report = build_validation_quality_report(
        validation
    )

    assert report.average_excess_return is None
    assert report.positive_excess_return_rate is None


def test_convenience_builder_matches_classmethod():
    validation = make_validation_result()

    first = build_validation_quality_report(
        validation
    )

    second = (
        ValidationQualityReport.from_validation_result(
            validation
        )
    )

    assert first == second


def test_report_does_not_modify_validation_result():
    validation = make_validation_result()

    before = (
        validation.horizon,
        validation.observation_count,
        validation.average_forward_return,
        validation.median_forward_return,
        validation.positive_return_rate,
        validation.average_excess_return,
        validation.positive_excess_return_rate,
        validation.score_return_correlation,
    )

    build_validation_quality_report(
        validation
    )

    after = (
        validation.horizon,
        validation.observation_count,
        validation.average_forward_return,
        validation.median_forward_return,
        validation.positive_return_rate,
        validation.average_excess_return,
        validation.positive_excess_return_rate,
        validation.score_return_correlation,
    )

    assert before == after