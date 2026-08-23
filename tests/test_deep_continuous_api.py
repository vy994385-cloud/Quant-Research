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
        assert obs["severity"] in ("INFO", "WARN", "ALERT")


def test_hidden_information_pit_safe(client):
    resp = client.get(
        "/api/v1/companies/TCS/hidden-information",
        params={"as_of": "2026-04-01T00:00:00+00:00"},
    )
    payload = resp.json()

    hidden = payload["hidden_information"]
    assert hidden is not None

    for obs in hidden["observations"]:
        assert obs["as_of"] <= hidden["as_of"]


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


# =================================================================
# R2 — Cross-domain endpoint
# =================================================================


def test_cross_domain_route_exposed(client):
    resp = client.get(
        "/api/v1/companies/TCS/cross-domain"
    )
    assert resp.status_code == 200
    assert resp.json()["company"]["symbol"] == "TCS"


def test_tcs_cross_domain_structure(client):
    resp = client.get(
        "/api/v1/companies/TCS/cross-domain"
    )
    payload = resp.json()

    assert payload["company"]["as_of"] == DEFAULT_AS_OF_ISO

    cd = payload["cross_domain"]
    assert cd is not None
    assert cd["symbol"] == "TCS"
    assert cd["as_of"] == DEFAULT_AS_OF_ISO
    assert isinstance(cd["observations"], list)
    assert isinstance(cd["notes"], list)
    assert isinstance(cd["positive_count"], int)
    assert isinstance(cd["negative_count"], int)
    assert isinstance(cd["mixed_count"], int)
    assert isinstance(cd["neutral_count"], int)

    for obs in cd["observations"]:
        assert obs["observation_id"]
        assert obs["symbol"] == "TCS"
        assert obs["label"]
        assert obs["semantic_category"]
        assert obs["description"]
        assert obs["severity"] in ("INFO", "WARN", "ALERT")
        assert obs["as_of"]


def test_cross_domain_pit_safe(client):
    resp = client.get(
        "/api/v1/companies/TCS/cross-domain",
        params={"as_of": "2026-04-01T00:00:00+00:00"},
    )
    payload = resp.json()
    cd = payload["cross_domain"]
    assert cd is not None
    assert payload["company"]["as_of"] == "2026-04-01T00:00:00+00:00"

    for obs in cd["observations"]:
        assert obs["as_of"] <= cd["as_of"]


def test_cross_domain_deterministic(client):
    a = client.get(
        "/api/v1/companies/TCS/cross-domain"
    ).json()
    b = client.get(
        "/api/v1/companies/TCS/cross-domain"
    ).json()
    assert a == b


@pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
def test_every_company_has_cross_domain(client, symbol):
    resp = client.get(
        f"/api/v1/companies/{symbol}/cross-domain"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["company"]["symbol"] == symbol
    cd = payload["cross_domain"]
    assert cd is not None
    assert isinstance(cd["observations"], list)


def test_unknown_company_cross_domain_returns_404(client):
    resp = client.get(
        "/api/v1/companies/UNKNOWN/cross-domain"
    )
    assert resp.status_code == 404


def test_naive_as_of_cross_domain_returns_400(client):
    resp = client.get(
        "/api/v1/companies/TCS/cross-domain",
        params={"as_of": "2026-08-10T12:00:00"},
    )
    assert resp.status_code == 400


# =================================================================
# R2 — Research contract surfaces expansion fields
# =================================================================


def test_research_contract_has_cash_flow_quality(client):
    resp = client.get("/api/v1/companies/TCS/research")
    payload = resp.json()
    assert "cash_flow_quality" in payload
    cfq = payload["cash_flow_quality"]
    assert cfq is not None
    assert cfq["symbol"] == "TCS"
    assert cfq["as_of"] == DEFAULT_AS_OF_ISO
    assert cfq["direction"] in (
        "IMPROVING", "DETERIORATING", "STABLE", "UNKNOWN",
    )
    assert isinstance(cfq["observations"], list)
    assert isinstance(cfq["notes"], list)


def test_research_contract_has_balance_sheet_deep(client):
    resp = client.get("/api/v1/companies/TCS/research")
    payload = resp.json()
    assert "balance_sheet_deep" in payload
    bsd = payload["balance_sheet_deep"]
    assert bsd is not None
    assert bsd["symbol"] == "TCS"
    assert bsd["as_of"] == DEFAULT_AS_OF_ISO
    assert isinstance(bsd["observations"], list)
    assert isinstance(bsd["notes"], list)


def test_research_contract_has_research_gaps(client):
    resp = client.get("/api/v1/companies/TCS/research")
    payload = resp.json()
    assert "research_gaps" in payload
    rg = payload["research_gaps"]
    assert rg is not None
    assert rg["symbol"] == "TCS"
    assert rg["as_of"] == DEFAULT_AS_OF_ISO
    assert isinstance(rg["gaps"], list)
    assert isinstance(rg["notes"], list)


def test_research_contract_has_cross_domain(client):
    resp = client.get("/api/v1/companies/TCS/research")
    payload = resp.json()
    assert "cross_domain" in payload
    cd = payload["cross_domain"]
    assert cd is not None
    assert cd["symbol"] == "TCS"
    assert isinstance(cd["observations"], list)


def test_research_contract_has_financial_anomalies(client):
    resp = client.get("/api/v1/companies/TCS/research")
    payload = resp.json()
    assert "financial_anomalies" in payload
    fa = payload["financial_anomalies"]
    assert fa is not None
    assert fa["symbol"] == "TCS"
    assert fa["as_of"] == DEFAULT_AS_OF_ISO
    assert isinstance(fa["anomalies"], list)
    assert isinstance(fa["notes"], list)


# =================================================================
# R2 — Intelligence contract surfaces expansion fields
# =================================================================


def test_intelligence_contract_has_expansion_fields(client):
    resp = client.get("/api/v1/companies/TCS/intelligence")
    payload = resp.json()

    assert "cash_flow_quality" in payload
    assert "balance_sheet_deep" in payload
    assert "research_gaps" in payload
    assert "cross_domain" in payload
    assert "financial_anomalies" in payload


def test_intelligence_cash_flow_quality_structure(client):
    resp = client.get("/api/v1/companies/TCS/intelligence")
    cfq = resp.json()["cash_flow_quality"]

    assert cfq is not None
    assert cfq["symbol"] == "TCS"
    assert isinstance(cfq["observations"], list)

    for obs in cfq["observations"]:
        assert obs["observation_id"]
        assert obs["symbol"] == "TCS"
        assert obs["as_of"]


def test_intelligence_balance_sheet_deep_structure(client):
    resp = client.get("/api/v1/companies/TCS/intelligence")
    bsd = resp.json()["balance_sheet_deep"]

    assert bsd is not None
    assert bsd["symbol"] == "TCS"
    assert isinstance(bsd["observations"], list)

    for obs in bsd["observations"]:
        assert obs["observation_id"]
        assert obs["symbol"] == "TCS"
        assert obs["as_of"]


def test_intelligence_research_gaps_structure(client):
    resp = client.get("/api/v1/companies/TCS/intelligence")
    rg = resp.json()["research_gaps"]

    assert rg is not None
    assert rg["symbol"] == "TCS"
    assert isinstance(rg["gaps"], list)


def test_intelligence_cross_domain_structure(client):
    resp = client.get("/api/v1/companies/TCS/intelligence")
    cd = resp.json()["cross_domain"]

    assert cd is not None
    assert cd["symbol"] == "TCS"
    assert isinstance(cd["observations"], list)


def test_intelligence_financial_anomalies_structure(client):
    resp = client.get("/api/v1/companies/TCS/intelligence")
    fa = resp.json()["financial_anomalies"]

    assert fa is not None
    assert fa["symbol"] == "TCS"
    assert isinstance(fa["anomalies"], list)


# =================================================================
# R2 — Every company has expansion fields in research contract
# =================================================================


@pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
def test_every_company_research_has_expansion_fields(client, symbol):
    resp = client.get(
        f"/api/v1/companies/{symbol}/research"
    )
    assert resp.status_code == 200
    payload = resp.json()

    assert payload["cash_flow_quality"] is not None
    assert payload["balance_sheet_deep"] is not None
    assert payload["research_gaps"] is not None
    assert payload["cross_domain"] is not None
    assert payload["financial_anomalies"] is not None


# =================================================================
# R2 — Provenance: expansion observations carry as_of
# =================================================================


def test_expansion_observations_carry_as_of(client):
    resp = client.get("/api/v1/companies/TCS/research")
    payload = resp.json()

    pit_as_of = payload["point_in_time"]["effective_as_of"]

    cfq = payload["cash_flow_quality"]
    for obs in cfq["observations"]:
        assert obs["as_of"] <= pit_as_of

    bsd = payload["balance_sheet_deep"]
    for obs in bsd["observations"]:
        assert obs["as_of"] <= pit_as_of

    cd = payload["cross_domain"]
    for obs in cd["observations"]:
        assert obs["as_of"] <= pit_as_of

    fa = payload["financial_anomalies"]
    for obs in fa["anomalies"]:
        assert obs["as_of"] <= pit_as_of


# =================================================================
# R2 — PIT: earlier as_of has fewer or equal observations
# =================================================================


def test_earlier_as_of_fewer_or_equal_expansion_obs(client):
    default = client.get(
        "/api/v1/companies/TCS/research"
    ).json()
    earlier = client.get(
        "/api/v1/companies/TCS/research",
        params={"as_of": "2026-04-01T00:00:00+00:00"},
    ).json()

    default_gaps = default["research_gaps"]["gap_count"]
    earlier_gaps = earlier["research_gaps"]["gap_count"]
    assert earlier_gaps <= default_gaps

    default_cfq = len(default["cash_flow_quality"]["observations"])
    earlier_cfq = len(earlier["cash_flow_quality"]["observations"])
    assert earlier_cfq <= default_cfq

    default_bsd = len(default["balance_sheet_deep"]["observations"])
    earlier_bsd = len(earlier["balance_sheet_deep"]["observations"])
    assert earlier_bsd <= default_bsd


# =================================================================
# R2 — Research Gaps endpoint
# =================================================================


def test_research_gaps_route_exposed(client):
    resp = client.get(
        "/api/v1/companies/TCS/research-gaps"
    )
    assert resp.status_code == 200
    assert resp.json()["company"]["symbol"] == "TCS"


def test_tcs_research_gaps_structure(client):
    resp = client.get(
        "/api/v1/companies/TCS/research-gaps"
    )
    payload = resp.json()

    assert payload["company"]["as_of"] == DEFAULT_AS_OF_ISO

    rg = payload["research_gaps"]
    assert rg is not None
    assert rg["symbol"] == "TCS"
    assert rg["as_of"] == DEFAULT_AS_OF_ISO
    assert isinstance(rg["gaps"], list)
    assert isinstance(rg["gap_count"], int)
    assert isinstance(rg["status_counts"], dict)
    assert isinstance(rg["category_counts"], dict)
    assert isinstance(rg["notes"], list)
    assert rg["coverage_score"] in ("HIGH", "MEDIUM", "LOW", None)

    for gap in rg["gaps"]:
        assert gap["gap_id"]
        assert gap["symbol"] == "TCS"
        assert gap["category"]
        assert gap["description"]
        assert gap["status"]
        assert gap["severity"] in ("HIGH", "MEDIUM", "LOW")
        assert gap["as_of"]
        assert isinstance(gap["sources_checked"], list)
        assert isinstance(gap["evidence_refs"], list)
        assert isinstance(gap["related_metrics"], list)
        assert isinstance(gap["supporting_data"], dict)


def test_research_gaps_pit_safe(client):
    resp = client.get(
        "/api/v1/companies/TCS/research-gaps",
        params={"as_of": "2026-04-01T00:00:00+00:00"},
    )
    payload = resp.json()
    rg = payload["research_gaps"]
    assert rg is not None
    assert payload["company"]["as_of"] == "2026-04-01T00:00:00+00:00"


def test_research_gaps_deterministic(client):
    a = client.get(
        "/api/v1/companies/TCS/research-gaps"
    ).json()
    b = client.get(
        "/api/v1/companies/TCS/research-gaps"
    ).json()
    assert a == b


@pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
def test_every_company_has_research_gaps(client, symbol):
    resp = client.get(
        f"/api/v1/companies/{symbol}/research-gaps"
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["company"]["symbol"] == symbol
    rg = payload["research_gaps"]
    assert rg is not None
    assert isinstance(rg["gaps"], list)
    assert rg["gap_count"] >= 0


def test_unknown_company_research_gaps_returns_404(client):
    resp = client.get(
        "/api/v1/companies/UNKNOWN/research-gaps"
    )
    assert resp.status_code == 404


def test_naive_as_of_research_gaps_returns_400(client):
    resp = client.get(
        "/api/v1/companies/TCS/research-gaps",
        params={"as_of": "2026-08-10T12:00:00"},
    )
    assert resp.status_code == 400


def test_research_gaps_coverage_score(client):
    resp = client.get(
        "/api/v1/companies/TCS/research-gaps"
    )
    rg = resp.json()["research_gaps"]
    assert rg is not None
    assert rg["coverage_score"] in ("HIGH", "MEDIUM", "LOW")
    assert rg["coverage_explanation"]


def test_research_contract_has_research_gaps(client):
    resp = client.get("/api/v1/companies/TCS/research")
    payload = resp.json()
    assert "research_gaps" in payload
    rg = payload["research_gaps"]
    assert rg is not None
    assert rg["gap_count"] >= 0
    assert isinstance(rg["gaps"], list)


def test_intelligence_has_research_gaps(client):
    resp = client.get("/api/v1/companies/TCS/intelligence")
    payload = resp.json()
    assert "research_gaps" in payload
    rg = payload["research_gaps"]
    assert rg is not None
    assert rg["gap_count"] >= 0
