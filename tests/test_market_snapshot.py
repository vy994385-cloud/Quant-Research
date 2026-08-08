from datetime import date
from decimal import Decimal

import pytest

from src.features.market_snapshot import (
    MarketFeatureSnapshot,
    build_market_feature_snapshot,
)
from src.features.market_structure import MarketStructure
from src.features.relative_strength import RelativeStrength
from src.features.technical import TechnicalFeatures


OBSERVATION_DATE = date(2026, 8, 7)


def make_technical(
    symbol: str = "TEST",
    trading_date: date = OBSERVATION_DATE,
) -> TechnicalFeatures:
    return TechnicalFeatures(
        symbol=symbol,
        trading_date=trading_date,
        return_1d=Decimal("1"),
        return_5d=Decimal("5"),
        return_20d=Decimal("12"),
        sma_5=Decimal("105"),
        sma_20=Decimal("100"),
        momentum=Decimal("12"),
        volatility_20d=Decimal("2"),
        average_volume_20d=Decimal("1000"),
        volume_ratio=Decimal("1.2"),
        drawdown_20d=Decimal("0"),
    )


def make_structure(
    symbol: str = "TEST",
    trading_date: date = OBSERVATION_DATE,
) -> MarketStructure:
    return MarketStructure(
        symbol=symbol,
        trading_date=trading_date,
        price_vs_sma_5_pct=Decimal("2"),
        price_vs_sma_20_pct=Decimal("5"),
        sma_5_vs_sma_20_pct=Decimal("3"),
        momentum_acceleration=Decimal("1"),
        trend_persistence=Decimal("80"),
        volume_confirmation=Decimal("1.2"),
        recovery_from_drawdown_pct=Decimal("100"),
        regime="BULLISH",
    )


def make_relative_strength(
    symbol: str = "TEST",
    benchmark_symbol: str = "NIFTY",
    trading_date: date = OBSERVATION_DATE,
) -> RelativeStrength:
    return RelativeStrength(
        symbol=symbol,
        benchmark_symbol=benchmark_symbol,
        trading_date=trading_date,
        stock_return_1d=Decimal("1"),
        benchmark_return_1d=Decimal("0.5"),
        relative_return_1d=Decimal("0.5"),
        stock_return_5d=Decimal("5"),
        benchmark_return_5d=Decimal("2"),
        relative_return_5d=Decimal("3"),
        stock_return_20d=Decimal("12"),
        benchmark_return_20d=Decimal("7"),
        relative_return_20d=Decimal("5"),
        relative_momentum=Decimal("4"),
    )


def test_builds_snapshot():
    technical = make_technical()
    structure = make_structure()
    relative = make_relative_strength()

    snapshot = build_market_feature_snapshot(
        technical,
        structure,
        relative,
    )

    assert isinstance(
        snapshot,
        MarketFeatureSnapshot,
    )

    assert snapshot.symbol == "TEST"
    assert snapshot.trading_date == OBSERVATION_DATE
    assert snapshot.benchmark_symbol == "NIFTY"


def test_preserves_component_objects():
    technical = make_technical()
    structure = make_structure()
    relative = make_relative_strength()

    snapshot = build_market_feature_snapshot(
        technical,
        structure,
        relative,
    )

    assert snapshot.technical is technical
    assert snapshot.structure is structure
    assert snapshot.relative_strength is relative


def test_mismatched_symbol_is_rejected():
    with pytest.raises(ValueError):
        build_market_feature_snapshot(
            make_technical(symbol="TEST"),
            make_structure(symbol="OTHER"),
            make_relative_strength(symbol="TEST"),
        )


def test_mismatched_relative_symbol_is_rejected():
    with pytest.raises(ValueError):
        build_market_feature_snapshot(
            make_technical(symbol="TEST"),
            make_structure(symbol="TEST"),
            make_relative_strength(symbol="OTHER"),
        )


def test_mismatched_date_is_rejected():
    with pytest.raises(ValueError):
        build_market_feature_snapshot(
            make_technical(),
            make_structure(
                trading_date=date(2026, 8, 6)
            ),
            make_relative_strength(),
        )


def test_mismatched_relative_date_is_rejected():
    with pytest.raises(ValueError):
        build_market_feature_snapshot(
            make_technical(),
            make_structure(),
            make_relative_strength(
                trading_date=date(2026, 8, 6)
            ),
        )


def test_empty_benchmark_symbol_is_rejected():
    with pytest.raises(ValueError):
        build_market_feature_snapshot(
            make_technical(),
            make_structure(),
            make_relative_strength(
                benchmark_symbol=""
            ),
        )


def test_snapshot_is_immutable():
    snapshot = build_market_feature_snapshot(
        make_technical(),
        make_structure(),
        make_relative_strength(),
    )

    with pytest.raises(AttributeError):
        snapshot.symbol = "OTHER"
