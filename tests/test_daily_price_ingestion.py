from datetime import date, datetime, timezone
from src.data.ingestion.daily_prices import DailyPriceIngestion
from src.data.providers.csv_provider import CSVMarketDataProvider
from src.research.raw_archive import RawArchive


def make_csv(tmp_path):
    csv_file = tmp_path / "prices.csv"

    csv_file.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "TEST,2026-08-03,100,110,95,105,100000\n"
        "TEST,2026-08-04,105,115,100,112,120000\n"
        "TEST,2026-08-05,112,118,108,115,130000\n",
        encoding="utf-8",
    )

    return csv_file


def test_daily_ingestion_fetches_validates_and_archives(
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

    retrieved_at = datetime(
        2026,
        8,
        6,
        10,
        0,
        tzinfo=timezone.utc,
    )

    result = ingestion.ingest(
        symbol="TEST",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 5),
        retrieved_at=retrieved_at,
        dataset_id="test_prices",
        dataset_version="v1",
    )

    assert result.is_clean
    assert len(result.accepted) == 3
    assert result.rejected == []

    first = archive.load(
        "csvmarketdataprovider",
        "TEST_2026-08-03",
    )

    assert first.source_id == "csvmarketdataprovider"
    assert first.record_id == "TEST_2026-08-03"
    assert first.retrieved_at == retrieved_at
    assert first.dataset_id == "test_prices"
    assert first.dataset_version == "v1"
    assert first.payload["symbol"] == "TEST"
    assert first.payload["close"] == "105"


def test_daily_ingestion_archives_only_accepted_records(
    tmp_path,
):
    csv_file = tmp_path / "prices.csv"

    csv_file.write_text(
        "symbol,date,open,high,low,close,volume\n"
        "TEST,2026-08-03,100,110,95,105,100000\n"
        "OTHER,2026-08-04,50,55,48,53,90000\n",
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
        end_date=date(2026, 8, 4),
    )

    assert len(result.accepted) == 1
    assert len(result.rejected) == 0

    assert archive.load(
        "csvmarketdataprovider",
        "TEST_2026-08-03",
    ).payload["symbol"] == "TEST"

    import pytest

    with pytest.raises(FileNotFoundError):
        archive.load(
            "csvmarketdataprovider",
            "OTHER_2026-08-04",
        )


def test_retrieved_at_must_be_timezone_aware(
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

    import pytest

    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        ingestion.ingest(
            symbol="TEST",
            start_date=date(2026, 8, 3),
            end_date=date(2026, 8, 3),
            retrieved_at=datetime(
                2026,
                8,
                6,
                10,
            ),
        )


def test_existing_identical_records_are_idempotent(
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

    retrieved_at = datetime(
        2026,
        8,
        6,
        10,
        tzinfo=timezone.utc,
    )

    first = ingestion.ingest(
        symbol="TEST",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 3),
        retrieved_at=retrieved_at,
    )

    second = ingestion.ingest(
        symbol="TEST",
        start_date=date(2026, 8, 3),
        end_date=date(2026, 8, 3),
        retrieved_at=retrieved_at,
    )

    assert first.accepted == second.accepted

    loaded = archive.load(
        "csvmarketdataprovider",
        "TEST_2026-08-03",
    )

    assert loaded.checksum
