from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.data.company.financials import FinancialSnapshot


class YahooFinanceFinancialProvider:
    """
    Real Yahoo Finance annual financial-data provider.

    Converts Yahoo Finance fundamentals-timeseries data into
    normalized FinancialSnapshot objects.
    """

    BASE_URL = (
        "https://query1.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries"
    )

    METRICS = (
        "annualTotalRevenue",
        "annualNetIncome",
        "annualTotalAssets",
        "annualTotalDebt",
        "annualFreeCashFlow",
        "annualAccountsReceivable",
        "annualOperatingCashFlow",
    )

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        value = symbol.strip().upper()

        if not value:
            raise ValueError("symbol must not be empty")

        if value.startswith("^") or "." in value:
            return value

        return f"{value}.NS"

    def get_annual_financials(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[FinancialSnapshot]:

        if start_date > end_date:
            raise ValueError(
                "start_date must not be after end_date"
            )

        requested_symbol = symbol.strip().upper()
        yahoo_symbol = self._normalize_symbol(symbol)

        period1 = int(
            __import__("datetime").datetime(
                start_date.year,
                start_date.month,
                start_date.day,
                tzinfo=__import__("datetime").timezone.utc,
            ).timestamp()
        )

        period2 = int(
            __import__("datetime").datetime(
                end_date.year,
                end_date.month,
                end_date.day,
                tzinfo=__import__("datetime").timezone.utc,
            ).timestamp()
        )

        metrics = ",".join(self.METRICS)

        url = (
            f"{self.BASE_URL}/{quote(yahoo_symbol, safe='')}"
            f"?symbol={quote(yahoo_symbol, safe='')}"
            f"&type={metrics}"
            f"&period1={period1}"
            f"&period2={period2}"
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
                f"Yahoo financial request failed for "
                f"{requested_symbol}: HTTP {exc.code}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"Yahoo financial request failed for "
                f"{requested_symbol}: {exc.reason}"
            ) from exc

        result = (
            payload
            .get("timeseries", {})
            .get("result", [])
        )

        by_date: dict[date, dict[str, Decimal]] = {}

        for metric_block in result:
            meta = metric_block.get("meta", {})
            metric_types = meta.get("type", [])

            if not metric_types:
                continue

            metric = metric_types[0]

            for row in metric_block.get(metric, []):
                as_of = row.get("asOfDate")
                reported = row.get("reportedValue", {})
                raw = reported.get("raw")

                if not as_of or raw is None:
                    continue

                period_end = date.fromisoformat(as_of)

                if period_end < start_date:
                    continue

                if period_end > end_date:
                    continue

                by_date.setdefault(
                    period_end,
                    {}
                )[metric] = Decimal(str(raw))

        snapshots: list[FinancialSnapshot] = []

        for period_end in sorted(by_date):
            values = by_date[period_end]

            snapshots.append(
                FinancialSnapshot(
                    symbol=requested_symbol,
                    period_end=period_end,
                    revenue=values.get(
                        "annualTotalRevenue"
                    ),
                    net_profit=values.get(
                        "annualNetIncome"
                    ),
                    total_assets=values.get(
                        "annualTotalAssets"
                    ),
                    total_debt=values.get(
                        "annualTotalDebt"
                    ),
                    free_cash_flow=values.get(
                        "annualFreeCashFlow"
                    ),
                    receivables=values.get(
                        "annualAccountsReceivable"
                    ),
                    operating_cash_flow=values.get(
                        "annualOperatingCashFlow"
                    ),
                )
            )

        return snapshots
