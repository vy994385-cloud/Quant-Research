from datetime import date

import pytest

from src.data.providers.nse_provider import NSEMarketDataProvider


def test_nse_provider_requires_configuration():

    provider = NSEMarketDataProvider()

    assert provider.source_name == "NSE"
    assert not provider.is_configured

    with pytest.raises(RuntimeError):
        provider.get_daily_prices(
            symbol="RELIANCE",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )


def test_nse_provider_detects_missing_file(tmp_path):

    missing_file = tmp_path / "missing.csv"

    provider = NSEMarketDataProvider(
        missing_file
    )

    assert not provider.is_configured

    with pytest.raises(FileNotFoundError):
        provider.get_daily_prices(
            symbol="RELIANCE",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )


def test_nse_provider_reads_authorized_csv(tmp_path):

    csv_file = tmp_path / "nse_prices.csv"

    csv_file.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "RELIANCE,2026-08-03,100,110,95,105,100000\n"
        "RELIANCE,2026-08-04,105,115,100,112,120000\n",
        encoding="utf-8",
    )

    provider = NSEMarketDataProvider(csv_file)

    assert provider.is_configured

    bars = provider.get_daily_prices(
        symbol="RELIANCE",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 4),
    )

    assert len(bars) == 2
    assert bars[0].symbol == "RELIANCE"
    assert bars[1].close == 112
