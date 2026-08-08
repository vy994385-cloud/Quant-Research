from datetime import date

from src.data.providers.csv_provider import CSVMarketDataProvider


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