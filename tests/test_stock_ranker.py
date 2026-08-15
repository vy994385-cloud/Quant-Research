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

def test_missing_components_are_excluded_from_score():
    stock = make_stock()

    result = rank_stock(
        RankingInput(
            **{
                **vars(stock),
                "available_components": frozenset({
                    "research_score",
                    "fundamentals",
                }),
            }
        ),
        "LONG_TERM",
    )

    assert result.score == Decimal("80")
    assert result.coverage < Decimal("100")

    assert "cash_flow" in result.missing_components
    assert "sector_fit" in result.missing_components


def test_missing_component_does_not_count_as_neutral_evidence():
    stock = make_stock()

    # Build a stock where future_readiness has a deliberately
    # extreme compatibility value, but no evidence is available.
    partial = rank_stock(
        RankingInput(
            **{
                **vars(stock),
                "future_readiness": Decimal("0"),
                "available_components": frozenset({
                    "research_score",
                    "fundamentals",
                    "financial_trends",
                    "cash_flow",
                    "balance_sheet",
                    "risk",
                    "momentum",
                    "trend_strength",
                    "liquidity",
                    "volatility",
                    "relative_strength",
                    "catalyst_strength",
                    "valuation",
                    "management",
                    "evidence_quality",
                }),
            }
        ),
        "LONG_TERM",
    )

    # The unavailable zero must not pull the ranking down.
    # The remaining available components are all 80.
    assert abs(partial.score - Decimal("80")) < Decimal("0.00000001")
    assert "future_readiness" in partial.missing_components
    assert partial.coverage < Decimal("100")


def test_normalised_ranking_weights_sum_to_one():
    from src.ranking.stock_ranker import (
        _WEIGHTS,
        _normalise_weights,
    )

    for horizon, weights in _WEIGHTS.items():
        normalised = _normalise_weights(weights)

        assert (
            sum(
                normalised.values(),
                Decimal("0"),
            )
            == Decimal("1")
        )


def test_higher_component_value_cannot_reduce_score_when_all_else_equal():
    low = make_stock("LOW", "60")
    high = make_stock("HIGH", "60")

    high = RankingInput(
        **{
            **vars(high),
            "fundamentals": Decimal("90"),
        }
    )

    low_result = rank_stock(low, "LONG_TERM")
    high_result = rank_stock(high, "LONG_TERM")

    assert high_result.score > low_result.score


def test_missing_zero_weight_component_does_not_reduce_coverage():
    stock = make_stock()

    result = rank_stock(
        RankingInput(
            **{
                **vars(stock),
                "available_components": frozenset(
                    set(vars(stock)) - {
                        "symbol",
                        "available_components",
                        "ai_participation",
                        "technology_diversification",
                    }
                ),
            }
        ),
        "INTRADAY",
    )

    assert result.coverage == Decimal("100")
    assert "ai_participation" not in result.missing_components
    assert "technology_diversification" not in result.missing_components


def test_missing_high_weight_component_reduces_coverage():
    stock = make_stock()

    available = set(vars(stock)) - {
        "symbol",
        "available_components",
        "fundamentals",
    }

    result = rank_stock(
        RankingInput(
            **{
                **vars(stock),
                "available_components": frozenset(available),
            }
        ),
        "LONG_TERM",
    )

    assert result.coverage < Decimal("100")
    assert "fundamentals" in result.missing_components


def test_missing_evidence_is_not_neutral():
    stock = make_stock()

    complete = rank_stock(
        stock,
        "LONG_TERM",
    )

    partial = rank_stock(
        RankingInput(
            **{
                **vars(stock),
                "available_components": frozenset({
                    "fundamentals",
                }),
            }
        ),
        "LONG_TERM",
    )

    # Only fundamentals is available, so its configured weight is
    # renormalized to 100% rather than mixing missing evidence
    # with compatibility values.
    assert partial.score == Decimal("80")
    assert partial.coverage < Decimal("100")

    # The complete ranking legitimately differs because its future
    # intelligence dimensions are available at their compatibility
    # values rather than being absent.
    assert partial.score != complete.score


def test_extreme_future_score_cannot_affect_intraday():
    stock = make_stock()

    extreme = RankingInput(
        **{
            **vars(stock),
            "future_readiness": Decimal("0"),
            "ai_participation": Decimal("100"),
            "innovation_execution": Decimal("0"),
            "technology_diversification": Decimal("100"),
            "sector_fit": Decimal("0"),
        }
    )

    normal_result = rank_stock(stock, "INTRADAY")
    extreme_result = rank_stock(extreme, "INTRADAY")

    assert extreme_result.score == normal_result.score


def test_future_components_affect_long_term_when_available():
    stock = make_stock()

    strong_future = RankingInput(
        **{
            **vars(stock),
            "future_readiness": Decimal("100"),
            "ai_participation": Decimal("100"),
            "innovation_execution": Decimal("100"),
            "technology_diversification": Decimal("100"),
            "sector_fit": Decimal("100"),
        }
    )

    weak_future = RankingInput(
        **{
            **vars(stock),
            "future_readiness": Decimal("0"),
            "ai_participation": Decimal("0"),
            "innovation_execution": Decimal("0"),
            "technology_diversification": Decimal("0"),
            "sector_fit": Decimal("0"),
        }
    )

    strong = rank_stock(strong_future, "LONG_TERM")
    weak = rank_stock(weak_future, "LONG_TERM")

    assert strong.score > weak.score


def test_ranking_is_deterministic():
    stock = make_stock()

    first = rank_stock(stock, "LONG_TERM")
    second = rank_stock(stock, "LONG_TERM")

    assert first == second


def test_rank_stocks_does_not_mutate_input_order():
    stocks = [
        make_stock("B", "70"),
        make_stock("A", "90"),
        make_stock("C", "80"),
    ]

    original = [stock.symbol for stock in stocks]

    rankings = rank_stocks(
        stocks,
        "LONG_TERM",
    )

    assert [stock.symbol for stock in stocks] == original
    assert [item.symbol for item in rankings] == [
        "A",
        "C",
        "B",
    ]
