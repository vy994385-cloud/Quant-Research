"""
Yahoo Finance analyst intelligence provider.

Fetches analyst recommendations, rating changes, earnings
history, calendar events, and market valuation from Yahoo
Finance's quote summary API.

Modules queried:
  - recommendationTrend: analyst buy/hold/sell recommendations
  - upgradeDowngradeHistory: analyst rating changes
  - earningsHistory: historical earnings surprises
  - calendarEvents: ex-dividend dates, earnings dates
  - summaryDetail: market cap, P/E, dividend yield, 52-week range

All data is factual and never invented.
"""

from __future__ import annotations

import json
import ssl
from datetime import date, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import certifi

from src.data.company.analyst import (
    AnalystIntelligence,
    AnalystRatingChange,
    AnalystRecommendation,
    CalendarEvent,
    EarningsSurprise,
    MarketValuation,
)


class YahooAnalystProvider:
    """
    Fetches analyst intelligence from Yahoo Finance.

    Uses the v6 quoteSummary endpoint with modules:
      recommendationTrend, upgradeDowngradeHistory,
      earningsHistory, calendarEvents, summaryDetail
    """

    BASE_URL = "https://query2.finance.yahoo.com/v6/finance/quoteSummary"

    MODULES = (
        "recommendationTrend,"
        "upgradeDowngradeHistory,"
        "earningsHistory,"
        "calendarEvents,"
        "summaryDetail,"
        "defaultKeyStatistics"
    )

    def __init__(self, timeout: int = 20):
        self.timeout = timeout
        self.ssl_context = ssl.create_default_context(
            cafile=certifi.where()
        )

    def get_analyst_intelligence(
        self, symbol: str
    ) -> AnalystIntelligence:
        """
        Fetch complete analyst intelligence for a symbol.

        Returns AnalystIntelligence with whatever data Yahoo
        exposes. Missing data is represented as empty tuples
        or None — never fabricated.
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

        except (HTTPError, URLError, OSError):
            return AnalystIntelligence(
                symbol=yahoo_symbol,
                source_name="yahoo_finance",
                source_type="ANALYST",
            )

        result = (
            payload
            .get("quoteSummary", {})
            .get("result", [])
        )

        if not result:
            return AnalystIntelligence(
                symbol=yahoo_symbol,
                source_name="yahoo_finance",
                source_type="ANALYST",
            )

        data = result[0]

        recommendations = self._parse_recommendations(
            data.get("recommendationTrend", {})
        )

        rating_changes = self._parse_rating_changes(
            data.get("upgradeDowngradeHistory", {})
        )

        earnings = self._parse_earnings_history(
            data.get("earningsHistory", {})
        )

        calendar = self._parse_calendar_events(
            data.get("calendarEvents", {})
        )

        valuation = self._parse_valuation(
            yahoo_symbol,
            data.get("summaryDetail", {}),
            data.get("defaultKeyStatistics", {}),
        )

        return AnalystIntelligence(
            symbol=yahoo_symbol,
            recommendations=tuple(recommendations),
            rating_changes=tuple(rating_changes),
            earnings_surprises=tuple(earnings),
            calendar_events=tuple(calendar),
            valuation=valuation,
            source_name="yahoo_finance",
            source_type="ANALYST",
        )

    def _parse_recommendations(
        self, trend_data: dict
    ) -> list[AnalystRecommendation]:
        """Parse recommendationTrend module."""
        recommendations: list[AnalystRecommendation] = []

        trend = trend_data.get("trend", [])
        if not trend:
            return recommendations

        for period_data in trend:
            period = period_data.get("period", "")
            if not period:
                continue

            strong_buy = self._parse_int(
                period_data.get("strongBuy")
            )
            buy = self._parse_int(
                period_data.get("buy")
            )
            hold = self._parse_int(
                period_data.get("hold")
            )
            sell = self._parse_int(
                period_data.get("sell")
            )
            strong_sell = self._parse_int(
                period_data.get("strongSell")
            )

            recommendations.append(
                AnalystRecommendation(
                    period=period,
                    strong_buy=strong_buy or 0,
                    buy=buy or 0,
                    hold=hold or 0,
                    sell=sell or 0,
                    strong_sell=strong_sell or 0,
                )
            )

        return recommendations

    def _parse_rating_changes(
        self, history_data: dict
    ) -> list[AnalystRatingChange]:
        """Parse upgradeDowngradeHistory module."""
        changes: list[AnalystRatingChange] = []

        history = history_data.get("history", [])
        if not history:
            return changes

        for entry in history:
            firm = entry.get("firm")
            if not firm:
                continue

            action = entry.get("action")
            if not action:
                continue

            from_grade = entry.get("fromGrade")
            to_grade = entry.get("toGrade")

            event_date = None
            raw_date = entry.get("date")
            if raw_date:
                try:
                    event_date = datetime.fromtimestamp(
                        raw_date, tz=None
                    ).date()
                except (ValueError, TypeError, OSError):
                    pass

            changes.append(
                AnalystRatingChange(
                    firm=firm,
                    analyst_name=entry.get("analystName"),
                    action=action,
                    from_grade=from_grade,
                    to_grade=to_grade,
                    rating_date=event_date,
                    source_name="yahoo_finance",
                    source_type="ANALYST",
                )
            )

        return changes

    def _parse_earnings_history(
        self, earnings_data: dict
    ) -> list[EarningsSurprise]:
        """Parse earningsHistory module."""
        surprises: list[EarningsSurprise] = []

        history = earnings_data.get("earningsChart", [])
        if not history:
            # Try alternative structure
            history = earnings_data.get("financialsChart", [])

        for entry in history:
            period_ending = None
            raw_date = entry.get("date") or entry.get("quarter")
            if raw_date:
                try:
                    period_ending = date.fromisoformat(str(raw_date)[:10])
                except (ValueError, TypeError):
                    pass

            # Earnings surprise from earningsChart
            actual = entry.get("actual", {})
            estimate = entry.get("estimate", {})

            reported_eps = self._parse_float(
                actual.get("raw") if isinstance(actual, dict) else actual
            )
            estimated_eps = self._parse_float(
                estimate.get("raw") if isinstance(estimate, dict) else estimate
            )

            surprise_amount = None
            surprise_pct = None
            if (
                reported_eps is not None
                and estimated_eps is not None
                and estimated_eps != 0
            ):
                surprise_amount = round(reported_eps - estimated_eps, 4)
                surprise_pct = round(
                    ((reported_eps - estimated_eps) / abs(estimated_eps)) * 100,
                    2,
                )

            surprises.append(
                EarningsSurprise(
                    period_ending=period_ending,
                    reported_eps=reported_eps,
                    estimated_eps=estimated_eps,
                    surprise_amount=surprise_amount,
                    surprise_percentage=surprise_pct,
                )
            )

        return surprises

    def _parse_calendar_events(
        self, calendar_data: dict
    ) -> list[CalendarEvent]:
        """Parse calendarEvents module."""
        events: list[CalendarEvent] = []

        # Earnings date
        earnings_date = calendar_data.get("earningsDate", [])
        if isinstance(earnings_date, list):
            for raw_date in earnings_date:
                event_date = self._parse_timestamp(raw_date)
                if event_date:
                    events.append(
                        CalendarEvent(
                            event_type="EARNINGS_DATE",
                            event_date=event_date,
                            description="Upcoming earnings date",
                            source_name="yahoo_finance",
                            source_type="CALENDAR",
                        )
                    )
        elif earnings_date:
            event_date = self._parse_timestamp(earnings_date)
            if event_date:
                events.append(
                    CalendarEvent(
                        event_type="EARNINGS_DATE",
                        event_date=event_date,
                        description="Upcoming earnings date",
                        source_name="yahoo_finance",
                        source_type="CALENDAR",
                    )
                )

        # Ex-dividend date
        ex_div = calendar_data.get("exDividendDate")
        if ex_div:
            event_date = self._parse_timestamp(ex_div)
            if event_date:
                events.append(
                    CalendarEvent(
                        event_type="EX_DIVIDEND_DATE",
                        event_date=event_date,
                        description="Ex-dividend date",
                        source_name="yahoo_finance",
                        source_type="CALENDAR",
                    )
                )

        return events

    def _parse_valuation(
        self,
        symbol: str,
        summary_detail: dict,
        key_stats: dict,
    ) -> MarketValuation:
        """Parse summaryDetail and defaultKeyStatistics for valuation."""
        return MarketValuation(
            symbol=symbol,
            market_cap=self._parse_float(
                summary_detail.get("marketCap", {}).get("raw")
                if isinstance(summary_detail.get("marketCap"), dict)
                else summary_detail.get("marketCap")
            ),
            enterprise_value=self._parse_float(
                key_stats.get("enterpriseValue", {}).get("raw")
                if isinstance(key_stats.get("enterpriseValue"), dict)
                else key_stats.get("enterpriseValue")
            ),
            trailing_pe=self._parse_float(
                summary_detail.get("trailingPE", {}).get("raw")
                if isinstance(summary_detail.get("trailingPE"), dict)
                else summary_detail.get("trailingPE")
            ),
            forward_pe=self._parse_float(
                summary_detail.get("forwardPE", {}).get("raw")
                if isinstance(summary_detail.get("forwardPE"), dict)
                else summary_detail.get("forwardPE")
            ),
            peg_ratio=self._parse_float(
                key_stats.get("pegRatio", {}).get("raw")
                if isinstance(key_stats.get("pegRatio"), dict)
                else key_stats.get("pegRatio")
            ),
            price_to_book=self._parse_float(
                key_stats.get("priceToBook", {}).get("raw")
                if isinstance(key_stats.get("priceToBook"), dict)
                else key_stats.get("priceToBook")
            ),
            price_to_sales=self._parse_float(
                key_stats.get("priceToSalesTrailing12Months", {}).get("raw")
                if isinstance(key_stats.get("priceToSalesTrailing12Months"), dict)
                else key_stats.get("priceToSalesTrailing12Months")
            ),
            enterprise_to_revenue=self._parse_float(
                key_stats.get("enterpriseToRevenue", {}).get("raw")
                if isinstance(key_stats.get("enterpriseToRevenue"), dict)
                else key_stats.get("enterpriseToRevenue")
            ),
            enterprise_to_ebitda=self._parse_float(
                key_stats.get("enterpriseToEbitda", {}).get("raw")
                if isinstance(key_stats.get("enterpriseToEbitda"), dict)
                else key_stats.get("enterpriseToEbitda")
            ),
            dividend_yield=self._parse_float(
                summary_detail.get("dividendYield", {}).get("raw")
                if isinstance(summary_detail.get("dividendYield"), dict)
                else summary_detail.get("dividendYield")
            ),
            trailing_annual_dividend_yield=self._parse_float(
                summary_detail.get("trailingAnnualDividendYield", {}).get("raw")
                if isinstance(summary_detail.get("trailingAnnualDividendYield"), dict)
                else summary_detail.get("trailingAnnualDividendYield")
            ),
            five_year_avg_dividend_yield=self._parse_float(
                summary_detail.get("fiveYearAvgDividendYield", {}).get("raw")
                if isinstance(summary_detail.get("fiveYearAvgDividendYield"), dict)
                else summary_detail.get("fiveYearAvgDividendYield")
            ),
            beta=self._parse_float(
                key_stats.get("beta", {}).get("raw")
                if isinstance(key_stats.get("beta"), dict)
                else key_stats.get("beta")
            ),
            fifty_two_week_high=self._parse_float(
                summary_detail.get("fiftyTwoWeekHigh", {}).get("raw")
                if isinstance(summary_detail.get("fiftyTwoWeekHigh"), dict)
                else summary_detail.get("fiftyTwoWeekHigh")
            ),
            fifty_two_week_low=self._parse_float(
                summary_detail.get("fiftyTwoWeekLow", {}).get("raw")
                if isinstance(summary_detail.get("fiftyTwoWeekLow"), dict)
                else summary_detail.get("fiftyTwoWeekLow")
            ),
            fifty_day_average=self._parse_float(
                summary_detail.get("fiftyDayAverage", {}).get("raw")
                if isinstance(summary_detail.get("fiftyDayAverage"), dict)
                else summary_detail.get("fiftyDayAverage")
            ),
            two_hundred_day_average=self._parse_float(
                summary_detail.get("twoHundredDayAverage", {}).get("raw")
                if isinstance(summary_detail.get("twoHundredDayAverage"), dict)
                else summary_detail.get("twoHundredDayAverage")
            ),
            avg_volume_10d=self._parse_int(
                summary_detail.get("averageVolume10days", {}).get("raw")
                if isinstance(summary_detail.get("averageVolume10days"), dict)
                else summary_detail.get("averageVolume10days")
            ),
            shares_outstanding=self._parse_int(
                key_stats.get("sharesOutstanding", {}).get("raw")
                if isinstance(key_stats.get("sharesOutstanding"), dict)
                else key_stats.get("sharesOutstanding")
            ),
            float_shares=self._parse_int(
                key_stats.get("floatShares", {}).get("raw")
                if isinstance(key_stats.get("floatShares"), dict)
                else key_stats.get("floatShares")
            ),
            source_name="yahoo_finance",
            source_type="VALUATION",
        )

    def _parse_float(self, value) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    def _parse_int(self, value) -> int | None:
        if value is None:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None

    def _parse_timestamp(self, value) -> date | None:
        if value is None:
            return None
        try:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(value).date()
            return date.fromisoformat(str(value)[:10])
        except (ValueError, TypeError, OSError):
            return None
