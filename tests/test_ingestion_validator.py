from datetime import date
from decimal import Decimal

from src.data.ingestion.validator import (
    ValidationStatus,
    validate_price_bars,
)
from src.data.models import PriceBar


def make_bar(
    trading_date,
    symbol="TEST",
    open_price="100",
    high="110",
    low="95",
    close="105",
    volume=100000,
):
    return PriceBar(
        symbol=symbol,
        trading_date=trading_date,
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=volume,
    )


def test_valid_bars_are_accepted():

    bars = [
        make_bar(date(2026, 8, 3)),
        make_bar(date(2026, 8, 4)),
    ]

    result = validate_price_bars(
        bars,
        symbol="TEST",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 5),
    )

    assert result.status == ValidationStatus.ACCEPT
    assert len(result.accepted) == 2
    assert result.rejected == []


def test_out_of_range_bar_is_rejected():

    bars = [
        make_bar(date(2026, 7, 31)),
        make_bar(date(2026, 8, 3)),
    ]

    result = validate_price_bars(
        bars,
        symbol="TEST",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 5),
    )

    assert len(result.accepted) == 1
    assert len(result.rejected) == 1
    assert any(
        issue.code == "DATE_OUT_OF_RANGE"
        for issue in result.issues
    )


def test_wrong_symbol_is_rejected():

    bars = [
        make_bar(
            date(2026, 8, 3),
            symbol="OTHER",
        ),
    ]

    result = validate_price_bars(
        bars,
        symbol="TEST",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 5),
    )

    assert result.accepted == []
    assert len(result.rejected) == 1
    assert any(
        issue.code == "SYMBOL_MISMATCH"
        for issue in result.issues
    )


def test_invalid_ohlc_is_rejected():

    bars = [
        make_bar(
            date(2026, 8, 3),
            high="99",
        ),
    ]

    result = validate_price_bars(
        bars,
        symbol="TEST",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 5),
    )

    assert result.accepted == []
    assert len(result.rejected) == 1
    assert any(
        issue.code == "INVALID_OHLC"
        for issue in result.issues
    )


def test_invalid_date_range_is_rejected():

    bars = [
        make_bar(date(2026, 8, 3)),
    ]

    result = validate_price_bars(
        bars,
        symbol="TEST",
        start_date=date(2026, 8, 10),
        end_date=date(2026, 8, 1),
    )

    assert result.status == ValidationStatus.REJECT
    assert result.accepted == []
    assert any(
        issue.code == "INVALID_DATE_RANGE"
        for issue in result.issues
    )


def test_duplicate_trading_date_is_rejected():

    bars = [
        make_bar(
            date(2026, 8, 3),
            close="105",
        ),
        make_bar(
            date(2026, 8, 3),
            close="106",
        ),
    ]

    result = validate_price_bars(
        bars,
        symbol="TEST",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 5),
    )

    assert result.accepted == []
    assert len(result.rejected) == 2
    assert any(
        issue.code == "DUPLICATE_DATE"
        for issue in result.issues
    )


def test_accepted_bars_are_sorted():

    bars = [
        make_bar(date(2026, 8, 5)),
        make_bar(date(2026, 8, 3)),
        make_bar(date(2026, 8, 4)),
    ]

    result = validate_price_bars(
        bars,
        symbol="TEST",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 10),
    )

    assert [
        bar.trading_date
        for bar in result.accepted
    ] == [
        date(2026, 8, 3),
        date(2026, 8, 4),
        date(2026, 8, 5),
    ]
