"""
Comprehensive tests for F6 — Research Product Expansion.

Covers:
- Chart data generation (chart_data.py)
- Company news (news.py)
- Corporate actions (corporate_actions.py)
- Industry context (industry_context.py)
- Financial change tracking (tracking/)
- API integration tests for all F6 endpoints
"""

from __future__ import annotations

import dataclasses

import pytest
from datetime import date, datetime, timezone
from decimal import Decimal

from src.analysis.chart_data import (
    ChartDataSet,
    ChartDataPoint,
    ChartMetricCategory,
    ChartSeries,
    ChartUnit,
    build_chart_data,
)
from src.data.company.news import (
    CompanyNewsItem,
    CompanyNewsResult,
    NewsCategory,
    NewsDirection,
)
from src.data.company.corporate_actions import (
    CorporateActionItem,
    CorporateActionResult,
    CorporateActionType,
)
from src.analysis.industry_context import (
    IndustryCharacteristic,
    IndustryContextResult,
    IndustryResearchQuestion,
    build_industry_context,
)
from src.data.company.business_profile import BusinessProfile
from src.data.company.financials import FinancialSnapshot
from src.tracking.engine import build_tracking_result
from src.tracking.models import (
    ChangeDomain,
    CompanyTrackingResult,
    TrackingChange,
    TrackingSeverity,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TZ = timezone.utc


def _snap(
    symbol: str,
    period_end: date,
    revenue: Decimal | None = None,
    net_profit: Decimal | None = None,
    total_assets: Decimal | None = None,
    total_debt: Decimal | None = None,
    cash: Decimal | None = None,
    operating_cf: Decimal | None = None,
) -> FinancialSnapshot:
    return FinancialSnapshot(
        symbol=symbol,
        period_end=period_end,
        revenue=revenue,
        net_profit=net_profit,
        total_assets=total_assets,
        total_debt=total_debt,
        cash_and_equivalents=cash,
        operating_cash_flow=operating_cf,
    )


@pytest.fixture
def two_periods():
    return [
        _snap(
            "TEST",
            date(2025, 3, 31),
            revenue=Decimal("1000"),
            net_profit=Decimal("100"),
            total_assets=Decimal("5000"),
            total_debt=Decimal("2000"),
            cash=Decimal("500"),
            operating_cf=Decimal("150"),
        ),
        _snap(
            "TEST",
            date(2025, 6, 30),
            revenue=Decimal("1200"),
            net_profit=Decimal("120"),
            total_assets=Decimal("5500"),
            total_debt=Decimal("1800"),
            cash=Decimal("600"),
            operating_cf=Decimal("180"),
        ),
    ]


@pytest.fixture
def as_of_dt():
    return datetime(2025, 9, 15, tzinfo=TZ)


# ---------------------------------------------------------------------------
# chart_data.py tests
# ---------------------------------------------------------------------------


class TestChartDataPoint:
    def test_available(self):
        pt = ChartDataPoint(
            period_end="2025-06-30",
            value="1200",
            available=True,
            as_of="2025-09-15",
            source="test",
        )
        assert pt.available is True
        assert pt.value == "1200"

    def test_unavailable(self):
        pt = ChartDataPoint(
            period_end="2025-06-30",
            value=None,
            available=False,
            as_of="2025-09-15",
            source="test",
        )
        assert pt.available is False
        assert pt.value is None

    def test_as_dict(self):
        pt = ChartDataPoint(
            period_end="2025-06-30",
            value="1200",
            available=True,
            as_of="2025-09-15",
            source="test",
        )
        d = dataclasses.asdict(pt)
        assert d["period_end"] == "2025-06-30"
        assert d["available"] is True


class TestChartSeries:
    def test_creation(self):
        s = ChartSeries(
            metric="revenue",
            label="Revenue",
            unit=ChartUnit.CURRENCY,
            category=ChartMetricCategory.INCOME,
            data_points=(),
            period_count=0,
            available_count=0,
            missing_count=0,
            source="test",
        )
        assert s.metric == "revenue"
        assert s.unit == ChartUnit.CURRENCY

    def test_as_dict(self):
        s = ChartSeries(
            metric="revenue",
            label="Revenue",
            unit=ChartUnit.CURRENCY,
            category=ChartMetricCategory.INCOME,
            data_points=(),
            period_count=0,
            available_count=0,
            missing_count=0,
            source="test",
        )
        d = dataclasses.asdict(s)
        assert d["metric"] == "revenue"
        assert d["unit"] == "CURRENCY"


class TestChartDataSet:
    def test_creation(self):
        ds = ChartDataSet(
            symbol="TEST",
            as_of="2025-09-15",
            notes=("test note",),
        )
        assert ds.symbol == "TEST"
        assert ds.total_metrics == 0

    def test_as_dict(self):
        ds = ChartDataSet(
            symbol="TEST",
            as_of="2025-09-15",
            notes=("test note",),
        )
        d = dataclasses.asdict(ds)
        assert d["symbol"] == "TEST"
        assert d["notes"] == ("test note",)


class TestBuildChartData:
    def test_builds_chart_from_snapshots(self, two_periods, as_of_dt):
        ds = build_chart_data(two_periods, "TEST", as_of_dt)
        assert ds.symbol == "TEST"
        assert ds.total_metrics > 0
        assert ds.total_data_points > 0

    def test_revenue_series_has_data(self, two_periods, as_of_dt):
        ds = build_chart_data(two_periods, "TEST", as_of_dt)
        revenue_series = next(
            (s for s in ds.series if s.metric == "revenue"),
            None,
        )
        assert revenue_series is not None
        assert revenue_series.period_count == 2
        assert revenue_series.available_count == 2
        assert len(revenue_series.data_points) == 2
        assert revenue_series.data_points[0].available is True

    def test_empty_snapshots(self, as_of_dt):
        ds = build_chart_data([], "TEST", as_of_dt)
        assert ds.total_metrics == 0
        assert ds.total_data_points == 0

    def test_single_snapshot(self, as_of_dt):
        snapshots = [
            _snap(
                "TEST",
                date(2025, 6, 30),
                revenue=Decimal("1000"),
                net_profit=Decimal("100"),
            )
        ]
        ds = build_chart_data(snapshots, "TEST", as_of_dt)
        assert ds.total_metrics > 0

    def test_categories_populated(self, two_periods, as_of_dt):
        ds = build_chart_data(two_periods, "TEST", as_of_dt)
        assert len(ds.categories) > 0

    def test_notes_field(self, two_periods, as_of_dt):
        ds = build_chart_data(two_periods, "TEST", as_of_dt)
        assert isinstance(ds.notes, tuple)

    def test_net_profit_margin_calculated(
        self, two_periods, as_of_dt
    ):
        ds = build_chart_data(two_periods, "TEST", as_of_dt)
        margin_series = next(
            (
                s
                for s in ds.series
                if s.metric == "net_profit_margin"
            ),
            None,
        )
        assert margin_series is not None
        assert margin_series.period_count == 2

    def test_operating_margin_calculated(
        self, two_periods, as_of_dt
    ):
        ds = build_chart_data(two_periods, "TEST", as_of_dt)
        op_margin = next(
            (
                s
                for s in ds.series
                if s.metric == "operating_margin"
            ),
            None,
        )
        assert op_margin is not None
        assert op_margin.period_count == 2

    def test_ocf_margin_calculated(self, two_periods, as_of_dt):
        ds = build_chart_data(two_periods, "TEST", as_of_dt)
        ocf = next(
            (s for s in ds.series if s.metric == "ocf_margin"),
            None,
        )
        assert ocf is not None
        assert ocf.period_count == 2

    def test_fcf_margin_calculated(self, two_periods, as_of_dt):
        ds = build_chart_data(two_periods, "TEST", as_of_dt)
        fcf = next(
            (s for s in ds.series if s.metric == "fcf_margin"),
            None,
        )
        # fcf_margin requires free_cash_flow which we didn't set
        assert fcf is not None
        assert fcf.period_count == 2

    def test_debt_to_equity_calculated(
        self, two_periods, as_of_dt
    ):
        ds = build_chart_data(two_periods, "TEST", as_of_dt)
        de_series = next(
            (
                s
                for s in ds.series
                if s.metric == "debt_to_equity"
            ),
            None,
        )
        assert de_series is not None
        assert de_series.period_count == 2

    def test_current_ratio_calculated(
        self, two_periods, as_of_dt
    ):
        ds = build_chart_data(two_periods, "TEST", as_of_dt)
        cr = next(
            (s for s in ds.series if s.metric == "current_ratio"),
            None,
        )
        assert cr is not None
        assert cr.period_count == 2

    def test_cash_to_debt_calculated(
        self, two_periods, as_of_dt
    ):
        ds = build_chart_data(two_periods, "TEST", as_of_dt)
        ctd = next(
            (
                s
                for s in ds.series
                if s.metric == "cash_to_debt"
            ),
            None,
        )
        assert ctd is not None
        assert ctd.period_count == 2

    def test_series_sorted_by_period(
        self, two_periods, as_of_dt
    ):
        ds = build_chart_data(two_periods, "TEST", as_of_dt)
        for s in ds.series:
            dates = [
                dp.period_end
                for dp in s.data_points
                if dp.available
            ]
            assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# news.py tests
# ---------------------------------------------------------------------------


class TestCompanyNewsItem:
    def test_creation(self):
        item = CompanyNewsItem(
            news_id="TEST-news-1",
            symbol="TEST",
            headline="Test headline",
            summary="Test summary",
            category=NewsCategory.EARNINGS,
            direction=NewsDirection.POSITIVE,
            source_name="test_source",
            source_url="https://test.com",
            source_type="NEWS",
            published_at=datetime(2025, 9, 1, tzinfo=TZ),
            available_at=datetime(2025, 9, 1, tzinfo=TZ),
            as_of=datetime(2025, 9, 15, tzinfo=TZ),
            provenance_id="prov-001",
        )
        assert item.news_id == "TEST-news-1"
        assert item.category == NewsCategory.EARNINGS

    def test_model_dump(self):
        item = CompanyNewsItem(
            news_id="TEST-news-1",
            symbol="TEST",
            headline="Test headline",
            summary="Test summary",
            category=NewsCategory.OTHER,
            direction=NewsDirection.UNKNOWN,
        )
        d = item.model_dump()
        assert d["news_id"] == "TEST-news-1"
        assert d["category"] == "OTHER"


class TestCompanyNewsResult:
    def test_from_items_empty(self, as_of_dt):
        r = CompanyNewsResult.from_items(
            symbol="TEST", as_of=as_of_dt, items=()
        )
        assert r.symbol == "TEST"
        assert r.item_count == 0
        assert r.category_counts == {}

    def test_from_items_with_data(self, as_of_dt):
        items = (
            CompanyNewsItem(
                news_id="n1",
                symbol="TEST",
                headline="Headline 1",
                summary="Summary 1",
                category=NewsCategory.EARNINGS,
                direction=NewsDirection.POSITIVE,
            ),
            CompanyNewsItem(
                news_id="n2",
                symbol="TEST",
                headline="Headline 2",
                summary="Summary 2",
                category=NewsCategory.MANAGEMENT,
                direction=NewsDirection.NEUTRAL,
            ),
        )
        r = CompanyNewsResult.from_items(
            symbol="TEST", as_of=as_of_dt, items=items
        )
        assert r.item_count == 2
        assert r.category_counts.get("EARNINGS") == 1
        assert r.category_counts.get("MANAGEMENT") == 1

    def test_from_items_source_count(self, as_of_dt):
        items = (
            CompanyNewsItem(
                news_id="n1",
                symbol="TEST",
                headline="H1",
                summary="S1",
                category=NewsCategory.OTHER,
                direction=NewsDirection.UNKNOWN,
                source_name="source_a",
            ),
            CompanyNewsItem(
                news_id="n2",
                symbol="TEST",
                headline="H2",
                summary="S2",
                category=NewsCategory.OTHER,
                direction=NewsDirection.UNKNOWN,
                source_name="source_b",
            ),
        )
        r = CompanyNewsResult.from_items(
            symbol="TEST", as_of=as_of_dt, items=items
        )
        assert r.source_count == 2
        assert "source_a" in r.source_names
        assert "source_b" in r.source_names


# ---------------------------------------------------------------------------
# corporate_actions.py tests
# ---------------------------------------------------------------------------


class TestCorporateActionItem:
    def test_creation(self):
        item = CorporateActionItem(
            action_id="TEST-ca-1",
            symbol="TEST",
            action_type=CorporateActionType.BUYBACK,
            title="Buyback announcement",
            description="Company announced buyback",
            source_name="test_source",
        )
        assert item.action_id == "TEST-ca-1"
        assert item.action_type == CorporateActionType.BUYBACK

    def test_model_dump(self):
        item = CorporateActionItem(
            action_id="TEST-ca-1",
            symbol="TEST",
            action_type=CorporateActionType.DIVIDEND,
            title="Dividend",
            description="Dividend announced",
        )
        d = item.model_dump()
        assert d["action_id"] == "TEST-ca-1"
        assert d["action_type"] == "DIVIDEND"


class TestCorporateActionResult:
    def test_from_items_empty(self, as_of_dt):
        r = CorporateActionResult.from_items(
            symbol="TEST", as_of=as_of_dt, items=()
        )
        assert r.symbol == "TEST"
        assert r.item_count == 0

    def test_from_items_with_data(self, as_of_dt):
        items = (
            CorporateActionItem(
                action_id="ca1",
                symbol="TEST",
                action_type=CorporateActionType.BUYBACK,
                title="Buyback",
                description="Buyback",
            ),
            CorporateActionItem(
                action_id="ca2",
                symbol="TEST",
                action_type=CorporateActionType.DIVIDEND,
                title="Dividend",
                description="Dividend",
            ),
            CorporateActionItem(
                action_id="ca3",
                symbol="TEST",
                action_type=CorporateActionType.BUYBACK,
                title="Buyback 2",
                description="Buyback 2",
            ),
        )
        r = CorporateActionResult.from_items(
            symbol="TEST", as_of=as_of_dt, items=items
        )
        assert r.item_count == 3
        assert r.type_counts.get("BUYBACK") == 2
        assert r.type_counts.get("DIVIDEND") == 1


# ---------------------------------------------------------------------------
# industry_context.py tests
# ---------------------------------------------------------------------------


class TestIndustryCharacteristic:
    def test_creation(self):
        c = IndustryCharacteristic(
            name="test_char",
            description="Test characteristic",
            relevance="HIGH",
        )
        assert c.name == "test_char"
        assert c.relevance == "HIGH"

    def test_as_dict(self):
        c = IndustryCharacteristic(
            name="test",
            description="desc",
            relevance="MEDIUM",
        )
        d = dataclasses.asdict(c)
        assert d["name"] == "test"
        assert d["relevance"] == "MEDIUM"


class TestIndustryResearchQuestion:
    def test_creation(self):
        q = IndustryResearchQuestion(
            question="What is the growth rate?",
            category="growth",
            priority="HIGH",
        )
        assert q.question == "What is the growth rate?"
        assert q.priority == "HIGH"

    def test_as_dict(self):
        q = IndustryResearchQuestion(
            question="Test?",
            category="test",
            priority="LOW",
        )
        d = dataclasses.asdict(q)
        assert d["question"] == "Test?"
        assert d["priority"] == "LOW"


class TestIndustryContextResult:
    def test_creation(self):
        r = IndustryContextResult(
            symbol="TEST",
            sector="Technology",
            industry="test",
            country="India",
            characteristics=(),
            relevant_metrics=(),
            research_questions=(),
            relevant_technology_areas=(),
            industry_risks=(),
            company_context=(),
        )
        assert r.symbol == "TEST"
        assert r.sector == "Technology"

    def test_as_dict(self):
        r = IndustryContextResult(
            symbol="TEST",
            sector="Technology",
            industry="test",
            country="India",
            characteristics=(),
            relevant_metrics=(),
            research_questions=(),
            relevant_technology_areas=(),
            industry_risks=(),
            company_context=(),
        )
        d = dataclasses.asdict(r)
        assert d["symbol"] == "TEST"
        assert d["sector"] == "Technology"


class TestBuildIndustryContext:
    def test_technology_sector(self):
        profile = BusinessProfile(
            symbol="TEST",
            sector="Technology",
        )
        result = build_industry_context(profile, "TEST")
        assert result.symbol == "TEST"
        assert result.sector == "Technology"
        assert len(result.characteristics) > 0
        assert len(result.relevant_metrics) > 0

    def test_financial_services_sector(self):
        profile = BusinessProfile(
            symbol="TEST",
            sector="Financial Services",
        )
        result = build_industry_context(profile, "TEST")
        assert result.sector == "Financial Services"
        assert len(result.characteristics) > 0

    def test_healthcare_sector(self):
        profile = BusinessProfile(
            symbol="TEST",
            sector="Healthcare",
        )
        result = build_industry_context(profile, "TEST")
        assert result.sector == "Healthcare"

    def test_energy_sector(self):
        profile = BusinessProfile(
            symbol="TEST",
            sector="Energy",
        )
        result = build_industry_context(profile, "TEST")
        assert result.sector == "Energy"

    def test_consumer_sector(self):
        profile = BusinessProfile(
            symbol="TEST",
            sector="Consumer",
        )
        result = build_industry_context(profile, "TEST")
        assert result.sector == "Consumer"

    def test_manufacturing_sector(self):
        profile = BusinessProfile(
            symbol="TEST",
            sector="Manufacturing",
        )
        result = build_industry_context(profile, "TEST")
        assert result.sector == "Manufacturing"

    def test_unknown_sector(self):
        profile = BusinessProfile(
            symbol="TEST",
            sector="Unknown",
        )
        result = build_industry_context(profile, "TEST")
        assert result.sector == "Unknown"
        assert len(result.characteristics) == 0
        assert len(result.relevant_metrics) == 0


# ---------------------------------------------------------------------------
# tracking/ tests
# ---------------------------------------------------------------------------


class TestTrackingChange:
    def test_creation(self):
        change = TrackingChange(
            change_id="test-change-1",
            symbol="TEST",
            domain=ChangeDomain.FINANCIAL,
            severity=TrackingSeverity.NOTABLE,
            title="Revenue growth",
            description="Revenue increased",
            previous_value="1000",
            current_value="1200",
        )
        assert change.change_id == "test-change-1"
        assert change.domain == ChangeDomain.FINANCIAL

    def test_model_dump(self):
        change = TrackingChange(
            change_id="test-change-1",
            symbol="TEST",
            domain=ChangeDomain.FINANCIAL,
            severity=TrackingSeverity.NOTABLE,
            title="Revenue growth",
            description="Revenue increased",
        )
        d = change.model_dump()
        assert d["change_id"] == "test-change-1"
        assert d["domain"] == "FINANCIAL"
        assert d["severity"] == "NOTABLE"


class TestCompanyTrackingResult:
    def test_creation(self):
        r = CompanyTrackingResult(
            symbol="TEST",
            as_of=datetime(2025, 9, 15, tzinfo=TZ),
        )
        assert r.symbol == "TEST"
        assert r.change_count == 0

    def test_model_dump(self):
        r = CompanyTrackingResult(
            symbol="TEST",
            as_of=datetime(2025, 9, 15, tzinfo=TZ),
        )
        d = r.model_dump()
        assert d["symbol"] == "TEST"
        assert d["change_count"] == 0


class TestBuildTrackingResult:
    def test_builds_tracking_from_snapshots(
        self, two_periods, as_of_dt
    ):
        result = build_tracking_result(
            two_periods, "TEST", as_of_dt
        )
        assert result.symbol == "TEST"
        assert result.as_of == as_of_dt
        assert result.change_count > 0

    def test_revenue_change_detected(
        self, two_periods, as_of_dt
    ):
        result = build_tracking_result(
            two_periods, "TEST", as_of_dt
        )
        financial_changes = [
            c
            for c in result.changes
            if c.domain == ChangeDomain.FINANCIAL
        ]
        assert len(financial_changes) > 0
        rev_change = next(
            (c for c in financial_changes if "Revenue" in c.title),
            None,
        )
        assert rev_change is not None
        assert rev_change.previous_value == "1000"
        assert rev_change.current_value == "1200"

    def test_profit_change_detected(
        self, two_periods, as_of_dt
    ):
        result = build_tracking_result(
            two_periods, "TEST", as_of_dt
        )
        financial_changes = [
            c
            for c in result.changes
            if c.domain == ChangeDomain.FINANCIAL
        ]
        profit_change = next(
            (c for c in financial_changes if "profit" in c.title.lower()),
            None,
        )
        assert profit_change is not None

    def test_debt_change_detected(
        self, two_periods, as_of_dt
    ):
        snapshots = [
            _snap(
                "TEST",
                date(2025, 3, 31),
                total_debt=Decimal("2000"),
            ),
            _snap(
                "TEST",
                date(2025, 6, 30),
                total_debt=Decimal("1500"),
            ),
        ]
        result = build_tracking_result(
            snapshots, "TEST", as_of_dt
        )
        financial_changes = [
            c
            for c in result.changes
            if c.domain == ChangeDomain.FINANCIAL
        ]
        debt_change = next(
            (c for c in financial_changes if "debt" in c.title.lower()),
            None,
        )
        assert debt_change is not None
        assert debt_change.previous_value == "2000"
        assert debt_change.current_value == "1500"

    def test_empty_snapshots(self, as_of_dt):
        result = build_tracking_result([], "TEST", as_of_dt)
        assert result.change_count == 0

    def test_single_snapshot(self, as_of_dt):
        snapshots = [
            _snap(
                "TEST",
                date(2025, 6, 30),
                revenue=Decimal("1000"),
                net_profit=Decimal("100"),
            )
        ]
        result = build_tracking_result(
            snapshots, "TEST", as_of_dt
        )
        assert result.change_count == 0

    def test_domain_counts(self, two_periods, as_of_dt):
        result = build_tracking_result(
            two_periods, "TEST", as_of_dt
        )
        assert len(result.domain_counts) > 0

    def test_significant_count(self, two_periods, as_of_dt):
        result = build_tracking_result(
            two_periods, "TEST", as_of_dt
        )
        assert result.significant_count >= 0


# ---------------------------------------------------------------------------
# API integration tests
# ---------------------------------------------------------------------------


class TestF6APIEndpoints:
    """Tests for all F6 API endpoints."""

    def test_chart_data_endpoint(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.f6_router import create_f6_router

        app = FastAPI()
        app.include_router(create_f6_router())
        client = TestClient(app)

        response = client.get(
            "/api/v1/companies/TCS/chart-data"
        )
        assert response.status_code == 200
        data = response.json()
        assert "company" in data
        assert "chart_data" in data
        assert data["company"]["symbol"] == "TCS"
        assert data["chart_data"]["symbol"] == "TCS"
        assert "series" in data["chart_data"]
        assert "categories" in data["chart_data"]

    def test_news_endpoint(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.f6_router import create_f6_router

        app = FastAPI()
        app.include_router(create_f6_router())
        client = TestClient(app)

        response = client.get(
            "/api/v1/companies/TCS/news"
        )
        assert response.status_code == 200
        data = response.json()
        assert "company" in data
        assert "news" in data
        assert data["company"]["symbol"] == "TCS"

    def test_corporate_actions_endpoint(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.f6_router import create_f6_router

        app = FastAPI()
        app.include_router(create_f6_router())
        client = TestClient(app)

        response = client.get(
            "/api/v1/companies/TCS/corporate-actions"
        )
        assert response.status_code == 200
        data = response.json()
        assert "company" in data
        assert "corporate_actions" in data
        assert data["company"]["symbol"] == "TCS"

    def test_industry_context_endpoint(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.f6_router import create_f6_router

        app = FastAPI()
        app.include_router(create_f6_router())
        client = TestClient(app)

        response = client.get(
            "/api/v1/companies/TCS/industry-context"
        )
        assert response.status_code == 200
        data = response.json()
        assert "company" in data
        assert "industry_context" in data
        assert data["company"]["symbol"] == "TCS"

    def test_tracking_endpoint(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.f6_router import create_f6_router

        app = FastAPI()
        app.include_router(create_f6_router())
        client = TestClient(app)

        response = client.get(
            "/api/v1/companies/TCS/tracking"
        )
        assert response.status_code == 200
        data = response.json()
        assert "company" in data
        assert "tracking" in data
        assert data["company"]["symbol"] == "TCS"

    def test_unknown_company_returns_error(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.f6_router import create_f6_router
        from src.api.errors import register_api_error_handlers

        app = FastAPI()
        register_api_error_handlers(app)
        app.include_router(create_f6_router())
        client = TestClient(app)

        response = client.get(
            "/api/v1/companies/UNKNOWN/chart-data"
        )
        assert response.status_code == 404

    def test_chart_data_with_as_of(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.f6_router import create_f6_router

        app = FastAPI()
        app.include_router(create_f6_router())
        client = TestClient(app)

        response = client.get(
            "/api/v1/companies/TCS/chart-data",
            params={"as_of": "2025-09-15T00:00:00+00:00"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company"]["symbol"] == "TCS"

    def test_all_endpoints_deterministic(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from src.api.f6_router import create_f6_router

        app = FastAPI()
        app.include_router(create_f6_router())
        client = TestClient(app)

        endpoints = [
            "/api/v1/companies/TCS/chart-data",
            "/api/v1/companies/TCS/news",
            "/api/v1/companies/TCS/corporate-actions",
            "/api/v1/companies/TCS/industry-context",
            "/api/v1/companies/TCS/tracking",
        ]

        for ep in endpoints:
            r1 = client.get(ep)
            r2 = client.get(ep)
            assert r1.status_code == r2.status_code
            assert r1.json() == r2.json()


# ---------------------------------------------------------------------------
# Contract serialization tests
# ---------------------------------------------------------------------------


class TestF6Contracts:
    """Tests for F6 contract models in contracts.py."""

    def test_contract_chart_data_point(self):
        from src.api.contracts import ContractChartDataPoint

        pt = ContractChartDataPoint(
            period_end="2025-06-30",
            value="1200",
            available=True,
            as_of="2025-09-15",
            source="test",
        )
        assert pt.period_end == "2025-06-30"
        assert pt.available is True

    def test_contract_chart_series(self):
        from src.api.contracts import ContractChartSeries

        s = ContractChartSeries(
            metric="revenue",
            label="Revenue",
            unit="CURRENCY",
            category="INCOME",
            data_points=[],
            period_count=0,
            available_count=0,
            missing_count=0,
            source="test",
        )
        assert s.metric == "revenue"
        assert s.unit == "CURRENCY"

    def test_contract_chart_data_set(self):
        from src.api.contracts import ContractChartDataSet

        ds = ContractChartDataSet(
            symbol="TEST",
            as_of="2025-09-15",
            notes=["test"],
        )
        assert ds.symbol == "TEST"
        assert ds.notes == ["test"]

    def test_contract_company_news_item(self):
        from src.api.contracts import ContractCompanyNewsItem

        item = ContractCompanyNewsItem(
            news_id="n1",
            symbol="TEST",
            headline="Headline",
            summary="Summary",
            category="EARNINGS",
            direction="POSITIVE",
            source_name="source",
        )
        assert item.news_id == "n1"
        assert item.category == "EARNINGS"

    def test_contract_corporate_action_item(self):
        from src.api.contracts import (
            ContractCorporateActionItem,
        )

        item = ContractCorporateActionItem(
            action_id="ca1",
            symbol="TEST",
            action_type="BUYBACK",
            title="Buyback",
            description="Buyback",
        )
        assert item.action_id == "ca1"
        assert item.action_type == "BUYBACK"

    def test_contract_industry_characteristic(self):
        from src.api.contracts import (
            ContractIndustryCharacteristic,
        )

        c = ContractIndustryCharacteristic(
            name="test",
            description="desc",
            relevance="HIGH",
        )
        assert c.name == "test"
        assert c.relevance == "HIGH"

    def test_contract_tracking_change(self):
        from src.api.contracts import ContractTrackingChange

        tc = ContractTrackingChange(
            change_id="tc1",
            symbol="TEST",
            domain="FINANCIAL",
            severity="NOTABLE",
            title="Revenue growth",
            description="Revenue increased",
        )
        assert tc.change_id == "tc1"
        assert tc.domain == "FINANCIAL"


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_chart_data_single_metric(self, as_of_dt):
        snapshots = [
            _snap(
                "TEST",
                date(2025, 6, 30),
                revenue=Decimal("1000"),
            )
        ]
        ds = build_chart_data(snapshots, "TEST", as_of_dt)
        assert ds.total_metrics > 0

    def test_chart_data_zero_values(self, as_of_dt):
        snapshots = [
            _snap(
                "TEST",
                date(2025, 6, 30),
                revenue=Decimal("0"),
                net_profit=Decimal("0"),
            )
        ]
        ds = build_chart_data(snapshots, "TEST", as_of_dt)
        assert ds.total_metrics > 0

    def test_news_item_with_all_fields(self, as_of_dt):
        item = CompanyNewsItem(
            news_id="n1",
            symbol="TEST",
            headline="Headline",
            summary="Summary",
            category=NewsCategory.EARNINGS,
            direction=NewsDirection.POSITIVE,
            source_name="source",
            source_url="https://test.com",
            source_type="NEWS",
            published_at=datetime(2025, 9, 1, tzinfo=TZ),
            available_at=datetime(2025, 9, 1, tzinfo=TZ),
            event_date=date(2025, 8, 31),
            related_metrics=("revenue", "net_profit"),
            evidence_refs=("ev-1", "ev-2"),
            as_of=as_of_dt,
            provenance_id="prov-001",
        )
        assert item.event_date == date(2025, 8, 31)
        assert len(item.related_metrics) == 2
        assert len(item.evidence_refs) == 2

    def test_corporate_action_item_with_dates(self):
        item = CorporateActionItem(
            action_id="ca1",
            symbol="TEST",
            action_type=CorporateActionType.DIVIDEND,
            title="Dividend",
            description="Dividend",
            announcement_date=date(2025, 9, 1),
            effective_date=date(2025, 9, 15),
            record_date=date(2025, 9, 10),
            value="10",
            ratio="1:1",
        )
        assert item.announcement_date == date(2025, 9, 1)
        assert item.value == "10"
        assert item.ratio == "1:1"

    def test_tracking_multiple_changes(self, as_of_dt):
        snapshots = [
            _snap(
                "TEST",
                date(2025, 3, 31),
                revenue=Decimal("1000"),
                net_profit=Decimal("100"),
                total_assets=Decimal("5000"),
                total_debt=Decimal("2000"),
                cash=Decimal("500"),
                operating_cf=Decimal("150"),
            ),
            _snap(
                "TEST",
                date(2025, 6, 30),
                revenue=Decimal("1200"),
                net_profit=Decimal("120"),
                total_assets=Decimal("5500"),
                total_debt=Decimal("1800"),
                cash=Decimal("600"),
                operating_cf=Decimal("180"),
            ),
            _snap(
                "TEST",
                date(2025, 9, 30),
                revenue=Decimal("1400"),
                net_profit=Decimal("140"),
                total_assets=Decimal("6000"),
                total_debt=Decimal("1600"),
                cash=Decimal("700"),
                operating_cf=Decimal("210"),
            ),
        ]
        result = build_tracking_result(
            snapshots, "TEST", as_of_dt
        )
        assert result.change_count > 0
        assert result.significant_count >= 0
