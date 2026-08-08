import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from .base import MarketDataProvider
from src.data.models import PriceBar


class CSVMarketDataProvider(MarketDataProvider):
    """
    Simple CSV provider used for development and testing.

    Expected columns:

    symbol,date,open,high,low,close,volume
    """

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def get_daily_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[PriceBar]:

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

            required_columns = {
                "symbol",
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
            }

            if not required_columns.issubset(reader.fieldnames or set()):
                raise ValueError(
                    "CSV is missing required columns: "
                    f"{sorted(required_columns)}"
                )

            for row in reader:
                if row["symbol"] != symbol:
                    continue

                trading_date = date.fromisoformat(row["date"])

                if trading_date < start_date:
                    continue

                if trading_date > end_date:
                    continue

                bar = PriceBar(
                    symbol=row["symbol"],
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