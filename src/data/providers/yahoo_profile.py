"""
Yahoo Finance business profile provider.

Fetches company profile metadata from Yahoo Finance v6 quote
summary endpoint using assetProfile, summaryProfile, and
defaultKeyStatistics modules.

This provider exposes factual metadata only. It never
derives scores, ratings, or analytical conclusions.
"""

from __future__ import annotations

import json
import ssl
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote

from src.data.company.business_profile import BusinessProfile


class YahooProfileProvider:
    """
    Fetches business profile data from Yahoo Finance.

    Uses the v6 quoteSummary endpoint with modules:
      - assetProfile: sector, industry, business summary, employees
      - summaryProfile: sector, industry, country
      - defaultKeyStatistics: beta, enterprise value, profit margins

    Returns raw factual metadata only.
    """

    BASE_URL = "https://query2.finance.yahoo.com/v6/finance/quoteSummary"

    MODULES = "assetProfile,summaryProfile,defaultKeyStatistics"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.ssl_context = ssl.create_default_context()

    def get_business_profile(
        self, symbol: str
    ) -> BusinessProfile:
        """
        Fetch the business profile for a given symbol.

        Returns a BusinessProfile with whatever data Yahoo
        exposes. Missing fields are None — never fabricated.
        """

        yahoo_symbol = symbol.strip().upper()

        url = (
            f"{self.BASE_URL}/{quote(yahoo_symbol, safe='')}"
            f"?modules={self.MODULES}"
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
                context=self.ssl_context,
            ) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )

        except HTTPError as exc:
            raise RuntimeError(
                f"Yahoo profile request failed for "
                f"{yahoo_symbol}: HTTP {exc.code}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"Yahoo profile request failed for "
                f"{yahoo_symbol}: {exc.reason}"
            ) from exc

        result = (
            payload
            .get("quoteSummary", {})
            .get("result", [])
        )

        if not result:
            return BusinessProfile(
                symbol=yahoo_symbol,
                source_name="yahoo_finance",
                source_type="PROFILE",
            )

        data = result[0]

        asset_profile = data.get("assetProfile", {})
        summary_profile = data.get("summaryProfile", {})
        key_stats = data.get("defaultKeyStatistics", {})
        summary_detail = data.get("summaryDetail", {})

        # Company name: prefer shortName/longName from key stats
        # or summaryDetail, fall back to assetProfile
        company_name = (
            key_stats.get("longName")
            or key_stats.get("shortName")
            or summary_detail.get("longName")
            or summary_detail.get("shortName")
            or asset_profile.get("longBusinessSummary")
        )

        # Merge sector from assetProfile and summaryProfile
        sector = (
            asset_profile.get("sector")
            or summary_profile.get("sector")
        )
        industry = (
            asset_profile.get("industry")
            or summary_profile.get("industry")
        )

        employees = None
        raw_employees = (
            asset_profile.get("fullTimeEmployees")
            or summary_profile.get("fullTimeEmployees")
        )
        if raw_employees is not None:
            try:
                employees = int(raw_employees)
            except (ValueError, TypeError):
                pass

        # Parse valuation metrics from defaultKeyStatistics
        beta = self._parse_float(
            key_stats.get("beta")
        )
        trailing_pe = self._parse_float(
            key_stats.get("trailingPE")
        )
        forward_pe = self._parse_float(
            key_stats.get("forwardPE")
        )
        peg_ratio = self._parse_float(
            key_stats.get("pegRatio")
        )
        price_to_book = self._parse_float(
            key_stats.get("priceToBook")
        )
        price_to_sales = self._parse_float(
            key_stats.get("priceToSalesTrailing12Months")
        )
        enterprise_value = self._parse_float(
            key_stats.get("enterpriseValue")
        )
        profit_margin = self._parse_float(
            key_stats.get("profitMargins")
        )
        gross_margin = self._parse_float(
            key_stats.get("grossMargins")
        )
        operating_margin = self._parse_float(
            key_stats.get("operatingMargins")
        )
        ebitda_margin = self._parse_float(
            key_stats.get("ebitdaMargins")
        )
        book_value = self._parse_float(
            key_stats.get("bookValue")
        )
        shares_outstanding = self._parse_int(
            key_stats.get("sharesOutstanding")
        )
        float_shares = self._parse_int(
            key_stats.get("floatShares")
        )
        held_insiders = self._parse_float(
            key_stats.get("heldPercentInsiders")
        )
        held_institutions = self._parse_float(
            key_stats.get("heldPercentInstitutions")
        )
        short_ratio = self._parse_float(
            key_stats.get("shortRatio")
        )
        raw_div_yield = summary_detail.get("dividendYield")
        if isinstance(raw_div_yield, dict):
            raw_div_yield = raw_div_yield.get("raw")
        dividend_yield = self._parse_float(
            raw_div_yield
            or key_stats.get("trailingAnnualDividendYield")
        )

        return BusinessProfile(
            symbol=yahoo_symbol,
            company_name=company_name,
            sector=sector,
            industry=industry,
            country=summary_profile.get("country"),
            full_time_employees=employees,
            business_summary=asset_profile.get(
                "longBusinessSummary"
            ),
            website=asset_profile.get("website"),
            source_name="yahoo_finance",
            source_type="PROFILE",
            beta=beta,
            trailing_pe=trailing_pe,
            forward_pe=forward_pe,
            peg_ratio=peg_ratio,
            price_to_book=price_to_book,
            price_to_sales_trailing_12m=price_to_sales,
            enterprise_value=enterprise_value,
            profit_margin=profit_margin,
            gross_margin=gross_margin,
            operating_margin=operating_margin,
            ebitda_margin=ebitda_margin,
            book_value=book_value,
            shares_outstanding=shares_outstanding,
            float_shares=float_shares,
            held_percent_insiders=held_insiders,
            held_percent_institutions=held_institutions,
            short_ratio=short_ratio,
            dividend_yield=dividend_yield,
        )

    @staticmethod
    def _parse_float(value) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_int(value) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
