"""
L1 end-to-end verification tests.

Verifies the complete research path:
  discovery -> provider -> validation -> PIT context ->
  provenance/evidence -> research -> intelligence -> ranking

Tests all 9 v1 API endpoints across all 6 verified companies,
including PIT purity, error contracts, and cross-endpoint consistency.
"""

from __future__ import annotations

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
    archive_root = tmp_path_factory.mktemp("l1-e2e-archive")
    return RecordedCompanyResearchService(archive_root=archive_root)


@pytest.fixture(scope="module")
def client(service):
    app = FastAPI()
    register_api_error_handlers(app)
    app.include_router(create_research_router(service=service))
    return TestClient(app)


# ------------------------------------------------------------------
# 1. FULL CHAIN: discovery -> research -> rankings
# ------------------------------------------------------------------


class TestFullChain:
    """Verify that discovery, research, and rankings form a coherent chain."""

    def test_discovery_returns_all_verified_companies(self, client):
        resp = client.get("/api/v1/companies")
        assert resp.status_code == 200
        data = resp.json()
        symbols = {r["symbol"] for r in data["results"]}
        for company in VERIFIED_COMPANIES:
            assert company in symbols

    def test_full_chain_for_tcs(self, client):
        # 1. Discovery
        disc = client.get("/api/v1/companies").json()
        tcs_disc = next(
            r for r in disc["results"] if r["symbol"] == "TCS"
        )
        assert tcs_disc["research_available"] is True

        # 2. Research
        research = client.get(
            "/api/v1/companies/TCS/research"
        ).json()
        assert research["company"]["symbol"] == "TCS"
        assert "assessment" in research
        assert "evidence" in research
        assert "rankings" in research
        assert "provenance" in research

        # 3. Rankings
        rankings = client.get(
            "/api/v1/companies/TCS/rankings"
        ).json()
        assert rankings["symbol"] == "TCS"
        assert set(rankings["rankings"]) == {
            "intraday",
            "swing",
            "long_term",
        }

        # 4. Verify consistency
        assert (
            research["rankings"]["intraday"]["score"]
            == rankings["rankings"]["intraday"]["score"]
        )

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_full_chain_each_company(self, client, symbol):
        disc = client.get("/api/v1/companies").json()
        company_disc = next(
            r for r in disc["results"] if r["symbol"] == symbol
        )
        assert company_disc["research_available"] is True

        research = client.get(
            f"/api/v1/companies/{symbol}/research"
        ).json()
        assert research["company"]["symbol"] == symbol
        assert research["assessment"]["conclusion"] in {
            "POSITIVE",
            "NEGATIVE",
            "MIXED",
            "NEUTRAL",
            "INSUFFICIENT_EVIDENCE",
        }

        rankings = client.get(
            f"/api/v1/companies/{symbol}/rankings"
        ).json()
        assert rankings["symbol"] == symbol
        for horizon in ("intraday", "swing", "long_term"):
            assert horizon in rankings["rankings"]
            assert "score" in rankings["rankings"][horizon]


# ------------------------------------------------------------------
# 2. ALL 6 COMPANIES across ALL v1 endpoints
# ------------------------------------------------------------------


