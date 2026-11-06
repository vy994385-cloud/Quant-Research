from __future__ import annotations

from datetime import date
from pathlib import Path

from src.data.models import PriceBar
from src.data.providers.yahoo_provider import (
    SecurityMetadata,
    YahooFinanceMarketDataProvider,
)

from .models import UniverseSecurity
from .registry import UniverseRegistry


class UniverseProvider:
    """
    V2 security-universe facade.

    Membership comes from QRQuant's configured universe.
    Identity metadata comes from the same Yahoo Chart response
    used for market data.

    No Yahoo quoteSummary/profile dependency is used here.
    """

    ROOT = Path(__file__).resolve().parents[4]

    UNIVERSE_FILE = (
        ROOT
        / "data"
        / "raw"
        / "universe"
        / "nse_equities.csv"
    )

    def __init__(self):
        self.registry = UniverseRegistry(
            self.UNIVERSE_FILE
        )
        self.market_provider = YahooFinanceMarketDataProvider()

    def securities(self) -> tuple[UniverseSecurity, ...]:
        return self.registry.load()

    def get(self, symbol: str) -> UniverseSecurity:
        normalized = symbol.strip().upper()

        for security in self.securities():
            if security.symbol == normalized:
                return security

        raise KeyError(
            f"Security is not in the configured QRQuant universe: "
            f"{normalized}"
        )

    def count(self) -> int:
        return len(self.securities())

    def get_market_data(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> tuple[list[PriceBar], UniverseSecurity]:
        """
        Return price observations and the canonical V2 security identity.

        Yahoo Chart is requested once. Its identity metadata is merged
        into the configured universe record.
        """

        security = self.get(symbol)

        bars, metadata = (
            self.market_provider
            .get_daily_prices_with_metadata(
                symbol=security.symbol,
                start_date=start_date,
                end_date=end_date,
            )
        )

        enriched = security.model_copy(
            update={
                "company_name": metadata.company_name,
                "exchange": metadata.exchange,
                "currency": metadata.currency,
                "instrument_type": metadata.instrument_type,
                "metadata_source": metadata.metadata_source,
            }
        )

        return bars, enriched
