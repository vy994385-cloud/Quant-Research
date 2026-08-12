from __future__ import annotations

from datetime import date
from decimal import Decimal
from urllib.parse import quote

import requests

from src.data.models import PriceBar

from .base import MarketDataProvider


class UpstoxMarketDataProvider(MarketDataProvider):
    """
    Upstox V3 historical daily market-data provider.

    Converts Upstox daily candles into the project's normalized
    PriceBar model.

    Authentication is supplied explicitly so credentials are never
    stored in source code.
    """

    BASE_URL = "https://api.upstox.com/v3/historical-candle"

    def __init__(
        self,
        access_token: str,
        instrument_keys: dict[str, str],
        *,
        timeout: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        if not access_token.strip():
            raise ValueError("access_token must not be empty.")

        if not instrument_keys:
            raise ValueError(
                "instrument_keys must not be empty."
            )

        self.access_token = access_token.strip()
        self.instrument_keys = {
            symbol.strip().upper(): key.strip()
            for symbol, key in instrument_keys.items()
        }
        self.timeout = timeout
        self.session = session or requests.Session()
        self.source_name = "UPSTOX"

    @staticmethod
    def _validate_date_range(
        start_date: date,
        end_date: date,
    ) -> None:
        if start_date > end_date:
            raise ValueError(
                "start_date must not be after end_date."
            )

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()

        if not normalized:
            raise ValueError(
                "symbol must not be empty."
            )

        return normalized

    def _instrument_key(
        self,
        symbol: str,
    ) -> str:
        try:
            return self.instrument_keys[symbol]
        except KeyError as exc:
            raise KeyError(
                f"No Upstox instrument key configured "
                f"for symbol: {symbol}"
            ) from exc

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
        instrument_key = self._instrument_key(
            normalized_symbol
        )

        encoded_key = quote(
            instrument_key,
            safe="",
        )

        url = (
            f"{self.BASE_URL}/"
            f"{encoded_key}/days/1/"
            f"{end_date.isoformat()}/"
            f"{start_date.isoformat()}"
        )

        response = self.session.get(
            url,
            headers={
                "Accept": "application/json",
                "Authorization": (
                    f"Bearer {self.access_token}"
                ),
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        payload = response.json()

        if payload.get("status") != "success":
            raise ValueError(
                "Upstox returned an unsuccessful response."
            )

        candles = (
            payload.get("data", {})
            .get("candles", [])
        )

        results: list[PriceBar] = []

        for candle in candles:
            if len(candle) < 6:
                raise ValueError(
                    "Upstox candle has fewer than "
                    "6 expected fields."
                )

            timestamp = candle[0]
            trading_date = date.fromisoformat(
                timestamp[:10]
            )

            if (
                trading_date < start_date
                or trading_date > end_date
            ):
                continue

            results.append(
                PriceBar(
                    symbol=normalized_symbol,
                    trading_date=trading_date,
                    open=Decimal(str(candle[1])),
                    high=Decimal(str(candle[2])),
                    low=Decimal(str(candle[3])),
                    close=Decimal(str(candle[4])),
                    volume=int(candle[5]),
                )
            )

        return sorted(
            results,
            key=lambda bar: bar.trading_date,
        )
