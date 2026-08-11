from datetime import date
from decimal import Decimal

import pytest

from src.validation.ranking_outcomes import (
    build_ranking_outcome,
)
from src.validation.ranking_validation import (
    RankingObservation,
    validate_rankings,
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


def test_validation_calculates_average_return():
    result = validate_rankings(
        [
            make_observation("AAA", "80", "100", "110"),
            make_observation("BBB", "60", "100", "90"),
        ]
    )

    assert result.observation_count == 2
    assert result.average_forward_return == Decimal("0")
    assert result.average_excess_return is None
    assert result.positive_return_rate == Decimal("0.5")


def test_validation_calculates_median_return():
    result = validate_rankings(
        [
            make_observation("AAA", "90", "100", "110"),
            make_observation("BBB", "80", "100", "120"),
            make_observation("CCC", "70", "100", "130"),
        ]
    )

    assert result.median_forward_return == Decimal("0.20")


def test_validation_calculates_excess_return():
    result = validate_rankings(
        [
            make_observation(
                "AAA",
                "90",
                "100",
                "120",
                benchmark="0.10",
            ),
            make_observation(
                "BBB",
                "80",
                "100",
                "90",
                benchmark="0.10",
            ),
        ]
    )

    assert result.average_excess_return == Decimal("-0.05")
    assert result.positive_excess_return_rate == Decimal("0.5")


def test_validation_calculates_score_return_correlation():
    result = validate_rankings(
        [
            make_observation("AAA", "100", "100", "130"),
            make_observation("BBB", "80", "100", "120"),
            make_observation("CCC", "60", "100", "110"),
        ]
    )

    assert result.score_return_correlation == Decimal("1")


def test_missing_benchmark_returns_none():
    result = validate_rankings(
        [
            make_observation("AAA", "80", "100", "110"),
        ]
    )

    assert result.average_excess_return is None
    assert result.positive_excess_return_rate is None


def test_empty_observations_are_rejected():
    with pytest.raises(
        ValueError,
        match="at least one",
    ):
        validate_rankings([])


def test_mixed_horizons_are_rejected():
    first = make_observation(
        "AAA",
        "80",
        "100",
        "110",
        horizon="LONG_TERM",
    )

    second = make_observation(
        "BBB",
        "80",
        "100",
        "110",
        horizon="SWING",
    )

    with pytest.raises(
        ValueError,
        match="same horizon",
    ):
        validate_rankings([first, second])


def test_symbol_mismatch_is_rejected():
    outcome = build_ranking_outcome(
        symbol="AAA",
        ranking_date=date(2024, 1, 1),
        outcome_date=date(2024, 4, 1),
        horizon="LONG_TERM",
        entry_price=Decimal("100"),
        outcome_price=Decimal("110"),
    )

    with pytest.raises(
        ValueError,
        match="symbol",
    ):
        RankingObservation(
            symbol="BBB",
            ranking_date=date(2024, 1, 1),
            horizon="LONG_TERM",
            score=Decimal("80"),
            outcome=outcome,
        )