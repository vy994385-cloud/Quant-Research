"""Tests for the deep continuous company research API endpoints."""

from __future__ import annotations

from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.errors import register_api_error_handlers
from src.api.recorded_research import (
    RecordedCompanyResearchService,
)
from src.api.research_router import create_research_router

VERIFIED_COMPANIES = (
    "TCS",
    "RELIANCE",
    "INFY",
    "HDFCBANK",
    "SUNPHARMA",
    "M&M",
)

DEFAULT_AS_OF_ISO = "2026-08-10T12:00:00+00:00"


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    archive_root = tmp_path_factory.mktemp(
        "deep-continuous-archive"
    )
    return RecordedCompanyResearchService(archive_root=archive_root)


@pytest.fixture(scope="module")
def client(service):
    app = FastAPI()
    register_api_error_handlers(app)
    app.include_router(
        create_research_router(service=service)
    )
    return TestClient(app)


# ── deep financial insights ───────────────────────────────────────


def test_deep_financial_insights_route_exposed(client):
    resp = client.get(
        "/api/v1/companies/TCS/deep-financial-insights"
    )
    assert resp.status_code == 200
    assert resp.json()["company"]["symbol"] == "TCS"


def test_tcs_deep_financial_has_series_and_observations(client):
    resp = client.get(
        "/api/v1/companies/TCS/deep-financial-insights"
    )
    payload = resp.json()

    assert payload["company"]["as_of"] == DEFAULT_AS_OF_ISO

    dfi = payload["deep_financial_insights"]
    assert dfi is not None
    assert dfi["symbol"] == "TCS"
    assert dfi["as_of"] == DEFAULT_AS_OF_ISO
    assert len(dfi["series"]) >= 1
    assert len(dfi["observations"]) >= 10

    for obs in dfi["observations"]:
        assert obs["observation_id"]
        assert obs["observation_type"] in {
            "REPORTED",
            "DERIVED",
            "UNAVAILABLE",
        }
        assert obs["period_type"]
        assert obs["consolidation"]
        assert obs["derivation"]


def test_deep_financial_observations_are_pit_safe(client):
    resp = client.get(
        "/api/v1/companies/TCS/deep-financial-insights",
        params={"as_of": "2026-04-01T00:00:00+00:00"},
    )
    payload = resp.json()
    dfi = payload["deep_financial_insights"]

    # At 2026-04-01, FY2026 annual (ended 2026-03-31) is knowable.
    assert len(dfi["series"]) >= 1

    for series in dfi["series"]:
        assert series["period_count"] >= 1

    as_of = payload["company"]["as_of"]
    for obs in dfi["observations"]:
        assert obs["period_end"] <= as_of


def test_deep_financial_deterministic(client):
    a = client.get(
        "/api/v1/companies/TCS/deep-financial-insights"
    ).json()
    b = client.get(
        "/api/v1/companies/TCS/deep-financial-insights"
    ).json()
    assert a == b


def test_earlier_as_of_fewer_periods(client):
    default = client.get(
        "/api/v1/companies/TCS/deep-financial-insights"
    ).json()
    earlier = client.get(
        "/api/v1/companies/TCS/deep-financial-insights",
        params={"as_of": "2026-04-01T00:00:00+00:00"},
    ).json()

    default_dfi = default["deep_financial_insights"]
    earlier_dfi = earlier["deep_financial_insights"]

    default_obs = len(default_dfi["observations"])
    earlier_obs = len(earlier_dfi["observations"])

    # At 2026-04-01, FY2026 annual is knowable but intel feed
    # items from Q4 FY2027 are not yet available.
    assert earlier_obs <= default_obs


@pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
def test_every_company_has_deep_financial(client, symbol):
    resp = client.get(
        f"/api/v1/companies/{symbol}/deep-financial-insights"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["company"]["symbol"] == symbol

    dfi = payload["deep_financial_insights"]
    assert dfi is not None
    assert len(dfi["series"]) >= 1
    assert len(dfi["observations"]) >= 1


def test_unknown_company_deep_financial_returns_404(client):
    resp = client.get(
        "/api/v1/companies/UNKNOWN/deep-financial-insights"
    )
    assert resp.status_code == 404


def test_naive_as_of_deep_financial_returns_400(client):
    resp = client.get(
        "/api/v1/companies/TCS/deep-financial-insights",
        params={"as_of": "2026-08-10T12:00:00"},
    )
    assert resp.status_code == 400


# ── source statuses ───────────────────────────────────────────────


def test_source_statuses_route_exposed(client):
    resp = client.get(
        "/api/v1/companies/TCS/source-statuses"
    )
    assert resp.status_code == 200
    assert resp.json()["company"]["symbol"] == "TCS"


def test_tcs_source_statuses_structure(client):
    resp = client.get(
        "/api/v1/companies/TCS/source-statuses"
    )
    payload = resp.json()

    statuses = payload["source_statuses"]
    assert isinstance(statuses, list)
    assert len(statuses) >= 1

    for s in statuses:
        assert s["source_name"]
        assert s["source_type"]
        assert s["item_count"] >= 1
        assert isinstance(s["categories"], list)
        assert isinstance(s["stale"], bool)
        assert isinstance(s["provenance_completeness"], bool)


def test_source_statuses_pit_safe(client):
    resp = client.get(
        "/api/v1/companies/TCS/source-statuses",
        params={"as_of": "2026-04-01T00:00:00+00:00"},
    )
    payload = resp.json()

    assert payload["company"]["as_of"] == (
        "2026-04-01T00:00:00+00:00"
    )

    # At 2026-04-01, intel feed items are not yet available,
    # so sources are fewer or empty.
    statuses = payload["source_statuses"]
    assert isinstance(statuses, list)


def test_source_statuses_deterministic(client):
    a = client.get(
        "/api/v1/companies/TCS/source-statuses"
    ).json()
    b = client.get(
        "/api/v1/companies/TCS/source-statuses"
    ).json()
    assert a == b


@pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
def test_every_company_has_source_statuses(client, symbol):
    resp = client.get(
        f"/api/v1/companies/{symbol}/source-statuses"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["company"]["symbol"] == symbol
    assert isinstance(payload["source_statuses"], list)


def test_unknown_company_source_statuses_returns_404(client):
    resp = client.get(
        "/api/v1/companies/UNKNOWN/source-statuses"
    )
    assert resp.status_code == 404


def test_naive_as_of_source_statuses_returns_400(client):
    resp = client.get(
        "/api/v1/companies/TCS/source-statuses",
        params={"as_of": "2026-08-10T12:00:00"},
    )
    assert resp.status_code == 400


# ── hidden information ────────────────────────────────────────────


def test_hidden_information_route_exposed(client):
    resp = client.get(
        "/api/v1/companies/TCS/hidden-information"
    )
    assert resp.status_code == 200
    assert resp.json()["company"]["symbol"] == "TCS"


def test_tcs_hidden_information_structure(client):
    resp = client.get(
        "/api/v1/companies/TCS/hidden-information"
    )
    payload = resp.json()

    hidden = payload["hidden_information"]
    assert hidden is not None
    assert hidden["symbol"] == "TCS"
    assert hidden["as_of"] == DEFAULT_AS_OF_ISO
    assert isinstance(hidden["observations"], list)
    assert isinstance(hidden["notes"], list)

    for obs in hidden["observations"]:
        assert obs["observation_id"]
        assert obs["label"]
        assert obs["semantic_category"]
        assert obs["description"]
        assert obs["derivation"]
        assert isinstance(obs["source_ids"], list)
        assert isinstance(obs["provenance_ids"], list)
        assert isinstance(obs["related_item_ids"], list)
        assert obs["as_of"]


def test_hidden_information_pit_safe(client):
    resp = client.get(
        "/api/v1/companies/TCS/hidden-information",
        params={"as_of": "2026-04-01T00:00:00+00:00"},
    )
    payload = resp.json()

    hidden = payload["hidden_information"]
    assert hidden is not None

    for obs in hidden["observations"]:
        assert obs["as_of"] <= payload["as_of"]


def test_hidden_information_deterministic(client):
    a = client.get(
        "/api/v1/companies/TCS/hidden-information"
    ).json()
    b = client.get(
        "/api/v1/companies/TCS/hidden-information"
    ).json()
    assert a == b


@pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
def test_every_company_has_hidden_information(client, symbol):
    resp = client.get(
        f"/api/v1/companies/{symbol}/hidden-information"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["company"]["symbol"] == symbol
    assert payload["hidden_information"] is not None


def test_unknown_company_hidden_information_returns_404(client):
    resp = client.get(
        "/api/v1/companies/UNKNOWN/hidden-information"
    )
    assert resp.status_code == 404


def test_naive_as_of_hidden_information_returns_400(client):
    resp = client.get(
        "/api/v1/companies/TCS/hidden-information",
        params={"as_of": "2026-08-10T12:00:00"},
    )
    assert resp.status_code == 400


# ── future evidence leakage across all new endpoints ─────────────


def _no_future_observations(items: list[dict], as_of: str) -> None:
    for obs in items:
        available = obs.get("available_at")
        if available:
            assert available <= as_of, (
                f"future observation: {obs.get('observation_id', obs.get('item_id', 'unknown'))}"
            )


def test_no_future_evidence_in_deep_financial(client):
    resp = client.get(
        "/api/v1/companies/TCS/deep-financial-insights"
    )
    payload = resp.json()
    as_of = payload["company"]["as_of"]

    for obs in payload["deep_financial_insights"]["observations"]:
        if obs.get("published_at"):
            assert obs["published_at"] <= as_of


def test_no_future_evidence_in_hidden_information(client):
    resp = client.get(
        "/api/v1/companies/TCS/hidden-information"
    )
    payload = resp.json()
    as_of = payload["company"]["as_of"]

    for obs in payload["hidden_information"]["observations"]:
        assert obs["as_of"] <= as_of


# ── hidden info is strictly evidence-backed ───────────────────────


def test_hidden_observations_reference_provenance(client):
    resp = client.get(
        "/api/v1/companies/TCS/hidden-information"
    )
    payload = resp.json()

    for obs in payload["hidden_information"]["observations"]:
        has_evidence = (
            obs["source_ids"] or obs["provenance_ids"] or obs["related_item_ids"]
        )
        # Every hidden observation must be traceable to something.
        assert has_evidence or obs["derivation"], (
            f"hidden observation {obs['observation_id']} "
            "lacks evidence traceability"
        )


# ── intelligence endpoint surfaces new fields ─────────────────────


def test_intelligence_surfaces_deep_financial(client):
    resp = client.get("/api/v1/companies/TCS/intelligence")
    payload = resp.json()

    assert "deep_financial_insights" in payload
    assert "source_statuses" in payload
    assert "hidden_information" in payload
    assert "provider_failures" in payload
    assert isinstance(payload["provider_failures"], list)


def test_intelligence_changes_have_new_fields(client):
    resp = client.get("/api/v1/companies/TCS/intelligence")
    payload = resp.json()

    for change in payload["changes"]:
        assert "previous_title" in change
        assert "semantic_category" in change
        assert "intel_category" in change
        assert "event_type" in change
        assert "published_at" in change
        assert "available_at" in change
