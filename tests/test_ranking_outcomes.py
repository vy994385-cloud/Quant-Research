from datetime import date
from decimal import Decimal

import pytest

from src.validation.ranking_outcomes import (
    RankingOutcome,
    build_ranking_outcome,
)


def test_ranking_outcome_calculates_forward_return():
    result = build_ranking_outcome(
        symbol="test",
        ranking_date=date(2024, 1, 1),
        outcome_date=date(2024, 4, 1),
        horizon="long_term",
        entry_price=Decimal("100"),
        outcome_price=Decimal("120"),
    )

    assert result.symbol == "TEST"
    assert result.horizon == "LONG_TERM"
    assert result.forward_return == Decimal("0.20")
    assert result.is_positive is True


def test_ranking_outcome_calculates_excess_return():
    result = build_ranking_outcome(
        symbol="TEST",
        ranking_date=date(2024, 1, 1),
        outcome_date=date(2024, 4, 1),
        horizon="LONG_TERM",
        entry_price=Decimal("100"),
        outcome_price=Decimal("120"),
        benchmark_return=Decimal("0.10"),
    )

    assert result.forward_return == Decimal("0.20")
    assert result.excess_return == Decimal("0.10")
    assert result.is_benchmark_outperforming is True


def test_outcome_date_must_be_after_ranking_date():
    with pytest.raises(ValueError, match="outcome_date"):
        build_ranking_outcome(
            symbol="TEST",
            ranking_date=date(2024, 4, 1),
            outcome_date=date(2024, 4, 1),
            horizon="LONG_TERM",
            entry_price=Decimal("100"),
            outcome_price=Decimal("120"),
        )


def test_outcome_price_must_be_positive():
    with pytest.raises(ValueError, match="outcome_price"):
        build_ranking_outcome(
            symbol="TEST",
            ranking_date=date(2024, 1, 1),
            outcome_date=date(2024, 4, 1),
            horizon="LONG_TERM",
            entry_price=Decimal("100"),
            outcome_price=Decimal("0"),
        )


def test_entry_price_must_be_positive():
    with pytest.raises(ValueError, match="entry_price"):
        build_ranking_outcome(
            symbol="TEST",
            ranking_date=date(2024, 1, 1),
            outcome_date=date(2024, 4, 1),
            horizon="LONG_TERM",
            entry_price=Decimal("0"),
            outcome_price=Decimal("120"),
        )


def test_forward_return_cannot_be_manually_inconsistent():
    with pytest.raises(
        ValueError,
        match="forward_return",
    ):
        RankingOutcome(
            symbol="TEST",
            ranking_date=date(2024, 1, 1),
            outcome_date=date(2024, 4, 1),
            horizon="LONG_TERM",
            entry_price=Decimal("100"),
            outcome_price=Decimal("120"),
            forward_return=Decimal("0.10"),
        )


def test_excess_return_cannot_be_manually_inconsistent():
    with pytest.raises(
        ValueError,
        match="excess_return",
    ):
        RankingOutcome(
            symbol="TEST",
            ranking_date=date(2024, 1, 1),
            outcome_date=date(2024, 4, 1),
            horizon="LONG_TERM",
            entry_price=Decimal("100"),
            outcome_price=Decimal("120"),
            forward_return=Decimal("0.20"),
            benchmark_return=Decimal("0.10"),
            excess_return=Decimal("0.05"),
        )