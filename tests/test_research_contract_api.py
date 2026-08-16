from datetime import datetime
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import main as api_main
from src.api.errors import register_api_error_handlers
from src.api.recorded_research import (
    RecordedCompanyResearchService,
)
from src.api.research_router import create_research_router
from src.api.serializers import research_contract
from src.verification.real_data import (
    FailedSourcesProvider,
    MissingSourcesProvider,
    run_source_scenario,
)

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
        "research-contract-archive"
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


def _all_evidence(payload: dict) -> list[dict]:
    return [
        *payload["evidence"]["positive"],
        *payload["evidence"]["negative"],
        *payload["evidence"]["neutral"],
    ]


def _assert_no_future_evidence(payload: dict) -> None:
    as_of = payload["point_in_time"]["effective_as_of"]

    future = [
        item
        for item in _all_evidence(payload)
        if item["observation_at"]
        and item["observation_at"] > as_of
    ]

    assert future == []
    assert (
        payload["point_in_time"]["pit_checks_passed"]
        is True
    )


# ---------------------------------------------------------------------
# Company research contract
# ---------------------------------------------------------------------


def test_main_app_exposes_contract_routes():
    response = TestClient(api_main.app).get(
        "/api/v1/companies"
    )

    assert response.status_code == 200
    assert response.json()["count"] == len(VERIFIED_COMPANIES)


def test_tcs_research_contract_is_complete(client):
    response = client.get("/api/v1/companies/TCS/research")

    assert response.status_code == 200
    payload = response.json()

    assert payload["company"]["symbol"] == "TCS"
    assert payload["company"]["sector"] == (
        "information technology"
    )
    assert payload["company"]["as_of"] == DEFAULT_AS_OF_ISO

    assert payload["assessment"]["conclusion"] in {
        "POSITIVE",
        "NEGATIVE",
        "MIXED",
        "NEUTRAL",
        "INSUFFICIENT_EVIDENCE",
    }
    assert payload["assessment"]["thesis"]
    assert payload["assessment"]["research_ready"] is True

    expected_sections = {
        "business_quality",
        "financial_quality",
        "transformation",
        "capital_allocation",
        "competitive_position",
        "innovation",
        "future_technology",
        "customer_intelligence",
        "management_intelligence",
        "market_intelligence",
        "risks_anomalies",
        "unknown_missing",
    }

    assert expected_sections.issubset(
        payload["intelligence"]
    )

    for section_name in expected_sections - {
        "unknown_missing"
    }:
        section = payload["intelligence"][section_name]
        assert section["status"] in {
            "SUPPORTED",
            "CONTRADICTED",
            "MIXED",
            "PARTIAL",
            "UNKNOWN",
        }

    assert payload["evidence"]["positive"]
    assert payload["evidence"]["negative"]
    assert payload["evidence"]["neutral"]

    assert payload["narrative"]["thesis"]
    assert payload["signals"]

    assert payload["data_quality"]["market_validation_status"] in {
        "VALID",
        "NEEDS_REVIEW",
    }
    assert (
        payload["data_quality"]["market_accepted_records"]
        >= 200
    )
    assert (
        payload["data_quality"]["financial_data_missing"]
        is False
    )

    assert payload["provenance"]["market"]["source"]
    assert payload["provenance"]["financials"]["source"]
    assert payload["provenance"]["archived_sources"]

    assert set(payload["rankings"]) == {
        "intraday",
        "swing",
        "long_term",
    }
    assert payload["research_score"]["total"]

    assert payload["timeline"]["company"] == "TCS"
    assert payload["timeline"]["entries"]
    assert payload["timeline"]["counts"]

    status = payload["research_status"]

    assert status["company"] == "TCS"
    assert status["freshness"]["stale"] in (True, False)
    assert status["coverage"]["item_count"] == len(
        payload["timeline"]["entries"]
    )
    assert status["quality"]["conflict_count"] >= 0


def test_research_timeline_is_point_in_time_pure(client):
    response = client.get(
        "/api/v1/companies/TCS/research"
        "?as_of=2026-04-01"
    )

    assert response.status_code == 200
    payload = response.json()

    timeline = payload["timeline"]
    status = payload["research_status"]

    assert timeline is not None
    assert status is not None

    assert timeline["as_of"] == "2026-04-01T00:00:00+00:00"

    for entry in timeline["entries"]:
        available = datetime.fromisoformat(entry["available_at"])
        assert available <= datetime.fromisoformat(
            timeline["as_of"]
        )

    assert status["coverage"]["item_count"] == len(
        timeline["entries"]
    )


