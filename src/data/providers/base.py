from abc import ABC, abstractmethod
from datetime import date

from src.data.models import PriceBar


class MarketDataProvider(ABC):
    """
    Provider-independent interface for market price data.

    The quant engine should depend on this interface,
    not on a particular exchange, broker, or vendor.
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
        - return only data within the requested range
        - preserve the source timestamps/dates
        - never silently invent missing values
        - return validated PriceBar objects
        """
        raise NotImplementedError