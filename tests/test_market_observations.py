from datetime import date, datetime, timezone

import pytest

from src.data.models import PriceBar
from src.research.market_observations import (
    MarketObservation,
    build_market_observations,
)


def make_bars(count=21):
    return [
        PriceBar(
            symbol="TEST",
            trading_date=date(2026, 7, 1 + index),
            open=100 + index,
            high=101 + index,
            low=99 + index,
            close=100 + index,
            volume=1000 + index * 100,
        )
        for index in range(count)
    ]


def test_empty_bars_produce_empty_observations():

    result = build_market_observations(
        symbol="TEST",
        bars=[],
        available_at=datetime(
            2026,
            8,
            1,
            tzinfo=timezone.utc,
        ),
    )

    assert result == []


def test_symbol_is_normalized():

    result = build_market_observations(
        symbol=" test ",
        bars=make_bars(1),
        available_at=datetime(
            2026,
            8,
            1,
            tzinfo=timezone.utc,
        ),
    )

    assert result[0].symbol == "TEST"


def test_first_observation_has_no_future_derived_features():

    result = build_market_observations(
        symbol="TEST",
        bars=make_bars(1),
        available_at=datetime(
            2026,
            8,
            1,
            tzinfo=timezone.utc,
        ),
    )

    observation = result[0]

    assert observation.return_1d is None
    assert observation.return_5d is None
    assert observation.return_20d is None
    assert observation.volatility_20d is None
    assert observation.volume_ratio_20d is None
    assert observation.drawdown_20d is None


def test_one_day_return_uses_previous_observation():

    result = build_market_observations(
        symbol="TEST",
        bars=make_bars(2),
        available_at=datetime(
            2026,
            8,
            1,
            tzinfo=timezone.utc,
        ),
    )

    assert result[1].return_1d == pytest.approx(
        101 / 100 - 1
    )


def test_five_day_return_requires_five_previous_days():

    result = build_market_observations(
        symbol="TEST",
        bars=make_bars(6),
        available_at=datetime(
            2026,
            8,
            1,
            tzinfo=timezone.utc,
        ),
    )

    assert result[4].return_5d is None

    assert result[5].return_5d == pytest.approx(
        105 / 100 - 1
    )


def test_twenty_day_features_require_twenty_previous_days():

    result = build_market_observations(
        symbol="TEST",
        bars=make_bars(21),
        available_at=datetime(
            2026,
            8,
            1,
            tzinfo=timezone.utc,
        ),
    )

    assert result[19].return_20d is None
    assert result[19].volatility_20d is None
    assert result[20].return_20d is not None
    assert result[20].volatility_20d is not None
    assert result[20].drawdown_20d is not None


def test_available_at_is_preserved():

    available_at = datetime(
        2026,
        8,
        6,
        10,
        tzinfo=timezone.utc,
    )

    result = build_market_observations(
        symbol="TEST",
        bars=make_bars(1),
        available_at=available_at,
    )

    assert result[0].available_at == available_at


def test_naive_available_at_is_rejected():

    with pytest.raises(ValueError):

        build_market_observations(
            symbol="TEST",
            bars=make_bars(1),
            available_at=datetime(2026, 8, 1),
        )


def test_observation_model_rejects_naive_timestamp():

    with pytest.raises(ValueError):

        MarketObservation(
            symbol="TEST",
            observation_date=date(2026, 8, 1),
            available_at=datetime(2026, 8, 1),
            close=100,
        )
