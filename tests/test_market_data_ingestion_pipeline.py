from datetime import date, datetime, timezone
from pathlib import Path

from src.data.ingestion.daily_prices import DailyPriceIngestion
from src.data.ingestion.provenance import (
    DataProvenance,
    ReviewStatus,
    SourceType,
)
from src.data.ingestion.review import ReviewDecision
from src.data.providers.csv_provider import CSVMarketDataProvider
from src.research.raw_archive import RawArchive


def make_csv(tmp_path: Path) -> Path:
    csv_file = tmp_path / "prices.csv"

    csv_file.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "TEST,2026-08-03,100,110,95,105,100000\n"
        "TEST,2026-08-04,105,115,100,112,120000\n"
        "TEST,2026-08-05,112,118,108,115,130000\n",
        encoding="utf-8",
    )

    return csv_file


def make_provenance() -> DataProvenance:
    return DataProvenance(
        provider_name="CSV Development Dataset",
        source_type=SourceType.EXCHANGE,
        retrieved_at=datetime(
            2026,
            8,
            6,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        period_start=date(2026, 8, 3),
        period_end=date(2026, 8, 5),
        reliability_tier=1,
        review_status=ReviewStatus.ACCEPT,
    )


def test_market_data_pipeline_preserves_research_boundary(
    tmp_path,
):
    provider = CSVMarketDataProvider(
        make_csv(tmp_path)
    )

    archive = RawArchive(
        tmp_path / "archive"
    )

    ingestion = DailyPriceIngestion(
        provider=provider,
        archive=archive,
    )

    result = ingestion.ingest(
        symbol=" test ",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 5),
        retrieved_at=datetime(
            2026,
            8,
            6,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        dataset_id="test_prices",
        dataset_version="v1",
    )

    assert result.is_clean
    assert len(result.accepted) == 3
    assert result.rejected == []

    provenance = make_provenance()

    assert provenance.review_status == ReviewStatus.ACCEPT
    assert provenance.is_high_quality

    archived = archive.load(
        "csvmarketdataprovider",
        "TEST_2026-08-03",
    )

    assert archived.payload["symbol"] == "TEST"
    assert archived.payload["close"] == "105"
    assert archived.dataset_id == "test_prices"
    assert archived.dataset_version == "v1"


def test_market_data_pipeline_does_not_archive_rejected_records(
    tmp_path,
):
    csv_file = tmp_path / "prices.csv"

    csv_file.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "TEST,2026-08-03,100,90,95,105,100000\n",
        encoding="utf-8",
    )

    provider = CSVMarketDataProvider(csv_file)

    archive = RawArchive(
        tmp_path / "archive"
    )

    ingestion = DailyPriceIngestion(
        provider=provider,
        archive=archive,
    )

    result = ingestion.ingest(
        symbol="TEST",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 3),
    )

    assert result.rejected
    assert not result.accepted

    try:
        archive.load(
            "csvmarketdataprovider",
            "TEST_2026-08-03",
        )
    except FileNotFoundError:
        pass
    else:
        raise AssertionError(
            "Rejected market data must never enter raw archive"
        )


def test_accepted_pipeline_output_is_chronological(
    tmp_path,
):
    provider = CSVMarketDataProvider(
        make_csv(tmp_path)
    )

    archive = RawArchive(
        tmp_path / "archive"
    )

    ingestion = DailyPriceIngestion(
        provider=provider,
        archive=archive,
    )

    result = ingestion.ingest(
        symbol="TEST",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 5),
    )

    assert [
        bar.trading_date
        for bar in result.accepted
    ] == [
        date(2026, 8, 3),
        date(2026, 8, 4),
        date(2026, 8, 5),
    ]