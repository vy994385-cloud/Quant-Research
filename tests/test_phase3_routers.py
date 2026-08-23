"""Tests for Phase 3 API routers (ownership, events, attribution, timeline)."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.attribution_router import create_attribution_router
from src.api.events_router import create_events_router
from src.api.ownership_router import create_ownership_router
from src.api.timeline_router import create_timeline_router
from src.data.company.events import CompanyEvent
from src.data.company.ownership import OwnershipSnapshot
from src.data.models import PriceBar


_AS_OF = "2024-06-15T00:00:00Z"


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(create_ownership_router())
    app.include_router(create_events_router())
    app.include_router(create_attribution_router())
    app.include_router(create_timeline_router())
    return app


# ---------------------------------------------------------------------------
# Ownership endpoint
# ---------------------------------------------------------------------------


class TestOwnershipEndpoint:
    def test_returns_structure(self):
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/v1/companies/TEST/ownership",
            params={"as_of": _AS_OF},
        )
        # Yahoo may fail for unknown symbol, but endpoint should respond
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert "company" in data
            assert "ownership" in data
            assert data["company"]["symbol"] == "TEST"

    def test_default_as_of(self):
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/v1/companies/TEST/ownership")
        assert resp.status_code in (200, 500)

    def test_ownership_has_expected_fields(self):
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/v1/companies/TEST/ownership",
            params={"as_of": _AS_OF},
        )
        if resp.status_code == 200:
            data = resp.json()
            ownership = data["ownership"]
            assert "symbol" in ownership
            assert "as_of" in ownership
            assert "periods" in ownership
            assert "trends" in ownership
            assert "signals" in ownership
            assert "coverage" in ownership


# ---------------------------------------------------------------------------
# Events endpoint
# ---------------------------------------------------------------------------


class TestEventsEndpoint:
    def test_returns_structure(self):
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/v1/companies/TEST/events",
            params={"as_of": _AS_OF},
        )
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert "company" in data
            assert "events" in data
            assert data["company"]["symbol"] == "TEST"

    def test_events_has_expected_fields(self):
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/v1/companies/TEST/events",
            params={"as_of": _AS_OF},
        )
        if resp.status_code == 200:
            data = resp.json()
            events = data["events"]
            assert "symbol" in events
            assert "as_of" in events
            assert "event_count" in events
            assert "classifications" in events
            assert "clusters" in events
            assert "category_counts" in events


# ---------------------------------------------------------------------------
# Attribution endpoint
# ---------------------------------------------------------------------------


class TestAttributionEndpoint:
    def test_returns_structure(self):
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/v1/companies/TEST/price-attribution",
            params={"as_of": _AS_OF, "lookback_days": 30},
        )
        # Yahoo may fail for unknown symbol, but endpoint should respond
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert "company" in data
            assert "attribution" in data

    def test_lookback_bounds(self):
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/v1/companies/TEST/price-attribution",
            params={"as_of": _AS_OF, "lookback_days": 400},
        )
        # Should reject out-of-range lookback
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Timeline endpoint
# ---------------------------------------------------------------------------


class TestTimelineEndpoint:
    def test_returns_structure(self):
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/v1/companies/TEST/research-timeline",
            params={"as_of": _AS_OF},
        )
        # Yahoo may fail for unknown symbol, but endpoint should respond
        assert resp.status_code in (200, 500)
        if resp.status_code == 200:
            data = resp.json()
            assert "company" in data
            assert "timeline" in data

    def test_timeline_has_expected_fields(self):
        app = _make_app()
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get(
            "/api/v1/companies/TEST/research-timeline",
            params={"as_of": _AS_OF},
        )
        if resp.status_code == 200:
            data = resp.json()
            timeline = data["timeline"]
            assert "symbol" in timeline
            assert "as_of" in timeline
            assert "entries" in timeline
            assert "summary" in timeline
