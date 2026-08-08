from datetime import date
from pathlib import Path

from src.data.models import PriceBar

from .csv_provider import CSVMarketDataProvider


class NSEMarketDataProvider:
    """
    Indian-market provider boundary.

    The provider intentionally does not scrape NSE.

    For now it can consume an authorized/exported NSE-compatible
    CSV dataset through the existing CSV adapter.

    This keeps the research engine independent from the eventual
    licensed/approved production data source.
    """

    def __init__(
        self,
        data_file: str | Path | None = None,
    ):
        self.source_name = "NSE"
        self.data_file = (
            Path(data_file)
            if data_file is not None
            else None
        )

    @property
    def is_configured(self) -> bool:
        return (
            self.data_file is not None
            and self.data_file.exists()
        )

    def get_daily_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[PriceBar]:

        if self.data_file is None:
            raise RuntimeError(
                "NSE provider is not configured. "
                "Provide an authorized market-data file."
            )

        if not self.data_file.exists():
            raise FileNotFoundError(
                f"NSE market-data file does not exist: "
                f"{self.data_file}"
            )

        provider = CSVMarketDataProvider(self.data_file)

        return provider.get_daily_prices(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
