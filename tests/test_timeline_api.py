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
    archive_root = tmp_path_factory.mktemp("timeline-contract-archive")

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


def test_main_app_exposes_timeline_route():
    response = TestClient(api_main.app).get(
        "/api/v1/companies/TCS/timeline"
    )

    assert response.status_code == 200
    assert response.json()["company"]["symbol"] == "TCS"


def test_tcs_timeline_contract_is_complete(client):
    response = client.get("/api/v1/companies/TCS/timeline")

    assert response.status_code == 200
    payload = response.json()

    assert payload["company"]["symbol"] == "TCS"
    assert payload["company"]["company_name"]
    assert payload["company"]["sector"] == "information technology"
    assert payload["company"]["as_of"] == DEFAULT_AS_OF_ISO

    timeline = payload["timeline"]

    assert timeline["company"] == "TCS"
    assert timeline["as_of"] == DEFAULT_AS_OF_ISO
    assert timeline["entries"]
    assert timeline["latest_at"]
    assert timeline["earliest_at"]
    assert timeline["counts"]

    earliest = datetime.fromisoformat(timeline["earliest_at"])
    latest = datetime.fromisoformat(timeline["latest_at"])
    assert earliest <= latest


def test_timeline_entries_are_chronological(client):
    response = client.get("/api/v1/companies/TCS/timeline")

    assert response.status_code == 200
    entries = response.json()["timeline"]["entries"]

    stamps = [
        entry["timeline_at"]
        for entry in entries
        if entry["timeline_at"]
    ]

    assert stamps == sorted(stamps)


def test_timeline_entries_never_leak_future_evidence(client):
    response = client.get(
        "/api/v1/companies/TCS/timeline",
        params={"as_of": "2026-04-01T00:00:00+00:00"},
    )

    assert response.status_code == 200
    timeline = response.json()["timeline"]

    assert timeline["as_of"] == "2026-04-01T00:00:00+00:00"

    for entry in timeline["entries"]:
        available = datetime.fromisoformat(entry["available_at"])
        assert available <= datetime.fromisoformat(
            timeline["as_of"]
        )


def test_timeline_research_status_is_coherent(client):
    response = client.get(
        "/api/v1/companies/TCS/research"
    )

    assert response.status_code == 200
    payload = response.json()

    timeline = payload["timeline"]
    status = payload["research_status"]

    assert timeline is not None
    assert status is not None
    assert status["company"] == "TCS"
    assert status["freshness"]["stale"] in (True, False)
    assert status["coverage"]["item_count"] == len(
        timeline["entries"]
    )
    assert "BUSINESS_NEWS" in {
        entry["intel_category"]
        for entry in timeline["entries"]
    }


@pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
def test_every_verified_company_has_timeline(client, symbol):
    response = client.get(f"/api/v1/companies/{symbol}/timeline")

    assert response.status_code == 200
    timeline = response.json()["timeline"]

    assert timeline["company"] == symbol
    assert timeline["entries"]
    assert all(
        entry["symbol"] == symbol
        for entry in timeline["entries"]
    )


def test_timeline_unknown_company_returns_404(client):
    response = client.get(
        "/api/v1/companies/UNKNOWN/timeline"
    )

    assert response.status_code == 404


def test_timeline_naive_as_of_returns_400(client):
    response = client.get(
        "/api/v1/companies/TCS/timeline",
        params={"as_of": "2026-08-10T12:00:00"},
    )

    assert response.status_code == 400


def test_timeline_response_is_deterministic(client):
    first = client.get(
        "/api/v1/companies/TCS/timeline"
    ).json()
    second = client.get(
        "/api/v1/companies/TCS/timeline"
    ).json()

    assert first == second
