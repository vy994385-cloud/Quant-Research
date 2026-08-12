from datetime import date

import pytest

from src.data.providers.csv_provider import CSVMarketDataProvider
from src.features.market_adapter import (
    build_market_feature_snapshot_from_provider,
)


def test_build_market_snapshot_from_csv_provider(tmp_path):
    path = tmp_path / "prices.csv"

    rows = [
        "symbol,date,open,high,low,close,volume",
    ]

    for index in range(25):
        day = date(2026, 7, 1)
        current = day.fromordinal(day.toordinal() + index)

        tcs_price = 100 + index
        nifty_price = 1000 + index

        rows.append(
            f"TCS,{current.isoformat()},"
            f"{tcs_price},{tcs_price + 1},"
            f"{tcs_price - 1},{tcs_price},1000"
        )

        rows.append(
            f"NIFTY,{current.isoformat()},"
            f"{nifty_price},{nifty_price + 1},"
            f"{nifty_price - 1},{nifty_price},10000"
        )

    path.write_text("\n".join(rows))

    provider = CSVMarketDataProvider(path)

    snapshot = build_market_feature_snapshot_from_provider(
        provider=provider,
        symbol="TCS",
        benchmark_symbol="NIFTY",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 25),
    )

    assert snapshot.symbol == "TCS"
    assert snapshot.benchmark_symbol == "NIFTY"
    assert snapshot.trading_date == date(2026, 7, 25)

    assert snapshot.technical.latest_close is not None
    assert snapshot.technical.sma_20 is not None
    assert snapshot.structure.regime in {
        "BULLISH",
        "BEARISH",
        "MIXED",
        "INSUFFICIENT_DATA",
    }

    assert snapshot.relative_strength.symbol == "TCS"
    assert snapshot.relative_strength.benchmark_symbol == "NIFTY"


def test_missing_stock_data_is_rejected(tmp_path):
    path = tmp_path / "prices.csv"

    path.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "NIFTY,2026-07-01,100,101,99,100,1000\n"
    )

    provider = CSVMarketDataProvider(path)

    with pytest.raises(ValueError, match="No market data"):
        build_market_feature_snapshot_from_provider(
            provider=provider,
            symbol="TCS",
            benchmark_symbol="NIFTY",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 1),
        )


def test_missing_benchmark_data_is_rejected(tmp_path):
    path = tmp_path / "prices.csv"

    path.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "TCS,2026-07-01,100,101,99,100,1000\n"
    )

    provider = CSVMarketDataProvider(path)

    with pytest.raises(ValueError, match="No market data"):
        build_market_feature_snapshot_from_provider(
            provider=provider,
            symbol="TCS",
            benchmark_symbol="NIFTY",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 1),
        )
