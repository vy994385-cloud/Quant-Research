from __future__ import annotations

from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import main as api_main
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
        "intelligence-contract-archive"
    )

    return RecordedCompanyResearchService(
        archive_root=archive_root,
    )


@pytest.fixture(scope="module")
def client(service):
    app = FastAPI()

    register_api_error_handlers(app)
    app.include_router(
        create_research_router(service=service)
    )

    return TestClient(app)


def _all_items(payload: dict) -> list[dict]:
    return [
        *payload["business_events"],
        *payload["management_commentary"],
        *payload["risk_intelligence"],
        *payload["indirect_intelligence"],
        *payload["financial_intelligence_items"],
        *payload["other_intelligence"],
    ]


def _assert_no_future_items(payload: dict) -> None:
    as_of = payload["as_of"]

    future = [
        item
        for item in _all_items(payload)
        if item["available_at"]
        and item["available_at"] > as_of
    ]

    assert future == []


def test_main_app_exposes_intelligence_route():
    response = TestClient(api_main.app).get(
        "/api/v1/companies/TCS/intelligence"
    )

    assert response.status_code == 200
    assert response.json()["company"]["symbol"] == "TCS"


def test_tcs_intelligence_contract_is_complete(client):
    response = client.get("/api/v1/companies/TCS/intelligence")

    assert response.status_code == 200
    payload = response.json()

    assert payload["company"]["symbol"] == "TCS"
    assert payload["company"]["company_name"]
    assert payload["company"]["sector"] == (
        "information technology"
    )
    assert payload["company"]["as_of"] == DEFAULT_AS_OF_ISO
    assert payload["as_of"] == DEFAULT_AS_OF_ISO

    assert payload["item_count"] >= 20

    financial = payload["financial_intelligence"]
    assert financial is not None
    assert financial["period_count"] == 4
    assert financial["annual_count"] == 4
    assert financial["latest_period_end"] == "2026-03-31"

    assert len(payload["business_events"]) >= 1
    assert len(payload["management_commentary"]) >= 1
    assert len(payload["risk_intelligence"]) >= 1

    assert payload["coverage"]["BUSINESS_EVENT"] == (
        len(payload["business_events"])
    )
    assert payload["semantic_summary"]["MANAGEMENT_COMMENTARY"] == (
        len(payload["management_commentary"])
    )

    _assert_no_future_items(payload)


def test_tcs_intelligence_surfaces_evidence_conflict(client):
    response = client.get("/api/v1/companies/TCS/intelligence")

    assert response.status_code == 200
    payload = response.json()

    conflicts = payload["conflicts"]

    assert len(conflicts) >= 1

    conflict = conflicts[0]

    assert conflict["topic"]
    assert conflict["description"]
    assert "no side is auto-concluded" in conflict["description"]
    assert conflict["first"]["verification_status"]
    assert conflict["second"]["verification_status"]
    assert conflict["first"]["source_name"]
    assert conflict["second"]["source_name"]

    assert any(
        conflict["management_involved"]
        for conflict in conflicts
    )


def test_management_commentary_is_never_fact(client):
    response = client.get("/api/v1/companies/TCS/intelligence")

    assert response.status_code == 200
    payload = response.json()

    for item in payload["management_commentary"]:
        assert (
            item["semantic_category"]
            == "MANAGEMENT_COMMENTARY"
        )

    for item in _all_items(payload):
        assert item["semantic_category"] not in {
            "CONCLUSION",
        }


@pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
def test_every_verified_company_has_intelligence(client, symbol):
    response = client.get(
        f"/api/v1/companies/{symbol}/intelligence"
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["company"]["symbol"] == symbol
    assert payload["item_count"] >= 5
    assert payload["financial_intelligence"] is not None
    assert payload["source_ids"]

    _assert_no_future_items(payload)


def test_unknown_company_returns_404(client):
    response = client.get(
        "/api/v1/companies/UNKNOWN/intelligence"
    )

    assert response.status_code == 404


def test_naive_as_of_returns_400(client):
    response = client.get(
        "/api/v1/companies/TCS/intelligence",
        params={"as_of": "2026-08-10T12:00:00"},
    )

    assert response.status_code == 400


def test_date_only_as_of_is_accepted(client):
    response = client.get(
        "/api/v1/companies/TCS/intelligence",
        params={"as_of": "2026-08-10"},
    )

    assert response.status_code == 200
    assert response.json()["as_of"] == (
        "2026-08-10T00:00:00+00:00"
    )


def test_earlier_as_of_is_point_in_time_pure(client):
    default = client.get(
        "/api/v1/companies/TCS/intelligence"
    ).json()

    earlier = client.get(
        "/api/v1/companies/TCS/intelligence",
        params={"as_of": "2026-04-01T00:00:00+00:00"},
    ).json()

    assert earlier["as_of"] == "2026-04-01T00:00:00+00:00"

    # The annual period ending 2026-03-31 is knowable at 2026-04-01,
    # so four reporting periods and their derived metrics survive.
    assert earlier["financial_intelligence"]["period_count"] == 4
    assert earlier["item_count"] == 8
    assert earlier["business_events"] == []
    assert earlier["management_commentary"] == []
    assert earlier["risk_intelligence"] == []
    assert earlier["indirect_intelligence"] == []
    assert earlier["other_intelligence"] == []

    # Intel feed items were only knowable from July 2026 onwards.
    assert default["item_count"] > earlier["item_count"]
    assert len(default["business_events"]) > 0


def test_intelligence_response_is_deterministic(client):
    first = client.get(
        "/api/v1/companies/TCS/intelligence"
    ).json()
    second = client.get(
        "/api/v1/companies/TCS/intelligence"
    ).json()

    assert first == second


def test_no_future_items_at_custom_as_of(client):
    response = client.get(
        "/api/v1/companies/TCS/intelligence",
        params={"as_of": "2026-08-10T00:00:00+00:00"},
    )

    assert response.status_code == 200
    payload = response.json()

    _assert_no_future_items(payload)

    for item in _all_items(payload):
        available = datetime.fromisoformat(item["available_at"])
        assert available <= datetime.fromisoformat(payload["as_of"])
