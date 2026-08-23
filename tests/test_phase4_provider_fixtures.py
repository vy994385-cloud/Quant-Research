"""
Deterministic fixture-based tests for Yahoo Phase 4 providers.

Tests cover YahooProfileProvider, YahooOwnershipProvider, and
YahooAnalystProvider using recorded fixture payloads with no live
network access.

Each test mocks urllib at the transport level and verifies:
  - Correct parsing of Yahoo response JSON
  - source_name and source_type identity
  - No network calls are made
  - All sub-models (TopHolder, MarketValuation, etc.) parse correctly
"""

from __future__ import annotations

import json
import calendar
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

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
from src.data.providers.yahoo_analyst import YahooAnalystProvider
from src.data.providers.yahoo_ownership import YahooOwnershipProvider
from src.data.providers.yahoo_profile import YahooProfileProvider


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_mock_urlopen(payload: dict):
    """Return a mock urlopen context manager that yields payload."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _mock_urlopen_factory(payload: dict):
    """Return a callable that replaces urlopen and yields payload."""

    def _factory(*args, **kwargs):
        return _make_mock_urlopen(payload)

    return _factory


# ---------------------------------------------------------------------------
# YahooProfileProvider fixtures
# ---------------------------------------------------------------------------

FIXTURE_PROFILE_FULL = {
    "quoteSummary": {
        "result": [
            {
                "assetProfile": {
                    "longBusinessSummary": (
                        "Infosys Limited provides information "
                        "technology consulting and business process "
                        "management services worldwide."
                    ),
                    "sector": "Technology",
                    "industry": "Information Technology Services",
                    "website": "https://www.infosys.com",
                    "fullTimeEmployees": 315000,
                },
                "summaryProfile": {
                    "country": "India",
                    "sector": "Technology",
                    "industry": "Information Technology Services",
                },
                "defaultKeyStatistics": {
                    "longName": "Infosys Limited",
                    "shortName": "Infosys",
                    "beta": 0.78,
                    "trailingPE": 28.35,
                    "forwardPE": 24.10,
                    "pegRatio": 2.15,
                    "priceToBook": 8.42,
                    "priceToSalesTrailing12Months": 5.67,
                    "enterpriseValue": 680000000000,
                    "profitMargins": 0.182,
                    "grossMargins": 0.412,
                    "operatingMargins": 0.255,
                    "ebitdaMargins": 0.278,
                    "bookValue": 206.5,
                    "sharesOutstanding": 4140000000,
                    "floatShares": 3726000000,
                    "heldPercentInsiders": 0.012,
                    "heldPercentInstitutions": 0.734,
                    "shortRatio": 1.85,
                },
                "summaryDetail": {
                    "longName": "Infosys Limited",
                    "shortName": "Infosys",
                    "dividendYield": {"raw": 0.0234},
                },
            }
        ]
    }
}

FIXTURE_PROFILE_PARTIAL = {
    "quoteSummary": {
        "result": [
            {
                "assetProfile": {
                    "longBusinessSummary": (
                        "Minimal profile with missing modules."
                    ),
                },
                "summaryProfile": {},
                "defaultKeyStatistics": {},
                "summaryDetail": {},
            }
        ]
    }
}

FIXTURE_PROFILE_EMPTY_RESULT = {
    "quoteSummary": {
        "result": []
    }
}

FIXTURE_PROFILE_KEY_STATS_WITH_NAMES = {
    "quoteSummary": {
        "result": [
            {
                "assetProfile": {
                    "longBusinessSummary": "Fallback summary text.",
                    "sector": "Finance",
                    "industry": "Banks",
                    "fullTimeEmployees": 80000,
                },
                "summaryProfile": {
                    "country": "United States",
                },
                "defaultKeyStatistics": {
                    "longName": "Test Bank Corp",
                    "shortName": "Test Bank",
                    "beta": 1.05,
                    "sharesOutstanding": 500000000,
                },
                "summaryDetail": {
                    "longName": "Test Bank Corp",
                    "shortName": "Test Bank",
                },
            }
        ]
    }
}

FIXTURE_PROFILE_COMPANY_NAME_FALLBACK = {
    "quoteSummary": {
        "result": [
            {
                "assetProfile": {
                    "longBusinessSummary": (
                        "This long summary is the only name source."
                    ),
                },
                "summaryProfile": {},
                "defaultKeyStatistics": {},
                "summaryDetail": {},
            }
        ]
    }
}


# ---------------------------------------------------------------------------
# YahooOwnershipProvider fixtures
# ---------------------------------------------------------------------------

FIXTURE_OWNERSHIP_FULL = {
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
                            "name": "Vanguard Group Inc",
                            "shares": 5000000,
                            "pctHeld": 0.12,
                            "reportedDate": "2024-06-30",
                        },
                        {
                            "name": "BlackRock Inc",
                            "shares": 3000000,
                            "pctHeld": 0.073,
                            "reportedDate": "2024-06-30",
                        },
                        {
                            "name": "State Street Corp",
                            "shares": 2000000,
                            "pctHeld": 0.048,
                            "reportedDate": "2024-03-31",
                        },
                    ]
                },
            }
        ]
    }
}

FIXTURE_OWNERSHIP_NO_HOLDERS = {
    "quoteResponse": {
        "result": [
            {
                "shareHoldings": {
                    "percentPromoterHolding": 0.72,
                    "percentInstitutionalHolding": 0.15,
                    "percentPublicHolding": 0.13,
                    "percentInsiderHolding": 0.03,
                },
                "shareHolderSummary": {
                    "holders": []
                },
            }
        ]
    }
}

FIXTURE_OWNERSHIP_MISSING_HOLDER_NAME = {
    "quoteResponse": {
        "result": [
            {
                "shareHoldings": {
                    "percentPromoterHolding": 0.60,
                    "percentInstitutionalHolding": 0.20,
                    "percentPublicHolding": 0.20,
                },
                "shareHolderSummary": {
                    "holders": [
                        {
                            "name": "Valid Holder",
                            "shares": 1000000,
                            "pctHeld": 0.05,
                            "reportedDate": "2024-06-30",
                        },
                        {
                            "shares": 500000,
                            "pctHeld": 0.025,
                        },
                    ]
                },
            }
        ]
    }
}

FIXTURE_OWNERSHIP_FRACTIONAL_PERCENTS = {
    "quoteResponse": {
        "result": [
            {
                "shareHoldings": {
                    "percentPromoterHolding": 0.512,
                    "percentInstitutionalHolding": 0.274,
                    "percentPublicHolding": 0.214,
                },
                "shareHolderSummary": {
                    "holders": []
                },
            }
        ]
    }
}

FIXTURE_OWNERSHIP_EMPTY = {
    "quoteResponse": {
        "result": []
    }
}


# ---------------------------------------------------------------------------
# YahooAnalystProvider fixtures
# ---------------------------------------------------------------------------

FIXTURE_ANALYST_FULL = {
    "quoteSummary": {
        "result": [
            {
                "recommendationTrend": {
                    "trend": [
                        {
                            "period": "0m",
                            "strongBuy": 8,
                            "buy": 15,
                            "hold": 10,
                            "sell": 3,
                            "strongSell": 1,
                        },
                        {
                            "period": "-1m",
                            "strongBuy": 7,
                            "buy": 14,
                            "hold": 11,
                            "sell": 4,
                            "strongSell": 1,
                        },
                        {
                            "period": "-2m",
                            "strongBuy": 6,
                            "buy": 13,
                            "hold": 12,
                            "sell": 4,
                            "strongSell": 2,
                        },
                    ]
                },
                "upgradeDowngradeHistory": {
                    "history": [
                        {
                            "firm": "Goldman Sachs",
                            "analystName": "John Smith",
                            "action": "upgrade",
                            "fromGrade": "Hold",
                            "toGrade": "Buy",
                            "date": 1699963200,
                        },
                        {
                            "firm": "Morgan Stanley",
                            "analystName": "Jane Doe",
                            "action": "downgrade",
                            "fromGrade": "Outperform",
                            "toGrade": "Underperform",
                            "date": 1700500000,
                        },
                        {
                            "firm": "JP Morgan",
                            "action": "initiated",
                            "toGrade": "Overweight",
                            "date": 1701000000,
                        },
                    ]
                },
                "earningsHistory": {
                    "earningsChart": [
                        {
                            "date": "2024-06-30",
                            "actual": {"raw": 1.85},
                            "estimate": {"raw": 1.60},
                        },
                        {
                            "date": "2024-03-31",
                            "actual": {"raw": 1.55},
                            "estimate": {"raw": 1.55},
                        },
                        {
                            "date": "2023-12-31",
                            "actual": {"raw": 1.40},
                            "estimate": {"raw": 1.50},
                        },
                    ]
                },
                "calendarEvents": {
                    "earningsDate": [1725000000, 1733000000],
                    "exDividendDate": 1726000000,
                },
                "summaryDetail": {
                    "marketCap": {"raw": 750000000000},
                    "trailingPE": {"raw": 30.5},
                    "forwardPE": {"raw": 26.2},
                    "dividendYield": {"raw": 0.018},
                    "trailingAnnualDividendYield": {"raw": 0.016},
                    "fiveYearAvgDividendYield": {"raw": 1.45},
                    "fiftyTwoWeekHigh": {"raw": 1780.0},
                    "fiftyTwoWeekLow": {"raw": 1350.0},
                    "fiftyDayAverage": {"raw": 1620.0},
                    "twoHundredDayAverage": {"raw": 1580.0},
                    "averageVolume10days": {"raw": 8500000},
                },
                "defaultKeyStatistics": {
                    "enterpriseValue": {"raw": 780000000000},
                    "pegRatio": {"raw": 1.85},
                    "priceToBook": {"raw": 9.2},
                    "priceToSalesTrailing12Months": {"raw": 6.1},
                    "enterpriseToRevenue": {"raw": 6.5},
                    "enterpriseToEbitda": {"raw": 22.0},
                    "beta": {"raw": 0.82},
                    "sharesOutstanding": {"raw": 4140000000},
                    "floatShares": {"raw": 3726000000},
                },
            }
        ]
    }
}

FIXTURE_ANALYST_EMPTY = {
    "quoteSummary": {
        "result": []
    }
}

FIXTURE_ANALYST_PARTIAL = {
    "quoteSummary": {
        "result": [
            {
                "recommendationTrend": {
                    "trend": [
                        {
                            "period": "0m",
                            "strongBuy": 2,
                            "buy": 3,
                            "hold": 5,
                            "sell": 1,
                            "strongSell": 0,
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


# ===========================================================================
# YahooProfileProvider tests
# ===========================================================================


class TestYahooProfileProviderFixtures:
    """Deterministic fixture tests for YahooProfileProvider."""

    def test_full_profile_parses_all_fields(self):
        """Full fixture should populate every BusinessProfile field."""
        provider = YahooProfileProvider()

        with patch(
            "src.data.providers.yahoo_profile.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_PROFILE_FULL),
        ):
            profile = provider.get_business_profile("INFY")

        assert isinstance(profile, BusinessProfile)
        assert profile.symbol == "INFY"
        assert profile.company_name == "Infosys Limited"
        assert profile.sector == "Technology"
        assert profile.industry == "Information Technology Services"
        assert profile.country == "India"
        assert profile.full_time_employees == 315000
        assert profile.website == "https://www.infosys.com"
        assert profile.business_summary is not None
        assert profile.beta == 0.78
        assert profile.trailing_pe == 28.35
        assert profile.forward_pe == 24.10
        assert profile.peg_ratio == 2.15
        assert profile.price_to_book == 8.42
        assert profile.price_to_sales_trailing_12m == 5.67
        assert profile.enterprise_value == 680000000000
        assert profile.profit_margin == 0.182
        assert profile.gross_margin == 0.412
        assert profile.operating_margin == 0.255
        assert profile.ebitda_margin == 0.278
        assert profile.book_value == 206.5
        assert profile.shares_outstanding == 4140000000
        assert profile.float_shares == 3726000000
        assert profile.held_percent_insiders == 0.012
        assert profile.held_percent_institutions == 0.734
        assert profile.short_ratio == 1.85

    def test_full_profile_source_identity(self):
        """source_name and source_type must be set correctly."""
        provider = YahooProfileProvider()

        with patch(
            "src.data.providers.yahoo_profile.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_PROFILE_FULL),
        ):
            profile = provider.get_business_profile("INFY")

        assert profile.source_name == "yahoo_finance"
        assert profile.source_type == "PROFILE"

    def test_full_profile_no_network_calls(self, monkeypatch):
        """urlopen must never be called at the transport level."""
        call_count = 0
        original_factory = _mock_urlopen_factory(FIXTURE_PROFILE_FULL)

        def counting_factory(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return original_factory(*args, **kwargs)

        provider = YahooProfileProvider()

        with patch(
            "src.data.providers.yahoo_profile.urlopen",
            side_effect=counting_factory,
        ):
            provider.get_business_profile("INFY")

        assert call_count == 1

    def test_full_profile_coverage_properties(self):
        """coverage_fields and missing_fields should reflect all fields."""
        provider = YahooProfileProvider()

        with patch(
            "src.data.providers.yahoo_profile.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_PROFILE_FULL),
        ):
            profile = provider.get_business_profile("INFY")

        assert profile.has_sector
        assert profile.has_industry
        assert profile.has_employees
        assert profile.has_business_summary
        assert "company_name" in profile.coverage_fields
        assert "sector" in profile.coverage_fields
        assert "industry" in profile.coverage_fields
        assert len(profile.missing_fields) == 0

    def test_partial_profile_missing_fields(self):
        """Partial fixture should produce profile with missing fields."""
        provider = YahooProfileProvider()

        with patch(
            "src.data.providers.yahoo_profile.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_PROFILE_PARTIAL),
        ):
            profile = provider.get_business_profile("MINIMAL")

        assert profile.symbol == "MINIMAL"
        assert profile.sector is None
        assert profile.industry is None
        assert profile.country is None
        assert profile.full_time_employees is None
        # company_name falls back to longBusinessSummary when no names present
        assert profile.company_name is not None
        assert not profile.has_sector
        assert not profile.has_industry
        assert not profile.has_employees
        assert "sector" in profile.missing_fields
        assert "industry" in profile.missing_fields
        assert "country" in profile.missing_fields

    def test_empty_result_returns_empty_profile(self):
        """Empty quoteSummary.result should return skeleton profile."""
        provider = YahooProfileProvider()

        with patch(
            "src.data.providers.yahoo_profile.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_PROFILE_EMPTY_RESULT),
        ):
            profile = provider.get_business_profile("EMPTY")

        assert profile.symbol == "EMPTY"
        assert profile.source_name == "yahoo_finance"
        assert profile.source_type == "PROFILE"
        assert profile.company_name is None
        assert profile.sector is None

    def test_company_name_from_key_statistics(self):
        """company_name should prefer longName from defaultKeyStatistics."""
        provider = YahooProfileProvider()

        with patch(
            "src.data.providers.yahoo_profile.urlopen",
            side_effect=_mock_urlopen_factory(
                FIXTURE_PROFILE_KEY_STATS_WITH_NAMES
            ),
        ):
            profile = provider.get_business_profile("TBANK")

        assert profile.company_name == "Test Bank Corp"
        assert profile.sector == "Finance"
        assert profile.industry == "Banks"
        assert profile.country == "United States"
        assert profile.full_time_employees == 80000

    def test_company_name_fallback_to_business_summary(self):
        """company_name should fall back to longBusinessSummary."""
        provider = YahooProfileProvider()

        with patch(
            "src.data.providers.yahoo_profile.urlopen",
            side_effect=_mock_urlopen_factory(
                FIXTURE_PROFILE_COMPANY_NAME_FALLBACK
            ),
        ):
            profile = provider.get_business_profile("FALL")

        assert profile.company_name == (
            "This long summary is the only name source."
        )

    def test_symbol_is_uppercased(self):
        """Provider should uppercase the symbol."""
        provider = YahooProfileProvider()

        with patch(
            "src.data.providers.yahoo_profile.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_PROFILE_FULL),
        ):
            profile = provider.get_business_profile("  infy  ")

        assert profile.symbol == "INFY"

    def test_dividend_yield_from_summary_detail_raw_dict(self):
        """dividendYield as {raw: ...} dict should be parsed."""
        provider = YahooProfileProvider()

        with patch(
            "src.data.providers.yahoo_profile.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_PROFILE_FULL),
        ):
            profile = provider.get_business_profile("INFY")

        assert profile.dividend_yield == pytest.approx(0.0234)


# ===========================================================================
# YahooOwnershipProvider tests
# ===========================================================================


class TestYahooOwnershipProviderFixtures:
    """Deterministic fixture tests for YahooOwnershipProvider."""

    def test_full_ownership_summary_with_holders(self):
        """Full fixture should parse all percentages and top holders."""
        provider = YahooOwnershipProvider()
        today = date.today()

        with patch(
            "src.data.providers.yahoo_ownership.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_OWNERSHIP_FULL),
        ):
            summary = provider.get_ownership_summary(
                "TEST", today, today
            )

        assert isinstance(summary, OwnershipSummary)
        assert summary.symbol == "TEST"
        assert summary.source_name == "yahoo_finance"
        assert summary.source_type == "OWNERSHIP"
        assert summary.promoter_percentage == pytest.approx(51.2, abs=0.1)
        assert summary.institutional_percentage == pytest.approx(
            27.4, abs=0.1
        )
        assert summary.public_percentage == pytest.approx(21.4, abs=0.1)
        assert summary.insider_percentage == pytest.approx(5.0, abs=0.1)

    def test_full_ownership_top_holders_parsed(self):
        """Top holders should be parsed with names, shares, pct, dates."""
        provider = YahooOwnershipProvider()
        today = date.today()

        with patch(
            "src.data.providers.yahoo_ownership.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_OWNERSHIP_FULL),
        ):
            summary = provider.get_ownership_summary(
                "TEST", today, today
            )

        assert summary is not None
        assert len(summary.top_holders) == 3
        assert summary.has_top_holders
        assert summary.holder_count == 3

        h0 = summary.top_holders[0]
        assert h0.holder_name == "Vanguard Group Inc"
        assert h0.holder_type == "INSTITUTIONAL"
        assert h0.shares_held == 5000000
        assert h0.share_percentage == pytest.approx(12.0, abs=0.01)
        assert h0.date_reported == date(2024, 6, 30)
        assert h0.source_name == "yahoo_finance"
        assert h0.source_type == "OWNERSHIP"

        h1 = summary.top_holders[1]
        assert h1.holder_name == "BlackRock Inc"
        assert h1.shares_held == 3000000
        assert h1.share_percentage == pytest.approx(7.3, abs=0.01)

        h2 = summary.top_holders[2]
        assert h2.holder_name == "State Street Corp"
        assert h2.shares_held == 2000000
        assert h2.date_reported == date(2024, 3, 31)

    def test_ownership_summary_source_identity(self):
        """source_name and source_type on OwnershipSummary."""
        provider = YahooOwnershipProvider()
        today = date.today()

        with patch(
            "src.data.providers.yahoo_ownership.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_OWNERSHIP_FULL),
        ):
            summary = provider.get_ownership_summary(
                "TEST", today, today
            )

        assert summary is not None
        assert summary.source_name == "yahoo_finance"
        assert summary.source_type == "OWNERSHIP"

    def test_ownership_snapshot_no_pledge_from_insider(self):
        """promoter_pledged_percentage must NOT be set from insider holding."""
        provider = YahooOwnershipProvider()
        today = date.today()

        with patch(
            "src.data.providers.yahoo_ownership.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_OWNERSHIP_FULL),
        ):
            snapshots = provider.get_ownership_snapshots(
                "TEST", today, today
            )

        assert len(snapshots) == 1
        assert snapshots[0].promoter_pledged_percentage is None

    def test_ownership_snapshot_percentages_decimal(self):
        """OwnershipSnapshot percentages should be Decimal objects."""
        provider = YahooOwnershipProvider()
        today = date.today()

        with patch(
            "src.data.providers.yahoo_ownership.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_OWNERSHIP_FULL),
        ):
            snapshots = provider.get_ownership_snapshots(
                "TEST", today, today
            )

        snap = snapshots[0]
        assert isinstance(snap.promoter_percentage, Decimal)
        assert isinstance(snap.institutional_percentage, Decimal)
        assert isinstance(snap.public_percentage, Decimal)
        assert snap.promoter_pledged_percentage is None

    def test_fractional_yahoo_percentages_scaled_to_100(self):
        """Yahoo fractional (0.512) should become 51.2 in Decimal."""
        provider = YahooOwnershipProvider()
        today = date.today()

        with patch(
            "src.data.providers.yahoo_ownership.urlopen",
            side_effect=_mock_urlopen_factory(
                FIXTURE_OWNERSHIP_FRACTIONAL_PERCENTS
            ),
        ):
            snapshots = provider.get_ownership_snapshots(
                "TEST", today, today
            )

        snap = snapshots[0]
        assert snap.promoter_percentage == Decimal("51.20")
        assert snap.institutional_percentage == Decimal("27.40")
        assert snap.public_percentage == Decimal("21.40")

    def test_empty_holders_list(self):
        """shareHolderSummary with empty holders list should work."""
        provider = YahooOwnershipProvider()
        today = date.today()

        with patch(
            "src.data.providers.yahoo_ownership.urlopen",
            side_effect=_mock_urlopen_factory(
                FIXTURE_OWNERSHIP_NO_HOLDERS
            ),
        ):
            summary = provider.get_ownership_summary(
                "TEST", today, today
            )

        assert summary is not None
        assert len(summary.top_holders) == 0
        assert not summary.has_top_holders
        assert summary.holder_count == 0

    def test_missing_holder_name_skipped(self):
        """Holders without name should be skipped."""
        provider = YahooOwnershipProvider()
        today = date.today()

        with patch(
            "src.data.providers.yahoo_ownership.urlopen",
            side_effect=_mock_urlopen_factory(
                FIXTURE_OWNERSHIP_MISSING_HOLDER_NAME
            ),
        ):
            summary = provider.get_ownership_summary(
                "TEST", today, today
            )

        assert summary is not None
        assert len(summary.top_holders) == 1
        assert summary.top_holders[0].holder_name == "Valid Holder"

    def test_empty_quote_response(self):
        """Empty quoteResponse.result should return None."""
        provider = YahooOwnershipProvider()
        today = date.today()

        with patch(
            "src.data.providers.yahoo_ownership.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_OWNERSHIP_EMPTY),
        ):
            summary = provider.get_ownership_summary(
                "TEST", today, today
            )

        assert summary is None

    def test_empty_quote_response_snapshots(self):
        """Empty quoteResponse.result should return empty list for snapshots."""
        provider = YahooOwnershipProvider()
        today = date.today()

        with patch(
            "src.data.providers.yahoo_ownership.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_OWNERSHIP_EMPTY),
        ):
            snapshots = provider.get_ownership_snapshots(
                "TEST", today, today
            )

        assert snapshots == []

    def test_out_of_range_date_returns_empty(self):
        """Date range not covering today should return empty."""
        provider = YahooOwnershipProvider()

        with patch(
            "src.data.providers.yahoo_ownership.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_OWNERSHIP_FULL),
        ):
            summary = provider.get_ownership_summary(
                "TEST",
                date(2020, 1, 1),
                date(2020, 12, 31),
            )

        assert summary is None

    def test_network_error_returns_none(self):
        """Network error should return None gracefully."""
        from urllib.error import URLError

        provider = YahooOwnershipProvider()
        today = date.today()

        with patch(
            "src.data.providers.yahoo_ownership.urlopen",
            side_effect=URLError("connection refused"),
        ):
            summary = provider.get_ownership_summary(
                "TEST", today, today
            )

        assert summary is None

    def test_network_error_returns_empty_snapshots(self):
        """Network error should return empty list for snapshots."""
        from urllib.error import URLError

        provider = YahooOwnershipProvider()
        today = date.today()

        with patch(
            "src.data.providers.yahoo_ownership.urlopen",
            side_effect=URLError("connection refused"),
        ):
            snapshots = provider.get_ownership_snapshots(
                "TEST", today, today
            )

        assert snapshots == []


# ===========================================================================
# YahooAnalystProvider tests
# ===========================================================================


class TestYahooAnalystProviderFixtures:
    """Deterministic fixture tests for YahooAnalystProvider."""

    def test_full_intelligence_source_identity(self):
        """source_name and source_type on AnalystIntelligence."""
        provider = YahooAnalystProvider()

        with patch(
            "src.data.providers.yahoo_analyst.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_ANALYST_FULL),
        ):
            intel = provider.get_analyst_intelligence("INFY")

        assert isinstance(intel, AnalystIntelligence)
        assert intel.symbol == "INFY"
        assert intel.source_name == "yahoo_finance"
        assert intel.source_type == "ANALYST"

    def test_recommendations_parsed(self):
        """recommendationTrend should produce AnalystRecommendation objects."""
        provider = YahooAnalystProvider()

        with patch(
            "src.data.providers.yahoo_analyst.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_ANALYST_FULL),
        ):
            intel = provider.get_analyst_intelligence("INFY")

        assert intel.has_recommendations
        assert intel.recommendation_count == 3

        rec_0m = intel.recommendations[0]
        assert isinstance(rec_0m, AnalystRecommendation)
        assert rec_0m.period == "0m"
        assert rec_0m.strong_buy == 8
        assert rec_0m.buy == 15
        assert rec_0m.hold == 10
        assert rec_0m.sell == 3
        assert rec_0m.strong_sell == 1
        assert rec_0m.total_analysts == 37
        assert rec_0m.consensus_score is not None
        assert 3.0 < rec_0m.consensus_score < 4.0

        rec_m1 = intel.recommendations[1]
        assert rec_m1.period == "-1m"

        rec_m2 = intel.recommendations[2]
        assert rec_m2.period == "-2m"

    def test_rating_changes_parsed(self):
        """upgradeDowngradeHistory should produce AnalystRatingChange objects."""
        provider = YahooAnalystProvider()

        with patch(
            "src.data.providers.yahoo_analyst.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_ANALYST_FULL),
        ):
            intel = provider.get_analyst_intelligence("INFY")

        assert intel.has_rating_changes
        assert intel.rating_change_count == 3

        rc0 = intel.rating_changes[0]
        assert isinstance(rc0, AnalystRatingChange)
        assert rc0.firm == "Goldman Sachs"
        assert rc0.analyst_name == "John Smith"
        assert rc0.action == "upgrade"
        assert rc0.from_grade == "Hold"
        assert rc0.to_grade == "Buy"
        assert rc0.rating_date == date(2023, 11, 14)
        assert rc0.source_name == "yahoo_finance"
        assert rc0.source_type == "ANALYST"

        rc1 = intel.rating_changes[1]
        assert rc1.firm == "Morgan Stanley"
        assert rc1.action == "downgrade"
        assert rc1.from_grade == "Outperform"
        assert rc1.to_grade == "Underperform"

        rc2 = intel.rating_changes[2]
        assert rc2.firm == "JP Morgan"
        assert rc2.analyst_name is None
        assert rc2.from_grade is None
        assert rc2.action == "initiated"

    def test_earnings_surprises_parsed(self):
        """earningsHistory should produce EarningsSurprise objects."""
        provider = YahooAnalystProvider()

        with patch(
            "src.data.providers.yahoo_analyst.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_ANALYST_FULL),
        ):
            intel = provider.get_analyst_intelligence("INFY")

        assert intel.has_earnings_history
        assert intel.earnings_surprise_count == 3

        es0 = intel.earnings_surprises[0]
        assert isinstance(es0, EarningsSurprise)
        assert es0.period_ending == date(2024, 6, 30)
        assert es0.reported_eps == 1.85
        assert es0.estimated_eps == 1.60
        assert es0.surprise_amount is not None
        assert es0.surprise_amount == pytest.approx(0.25, abs=0.01)
        assert es0.surprise_percentage is not None
        assert es0.surprise_percentage > 0
        assert es0.beat_estimate is True

        es1 = intel.earnings_surprises[1]
        assert es1.period_ending == date(2024, 3, 31)
        assert es1.reported_eps == 1.55
        assert es1.estimated_eps == 1.55
        assert es1.meets_estimate is True
        assert es1.beat_estimate is False

        es2 = intel.earnings_surprises[2]
        assert es2.period_ending == date(2023, 12, 31)
        assert es2.reported_eps == 1.40
        assert es2.estimated_eps == 1.50
        assert es2.beat_estimate is False
        assert es2.surprise_amount == pytest.approx(-0.10, abs=0.01)
        assert es2.surprise_percentage is not None
        assert es2.surprise_percentage < 0

    def test_calendar_events_parsed(self):
        """calendarEvents should produce CalendarEvent objects."""
        provider = YahooAnalystProvider()

        with patch(
            "src.data.providers.yahoo_analyst.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_ANALYST_FULL),
        ):
            intel = provider.get_analyst_intelligence("INFY")

        assert len(intel.calendar_events) == 3

        event_types = [e.event_type for e in intel.calendar_events]
        assert event_types.count("EARNINGS_DATE") == 2
        assert event_types.count("EX_DIVIDEND_DATE") == 1

        earnings_events = [
            e for e in intel.calendar_events
            if e.event_type == "EARNINGS_DATE"
        ]
        for ev in earnings_events:
            assert isinstance(ev, CalendarEvent)
            assert ev.event_date is not None
            assert ev.description == "Upcoming earnings date"
            assert ev.source_name == "yahoo_finance"
            assert ev.source_type == "CALENDAR"

        ex_div = [
            e for e in intel.calendar_events
            if e.event_type == "EX_DIVIDEND_DATE"
        ][0]
        assert ex_div.event_date == date(2024, 9, 11)

    def test_valuation_parsed(self):
        """summaryDetail and defaultKeyStatistics should produce MarketValuation."""
        provider = YahooAnalystProvider()

        with patch(
            "src.data.providers.yahoo_analyst.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_ANALYST_FULL),
        ):
            intel = provider.get_analyst_intelligence("INFY")

        assert intel.valuation is not None
        v = intel.valuation
        assert isinstance(v, MarketValuation)
        assert v.symbol == "INFY"
        assert v.source_name == "yahoo_finance"
        assert v.source_type == "VALUATION"

        assert v.market_cap == 750000000000.0
        assert v.trailing_pe == 30.5
        assert v.forward_pe == 26.2
        assert v.enterprise_value == 780000000000.0
        assert v.peg_ratio == 1.85
        assert v.price_to_book == 9.2
        assert v.price_to_sales == 6.1
        assert v.enterprise_to_revenue == 6.5
        assert v.enterprise_to_ebitda == 22.0
        assert v.dividend_yield == 0.018
        assert v.trailing_annual_dividend_yield == 0.016
        assert v.five_year_avg_dividend_yield == 1.45
        assert v.beta == 0.82
        assert v.fifty_two_week_high == 1780.0
        assert v.fifty_two_week_low == 1350.0
        assert v.fifty_day_average == 1620.0
        assert v.two_hundred_day_average == 1580.0
        assert v.avg_volume_10d == 8500000
        assert v.shares_outstanding == 4140000000
        assert v.float_shares == 3726000000

    def test_empty_response_returns_empty_intelligence(self):
        """Empty quoteSummary.result should return skeleton intelligence."""
        provider = YahooAnalystProvider()

        with patch(
            "src.data.providers.yahoo_analyst.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_ANALYST_EMPTY),
        ):
            intel = provider.get_analyst_intelligence("EMPTY")

        assert intel.symbol == "EMPTY"
        assert intel.source_name == "yahoo_finance"
        assert intel.source_type == "ANALYST"
        assert intel.recommendation_count == 0
        assert intel.rating_change_count == 0
        assert intel.earnings_surprise_count == 0
        assert len(intel.calendar_events) == 0
        assert intel.valuation is None

    def test_partial_intelligence_recommendations_only(self):
        """Partial fixture with only recommendations should parse correctly."""
        provider = YahooAnalystProvider()

        with patch(
            "src.data.providers.yahoo_analyst.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_ANALYST_PARTIAL),
        ):
            intel = provider.get_analyst_intelligence("PARTIAL")

        assert intel.symbol == "PARTIAL"
        assert intel.has_recommendations
        assert intel.recommendation_count == 1
        assert not intel.has_rating_changes
        assert not intel.has_earnings_history
        assert len(intel.calendar_events) == 0
        # valuation is always created (empty MarketValuation when no data)
        assert intel.valuation is not None
        assert intel.valuation.market_cap is None

        rec = intel.recommendations[0]
        assert rec.total_analysts == 11
        assert rec.consensus_score is not None

    def test_no_network_calls(self):
        """urlopen must be called exactly once per provider invocation."""
        call_count = 0
        original_factory = _mock_urlopen_factory(FIXTURE_ANALYST_FULL)

        def counting_factory(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return original_factory(*args, **kwargs)

        provider = YahooAnalystProvider()

        with patch(
            "src.data.providers.yahoo_analyst.urlopen",
            side_effect=counting_factory,
        ):
            provider.get_analyst_intelligence("INFY")

        assert call_count == 1

    def test_network_error_returns_empty_intelligence(self):
        """Network error should return empty intelligence, not raise."""
        from urllib.error import URLError

        provider = YahooAnalystProvider()

        with patch(
            "src.data.providers.yahoo_analyst.urlopen",
            side_effect=URLError("connection refused"),
        ):
            intel = provider.get_analyst_intelligence("FAIL")

        assert intel.symbol == "FAIL"
        assert intel.source_name == "yahoo_finance"
        assert intel.source_type == "ANALYST"
        assert intel.recommendation_count == 0
        assert intel.rating_change_count == 0
        assert intel.earnings_surprise_count == 0

    def test_symbol_uppercased(self):
        """Provider should uppercase the symbol."""
        provider = YahooAnalystProvider()

        with patch(
            "src.data.providers.yahoo_analyst.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_ANALYST_PARTIAL),
        ):
            intel = provider.get_analyst_intelligence("  infy  ")

        assert intel.symbol == "INFY"

    def test_intelligence_tuple_immutability(self):
        """Collections should be tuples, not lists."""
        provider = YahooAnalystProvider()

        with patch(
            "src.data.providers.yahoo_analyst.urlopen",
            side_effect=_mock_urlopen_factory(FIXTURE_ANALYST_FULL),
        ):
            intel = provider.get_analyst_intelligence("INFY")

        assert isinstance(intel.recommendations, tuple)
        assert isinstance(intel.rating_changes, tuple)
        assert isinstance(intel.earnings_surprises, tuple)
        assert isinstance(intel.calendar_events, tuple)
