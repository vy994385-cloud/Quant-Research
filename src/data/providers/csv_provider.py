import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.data.models import PriceBar

from .base import MarketDataProvider


class CSVMarketDataProvider(MarketDataProvider):
    """
    CSV market-data provider used for development, testing,
    and authorized/exported datasets.

    Expected columns:

    symbol,date,open,high,low,close,volume
    """

    REQUIRED_COLUMNS = {
        "symbol",
        "date",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()

        if not normalized:
            raise ValueError("symbol must not be empty.")

        return normalized

    @staticmethod
    def _validate_date_range(
        start_date: date,
        end_date: date,
    ) -> None:
        if start_date > end_date:
            raise ValueError(
                "start_date must not be after end_date."
            )

    def get_daily_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[PriceBar]:

        self._validate_date_range(
            start_date,
            end_date,
        )

        normalized_symbol = self._normalize_symbol(symbol)

        if not self.file_path.exists():
            raise FileNotFoundError(
                f"Market data file not found: {self.file_path}"
            )

        results: list[PriceBar] = []

        with self.file_path.open(
            "r",
            newline="",
            encoding="utf-8",
        ) as file:

            reader = csv.DictReader(file)

            if not self.REQUIRED_COLUMNS.issubset(
                reader.fieldnames or set()
            ):
                raise ValueError(
                    "CSV is missing required columns: "
                    f"{sorted(self.REQUIRED_COLUMNS)}"
                )

            for row in reader:

                row_symbol = (
                    row["symbol"].strip().upper()
                )

                if row_symbol != normalized_symbol:
                    continue

                trading_date = date.fromisoformat(
                    row["date"]
                )

                if trading_date < start_date:
                    continue

                if trading_date > end_date:
                    continue

                bar = PriceBar(
                    symbol=row_symbol,
                    trading_date=trading_date,
                    open=Decimal(row["open"]),
                    high=Decimal(row["high"]),
                    low=Decimal(row["low"]),
                    close=Decimal(row["close"]),
                    volume=int(row["volume"]),
                )

                results.append(bar)

        return sorted(
            results,
            key=lambda bar: bar.trading_date,
        )