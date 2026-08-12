from datetime import date

from src.data.providers.csv_provider import CSVMarketDataProvider
from src.research.market_engine import (
    MarketResearchResult,
    run_market_research,
)


def _create_market_file(path):
    rows = [
        "symbol,date,open,high,low,close,volume",
    ]

    for index in range(30):
        day = date(2026, 7, 1).fromordinal(
            date(2026, 7, 1).toordinal() + index
        )

        tcs = 100 + index
        infy = 200 + index
        nifty = 1000 + index

        rows.append(
            f"TCS,{day.isoformat()},"
            f"{tcs},{tcs + 1},{tcs - 1},{tcs},1000"
        )

        rows.append(
            f"INFY,{day.isoformat()},"
            f"{infy},{infy + 1},{infy - 1},{infy},1200"
        )

        rows.append(
            f"NIFTY,{day.isoformat()},"
            f"{nifty},{nifty + 1},{nifty - 1},{nifty},10000"
        )

    path.write_text("\n".join(rows))


def test_market_engine_runs_real_provider_pipeline(tmp_path):
    path = tmp_path / "prices.csv"
    _create_market_file(path)

    universe = tmp_path / "universe.csv"
    universe.write_text(
        "symbol\n"
        "TCS\n"
        "INFY\n"
    )

    provider = CSVMarketDataProvider(path)

    result = run_market_research(
        provider=provider,
        universe_file=str(universe),
        benchmark_symbol="NIFTY",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 30),
    )

    assert isinstance(result, MarketResearchResult)
    assert result.as_of == date(2026, 7, 30)

    assert result.symbols == ("INFY", "TCS")
    assert result.successful_count == 2

    for report in result.results:
        assert report.is_research_ready
        assert report.market_snapshot.symbol == report.symbol
        assert report.market_snapshot.benchmark_symbol == "NIFTY"

        assert report.intraday.symbol == report.symbol
        assert report.swing.symbol == report.symbol
        assert report.long_term.symbol == report.symbol


def test_market_engine_skips_missing_security(tmp_path):
    path = tmp_path / "prices.csv"
    _create_market_file(path)

    universe = tmp_path / "universe.csv"
    universe.write_text(
        "symbol\n"
        "TCS\n"
        "MISSING\n"
    )

    provider = CSVMarketDataProvider(path)

    result = run_market_research(
        provider=provider,
        universe_file=str(universe),
        benchmark_symbol="NIFTY",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 30),
    )

    assert result.symbols == ("TCS",)
    assert result.successful_count == 1


def test_market_engine_rejects_invalid_date_range(tmp_path):
    path = tmp_path / "prices.csv"
    _create_market_file(path)

    universe = tmp_path / "universe.csv"
    universe.write_text("symbol\nTCS\n")

    provider = CSVMarketDataProvider(path)

    try:
        run_market_research(
            provider=provider,
            universe_file=str(universe),
            benchmark_symbol="NIFTY",
            start_date=date(2026, 7, 30),
            end_date=date(2026, 7, 1),
        )
    except ValueError as exc:
        assert "start_date" in str(exc)
    else:
        raise AssertionError(
            "Expected invalid date range to raise ValueError"
        )
