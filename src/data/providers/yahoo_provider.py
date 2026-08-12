from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.data.models import PriceBar

from .base import MarketDataProvider


class YahooFinanceMarketDataProvider(MarketDataProvider):
    """
    External historical market-data provider.

    Converts Yahoo Finance chart data into the project's
    provider-independent PriceBar model.

    Indian NSE symbols are automatically mapped:
        TCS   -> TCS.NS
        INFY  -> INFY.NS

    Index symbols may be supplied directly:
        ^NSEI
    """

    BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()

        if not normalized:
            raise ValueError("symbol must not be empty.")

        if normalized in {"NIFTY", "NIFTY50", "NIFTY_50"}:
            return "^NSEI"

        # Preserve explicit Yahoo symbols and indices.
        if normalized.startswith("^") or "." in normalized:
            return normalized

        # Default project universe is Indian NSE equities.
        return f"{normalized}.NS"

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

        requested_symbol = symbol.strip().upper()

        if not requested_symbol:
            raise ValueError("symbol must not be empty.")

        yahoo_symbol = self._normalize_symbol(
            requested_symbol
        )

        # Yahoo's period2 is exclusive, so request one day after
        # the requested end date.
        period1 = int(
            datetime(
                start_date.year,
                start_date.month,
                start_date.day,
                tzinfo=timezone.utc,
            ).timestamp()
        )

        period2 = int(
            datetime(
                end_date.year,
                end_date.month,
                end_date.day,
                tzinfo=timezone.utc
            ).timestamp()
        ) + 86400

        url = (
            f"{self.BASE_URL}/"
            f"{quote(yahoo_symbol, safe='')}"
            f"?period1={period1}"
            f"&period2={period2}"
            f"&interval=1d"
            f"&events=history"
        )

        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Macintosh; Intel Mac OS X)"
                )
            },
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )
        except HTTPError as exc:
            raise RuntimeError(
                f"Yahoo Finance request failed for "
                f"{requested_symbol}: HTTP {exc.code}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(
                f"Yahoo Finance request failed for "
                f"{requested_symbol}: {exc.reason}"
            ) from exc

        chart = payload.get("chart", {})
        error = chart.get("error")

        if error:
            description = (
                error.get("description")
                or error.get("code")
                or "unknown Yahoo Finance error"
            )
            raise RuntimeError(
                f"Yahoo Finance returned an error for "
                f"{requested_symbol}: {description}"
            )

        results = chart.get("result") or []

        if not results:
            return []

        result = results[0]

        timestamps = result.get("timestamp") or []
        quote_data = (
            result.get("indicators", {})
            .get("quote", [{}])[0]
        )

        opens = quote_data.get("open") or []
        highs = quote_data.get("high") or []
        lows = quote_data.get("low") or []
        closes = quote_data.get("close") or []
        volumes = quote_data.get("volume") or []

        bars: list[PriceBar] = []

        for index, timestamp in enumerate(timestamps):
            if index >= len(opens):
                continue
            if index >= len(highs):
                continue
            if index >= len(lows):
                continue
            if index >= len(closes):
                continue
            if index >= len(volumes):
                continue

            values = (
                opens[index],
                highs[index],
                lows[index],
                closes[index],
                volumes[index],
            )

            # Never invent incomplete observations.
            if any(value is None for value in values):
                continue

            trading_date = datetime.fromtimestamp(
                timestamp,
                tz=timezone.utc,
            ).date()

            if trading_date < start_date:
                continue

            if trading_date > end_date:
                continue

            bars.append(
                PriceBar(
                    symbol=requested_symbol,
                    trading_date=trading_date,
                    open=Decimal(str(opens[index])),
                    high=Decimal(str(highs[index])),
                    low=Decimal(str(lows[index])),
                    close=Decimal(str(closes[index])),
                    volume=int(volumes[index]),
                )
            )

        return sorted(
            bars,
            key=lambda bar: bar.trading_date,
        )