@pytest.mark.parametrize("company", VERIFIED_COMPANIES)
def test_research_for_every_verified_company(client, company):
    response = client.get(
        f"/api/v1/companies/{company}/research"
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["company"]["symbol"] == company
    assert payload["company"]["company_name"]
    assert payload["company"]["sector"]
    assert payload["assessment"]["research_ready"] is True

    _assert_no_future_evidence(payload)


def test_research_with_explicit_as_of(client):
    response = client.get(
        "/api/v1/companies/TCS/research"
        "?as_of=2026-08-01T00:00:00Z"
    )

    assert response.status_code == 200
    payload = response.json()

    assert (
        payload["point_in_time"]["effective_as_of"]
        == "2026-08-01T00:00:00+00:00"
    )
    assert (
        payload["point_in_time"]["as_of"]
        == "2026-08-01T00:00:00+00:00"
    )

    _assert_no_future_evidence(payload)


def test_research_with_date_only_as_of_uses_utc_midnight(client):
    response = client.get(
        "/api/v1/companies/TCS/research?as_of=2026-08-01"
    )

    assert response.status_code == 200
    payload = response.json()

    assert (
        payload["point_in_time"]["effective_as_of"]
        == "2026-08-01T00:00:00+00:00"
    )


def test_research_as_of_excludes_later_sources(client):
    default = client.get(
        "/api/v1/companies/TCS/research"
    ).json()
    earlier = client.get(
        "/api/v1/companies/TCS/research"
        "?as_of=2026-04-01"
    ).json()

    assert (
        default["point_in_time"]["sources_accepted"]
        > earlier["point_in_time"]["sources_accepted"]
    )
    assert (
        earlier["point_in_time"]["market_as_of"]
        == "2026-04-01"
    )

    _assert_no_future_evidence(earlier)


def test_research_is_deterministic_across_requests(client):
    first = client.get(
        "/api/v1/companies/HDFCBANK/research"
    )
    second = client.get(
        "/api/v1/companies/HDFCBANK/research"
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


# ---------------------------------------------------------------------
# Structured error contract
# ---------------------------------------------------------------------


def test_unknown_company_error(client):
    response = client.get(
        "/api/v1/companies/NONEXISTENT/research"
    )

    assert response.status_code == 404

    error = response.json()["error"]

    assert error["code"] == "unknown_company"
    assert error["message"]
    assert error["details"]["symbol"] == "NONEXISTENT"
    assert set(VERIFIED_COMPANIES).issubset(
        set(error["details"]["supported"])
    )

    assert "Traceback" not in response.text


def test_invalid_as_of_format_error(client):
    response = client.get(
        "/api/v1/companies/TCS/research?as_of=not-a-date"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_as_of"
    assert "Traceback" not in response.text


def test_naive_as_of_rejected(client):
    response = client.get(
        "/api/v1/companies/TCS/research"
        "?as_of=2026-08-01T12:00:00"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_as_of"


def test_unavailable_research_data_error(client):
    response = client.get(
        "/api/v1/companies/TCS/research?as_of=2020-01-01"
    )

    assert response.status_code == 404
    error = response.json()["error"]

    assert error["code"] == "research_data_unavailable"
    assert error["details"]["symbol"] == "TCS"
    assert "Traceback" not in response.text


def test_unknown_symbol_in_universe_error(client):
    response = client.get(
        "/api/v1/rankings/LONG_TERM?symbols=TCS,UNKNOWN"
    )

    assert response.status_code == 404
    assert (
        response.json()["error"]["code"]
        == "unknown_company"
    )


# ---------------------------------------------------------------------
# Point-in-time leak prevention through serialization
# ---------------------------------------------------------------------


def test_future_source_cannot_leak_through_api_serialization(
    service,
):
    result = service.run(
        "RELIANCE",
        include_future_sources=True,
    )

    # The future-dated candidate was discovered but rejected.
    assert (
        result.acquisition.sources_discovered
        > result.acquisition.sources_accepted
    )
    assert result.pit_checks["future_source_rejected"] is True
    assert (
        result.pit_checks["accepted_sources_known_at_as_of"]
        is True
    )

    payload = research_contract(
        result,
        company_name="Reliance Industries",
    )

    assert (
        payload["point_in_time"]["pit_checks_passed"]
        is True
    )
    assert payload["point_in_time"]["sources_rejected"] >= 1

    _assert_no_future_evidence(payload)


def test_naive_and_future_evidence_never_serialized(client):
    for company in VERIFIED_COMPANIES:
        response = client.get(
            f"/api/v1/companies/{company}/research"
        )

        assert response.status_code == 200
        payload = response.json()

        _assert_no_future_evidence(payload)

        for item in _all_evidence(payload):
            assert item["observation_at"]
            assert item["observation_at"].endswith("+00:00")


def test_provenance_survives_api_serialization(client):
    payload = client.get(
        "/api/v1/companies/SUNPHARMA/research"
    ).json()

    provenance = payload["provenance"]

    assert provenance["market"]["dataset_id"] == (
        "yahoo_finance_chart"
    )
    assert provenance["financials"]["dataset_id"] == (
        "yahoo_finance_fundamentals"
    )

    archived = set(provenance["archived_sources"])
    dataset_level = {
        provenance["market"]["source"],
        provenance["market"]["dataset_id"],
        provenance["financials"]["source"],
        provenance["financials"]["dataset_id"],
    }

    assert archived

    for item in _all_evidence(payload):
        for source_id in item["source_ids"]:
            # Every evidence item resolves to a source that the
            # response accounts for, either as an archived record
            # or as one of the dataset-level market/financial
            # provenance records.
            assert (
                source_id in archived
                or source_id in dataset_level
            )

    assert provenance["market"]["retrieved_at"]
    assert provenance["financials"]["available_at"]


# ---------------------------------------------------------------------
# Degraded / missing source behavior
# ---------------------------------------------------------------------


def test_missing_sources_are_surfaced_in_contract(
    tmp_path,
    service,
):
    result = run_source_scenario(
        company="INFY",
        source_provider=MissingSourcesProvider(),
        archive_root=tmp_path / "degraded-archive",
    )

    payload = research_contract(
        result,
        company_name="Infosys",
    )

    assert (
        payload["point_in_time"]["sources_discovered"] == 0
    )
    assert payload["point_in_time"]["sources_accepted"] == 0
    assert payload["evidence"]["neutral"] == []

    # The report is still produced from market/financial evidence.
    assert payload["assessment"]["conclusion"]
    assert payload["evidence"]["positive"]
    assert (
        payload["point_in_time"]["pit_checks_passed"]
        is True
    )

    _assert_no_future_evidence(payload)


def test_failed_source_provider_is_isolated_in_contract(
    tmp_path,
):
    result = run_source_scenario(
        company="HDFCBANK",
        source_provider=FailedSourcesProvider(),
        archive_root=tmp_path / "degraded-archive",
    )

    payload = research_contract(
        result,
        company_name="HDFC Bank",
    )

    assert payload["data_quality"]["provider_failures"]
    assert all(
        "failed-sources-provider" in failure
        for failure in payload["data_quality"][
            "provider_failures"
        ]
    )
    assert payload["point_in_time"]["sources_accepted"] == 0
    assert payload["assessment"]["conclusion"]
    assert any(
        "provider" in warning
        for warning in payload["data_quality"]["warnings"]
    )

    _assert_no_future_evidence(payload)


# ---------------------------------------------------------------------
# Ranking contract
# ---------------------------------------------------------------------


def test_company_rankings_contract(client):
    response = client.get(
        "/api/v1/companies/M&M/rankings"
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["symbol"] == "M&M"
    assert payload["company_name"] == "Mahindra & Mahindra"
    assert payload["as_of"] == DEFAULT_AS_OF_ISO

    rankings = payload["rankings"]

    assert set(rankings) == {
        "intraday",
        "swing",
        "long_term",
    }

    for ranking in rankings.values():
        assert ranking["horizon"] in {
            "INTRADAY",
            "SWING",
            "LONG_TERM",
        }
        assert ranking["score"]
        assert ranking["signal"]
        assert ranking["confidence"]
        assert ranking["coverage"]
        assert isinstance(
            ranking["missing_components"],
            list,
        )
        assert ranking["components"]

    # Degraded evidence is explicit: future-oriented components
    # without evidence are reported as missing, not as neutral 50s.
    long_term = rankings["long_term"]

    assert any(
        component.startswith(("future", "ai_", "sector_"))
        for component in long_term["missing_components"]
    )
    assert Decimal(long_term["coverage"]) < Decimal("100")


def test_universe_rankings_contract(client):
    response = client.get("/api/v1/rankings/LONG_TERM")

    assert response.status_code == 200
    payload = response.json()

    assert payload["horizon"] == "LONG_TERM"
    assert payload["count"] == len(VERIFIED_COMPANIES)
    assert payload["as_of"] == DEFAULT_AS_OF_ISO

    scores = [
        item["score"] for item in payload["results"]
    ]

    assert scores == sorted(scores, reverse=True)

    symbols = {item["symbol"] for item in payload["results"]}
    assert symbols == set(VERIFIED_COMPANIES)


def test_universe_rankings_supports_symbol_subset(client):
    response = client.get(
        "/api/v1/rankings/SWING?symbols=TCS,RELIANCE"
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["horizon"] == "SWING"
    assert payload["count"] == 2
    assert {item["symbol"] for item in payload["results"]} == {
        "TCS",
        "RELIANCE",
    }


def test_universe_rankings_invalid_horizon(client):
    response = client.get("/api/v1/rankings/BOGUS")

    assert response.status_code == 400
    error = response.json()["error"]

    assert error["code"] == "invalid_horizon"
    assert set(error["details"]["supported"]) == {
        "INTRADAY",
        "SWING",
        "LONG_TERM",
    }


# ---------------------------------------------------------------------
# Company discovery contract
# ---------------------------------------------------------------------


def test_company_discovery_response(client):
    response = client.get("/api/v1/companies")

    assert response.status_code == 200
    payload = response.json()

    assert payload["count"] == len(VERIFIED_COMPANIES)

    results = {
        item["symbol"]: item
        for item in payload["results"]
    }

    assert set(results) == set(VERIFIED_COMPANIES)

    for item in payload["results"]:
        assert item["company_name"]
        assert item["sector"]
        assert item["research_available"] is True

    assert results["TCS"]["company_name"] == (
        "Tata Consultancy Services"
    )
    assert results["M&M"]["company_name"] == (
        "Mahindra & Mahindra"
    )
