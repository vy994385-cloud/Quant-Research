from decimal import Decimal

import pytest

from src.ranking.stock_ranker import (
    RankingInput,
    rank_stock,
    rank_stocks,
)


def make_stock(
    symbol: str = "TEST",
    base: str = "80",
) -> RankingInput:
    value = Decimal(base)

    return RankingInput(
        symbol=symbol,
        research_score=value,
        fundamentals=value,
        financial_trends=value,
        cash_flow=value,
        balance_sheet=value,
        risk=value,
        momentum=value,
        trend_strength=value,
        liquidity=value,
        volatility=value,
        relative_strength=value,
        catalyst_strength=value,
        valuation=value,
        management=value,
        evidence_quality=value,
    )


def test_intraday_ranking_is_created():
    result = rank_stock(
        make_stock(),
        "INTRADAY",
    )

    assert result.symbol == "TEST"
    assert result.horizon == "INTRADAY"
    assert result.score == Decimal("80.00")
    assert result.rank_signal == "HIGH_PRIORITY"


def test_swing_ranking_is_created():
    result = rank_stock(
        make_stock(base="70"),
        "SWING",
    )

    assert result.symbol == "TEST"
    assert result.horizon == "SWING"

    # Future-aware ranking includes additional normalized
    # intelligence components, so the final score is not
    # necessarily identical to the base component value.
    assert result.score == Decimal("69.00")
    assert result.rank_signal == "WATCH"


def test_long_term_ranking_is_created():
    result = rank_stock(
        make_stock(base="90"),
        "LONG_TERM",
    )

    assert result.symbol == "TEST"
    assert result.horizon == "LONG_TERM"

    # Long-term ranking gives greater influence to
    # future-oriented research dimensions.
    assert result.score == Decimal(
        "80.82568807339449541284403672"
    )
    assert result.rank_signal == "HIGH_PRIORITY"


def test_different_horizons_use_different_weights():
    stock = make_stock()

    intraday = rank_stock(
        stock,
        "INTRADAY",
    )

    long_term = rank_stock(
        stock,
        "LONG_TERM",
    )

    # Horizon-specific weighting must actually affect the result.
    assert intraday.score != long_term.score


def test_future_aware_components_are_present():
    result = rank_stock(
        make_stock(),
        "LONG_TERM",
    )

    assert "ai_participation" in result.components
    assert "future_readiness" in result.components
    assert "innovation_execution" in result.components
    assert "technology_diversification" in result.components
    assert "sector_fit" in result.components


def test_future_aware_components_are_normalized():
    result = rank_stock(
        make_stock(),
        "LONG_TERM",
    )

    for name in (
        "ai_participation",
        "future_readiness",
        "innovation_execution",
        "technology_diversification",
        "sector_fit",
    ):
        value = result.components[name]

        assert Decimal("0") <= value <= Decimal("100")


def test_stocks_are_ranked_highest_first():
    stocks = [
        make_stock("LOW", "50"),
        make_stock("HIGH", "90"),
        make_stock("MID", "70"),
    ]

    rankings = rank_stocks(
        stocks,
        "SWING",
    )

    assert [item.symbol for item in rankings] == [
        "HIGH",
        "MID",
        "LOW",
    ]


def test_ties_are_deterministic():
    stocks = [
        make_stock("ZZZ", "80"),
        make_stock("AAA", "80"),
    ]

    rankings = rank_stocks(
        stocks,
        "SWING",
    )

    assert [item.symbol for item in rankings] == [
        "AAA",
        "ZZZ",
    ]


def test_invalid_component_is_rejected():
    stock = make_stock()

    invalid = RankingInput(
        **{
            **vars(stock),
            "momentum": Decimal("101"),
        }
    )

    with pytest.raises(ValueError):
        rank_stock(
            invalid,
            "INTRADAY",
        )


def test_invalid_horizon_is_rejected():
    with pytest.raises(ValueError):
        rank_stock(
            make_stock(),
            "INVALID",  # type: ignore[arg-type]
        )