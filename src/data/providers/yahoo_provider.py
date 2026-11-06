from __future__ import annotations

import certifi
import json
import ssl
from datetime import date, datetime, timezone
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict

from src.data.models import PriceBar

from .base import MarketDataProvider


class SecurityMetadata(BaseModel):
    """
    Normalized security identity returned by the Yahoo Chart endpoint.

    This is deliberately separate from PriceBar so historical market
    observations remain a stable provider-independent contract.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str
    company_name: str | None = None
    exchange: str | None = None
    currency: str | None = None
    instrument_type: str | None = None
    metadata_source: str = "yahoo_chart"


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

    BASE_URL = (
        "https://query1.finance.yahoo.com/v8/finance/chart"
    )

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()

        if not normalized:
            raise ValueError("symbol must not be empty.")

        if normalized in {"NIFTY", "NIFTY50", "NIFTY_50"}:
            return "^NSEI"

        if normalized.startswith("^") or "." in normalized:
            return normalized

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

    @staticmethod
    def _ssl_context() -> ssl.SSLContext:
        return ssl.create_default_context(
            cafile=certifi.where()
        )

    def _request_chart(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> dict:
        self._validate_date_range(start_date, end_date)

        requested_symbol = symbol.strip().upper()

        if not requested_symbol:
            raise ValueError("symbol must not be empty.")

        yahoo_symbol = self._normalize_symbol(
            requested_symbol
        )

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
                tzinfo=timezone.utc,
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
                context=self._ssl_context(),
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
            return {}

        return results[0]

    @staticmethod
    def _metadata_from_chart(
        requested_symbol: str,
        result: dict,
    ) -> SecurityMetadata:
        meta = result.get("meta") or {}

        company_name = (
            meta.get("longName")
            or meta.get("shortName")
        )

        exchange = (
            meta.get("fullExchangeName")
            or meta.get("exchangeName")
        )

        currency = meta.get("currency")
        instrument_type = meta.get("instrumentType")

        return SecurityMetadata(
            symbol=requested_symbol,
            company_name=company_name,
            exchange=exchange,
            currency=currency,
            instrument_type=instrument_type,
        )

    def get_metadata(
        self,
        symbol: str,
    ) -> SecurityMetadata:
        """
        Fetch normalized identity metadata from Yahoo Chart.

        A minimal recent window is used because Yahoo exposes the
        identity metadata in the same Chart response as the prices.
        """

        today = date.today()

        result = self._request_chart(
            symbol=symbol,
            start_date=today,
            end_date=today,
        )

        if not result:
            raise RuntimeError(
                f"Yahoo Finance returned no metadata for {symbol}."
            )

        requested_symbol = symbol.strip().upper()

        return self._metadata_from_chart(
            requested_symbol=requested_symbol,
            result=result,
        )

    def get_daily_prices_with_metadata(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> tuple[list[PriceBar], SecurityMetadata]:
        """
        Fetch normalized daily prices and identity metadata from one
        Yahoo Chart response.

        This is the preferred V2 path because Yahoo exposes both
        observations and identity metadata in the same response.
        """

        result = self._request_chart(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        requested_symbol = symbol.strip().upper()

        if not result:
            return [], SecurityMetadata(
                symbol=requested_symbol,
            )

        metadata = self._metadata_from_chart(
            requested_symbol=requested_symbol,
            result=result,
        )

        timestamps = result.get("timestamp") or []

        quote_data = (
            result.get("indicators", {})
            .get("quote", [{}])[0]
        )

        adjclose_data = (
            result.get("indicators", {})
            .get("adjclose", [{}])[0]
        )

        opens = quote_data.get("open") or []
        highs = quote_data.get("high") or []
        lows = quote_data.get("low") or []
        closes = quote_data.get("close") or []
        volumes = quote_data.get("volume") or []
        adjcloses = adjclose_data.get("adjclose") or []

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

            adj_close_value = None

            if (
                index < len(adjcloses)
                and adjcloses[index] is not None
            ):
                adj_close_value = Decimal(
                    str(adjcloses[index])
                )

            bars.append(
                PriceBar(
                    symbol=requested_symbol,
                    trading_date=trading_date,
                    open=Decimal(str(opens[index])),
                    high=Decimal(str(highs[index])),
                    low=Decimal(str(lows[index])),
                    close=Decimal(str(closes[index])),
                    volume=int(volumes[index]),
                    adjusted_close=adj_close_value,
                )
            )

        return (
            sorted(
                bars,
                key=lambda bar: bar.trading_date,
            ),
            metadata,
        )

    def get_daily_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[PriceBar]:
        """
        Preserve the existing MarketDataProvider contract.

        V2 callers that also need identity metadata should use
        get_daily_prices_with_metadata().
        """

        bars, _metadata = self.get_daily_prices_with_metadata(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )

        return bars
