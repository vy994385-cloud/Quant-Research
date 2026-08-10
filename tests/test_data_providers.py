from datetime import date

import pytest

from src.data.providers.csv_provider import (
    CSVMarketDataProvider,
)


def test_csv_provider_reads_requested_date_range(tmp_path):

    csv_file = tmp_path / "prices.csv"

    csv_file.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "TEST,2026-08-03,100,110,95,105,100000\n"
        "TEST,2026-08-04,105,115,100,112,120000\n"
        "TEST,2026-08-05,112,118,108,115,130000\n"
        "OTHER,2026-08-04,50,55,48,53,90000\n",
        encoding="utf-8",
    )

    provider = CSVMarketDataProvider(csv_file)

    bars = provider.get_daily_prices(
        symbol="TEST",
        start_date=date(2026, 8, 4),
        end_date=date(2026, 8, 5),
    )

    assert len(bars) == 2
    assert bars[0].trading_date == date(2026, 8, 4)
    assert bars[1].trading_date == date(2026, 8, 5)
    assert bars[0].close == 112


def test_csv_provider_normalizes_symbol(tmp_path):

    csv_file = tmp_path / "prices.csv"

    csv_file.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "RELIANCE,2026-08-03,100,110,95,105,100000\n",
        encoding="utf-8",
    )

    provider = CSVMarketDataProvider(csv_file)

    bars = provider.get_daily_prices(
        symbol=" reliance ",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 3),
    )

    assert len(bars) == 1
    assert bars[0].symbol == "RELIANCE"


def test_csv_provider_rejects_invalid_date_range(tmp_path):

    csv_file = tmp_path / "prices.csv"

    csv_file.write_text(
        "symbol,date,open,high,low,close,volume\n",
        encoding="utf-8",
    )

    provider = CSVMarketDataProvider(csv_file)

    with pytest.raises(ValueError):

        provider.get_daily_prices(
            symbol="TEST",
            start_date=date(2026, 8, 10),
            end_date=date(2026, 8, 1),
        )


def test_csv_provider_rejects_empty_symbol(tmp_path):

    csv_file = tmp_path / "prices.csv"

    csv_file.write_text(
        "symbol,date,open,high,low,close,volume\n",
        encoding="utf-8",
    )

    provider = CSVMarketDataProvider(csv_file)

    with pytest.raises(ValueError):

        provider.get_daily_prices(
            symbol="   ",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 5),
        )


def test_csv_provider_rejects_missing_columns(tmp_path):

    csv_file = tmp_path / "prices.csv"

    csv_file.write_text(
        "symbol,date,open,high,low,close\n"
        "TEST,2026-08-03,100,110,95,105\n",
        encoding="utf-8",
    )

    provider = CSVMarketDataProvider(csv_file)

    with pytest.raises(ValueError):

        provider.get_daily_prices(
            symbol="TEST",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 5),
        )


def test_csv_provider_returns_chronological_data(tmp_path):

    csv_file = tmp_path / "prices.csv"

    csv_file.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "TEST,2026-08-05,112,118,108,115,130000\n"
        "TEST,2026-08-03,100,110,95,105,100000\n"
        "TEST,2026-08-04,105,115,100,112,120000\n",
        encoding="utf-8",
    )

    provider = CSVMarketDataProvider(csv_file)

    bars = provider.get_daily_prices(
        symbol="TEST",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 10),
    )

    assert [
        bar.trading_date
        for bar in bars
    ] == [
        date(2026, 8, 3),
        date(2026, 8, 4),
        date(2026, 8, 5),
    ]