class TestAllCompaniesAllEndpoints:
    """Every verified company works on every v1 endpoint."""

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research(self, client, symbol):
        resp = client.get(
            f"/api/v1/companies/{symbol}/research"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["company"]["symbol"] == symbol
        assert data["point_in_time"]["pit_checks_passed"] is True

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_intelligence(self, client, symbol):
        resp = client.get(
            f"/api/v1/companies/{symbol}/intelligence"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["company"]["symbol"] == symbol
        assert data["item_count"] >= 5

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_timeline(self, client, symbol):
        resp = client.get(
            f"/api/v1/companies/{symbol}/timeline"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["company"]["symbol"] == symbol
        assert len(data["timeline"]["entries"]) >= 1

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_rankings(self, client, symbol):
        resp = client.get(
            f"/api/v1/companies/{symbol}/rankings"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == symbol
        assert set(data["rankings"]) == {
            "intraday",
            "swing",
            "long_term",
        }

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_deep_financial_insights(self, client, symbol):
        resp = client.get(
            f"/api/v1/companies/{symbol}/deep-financial-insights"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["company"]["symbol"] == symbol

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_source_statuses(self, client, symbol):
        resp = client.get(
            f"/api/v1/companies/{symbol}/source-statuses"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["company"]["symbol"] == symbol

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_hidden_information(self, client, symbol):
        resp = client.get(
            f"/api/v1/companies/{symbol}/hidden-information"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["company"]["symbol"] == symbol


# ------------------------------------------------------------------
# 3. UNIVERSE RANKINGS: all horizons + INTRADAY
# ------------------------------------------------------------------


class TestUniverseRankings:
    """Universe rankings endpoint works for all horizons."""

    @pytest.mark.parametrize(
        "horizon", ["INTRADAY", "SWING", "LONG_TERM"]
    )
    def test_universe_rankings_all_horizons(self, client, horizon):
        resp = client.get(f"/api/v1/rankings/{horizon}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["horizon"] == horizon
        assert data["count"] >= len(VERIFIED_COMPANIES)
        symbols = {r["symbol"] for r in data["results"]}
        for company in VERIFIED_COMPANIES:
            assert company in symbols

    def test_universe_rankings_sorted_descending(self, client):
        resp = client.get("/api/v1/rankings/LONG_TERM")
        data = resp.json()
        scores = [r["score"] for r in data["results"]]
        assert scores == sorted(scores, reverse=True)

    def test_universe_rankings_deterministic(self, client):
        r1 = client.get("/api/v1/rankings/SWING").json()
        r2 = client.get("/api/v1/rankings/SWING").json()
        assert r1 == r2


# ------------------------------------------------------------------
# 4. VALID / INVALID as_of
# ------------------------------------------------------------------


class TestAsOfValidation:
    """as_of parameter handling across endpoints."""

    def test_valid_as_of_with_timezone(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/research",
            params={"as_of": DEFAULT_AS_OF_ISO},
        )
        assert resp.status_code == 200
        assert (
            resp.json()["point_in_time"]["as_of"]
            == DEFAULT_AS_OF_ISO
        )

    def test_date_only_as_of_defaults_to_utc_midnight(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/research",
            params={"as_of": "2026-08-10"},
        )
        assert resp.status_code == 200
        pit = resp.json()["point_in_time"]
        assert pit["as_of"] == "2026-08-10T00:00:00+00:00"

    def test_z_suffix_as_of_is_accepted(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/research",
            params={"as_of": "2026-08-10T12:00:00Z"},
        )
        assert resp.status_code == 200

    def test_naive_datetime_with_time_rejected(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/research",
            params={"as_of": "2026-08-10T12:00:00"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_as_of"

    def test_invalid_format_rejected(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/research",
            params={"as_of": "not-a-date"},
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_as_of"

    def test_as_of_error_contract_shape(self, client):
        resp = client.get(
            "/api/v1/companies/TCS/research",
            params={"as_of": "garbage"},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/v1/companies/TCS/intelligence",
            "/api/v1/companies/TCS/timeline",
            "/api/v1/companies/TCS/rankings",
            "/api/v1/companies/TCS/deep-financial-insights",
            "/api/v1/companies/TCS/source-statuses",
            "/api/v1/companies/TCS/hidden-information",
        ],
    )
    def test_invalid_as_of_on_all_endpoints(self, client, endpoint):
        resp = client.get(endpoint, params={"as_of": "garbage"})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_as_of"

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/v1/companies/TCS/intelligence",
            "/api/v1/companies/TCS/timeline",
            "/api/v1/companies/TCS/rankings",
            "/api/v1/companies/TCS/deep-financial-insights",
            "/api/v1/companies/TCS/source-statuses",
            "/api/v1/companies/TCS/hidden-information",
        ],
    )
    def test_naive_as_of_on_all_endpoints(self, client, endpoint):
        resp = client.get(
            endpoint, params={"as_of": "2026-08-10T12:00:00"}
        )
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "invalid_as_of"


# ------------------------------------------------------------------
# 5. UNKNOWN COMPANIES
# ------------------------------------------------------------------


class TestUnknownCompany:
    """Unknown company returns 404 on all endpoints."""

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/api/v1/companies/FAKE/research",
            "/api/v1/companies/FAKE/intelligence",
            "/api/v1/companies/FAKE/timeline",
            "/api/v1/companies/FAKE/rankings",
            "/api/v1/companies/FAKE/deep-financial-insights",
            "/api/v1/companies/FAKE/source-statuses",
            "/api/v1/companies/FAKE/hidden-information",
        ],
    )
    def test_unknown_company_404(self, client, endpoint):
        resp = client.get(endpoint)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "unknown_company"

    def test_unknown_company_error_contract_shape(self, client):
        resp = client.get("/api/v1/companies/FAKE/research")
        assert resp.status_code == 404
        body = resp.json()
        assert "error" in body
        assert "code" in body["error"]
        assert body["error"]["code"] == "unknown_company"


# ------------------------------------------------------------------
# 6. PIT PURITY — no future-dated information leaks
# ------------------------------------------------------------------


class TestPITPurity:
    """No future-dated evidence leaks into any as_of context."""

    EARLY_AS_OF = "2026-04-01T00:00:00+00:00"

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_excludes_future_evidence(self, client, symbol):
        resp = client.get(
            f"/api/v1/companies/{symbol}/research",
            params={"as_of": self.EARLY_AS_OF},
        )
        assert resp.status_code == 200
        data = resp.json()
        pit = data["point_in_time"]
        assert pit["future_evidence_excluded"] >= 0
        assert pit["pit_checks_passed"] is True

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_intelligence_excludes_future_items(
        self, client, symbol
    ):
        resp = client.get(
            f"/api/v1/companies/{symbol}/intelligence",
            params={"as_of": self.EARLY_AS_OF},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data.get("business_events", []):
            assert item["available_at"] <= self.EARLY_AS_OF
        for item in data.get("management_commentary", []):
            assert item["available_at"] <= self.EARLY_AS_OF

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_timeline_excludes_future_entries(self, client, symbol):
        resp = client.get(
            f"/api/v1/companies/{symbol}/timeline",
            params={"as_of": self.EARLY_AS_OF},
        )
        assert resp.status_code == 200
        data = resp.json()
        for entry in data["timeline"]["entries"]:
            available = entry.get("available_at")
            if available:
                assert available <= self.EARLY_AS_OF

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_earlier_as_of_has_fewer_items(self, client, symbol):
        default = client.get(
            f"/api/v1/companies/{symbol}/intelligence"
        ).json()
        earlier = client.get(
            f"/api/v1/companies/{symbol}/intelligence",
            params={"as_of": self.EARLY_AS_OF},
        ).json()
        assert earlier["item_count"] <= default["item_count"]


# ------------------------------------------------------------------
# 7. CROSS-ENDPOINT CONSISTENCY
# ------------------------------------------------------------------


class TestCrossEndpointConsistency:
    """Embedded sub-objects match their standalone endpoints."""

    def test_research_timeline_matches_standalone(self, client):
        symbol = "TCS"
        research = client.get(
            f"/api/v1/companies/{symbol}/research"
        ).json()
        standalone = client.get(
            f"/api/v1/companies/{symbol}/timeline"
        ).json()
        assert (
            len(research["timeline"]["entries"])
            == len(standalone["timeline"]["entries"])
        )

    def test_research_rankings_match_standalone(self, client):
        symbol = "TCS"
        research = client.get(
            f"/api/v1/companies/{symbol}/research"
        ).json()
        standalone = client.get(
            f"/api/v1/companies/{symbol}/rankings"
        ).json()
        for horizon in ("intraday", "swing", "long_term"):
            assert (
                research["rankings"][horizon]["score"]
                == standalone["rankings"][horizon]["score"]
            )

    def test_intelligence_deep_financial_matches_standalone(
        self, client
    ):
        symbol = "TCS"
        intel = client.get(
            f"/api/v1/companies/{symbol}/intelligence"
        ).json()
        standalone = client.get(
            f"/api/v1/companies/{symbol}/deep-financial-insights"
        ).json()
        intel_series = intel.get("deep_financial_insights", {})
        standalone_series = standalone.get(
            "deep_financial_insights", {}
        )
        assert (
            len(intel_series.get("series", []))
            == len(standalone_series.get("series", []))
        )

    def test_intelligence_source_statuses_match_standalone(
        self, client
    ):
        symbol = "TCS"
        intel = client.get(
            f"/api/v1/companies/{symbol}/intelligence"
        ).json()
        standalone = client.get(
            f"/api/v1/companies/{symbol}/source-statuses"
        ).json()
        intel_statuses = intel.get("source_statuses", [])
        standalone_statuses = standalone.get(
            "source_statuses", []
        )
        assert len(intel_statuses) == len(standalone_statuses)

    def test_intelligence_hidden_info_matches_standalone(
        self, client
    ):
        symbol = "TCS"
        intel = client.get(
            f"/api/v1/companies/{symbol}/intelligence"
        ).json()
        standalone = client.get(
            f"/api/v1/companies/{symbol}/hidden-information"
        ).json()
        intel_obs = intel.get("hidden_information", {}).get(
            "observations", []
        )
        standalone_obs = standalone.get(
            "hidden_information", {}
        ).get("observations", [])
        assert len(intel_obs) == len(standalone_obs)


# ------------------------------------------------------------------
# 8. DETERMINISM
# ------------------------------------------------------------------


class TestDeterminism:
    """Identical requests produce identical responses."""

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_deterministic(self, client, symbol):
        r1 = client.get(
            f"/api/v1/companies/{symbol}/research"
        ).json()
        r2 = client.get(
            f"/api/v1/companies/{symbol}/research"
        ).json()
        assert r1 == r2

    def test_discovery_deterministic(self, client):
        r1 = client.get("/api/v1/companies").json()
        r2 = client.get("/api/v1/companies").json()
        assert r1 == r2

    def test_universe_rankings_deterministic(self, client):
        r1 = client.get("/api/v1/rankings/LONG_TERM").json()
        r2 = client.get("/api/v1/rankings/LONG_TERM").json()
        assert r1 == r2

    def test_research_with_as_of_deterministic(self, client):
        params = {"as_of": DEFAULT_AS_OF_ISO}
        r1 = client.get(
            "/api/v1/companies/TCS/research", params=params
        ).json()
        r2 = client.get(
            "/api/v1/companies/TCS/research", params=params
        ).json()
        assert r1 == r2


# ------------------------------------------------------------------
# 9. EVIDENCE COVERAGE & QUALITY
# ------------------------------------------------------------------


class TestEvidenceCoverage:
    """Research output has meaningful evidence coverage."""

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_has_evidence(self, client, symbol):
        data = client.get(
            f"/api/v1/companies/{symbol}/research"
        ).json()
        evidence = data["evidence"]
        total = (
            len(evidence["positive"])
            + len(evidence["negative"])
            + len(evidence["neutral"])
        )
        assert total >= 1

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_research_has_provenance(self, client, symbol):
        data = client.get(
            f"/api/v1/companies/{symbol}/research"
        ).json()
        prov = data["provenance"]
        assert len(prov["market"]) >= 1
        assert len(prov["financials"]) >= 1

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_intelligence_has_source_ids(self, client, symbol):
        data = client.get(
            f"/api/v1/companies/{symbol}/intelligence"
        ).json()
        assert len(data["source_ids"]) >= 1

    @pytest.mark.parametrize("symbol", VERIFIED_COMPANIES)
    def test_deep_financial_has_observations(self, client, symbol):
        data = client.get(
            f"/api/v1/companies/{symbol}/deep-financial-insights"
        ).json()
        dfi = data["deep_financial_insights"]
        assert len(dfi.get("observations", [])) >= 1


# ------------------------------------------------------------------
# 10. MISSING / STALE / DEGRADED EVIDENCE PATHS
# ------------------------------------------------------------------


class TestDegradedPaths:
    """Missing or degraded evidence is surfaced, not hidden."""

    def test_missing_sources_degrade_gracefully(self, tmp_path):
        from src.verification.real_data import (
            MissingSourcesProvider,
            run_source_scenario,
        )

        result = run_source_scenario(
            company="TCS",
            source_provider=MissingSourcesProvider(),
            archive_root=str(tmp_path / "missing"),
        )
        assert result.acquisition is not None

    def test_stale_sources_remain_pit_valid(self, tmp_path):
        from pathlib import Path
        from src.verification.real_data import (
            StaleSourcesProvider,
            run_source_scenario,
        )

        sources_json = (
            Path("fixtures/real_data/tcs_sources.json")
        )
        result = run_source_scenario(
            company="TCS",
            source_provider=StaleSourcesProvider(sources_json),
            archive_root=str(tmp_path / "stale"),
        )
        assert result.acquisition is not None

    def test_failed_sources_degrade_gracefully(self, tmp_path):
        from src.verification.real_data import (
            FailedSourcesProvider,
            run_source_scenario,
        )

        result = run_source_scenario(
            company="TCS",
            source_provider=FailedSourcesProvider(),
            archive_root=str(tmp_path / "failed"),
        )
        assert result.acquisition is not None
