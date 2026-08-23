"""
Tests for Phase 5A provider gap fixes and analyst intelligence.

Tests cover:
- Yahoo market provider adjusted_close parsing
- Yahoo financials provider metric mapping fixes
- Yahoo ownership provider shareHolderSummary parsing and pledge fix
- Yahoo profile provider company_name fix and valuation metrics
- Yahoo analyst provider (recommendations, rating changes, earnings, calendar, valuation)
- API contract serialization
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch
from urllib.request import Request

import pytest

from src.data.company.analyst import (
    AnalystIntelligence,
    AnalystRatingChange,
    AnalystRecommendation,
    CalendarEvent,
    EarningsSurprise,
    MarketValuation,
)
from src.data.company.business_profile import BusinessProfile
from src.data.company.ownership import (
    OwnershipSnapshot,
    OwnershipSummary,
    TopHolder,
)
from src.data.models import PriceBar
from src.data.providers.yahoo_analyst import YahooAnalystProvider
from src.data.providers.yahoo_financials import (
    YahooFinanceFinancialProvider,
)
from src.data.providers.yahoo_ownership import (
    YahooOwnershipProvider,
)
from src.data.providers.yahoo_profile import YahooProfileProvider
from src.data.providers.yahoo_provider import (
    YahooFinanceMarketDataProvider,
)


# ---------------------------------------------------------------------------
# Yahoo market provider: adjusted_close parsing
# ---------------------------------------------------------------------------


class TestYahooMarketAdjustedClose:
    """Test that adjusted_close is parsed from adjclose indicator."""

    def test_adjusted_close_parsed_from_adjclose(self):
        """adjusted_close should be populated from adjclose indicator."""
        provider = YahooFinanceMarketDataProvider()

        mock_response = {
            "chart": {
                "result": [
                    {
                        "meta": {"symbol": "TEST.NS"},
                        "timestamp": [1700000000, 1700086400],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [100.0, 101.0],
                                    "high": [105.0, 106.0],
                                    "low": [95.0, 96.0],
                                    "close": [102.0, 103.0],
                                    "volume": [1000000, 1100000],
                                }
                            ],
                            "adjclose": [
                                {
                                    "adjclose": [101.5, 102.5],
                                }
                            ],
                        },
                    }
                ],
                "error": None,
            }
        }

        with patch(
            "src.data.providers.yahoo_provider.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                mock_response
            ).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            bars = provider.get_daily_prices(
                "TEST", date(2023, 11, 14), date(2023, 11, 15)
            )

        assert len(bars) == 2
        assert bars[0].adjusted_close == Decimal("101.5")
        assert bars[1].adjusted_close == Decimal("102.5")

    def test_adjusted_close_none_when_missing(self):
        """adjusted_close should be None when adjclose indicator missing."""
        provider = YahooFinanceMarketDataProvider()

        mock_response = {
            "chart": {
                "result": [
                    {
                        "meta": {"symbol": "TEST.NS"},
                        "timestamp": [1700000000],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [100.0],
                                    "high": [105.0],
                                    "low": [95.0],
                                    "close": [102.0],
                                    "volume": [1000000],
                                }
                            ],
                        },
                    }
                ],
                "error": None,
            }
        }

        with patch(
            "src.data.providers.yahoo_provider.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                mock_response
            ).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            bars = provider.get_daily_prices(
                "TEST", date(2023, 11, 14), date(2023, 11, 14)
            )

        assert len(bars) == 1
        assert bars[0].adjusted_close is None


# ---------------------------------------------------------------------------
# Yahoo financials provider: metric mapping fixes
# ---------------------------------------------------------------------------


class TestYahooFinancialsMetricMapping:
    """Test that operating_profit, cash, total_equity are mapped."""

    def test_operating_profit_mapped(self):
        """operating_profit should map from annualOperatingIncome."""
        provider = YahooFinanceFinancialProvider()

        mock_response = {
            "timeseries": {
                "result": [
                    {
                        "meta": {"type": ["annualOperatingIncome"]},
                        "annualOperatingIncome": [
                            {
                                "asOfDate": "2024-03-31",
                                "reportedValue": {"raw": 5000000},
                            }
                        ],
                    },
                    {
                        "meta": {"type": ["annualTotalRevenue"]},
                        "annualTotalRevenue": [
                            {
                                "asOfDate": "2024-03-31",
                                "reportedValue": {"raw": 10000000},
                            }
                        ],
                    },
                    {
                        "meta": {"type": ["annualCashAndCashEquivalents"]},
                        "annualCashAndCashEquivalents": [
                            {
                                "asOfDate": "2024-03-31",
                                "reportedValue": {"raw": 1500000},
                            }
                        ],
                    },
                    {
                        "meta": {"type": ["annualTotalEquity"]},
                        "annualTotalEquity": [
                            {
                                "asOfDate": "2024-03-31",
                                "reportedValue": {"raw": 8000000},
                            }
                        ],
                    },
                ]
            }
        }

        with patch(
            "src.data.providers.yahoo_financials.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                mock_response
            ).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            snapshots = provider.get_annual_financials(
                "TEST", date(2024, 1, 1), date(2024, 12, 31)
            )

        assert len(snapshots) == 1
        snapshot = snapshots[0]
        assert snapshot.operating_profit == Decimal("5000000")
        assert snapshot.cash_and_equivalents == Decimal("1500000")
        assert snapshot.total_equity == Decimal("8000000")


# ---------------------------------------------------------------------------
# Yahoo ownership provider: shareHolderSummary and pledge fix
# ---------------------------------------------------------------------------


class TestYahooOwnershipShareHolderSummary:
    """Test shareHolderSummary parsing and pledge semantics fix."""

    def test_top_holders_parsed(self):
        """shareHolderSummary top holders should be parsed."""
        provider = YahooOwnershipProvider()

        mock_response = {
            "quoteResponse": {
                "result": [
                    {
                        "shareHoldings": {
                            "percentPromoterHolding": 0.512,
                            "percentInstitutionalHolding": 0.274,
                            "percentPublicHolding": 0.214,
                            "percentInsiderHolding": 0.05,
                        },
                        "shareHolderSummary": {
                            "holders": [
                                {
                                    "name": "Vanguard Group",
                                    "shares": 5000000,
                                    "pctHeld": 0.12,
                                    "reportedDate": "2024-06-30",
                                },
                                {
                                    "name": "BlackRock",
                                    "shares": 3000000,
                                    "pctHeld": 0.08,
                                    "reportedDate": "2024-06-30",
                                },
                            ]
                        },
                    }
                ]
            }
        }

        with patch(
            "src.data.providers.yahoo_ownership.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                mock_response
            ).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            today = date.today()
            summary = provider.get_ownership_summary(
                "TEST", today, today
            )

        assert summary is not None
        assert len(summary.top_holders) == 2
        assert summary.top_holders[0].holder_name == "Vanguard Group"
        assert summary.top_holders[0].shares_held == 5000000
        assert summary.top_holders[0].share_percentage == 12.0
        assert summary.top_holders[1].holder_name == "BlackRock"

    def test_pledge_not_set_from_insider_holding(self):
        """promoter_pledged_percentage should NOT be set from insider holding."""
        provider = YahooOwnershipProvider()

        mock_response = {
            "quoteResponse": {
                "result": [
                    {
                        "shareHoldings": {
                            "percentPromoterHolding": 0.512,
                            "percentInstitutionalHolding": 0.274,
                            "percentPublicHolding": 0.214,
                            "percentInsiderHolding": 0.05,
                        }
                    }
                ]
            }
        }

        with patch(
            "src.data.providers.yahoo_ownership.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                mock_response
            ).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            today = date.today()
            snapshots = provider.get_ownership_snapshots(
                "TEST", today, today
            )

        assert len(snapshots) == 1
        snapshot = snapshots[0]
        # Pledge should be None, not 5%
        assert snapshot.promoter_pledged_percentage is None


# ---------------------------------------------------------------------------
# Yahoo profile provider: company_name fix and valuation metrics
# ---------------------------------------------------------------------------


class TestYahooProfileCompanyAndValuation:
    """Test company_name mapping and valuation metrics parsing."""

    def test_company_name_from_short_name(self):
        """company_name should come from longName/shortName, not longBusinessSummary."""
        provider = YahooProfileProvider()

        mock_response = {
            "quoteSummary": {
                "result": [
                    {
                        "assetProfile": {
                            "longBusinessSummary": "A very long business summary...",
                            "sector": "Technology",
                            "industry": "Software",
                            "website": "https://example.com",
                            "fullTimeEmployees": 1000,
                        },
                        "summaryProfile": {
                            "country": "India",
                        },
                        "defaultKeyStatistics": {
                            "longName": "Test Corp",
                            "shortName": "Test",
                            "beta": 1.2,
                            "trailingPE": 25.5,
                            "forwardPE": 22.0,
                            "pegRatio": 1.1,
                            "priceToBook": 3.5,
                            "priceToSalesTrailing12Months": 2.8,
                            "enterpriseValue": 5000000000,
                            "profitMargins": 0.15,
                            "grossMargins": 0.45,
                            "operatingMargins": 0.20,
                            "ebitdaMargins": 0.25,
                            "bookValue": 15.0,
                            "sharesOutstanding": 100000000,
                            "floatShares": 80000000,
                            "heldPercentInsiders": 0.05,
                            "heldPercentInstitutions": 0.75,
                            "shortRatio": 2.5,
                        },
                        "summaryDetail": {
                            "dividendYield": {"raw": 0.02},
                        },
                    }
                ]
            }
        }

        with patch(
            "src.data.providers.yahoo_profile.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                mock_response
            ).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            profile = provider.get_business_profile("TEST")

        assert profile is not None
        assert profile.company_name == "Test Corp"
        assert profile.sector == "Technology"
        assert profile.industry == "Software"
        assert profile.country == "India"
        assert profile.full_time_employees == 1000

        # Valuation metrics
        assert profile.beta == 1.2
        assert profile.trailing_pe == 25.5
        assert profile.forward_pe == 22.0
        assert profile.peg_ratio == 1.1
        assert profile.price_to_book == 3.5
        assert profile.price_to_sales_trailing_12m == 2.8
        assert profile.enterprise_value == 5000000000
        assert profile.profit_margin == 0.15
        assert profile.gross_margin == 0.45
        assert profile.operating_margin == 0.20
        assert profile.ebitda_margin == 0.25
        assert profile.book_value == 15.0
        assert profile.shares_outstanding == 100000000
        assert profile.float_shares == 80000000
        assert profile.held_percent_insiders == 0.05
        assert profile.held_percent_institutions == 0.75
        assert profile.short_ratio == 2.5


# ---------------------------------------------------------------------------
# Yahoo analyst provider
# ---------------------------------------------------------------------------


class TestYahooAnalystProvider:
    """Test Yahoo analyst intelligence provider."""

    def test_parse_recommendations(self):
        """recommendationTrend should be parsed correctly."""
        provider = YahooAnalystProvider()

        mock_response = {
            "quoteSummary": {
                "result": [
                    {
                        "recommendationTrend": {
                            "trend": [
                                {
                                    "period": "0m",
                                    "strongBuy": 5,
                                    "buy": 10,
                                    "hold": 8,
                                    "sell": 2,
                                    "strongSell": 1,
                                },
                                {
                                    "period": "-1m",
                                    "strongBuy": 4,
                                    "buy": 9,
                                    "hold": 10,
                                    "sell": 3,
                                    "strongSell": 1,
                                },
                            ]
                        },
                        "upgradeDowngradeHistory": {"history": []},
                        "earningsHistory": {"earningsChart": []},
                        "calendarEvents": {},
                        "summaryDetail": {},
                        "defaultKeyStatistics": {},
                    }
                ]
            }
        }

        with patch(
            "src.data.providers.yahoo_analyst.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                mock_response
            ).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            intel = provider.get_analyst_intelligence("TEST")

        assert intel.has_recommendations
        assert intel.recommendation_count == 2

        rec_0m = intel.recommendations[0]
        assert rec_0m.period == "0m"
        assert rec_0m.strong_buy == 5
        assert rec_0m.buy == 10
        assert rec_0m.hold == 8
        assert rec_0m.sell == 2
        assert rec_0m.strong_sell == 1
        assert rec_0m.total_analysts == 26
        assert rec_0m.consensus_score is not None
        assert 3.0 < rec_0m.consensus_score < 4.0

    def test_parse_rating_changes(self):
        """upgradeDowngradeHistory should be parsed correctly."""
        provider = YahooAnalystProvider()

        mock_response = {
            "quoteSummary": {
                "result": [
                    {
                        "recommendationTrend": {"trend": []},
                        "upgradeDowngradeHistory": {
                            "history": [
                                {
                                    "firm": "Goldman Sachs",
                                    "analystName": "John Smith",
                                    "action": "upgrade",
                                    "fromGrade": "Hold",
                                    "toGrade": "Buy",
                                    "date": 1700000000,
                                },
                                {
                                    "firm": "Morgan Stanley",
                                    "action": "initiated",
                                    "toGrade": "Overweight",
                                    "date": 1700100000,
                                },
                            ]
                        },
                        "earningsHistory": {"earningsChart": []},
                        "calendarEvents": {},
                        "summaryDetail": {},
                        "defaultKeyStatistics": {},
                    }
                ]
            }
        }

        with patch(
            "src.data.providers.yahoo_analyst.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                mock_response
            ).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            intel = provider.get_analyst_intelligence("TEST")

        assert intel.has_rating_changes
        assert intel.rating_change_count == 2

        rc = intel.rating_changes[0]
        assert rc.firm == "Goldman Sachs"
        assert rc.analyst_name == "John Smith"
        assert rc.action == "upgrade"
        assert rc.from_grade == "Hold"
        assert rc.to_grade == "Buy"
        assert rc.rating_date is not None

    def test_parse_earnings_surprises(self):
        """earningsHistory should be parsed correctly."""
        provider = YahooAnalystProvider()

        mock_response = {
            "quoteSummary": {
                "result": [
                    {
                        "recommendationTrend": {"trend": []},
                        "upgradeDowngradeHistory": {"history": []},
                        "earningsHistory": {
                            "earningsChart": [
                                {
                                    "date": "2024-06-30",
                                    "actual": {"raw": 1.50},
                                    "estimate": {"raw": 1.35},
                                },
                                {
                                    "date": "2024-03-31",
                                    "actual": {"raw": 1.20},
                                    "estimate": {"raw": 1.25},
                                },
                            ]
                        },
                        "calendarEvents": {},
                        "summaryDetail": {},
                        "defaultKeyStatistics": {},
                    }
                ]
            }
        }

        with patch(
            "src.data.providers.yahoo_analyst.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                mock_response
            ).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            intel = provider.get_analyst_intelligence("TEST")

        assert intel.has_earnings_history
        assert intel.earnings_surprise_count == 2

        # Beat estimate
        es_0 = intel.earnings_surprises[0]
        assert es_0.reported_eps == 1.50
        assert es_0.estimated_eps == 1.35
        assert es_0.surprise_amount is not None
        assert es_0.beat_estimate is True

        # Missed estimate
        es_1 = intel.earnings_surprises[1]
        assert es_1.reported_eps == 1.20
        assert es_1.estimated_eps == 1.25
        assert es_1.beat_estimate is False

    def test_parse_calendar_events(self):
        """calendarEvents should be parsed correctly."""
        provider = YahooAnalystProvider()

        mock_response = {
            "quoteSummary": {
                "result": [
                    {
                        "recommendationTrend": {"trend": []},
                        "upgradeDowngradeHistory": {"history": []},
                        "earningsHistory": {"earningsChart": []},
                        "calendarEvents": {
                            "earningsDate": [1700000000],
                            "exDividendDate": 1700100000,
                        },
                        "summaryDetail": {},
                        "defaultKeyStatistics": {},
                    }
                ]
            }
        }

        with patch(
            "src.data.providers.yahoo_analyst.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                mock_response
            ).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            intel = provider.get_analyst_intelligence("TEST")

        assert len(intel.calendar_events) == 2
        event_types = [e.event_type for e in intel.calendar_events]
        assert "EARNINGS_DATE" in event_types
        assert "EX_DIVIDEND_DATE" in event_types

    def test_parse_valuation(self):
        """summaryDetail and defaultKeyStatistics should be parsed."""
        provider = YahooAnalystProvider()

        mock_response = {
            "quoteSummary": {
                "result": [
                    {
                        "recommendationTrend": {"trend": []},
                        "upgradeDowngradeHistory": {"history": []},
                        "earningsHistory": {"earningsChart": []},
                        "calendarEvents": {},
                        "summaryDetail": {
                            "marketCap": {"raw": 1000000000},
                            "trailingPE": {"raw": 20.5},
                            "forwardPE": {"raw": 18.0},
                            "dividendYield": {"raw": 0.025},
                            "fiftyTwoWeekHigh": {"raw": 150.0},
                            "fiftyTwoWeekLow": {"raw": 100.0},
                            "fiftyDayAverage": {"raw": 125.0},
                            "twoHundredDayAverage": {"raw": 120.0},
                            "averageVolume10days": {"raw": 500000},
                        },
                        "defaultKeyStatistics": {
                            "enterpriseValue": {"raw": 1200000000},
                            "pegRatio": {"raw": 1.5},
                            "priceToBook": {"raw": 3.0},
                            "priceToSalesTrailing12Months": {"raw": 2.5},
                            "enterpriseToRevenue": {"raw": 3.2},
                            "enterpriseToEbitda": {"raw": 12.0},
                            "beta": {"raw": 1.1},
                            "sharesOutstanding": {"raw": 10000000},
                            "floatShares": {"raw": 8000000},
                        },
                    }
                ]
            }
        }

        with patch(
            "src.data.providers.yahoo_analyst.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                mock_response
            ).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            intel = provider.get_analyst_intelligence("TEST")

        assert intel.valuation is not None
        v = intel.valuation
        assert v.symbol == "TEST"
        assert v.market_cap == 1000000000.0
        assert v.trailing_pe == 20.5
        assert v.forward_pe == 18.0
        assert v.enterprise_value == 1200000000.0
        assert v.peg_ratio == 1.5
        assert v.price_to_book == 3.0
        assert v.price_to_sales == 2.5
        assert v.enterprise_to_revenue == 3.2
        assert v.enterprise_to_ebitda == 12.0
        assert v.dividend_yield == 0.025
        assert v.beta == 1.1
        assert v.fifty_two_week_high == 150.0
        assert v.fifty_two_week_low == 100.0
        assert v.fifty_day_average == 125.0
        assert v.two_hundred_day_average == 120.0
        assert v.avg_volume_10d == 500000
        assert v.shares_outstanding == 10000000
        assert v.float_shares == 8000000

    def test_empty_response_returns_empty_intel(self):
        """Empty Yahoo response should return empty intelligence."""
        provider = YahooAnalystProvider()

        mock_response = {
            "quoteSummary": {
                "result": []
            }
        }

        with patch(
            "src.data.providers.yahoo_analyst.urlopen"
        ) as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps(
                mock_response
            ).encode("utf-8")
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            intel = provider.get_analyst_intelligence("TEST")

        assert intel.symbol == "TEST"
        assert intel.recommendation_count == 0
        assert intel.rating_change_count == 0
        assert intel.earnings_surprise_count == 0
        assert intel.valuation is None

    def test_network_error_returns_empty_intel(self):
        """Network error should return empty intelligence, not raise."""
        from urllib.error import URLError

        provider = YahooAnalystProvider()

        with patch(
            "src.data.providers.yahoo_analyst.urlopen"
        ) as mock_urlopen:
            mock_urlopen.side_effect = URLError("connection refused")

            intel = provider.get_analyst_intelligence("TEST")

        assert intel.symbol == "TEST"
        assert intel.recommendation_count == 0


# ---------------------------------------------------------------------------
# Analyst data model tests
# ---------------------------------------------------------------------------


class TestAnalystDataModels:
    """Test analyst data model properties and validation."""

    def test_consensus_score_calculation(self):
        """consensus_score should be correctly weighted."""
        rec = AnalystRecommendation(
            period="0m",
            strong_buy=2,
            buy=3,
            hold=5,
            sell=1,
            strong_sell=0,
        )
        # Total: 11, weighted: 2*5 + 3*4 + 5*3 + 1*2 + 0*1 = 10+12+15+2+0 = 39
        # 39/11 = 3.545... -> 3.55
        assert rec.total_analysts == 11
        assert rec.consensus_score == 3.55

    def test_consensus_score_zero_analysts(self):
        """consensus_score should be None when no analysts."""
        rec = AnalystRecommendation(
            period="0m",
            strong_buy=0,
            buy=0,
            hold=0,
            sell=0,
            strong_sell=0,
        )
        assert rec.total_analysts == 0
        assert rec.consensus_score is None

    def test_earnings_surprise_beat(self):
        """beat_estimate should correctly identify beat."""
        es = EarningsSurprise(
            reported_eps=1.50,
            estimated_eps=1.25,
        )
        assert es.beat_estimate is True

    def test_earnings_surprise_miss(self):
        """beat_estimate should correctly identify miss."""
        es = EarningsSurprise(
            reported_eps=1.20,
            estimated_eps=1.25,
        )
        assert es.beat_estimate is False

    def test_earnings_surprise_unknown(self):
        """beat_estimate should be None when data missing."""
        es = EarningsSurprise(
            reported_eps=None,
            estimated_eps=1.25,
        )
        assert es.beat_estimate is None

    def test_analyst_intelligence_properties(self):
        """AnalystIntelligence properties should work correctly."""
        intel = AnalystIntelligence(
            symbol="TEST",
            recommendations=(
                AnalystRecommendation(
                    period="0m",
                    strong_buy=1,
                    buy=2,
                    hold=3,
                    sell=1,
                    strong_sell=0,
                ),
            ),
            rating_changes=(
                AnalystRatingChange(
                    firm="GS",
                    action="upgrade",
                ),
            ),
            earnings_surprises=(
                EarningsSurprise(reported_eps=1.0),
                EarningsSurprise(reported_eps=1.5),
            ),
        )
        assert intel.has_recommendations
        assert intel.has_rating_changes
        assert intel.has_earnings_history
        assert intel.recommendation_count == 1
        assert intel.rating_change_count == 1
        assert intel.earnings_surprise_count == 2


# ---------------------------------------------------------------------------
# TopHolder and OwnershipSummary tests
# ---------------------------------------------------------------------------


class TestOwnershipModels:
    """Test TopHolder and OwnershipSummary models."""

    def test_top_holder_properties(self):
        """TopHolder should be constructable with required fields."""
        th = TopHolder(
            holder_name="Vanguard",
            shares_held=5000000,
            share_percentage=12.5,
        )
        assert th.holder_name == "Vanguard"
        assert th.holder_type == "INSTITUTIONAL"
        assert th.shares_held == 5000000

    def test_ownership_summary_properties(self):
        """OwnershipSummary properties should work correctly."""
        summary = OwnershipSummary(
            symbol="TEST",
            period_end=date.today(),
            promoter_percentage=51.2,
            institutional_percentage=27.4,
            public_percentage=21.4,
            top_holders=(
                TopHolder(holder_name="A"),
                TopHolder(holder_name="B"),
                TopHolder(holder_name="C"),
            ),
        )
        assert summary.has_top_holders
        assert summary.holder_count == 3

    def test_ownership_summary_empty_holders(self):
        """OwnershipSummary with no holders."""
        summary = OwnershipSummary(
            symbol="TEST",
            period_end=date.today(),
        )
        assert not summary.has_top_holders
        assert summary.holder_count == 0


# ---------------------------------------------------------------------------
# BusinessProfile valuation metrics tests
# ---------------------------------------------------------------------------


class TestBusinessProfileValuation:
    """Test BusinessProfile valuation metrics fields."""

    def test_valuation_fields_populated(self):
        """Valuation fields should be settable."""
        profile = BusinessProfile(
            symbol="TEST",
            company_name="Test Corp",
            beta=1.2,
            trailing_pe=25.5,
            forward_pe=22.0,
            peg_ratio=1.1,
            price_to_book=3.5,
            price_to_sales_trailing_12m=2.8,
            enterprise_value=5000000000,
            profit_margin=0.15,
            gross_margin=0.45,
            operating_margin=0.20,
            ebitda_margin=0.25,
            book_value=15.0,
            shares_outstanding=100000000,
            float_shares=80000000,
            held_percent_insiders=0.05,
            held_percent_institutions=0.75,
            short_ratio=2.5,
            dividend_yield=0.02,
        )
        assert profile.beta == 1.2
        assert profile.trailing_pe == 25.5
        assert profile.enterprise_value == 5000000000
        assert profile.shares_outstanding == 100000000

    def test_valuation_fields_default_none(self):
        """Valuation fields should default to None."""
        profile = BusinessProfile(
            symbol="TEST",
            company_name="Test Corp",
        )
        assert profile.beta is None
        assert profile.trailing_pe is None
        assert profile.enterprise_value is None


# ---------------------------------------------------------------------------
# API contract serialization tests
# ---------------------------------------------------------------------------


class TestPhase5AContractSerialization:
    """Test that Phase 5A API contracts serialize correctly."""

    def test_analyst_recommendation_contract(self):
        """ContractAnalystRecommendation should serialize."""
        from src.api.contracts import ContractAnalystRecommendation

        rec = ContractAnalystRecommendation(
            period="0m",
            strong_buy=5,
            buy=10,
            hold=8,
            sell=2,
            strong_sell=1,
            total_analysts=26,
            consensus_score="3.55",
        )
        data = rec.model_dump()
        assert data["period"] == "0m"
        assert data["total_analysts"] == 26
        assert data["consensus_score"] == "3.55"

    def test_market_valuation_contract(self):
        """ContractMarketValuation should serialize."""
        from src.api.contracts import ContractMarketValuation

        val = ContractMarketValuation(
            symbol="TEST",
            market_cap="1000000000",
            trailing_pe="20.5",
            forward_pe="18.0",
            beta="1.1",
        )
        data = val.model_dump()
        assert data["symbol"] == "TEST"
        assert data["market_cap"] == "1000000000"
        assert data["trailing_pe"] == "20.5"

    def test_analyst_intelligence_contract(self):
        """ContractAnalystIntelligence should serialize."""
        from src.api.contracts import ContractAnalystIntelligence

        intel = ContractAnalystIntelligence(
            symbol="TEST",
            has_recommendations=True,
            has_rating_changes=False,
            has_earnings_history=True,
            recommendation_count=3,
            rating_change_count=0,
            earnings_surprise_count=2,
            calendar_event_count=1,
        )
        data = intel.model_dump()
        assert data["symbol"] == "TEST"
        assert data["has_recommendations"] is True
        assert data["recommendation_count"] == 3

    def test_ownership_summary_contract(self):
        """ContractOwnershipSummary should serialize."""
        from src.api.contracts import (
            ContractOwnershipSummary,
            ContractTopHolder,
        )

        holder = ContractTopHolder(
            holder_name="Vanguard",
            holder_type="INSTITUTIONAL",
            shares_held="5000000",
            share_percentage="12.5",
        )
        summary = ContractOwnershipSummary(
            symbol="TEST",
            period_end="2024-06-30",
            promoter_percentage="51.2",
            institutional_percentage="27.4",
            public_percentage="21.4",
            top_holders=[holder],
            has_top_holders=True,
            holder_count=1,
        )
        data = summary.model_dump()
        assert data["symbol"] == "TEST"
        assert data["has_top_holders"] is True
        assert len(data["top_holders"]) == 1
        assert data["top_holders"][0]["holder_name"] == "Vanguard"
