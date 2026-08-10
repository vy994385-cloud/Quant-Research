from abc import ABC, abstractmethod
from datetime import date

from src.data.models import PriceBar


class MarketDataProvider(ABC):
    """
    Provider-independent interface for market price data.

    The research engine depends on this interface rather than
    on a particular exchange, broker, or vendor.
    """

    @abstractmethod
    def get_daily_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[PriceBar]:
        """
        Return daily OHLCV data for a symbol.

        Implementations must:

        - validate the requested date range
        - normalize the requested symbol
        - return only data within the requested range
        - preserve source trading dates
        - never silently invent missing values
        - return PriceBar objects
        - return records in chronological order
        """
        raise NotImplementedError