"""
Yahoo Finance ownership data provider.

Fetches ownership breakdown (promoter, institutional, public,
pledge) from Yahoo Finance's quote summary API.

Data available:
  - shareHoldings: percentage breakdown by category
  - shareHolderSummary: top institutional holders with names,
    share counts, and dates

Data NOT available (classified C):
  - FII/DII separate breakdowns
  - Individual insider transactions
  - Bulk/block deal details
  - Detailed pledge history beyond current quarter
"""

from __future__ import annotations

import json
import ssl
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import certifi

from src.data.company.ownership import OwnershipSnapshot, TopHolder, OwnershipSummary


class YahooOwnershipProvider:
    """
    Fetches ownership breakdowns from Yahoo Finance.

    Uses the v6 quote summary endpoint which provides:
      - shareHoldings: category-level percentage breakdown
      - shareHolderSummary: top holder list (optional)
    """

    BASE_URL = "https://query2.finance.yahoo.com/v6/finance/quoteModule"

    MODULES = "shareHolderSummary,shareHoldings"

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.ssl_context = ssl.create_default_context(
            cafile=certifi.where()
        )

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        value = symbol.strip().upper()
        if not value:
            raise ValueError("symbol must not be empty")
        if value.startswith("^") or "." in value:
            return value
        return f"{value}.NS"

    def get_ownership_snapshots(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[OwnershipSnapshot]:
        """
        Fetch current ownership breakdown.

        Yahoo Finance only provides the LATEST ownership data,
        not historical. We return a single snapshot for the
        latest available data point.
        """
        requested = symbol.strip().upper()
        yahoo_symbol = self._normalize_symbol(symbol)

        url = (
            f"{self.BASE_URL}"
            f"?modules={self.MODULES}"
            f"&symbols={quote(yahoo_symbol, safe='')}"
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
        except (HTTPError, URLError, OSError):
            return []

        quote_result = (
            payload.get("quoteResponse", {})
            .get("result", [])
        )

        if not quote_result:
            return []

        quote_data = quote_result[0]

        # Parse shareHoldings for category percentages
        share_holdings = quote_data.get("shareHoldings", {})

        # shareHoldings typically has categories like:
        # "percentPromoterHolding", "percentPublicHolding",
        # "percentInstitutionalHolding"
        promoter = self._parse_pct(
            share_holdings.get("percentPromoterHolding")
        )
        institutional = self._parse_pct(
            share_holdings.get("percentInstitutionalHolding")
        )
        public = self._parse_pct(
            share_holdings.get("percentPublicHolding")
        )

        # Note: percentInsiderHolding is NOT pledge data.
        # Insider holdings = directors/officers shareholding.
        # Pledge data is not available through this Yahoo module.
        # We intentionally do NOT map insider holdings to pledge.
        insider = self._parse_pct(
            share_holdings.get("percentInsiderHolding")
        )

        # Use today's date as the observation date
        # (Yahoo only provides current snapshot)
        today = date.today()
        if today < start_date or today > end_date:
            return []

        snapshot = OwnershipSnapshot(
            symbol=requested,
            period_end=today,
            promoter_percentage=promoter,
            institutional_percentage=institutional,
            public_percentage=public,
            promoter_pledged_percentage=None,
        )

        return [snapshot]

    def get_ownership_summary(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> OwnershipSummary | None:
        """
        Fetch complete ownership summary including top holders.

        Returns OwnershipSummary with breakdown percentages
        and top holder list. Returns None if data unavailable.
        """
        requested = symbol.strip().upper()
        yahoo_symbol = self._normalize_symbol(symbol)

        url = (
            f"{self.BASE_URL}"
            f"?modules={self.MODULES}"
            f"&symbols={quote(yahoo_symbol, safe='')}"
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
        except (HTTPError, URLError, OSError):
            return None

        quote_result = (
            payload.get("quoteResponse", {})
            .get("result", [])
        )

        if not quote_result:
            return None

        quote_data = quote_result[0]

        # Parse shareHoldings
        share_holdings = quote_data.get("shareHoldings", {})
        promoter = self._parse_pct(
            share_holdings.get("percentPromoterHolding")
        )
        institutional = self._parse_pct(
            share_holdings.get("percentInstitutionalHolding")
        )
        public = self._parse_pct(
            share_holdings.get("percentPublicHolding")
        )
        insider = self._parse_pct(
            share_holdings.get("percentInsiderHolding")
        )

        # Parse shareHolderSummary for top holders
        summary_data = quote_data.get("shareHolderSummary", {})
        holders_raw = summary_data.get(" holders", [])
        if not holders_raw:
            holders_raw = summary_data.get("holders", [])

        top_holders: list[TopHolder] = []
        for h in holders_raw:
            name = h.get("name") or h.get("holderName")
            if not name:
                continue

            shares = None
            raw_shares = h.get("shares") or h.get("sharesHeld")
            if raw_shares is not None:
                try:
                    shares = int(float(raw_shares))
                except (ValueError, TypeError):
                    pass

            pct = None
            raw_pct = h.get("pctHeld") or h.get("holdingPercent")
            if raw_pct is not None:
                try:
                    pct = float(raw_pct)
                    if pct <= 1:
                        pct = pct * 100.0
                except (ValueError, TypeError):
                    pass

            reported_date = None
            raw_date = h.get("reportedDate") or h.get("date")
            if raw_date:
                try:
                    reported_date = date.fromisoformat(str(raw_date)[:10])
                except (ValueError, TypeError):
                    pass

            top_holders.append(
                TopHolder(
                    holder_name=name,
                    holder_type="INSTITUTIONAL",
                    shares_held=shares,
                    share_percentage=pct,
                    date_reported=reported_date,
                    source_name="yahoo_finance",
                    source_type="OWNERSHIP",
                )
            )

        today = date.today()
        if today < start_date or today > end_date:
            return None

        return OwnershipSummary(
            symbol=requested,
            period_end=today,
            promoter_percentage=(
                float(promoter) if promoter is not None else None
            ),
            institutional_percentage=(
                float(institutional) if institutional is not None else None
            ),
            public_percentage=(
                float(public) if public is not None else None
            ),
            insider_percentage=(
                float(insider) if insider is not None else None
            ),
            top_holders=tuple(top_holders),
            source_name="yahoo_finance",
            source_type="OWNERSHIP",
        )

    @staticmethod
    def _parse_pct(value) -> Decimal | None:
        """Parse a percentage value from Yahoo's response."""
        if value is None:
            return None
        try:
            raw = Decimal(str(value))
            # Yahoo sometimes returns fractions (e.g., 0.54 for 54%)
            if raw <= 1:
                raw = raw * Decimal("100")
            return raw.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        except Exception:
            return None
