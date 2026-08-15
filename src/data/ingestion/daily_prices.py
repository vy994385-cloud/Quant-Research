from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from src.data.ingestion.validator import (
    IngestionResult,
    validate_price_bars,
)
from src.data.providers.base import MarketDataProvider
from src.research.raw_archive import RawArchive
from src.research.raw_record import RawRecord


class DailyPriceIngestion:
    """
    Orchestrates daily market-price ingestion.

    Flow:

        provider
            ↓
        normalized PriceBar records
            ↓
        structural + anomaly validation
            ↓
        immutable raw archive

    The provider remains responsible for obtaining normalized
    PriceBar objects. This class is responsible for controlling
    the ingestion boundary and preserving the source observations.
    """

    def __init__(
        self,
        provider: MarketDataProvider,
        archive: RawArchive,
    ) -> None:
        self.provider = provider
        self.archive = archive

    def ingest(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        *,
        retrieved_at: datetime | None = None,
        dataset_id: str | None = None,
        dataset_version: str | None = None,
        request_metadata: dict[str, Any] | None = None,
        price_jump_warning_pct=None,
        price_jump_critical_pct=None,
        volume_spike_multiple=None,
    ) -> IngestionResult:
        """
        Fetch, validate and archive daily price observations.

        Only structurally accepted PriceBar records are archived.

        The raw archive payload preserves the normalized observations
        exactly as supplied by the provider.
        """

        if retrieved_at is None:
            retrieved_at = datetime.now(timezone.utc)

        if retrieved_at.tzinfo is None:
            raise ValueError(
                "retrieved_at must be timezone-aware"
            )

        bars = self.provider.get_daily_prices(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        result = validate_price_bars(
            bars=bars,
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            price_jump_warning_pct=price_jump_warning_pct,
            price_jump_critical_pct=price_jump_critical_pct,
            volume_spike_multiple=volume_spike_multiple,
        )

        self._archive_accepted_bars(
            bars=result.accepted,
            retrieved_at=retrieved_at,
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            request_metadata=request_metadata,
        )

        return result

    def _archive_accepted_bars(
        self,
        bars,
        *,
        retrieved_at: datetime,
        dataset_id: str | None,
        dataset_version: str | None,
        request_metadata: dict[str, Any] | None,
    ) -> None:
        for bar in bars:
            record = RawRecord(
                source_id=self._source_id,
                record_id=self._record_id(bar),
                retrieved_at=retrieved_at,
                available_at=retrieved_at,
                payload=bar.model_dump(mode="json"),
                dataset_id=dataset_id,
                dataset_version=dataset_version,
                request_metadata=request_metadata,
            )

            self.archive.save(record)

    @property
    def _source_id(self) -> str:
        source_name = getattr(
            self.provider,
            "source_name",
            None,
        )

        if source_name:
            return str(source_name).strip().lower()

        return self.provider.__class__.__name__.strip().lower()

    @staticmethod
    def _record_id(bar) -> str:
        return (
            f"{bar.symbol.strip().upper()}"
            f"_{bar.trading_date.isoformat()}"
        )
