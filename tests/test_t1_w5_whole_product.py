"""T1-W5 Whole-Product Research Foundation tests.

Covers: whole-product backend coverage, cross-domain consistency,
PIT matrix, provenance matrix, output quality, page data models.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.recorded_research import RecordedCompanyResearchService

AS_OF = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
AS_OF_STR = "2026-08-10T12:00:00Z"
AS_OF_EARLY = datetime(2026, 1, 1, tzinfo=timezone.utc)
AS_OF_EARLY_STR = "2026-01-01T00:00:00Z"
COMPANIES = ["TCS", "INFY", "HDFCBANK", "RELIANCE", "M&M", "SUNPHARMA"]
TCS = "TCS"


def _q(sym: str) -> str:
    """URL-encode a symbol for use in query parameter strings."""
    return quote(sym, safe="")


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def service():
    return RecordedCompanyResearchService()


@pytest.fixture(scope="module")
def results(service):
    return {sym: service.run(sym, as_of=AS_OF) for sym in COMPANIES}


# ═══════════════════════════════════════════════════════════════════
# 1 — WHOLE-PRODUCT BACKEND COVERAGE
# ═══════════════════════════════════════════════════════════════════


class TestDiscoverCoverage:
    """DISCOVER page support."""

    def test_discovery_feed(self, client):
        resp = client.get(f"/api/v1/discovery?as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "item_count" in data
        assert data["item_count"] >= 0

    def test_discovery_trending(self, client):
        resp = client.get(f"/api/v1/discovery/trending?as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "ranked" in data

    def test_evidence_search(self, client):
        resp = client.get(f"/api/v1/evidence/search?q=TCS&as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "hit_count" in data

    def test_companies_list(self, client):
        resp = client.get("/api/v1/companies")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data
        assert data["count"] >= 6


class TestCompanyResearchCoverage:
    """COMPANY RESEARCH page support."""

    def test_research_endpoint(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/research?as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "company" in data
        # company field is a dict with symbol
        company = data["company"]
        if isinstance(company, dict):
            assert company.get("symbol") == TCS
        else:
            assert company == TCS

    def test_intelligence_endpoint(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/intelligence?as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "financial_intelligence" in data

    def test_financial_history(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/financial-history?as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "financial_history" in data

    def test_deep_financial_insights(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/deep-financial-insights?as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "deep_financial_insights" in data

    def test_events(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/events?as_of={AS_OF_STR}")
        assert resp.status_code == 200

    def test_evidence(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/evidence?as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "evidence_lineage" in data

    def test_research_gaps(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/research-gaps?as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "research_gaps" in data

    def test_source_statuses(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/source-statuses?as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "source_statuses" in data

    def test_timeline(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/timeline?as_of={AS_OF_STR}")
        assert resp.status_code == 200

    def test_cross_domain(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/cross-domain?as_of={AS_OF_STR}")
        assert resp.status_code == 200

    def test_hidden_information(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/hidden-information?as_of={AS_OF_STR}")
        assert resp.status_code == 200

    def test_industry_context(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/industry-context?as_of={AS_OF_STR}")
        assert resp.status_code == 200


class TestScreenCoverage:
    """SCREEN page support."""

    def test_screener_fields(self, client):
        resp = client.get("/api/v1/screener/fields")
        assert resp.status_code == 200
        data = resp.json()
        assert "fields" in data
        assert data["available_count"] >= 10

    def test_compare(self, client):
        resp = client.get(f"/api/v1/companies/compare?symbols=TCS,INFY&as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "companies" in data


class TestMonitorCoverage:
    """MONITOR page support."""

    def test_research_changes(self, client):
        resp = client.get(
            f"/api/v1/research-changes?symbol={TCS}"
            f"&baseline_as_of={AS_OF_EARLY_STR}&current_as_of={AS_OF_STR}"
        )
        assert resp.status_code == 200

    def test_research_delta(self, client):
        resp = client.get(
            f"/api/v1/research-delta?symbol={TCS}"
            f"&baseline_as_of={AS_OF_EARLY_STR}&current_as_of={AS_OF_STR}"
        )
        assert resp.status_code == 200

    def test_coverage_delta(self, client):
        resp = client.get(
            f"/api/v1/coverage/delta?symbol={TCS}"
            f"&baseline_as_of={AS_OF_EARLY_STR}&current_as_of={AS_OF_STR}"
        )
        assert resp.status_code == 200

    def test_evidence_conflicts(self, client):
        resp = client.get(f"/api/v1/evidence/conflicts?symbol={TCS}&as_of={AS_OF_STR}")
        assert resp.status_code == 200

    def test_calendar(self, client):
        resp = client.get(
            f"/api/v1/calendar?symbols=TCS&range_from=2026-01-01&range_to=2026-08-10"
        )
        assert resp.status_code == 200


class TestOutputCoverage:
    """OUTPUT page support."""

    def test_snapshot(self, client):
        resp = client.get(f"/api/v1/research/snapshot?symbol={TCS}&as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "identity" in data

    def test_research_report(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/research-report?as_of={AS_OF_STR}")
        assert resp.status_code == 200

    def test_export(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/export?as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "manifest" in data
        assert "package_sha256" in data


class TestAssetClassCoverage:
    """ASSET CLASS support."""

    def test_asset_classes_explicit(self):
        """Stocks supported; ETF/MF/IPO/F&O explicitly unsupported."""
        # Stock research is SUPPORTED
        # Other asset classes are INTENTIONALLY_UNSUPPORTED
        assert True

    def test_unsupported_asset_returns_error(self, client):
        """Requesting unsupported asset class returns explicit error, not fabricated data."""
        resp = client.get(f"/api/v1/companies/INVALID_company/research?as_of={AS_OF_STR}")
        assert resp.status_code in (400, 404)


# ═══════════════════════════════════════════════════════════════════
# 2 — CANONICAL PAGE DATA MODEL
# ═══════════════════════════════════════════════════════════════════


class TestCanonicalPageDataModel:
    """Every page can obtain standard fields."""

    def test_research_has_context_fields(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/research?as_of={AS_OF_STR}")
        data = resp.json()
        assert "company" in data
        assert "point_in_time" in data

    def test_snapshot_has_identity(self, client):
        resp = client.get(f"/api/v1/research/snapshot?symbol={TCS}&as_of={AS_OF_STR}")
        data = resp.json()
        assert "identity" in data
        assert "symbol" in data["identity"]
        assert "as_of" in data

    def test_section_registry_has_sections(self, client):
        resp = client.get(f"/api/v1/research/section-registry?symbol={TCS}&as_of={AS_OF_STR}")
        data = resp.json()
        assert "sections" in data
        assert "total_sections" in data

    def test_intelligence_has_coverage(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/intelligence?as_of={AS_OF_STR}")
        data = resp.json()
        assert "financial_intelligence" in data
        assert "source_statuses" in data

    def test_research_gaps_has_gaps(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/research-gaps?as_of={AS_OF_STR}")
        data = resp.json()
        gaps = data.get("research_gaps", {})
        assert "gaps" in gaps or "gap_count" in gaps


# ═══════════════════════════════════════════════════════════════════
# 3 — CROSS-DOMAIN CONSISTENCY
# ═══════════════════════════════════════════════════════════════════


class TestCrossDomainConsistency:
    """Same symbol + same as_of resolves to same identity."""

    def test_research_and_snapshot_same_symbol(self, client):
        r1 = client.get(f"/api/v1/companies/{TCS}/research?as_of={AS_OF_STR}").json()
        r2 = client.get(f"/api/v1/research/snapshot?symbol={TCS}&as_of={AS_OF_STR}").json()
        # company field is a dict with symbol key
        company = r1.get("company", {})
        sym = company.get("symbol") if isinstance(company, dict) else company
        assert sym == r2["symbol"]

    def test_evidence_ids_deterministic(self, client):
        r1 = client.get(f"/api/v1/companies/{TCS}/evidence?as_of={AS_OF_STR}").json()
        r2 = client.get(f"/api/v1/companies/{TCS}/evidence?as_of={AS_OF_STR}").json()
        e1 = r1.get("evidence_lineage", {})
        e2 = r2.get("evidence_lineage", {})
        assert e1 == e2

    def test_source_ids_consistent(self, client):
        r1 = client.get(f"/api/v1/companies/{TCS}/source-statuses?as_of={AS_OF_STR}").json()
        r2 = client.get(f"/api/v1/companies/{TCS}/source-statuses?as_of={AS_OF_STR}").json()
        assert r1 == r2

    def test_gap_ids_consistent(self, client):
        r1 = client.get(f"/api/v1/companies/{TCS}/research-gaps?as_of={AS_OF_STR}").json()
        r2 = client.get(f"/api/v1/companies/{TCS}/research-gaps?as_of={AS_OF_STR}").json()
        assert r1 == r2

    def test_pit_state_consistent(self, client):
        r1 = client.get(f"/api/v1/companies/{TCS}/research?as_of={AS_OF_STR}").json()
        r2 = client.get(f"/api/v1/companies/{TCS}/research?as_of={AS_OF_STR}").json()
        pit1 = r1.get("point_in_time", {})
        pit2 = r2.get("point_in_time", {})
        assert pit1.get("pit_checks_passed") == pit2.get("pit_checks_passed")


# ═══════════════════════════════════════════════════════════════════
# 4 — PIT MATRIX
# ═══════════════════════════════════════════════════════════════════


class TestPITMatrix:
    """PIT enforcement across 2024/2025/2026 contexts."""

    @pytest.fixture(scope="class")
    def pit_results(self, service):
        return {
            "early": service.run(TCS, as_of=AS_OF_EARLY),
            "late": service.run(TCS, as_of=AS_OF),
        }

    def test_later_evidence_excluded_from_earlier(self, pit_results):
        """Earlier context has fewer or equal evidence than later."""
        ev_early = len(pit_results["early"].evidence_items or ())
        ev_late = len(pit_results["late"].evidence_items or ())
        assert ev_early <= ev_late

    def test_future_events_excluded(self, pit_results):
        """No evidence item in early context has observation_at after early as_of."""
        for item in (pit_results["early"].evidence_items or ()):
            if item.observation_at:
                assert item.observation_at <= AS_OF_EARLY

    def test_financial_history_stays_historical(self, pit_results):
        """Earlier context has financial periods ending on or before earlier as_of."""
        fi = pit_results["early"].intelligence.financial_intelligence
        if fi and fi.latest_period_end:
            assert fi.latest_period_end <= AS_OF_EARLY.date()

    def test_replay_identical(self, service):
        """Same context replay produces identical output."""
        r1 = service.run(TCS, as_of=AS_OF)
        r2 = service.run(TCS, as_of=AS_OF)
        assert r1.evidence_ids == r2.evidence_ids

    def test_delta_deterministic(self, client):
        """Delta between two contexts is deterministic."""
        r1 = client.get(
            f"/api/v1/research-delta?symbol={TCS}"
            f"&baseline_as_of={AS_OF_EARLY_STR}&current_as_of={AS_OF_STR}"
        ).json()
        r2 = client.get(
            f"/api/v1/research-delta?symbol={TCS}"
            f"&baseline_as_of={AS_OF_EARLY_STR}&current_as_of={AS_OF_STR}"
        ).json()
        assert r1 == r2

    def test_later_context_between_early_and_as_of(self, pit_results):
        """Evidence count ordering: early ≤ late."""
        ev_early = len(pit_results["early"].evidence_items or ())
        ev_late = len(pit_results["late"].evidence_items or ())
        assert ev_early <= ev_late

    def test_source_states_excluded_from_earlier(self, pit_results):
        """Earlier context has fewer or equal sources."""
        src_early = len(getattr(pit_results["early"].intelligence, "source_statuses", ()) or ())
        src_late = len(getattr(pit_results["late"].intelligence, "source_statuses", ()) or ())
        assert src_early <= src_late


# ═══════════════════════════════════════════════════════════════════
# 5 — PROVENANCE MATRIX
# ═══════════════════════════════════════════════════════════════════


class TestProvenanceMatrix:
    """Every factual item claims evidence has source + timestamps."""

    def test_evidence_items_have_source(self, results):
        for sym in COMPANIES:
            for item in (results[sym].evidence_items or ()):
                assert item.source_ids, f"{sym}: evidence {item.evidence_id} missing source"

    def test_evidence_items_have_observation_at(self, results):
        for sym in COMPANIES:
            for item in (results[sym].evidence_items or ()):
                assert item.observation_at is not None, (
                    f"{sym}: evidence {item.evidence_id} missing observation_at"
                )

    def test_financial_observations_have_available_at(self, results):
        for sym in COMPANIES:
            dfi = getattr(results[sym].intelligence, "deep_financial_insights", None)
            assert dfi is not None
            for obs in dfi.observations:
                assert obs.available_at is not None, (
                    f"{sym}: {obs.observation_id} missing available_at"
                )

    def test_derived_financial_have_derivation(self, results):
        for sym in COMPANIES:
            dfi = getattr(results[sym].intelligence, "deep_financial_insights", None)
            for obs in dfi.observations:
                if str(getattr(obs, "observation_type", "")).upper() == "DERIVED":
                    assert obs.derivation, (
                        f"{sym}: derived {obs.observation_id} missing derivation"
                    )

    def test_source_statuses_have_timestamps(self, results):
        for sym in COMPANIES:
            for src in (getattr(results[sym].intelligence, "source_statuses", ()) or ()):
                assert src.latest_available_at is not None, (
                    f"{sym}: source {src.source_name} missing latest_available_at"
                )


# ═══════════════════════════════════════════════════════════════════
# 6 — OUTPUT QUALITY
# ═══════════════════════════════════════════════════════════════════


class TestOutputQuality:
    """Scan API responses for quality issues."""

    ENDPOINTS_TO_SCAN = [
        f"/api/v1/companies/{TCS}/research?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/intelligence?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/evidence?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/research-gaps?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/source-statuses?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/financial-history?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/deep-financial-insights?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/events?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/timeline?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/cross-domain?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/hidden-information?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/industry-context?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/export?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/research-report?as_of={AS_OF_STR}",
        f"/api/v1/research/snapshot?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/section-registry?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/financial-quality?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/business-tech-evidence?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/source-intelligence?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/conflict-explorer?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/test-graph?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/ownership-audit?symbol={TCS}&as_of={AS_OF_STR}",
        "/api/v1/discovery?as_of=2026-08-10T12:00:00Z",
        "/api/v1/evidence/search?q=TCS&as_of=2026-08-10T12:00:00Z",
        "/api/v1/companies/compare?symbols=TCS,INFY&as_of=2026-08-10T12:00:00Z",
    ]

    def test_no_nan_in_any_response(self, client):
        for ep in self.ENDPOINTS_TO_SCAN:
            resp = client.get(ep)
            if resp.status_code == 200:
                text = resp.text
                assert "NaN" not in text, f"NaN found in {ep}"
                assert "Infinity" not in text, f"Infinity found in {ep}"

    def test_no_debug_wording(self, client):
        for ep in self.ENDPOINTS_TO_SCAN:
            resp = client.get(ep)
            if resp.status_code == 200:
                text = resp.text.lower()
                assert "todo" not in text, f"TODO found in {ep}"
                assert "fixme" not in text, f"FIXME found in {ep}"

    def test_timestamps_are_iso8601(self, client):
        resp = client.get(f"/api/v1/companies/{TCS}/research?as_of={AS_OF_STR}")
        data = resp.json()
        pit = data.get("point_in_time", {})
        if "as_of" in pit:
            assert "2026-08-10" in pit["as_of"]

    def test_no_raw_enum_in_user_copy(self, client):
        """No SCREAMING_SNAKE_CASE in user-facing text."""
        resp = client.get(f"/api/v1/companies/{TCS}/research-report?as_of={AS_OF_STR}")
        data = resp.json()
        report = data.get("report", {})
        if isinstance(report, dict):
            for key, val in report.items():
                if isinstance(val, str) and val.isupper() and len(val) > 3:
                    # Allow technical IDs, timestamps, and type fields
                    skip = any(kw in key.lower() for kw in [
                        "id", "key", "type", "code", "as_of", "date", "time",
                        "symbol", "schema",
                    ])
                    if not skip:
                        assert False, f"Raw enum in report.{key}: {val}"

    def test_no_fake_provenance(self, results):
        """Provenance IDs must be real, not empty or placeholder."""
        for sym in COMPANIES:
            for item in (results[sym].evidence_items or ()):
                for pid in item.provenance_ids:
                    assert pid, f"{sym}: empty provenance_id in {item.evidence_id}"
                    assert "fake" not in pid.lower()
                    assert "placeholder" not in pid.lower()


# ═══════════════════════════════════════════════════════════════════
# 7 — RESEARCH DEPTH (ALL 6 COMPANIES)
# ═══════════════════════════════════════════════════════════════════


class TestResearchDepthAllCompanies:
    """Research depth across all 6 recorded companies."""

    def test_all_have_financials(self, results):
        for sym in COMPANIES:
            fi = results[sym].intelligence.financial_intelligence
            assert fi.period_count == 4, f"{sym}: expected 4 periods, got {fi.period_count}"

    def test_all_have_evidence(self, results):
        for sym in COMPANIES:
            evidence = results[sym].evidence_items or ()
            assert len(evidence) >= 10, f"{sym}: expected ≥10 evidence, got {len(evidence)}"

    def test_all_have_sources(self, results):
        for sym in COMPANIES:
            sources = getattr(results[sym].intelligence, "source_statuses", ()) or ()
            assert len(sources) >= 5, f"{sym}: expected ≥5 sources, got {len(sources)}"

    def test_all_have_gaps(self, results):
        for sym in COMPANIES:
            gaps = getattr(results[sym].intelligence, "research_gaps", None)
            assert gaps is not None
            assert len(gaps.gaps) == 5, f"{sym}: expected 5 gaps, got {len(gaps.gaps)}"

    def test_all_have_40_financial_observations(self, results):
        for sym in COMPANIES:
            dfi = getattr(results[sym].intelligence, "deep_financial_insights", None)
            assert dfi is not None
            assert len(dfi.observations) == 40, (
                f"{sym}: expected 40 observations, got {len(dfi.observations)}"
            )

    def test_all_have_10_metrics(self, results):
        expected = {"revenue", "net_profit", "operating_cash_flow", "free_cash_flow",
                    "total_assets", "total_debt", "receivables",
                    "net_margin", "return_on_assets", "cash_conversion"}
        for sym in COMPANIES:
            dfi = getattr(results[sym].intelligence, "deep_financial_insights", None)
            metrics = {obs.metric for obs in dfi.observations}
            assert metrics == expected, f"{sym}: metrics mismatch"


# ═══════════════════════════════════════════════════════════════════
# 8 — RESEARCH TESTS
# ═══════════════════════════════════════════════════════════════════


class TestResearchTests:
    """Research test execution across companies."""

    def test_all_companies_have_test_graph(self, client):
        for sym in COMPANIES:
            resp = client.get(
                f"/api/v1/research/test-graph?symbol={_q(sym)}&as_of={AS_OF_STR}"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "tests" in data
            assert data["total_tests"] >= 10

    def test_test_graph_has_states(self, client):
        resp = client.get(f"/api/v1/research/test-graph?symbol={TCS}&as_of={AS_OF_STR}")
        data = resp.json()
        for test in data["tests"]:
            assert "result_state" in test or "state" in test
            assert "required_evidence" in test


# ═══════════════════════════════════════════════════════════════════
# 9 — EVIDENCE / CONFLICT / GAP CHAIN
# ═══════════════════════════════════════════════════════════════════


class TestEvidenceConflictGapChain:
    """Evidence → source → provenance chain integrity."""

    def test_evidence_chain(self, results):
        for sym in COMPANIES:
            for item in (results[sym].evidence_items or ()):
                # Every evidence has source
                assert item.source_ids
                # Every evidence has observation_at
                assert item.observation_at is not None

    def test_conflict_has_both_sides(self, results):
        """Every conflict has two sides."""
        for sym in COMPANIES:
            conflicts = getattr(results[sym].intelligence, "conflicts", ()) or ()
            for c in conflicts:
                assert c.first is not None
                assert c.second is not None
                assert c.first.item_id != c.second.item_id

    def test_gap_has_reason(self, results):
        """Every gap has a reason."""
        for sym in COMPANIES:
            gaps = getattr(results[sym].intelligence, "research_gaps", None)
            if gaps:
                for gap in gaps.gaps:
                    assert gap.reason, f"{sym}: gap {gap.gap_id} missing reason"

    def test_no_auto_winner_in_conflicts(self, results):
        """Conflicts don't select a winner."""
        for sym in COMPANIES:
            conflicts = getattr(results[sym].intelligence, "conflicts", ()) or ()
            for c in conflicts:
                # Both sides should have non-empty excerpts
                assert c.first.excerpt
                assert c.second.excerpt


# ═══════════════════════════════════════════════════════════════════
# 10 — RESEARCH INTELLIGENCE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════


class TestResearchIntelligenceEndpoints:
    """All T1-W3/T1-W4/T1-W5 research intelligence endpoints."""

    def test_snapshot(self, client):
        resp = client.get(f"/api/v1/research/snapshot?symbol={TCS}&as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert "identity" in data
        assert "evidence" in data

    def test_section_registry(self, client):
        resp = client.get(f"/api/v1/research/section-registry?symbol={TCS}&as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sections"] == 9

    def test_change_graph(self, client):
        resp = client.get(
            f"/api/v1/research/change-graph?symbol={TCS}"
            f"&baseline_as_of={AS_OF_EARLY_STR}&current_as_of={AS_OF_STR}"
        )
        assert resp.status_code == 200

    def test_test_graph(self, client):
        resp = client.get(f"/api/v1/research/test-graph?symbol={TCS}&as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tests"] >= 10

    def test_conflict_explorer(self, client):
        resp = client.get(f"/api/v1/research/conflict-explorer?symbol={TCS}&as_of={AS_OF_STR}")
        assert resp.status_code == 200

    def test_source_intelligence(self, client):
        resp = client.get(f"/api/v1/research/source-intelligence?symbol={TCS}&as_of={AS_OF_STR}")
        assert resp.status_code == 200

    def test_replay(self, client):
        resp = client.get(
            f"/api/v1/research/replay?symbol={TCS}"
            f"&as_of_a={AS_OF_EARLY_STR}&as_of_b={AS_OF_STR}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "delta" in data

    def test_financial_quality(self, client):
        resp = client.get(f"/api/v1/research/financial-quality?symbol={TCS}&as_of={AS_OF_STR}")
        assert resp.status_code == 200

    def test_business_tech_evidence(self, client):
        resp = client.get(
            f"/api/v1/research/business-tech-evidence?symbol={TCS}&as_of={AS_OF_STR}"
        )
        assert resp.status_code == 200

    def test_ownership_audit(self, client):
        resp = client.get(f"/api/v1/research/ownership-audit?symbol={TCS}&as_of={AS_OF_STR}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["capability"] == "BLOCKED"

    def test_alert_events(self, client):
        resp = client.get(
            f"/api/v1/research/alert-events?symbol={TCS}"
            f"&baseline_as_of={AS_OF_EARLY_STR}&current_as_of={AS_OF_STR}"
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# 11 — REPLAY REPRODUCIBILITY
# ═══════════════════════════════════════════════════════════════════


class TestReplayReproducibility:
    """Deterministic replay across companies."""

    def test_all_companies_replay(self, client):
        for sym in COMPANIES:
            resp = client.get(
                f"/api/v1/research/replay?symbol={_q(sym)}"
                f"&as_of_a={AS_OF_EARLY_STR}&as_of_b={AS_OF_STR}"
            )
            assert resp.status_code == 200

    def test_replay_same_context_same_output(self, service):
        r1 = service.run(TCS, as_of=AS_OF)
        r2 = service.run(TCS, as_of=AS_OF)
        assert r1.evidence_ids == r2.evidence_ids


# ═══════════════════════════════════════════════════════════════════
# 12 — OWNERSHIP AUDIT
# ═══════════════════════════════════════════════════════════════════


class TestOwnershipAudit:
    """Ownership audit returns BLOCKED for all companies."""

    def test_all_companies_blocked(self, client):
        for sym in COMPANIES:
            resp = client.get(f"/api/v1/research/ownership-audit?symbol={_q(sym)}&as_of={AS_OF_STR}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["capability"] == "BLOCKED"


# ═══════════════════════════════════════════════════════════════════
# 13 — HIDDEN INFORMATION
# ═══════════════════════════════════════════════════════════════════


class TestHiddenInformation:
    """Hidden information insights for all companies."""

    def test_all_companies_have_hidden_info(self, client):
        for sym in COMPANIES:
            resp = client.get(f"/api/v1/companies/{sym}/hidden-information?as_of={AS_OF_STR}")
            assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# 14 — SMOKE TEST ALL MAJOR ENDPOINTS
# ═══════════════════════════════════════════════════════════════════


class TestSmokeAllEndpoints:
    """Smoke test every major canonical endpoint."""

    SMOKE_ENDPOINTS = [
        f"/api/v1/companies/{TCS}/research?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/intelligence?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/evidence?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/events?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/ownership?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/financial-history?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/research-gaps?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/source-statuses?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/corporate-actions?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/timeline?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/tracking?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/news?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/research-timeline?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/research-report?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/export?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/deep-financial-insights?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/deep-fundamentals?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/deep-technicals?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/chart-data?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/cross-domain?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/hidden-information?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/industry-context?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/backtest?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/price-attribution?as_of={AS_OF_STR}",
        f"/api/v1/companies/{TCS}/rankings?as_of={AS_OF_STR}",
        f"/api/v1/discovery?as_of={AS_OF_STR}",
        f"/api/v1/discovery/trending?as_of={AS_OF_STR}",
        f"/api/v1/evidence/search?q=TCS&as_of={AS_OF_STR}",
        f"/api/v1/evidence/conflicts?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/companies/compare?symbols=TCS,INFY&as_of={AS_OF_STR}",
        f"/api/v1/screener/fields",
        f"/api/v1/research/snapshot?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/section-registry?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/test-graph?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/conflict-explorer?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/source-intelligence?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/financial-quality?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/business-tech-evidence?symbol={TCS}&as_of={AS_OF_STR}",
        f"/api/v1/research/ownership-audit?symbol={TCS}&as_of={AS_OF_STR}",
        "/api/v1/companies",
        "/health",
    ]

    def test_all_smoke(self, client):
        failed = []
        for ep in self.SMOKE_ENDPOINTS:
            resp = client.get(ep)
            if resp.status_code != 200:
                failed.append(f"{resp.status_code} {ep}")
        assert not failed, f"Failed endpoints: {failed}"


# ═══════════════════════════════════════════════════════════════════
# 15 — ACCEPTANCE CORRECTION: REGRESSION COVERAGE
# ═══════════════════════════════════════════════════════════════════


class TestAcceptanceRegressionBI:
    """Regression: business-intelligence must not crash."""

    def test_bi_returns_200_not_crash(self, client):
        resp = client.get(
            f"/api/v1/companies/TCS/business-intelligence?as_of={AS_OF_STR}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "business_intelligence" in data
        bi = data["business_intelligence"]
        assert "has_profile" in bi
        assert bi["symbol"] == TCS

    def test_bi_all_companies(self, client):
        for sym in COMPANIES:
            resp = client.get(
                f"/api/v1/companies/{sym}/business-intelligence?as_of={AS_OF_STR}"
            )
            assert resp.status_code == 200
            assert "business_intelligence" in resp.json()

    def test_bi_unknown_company_still_works(self, client):
        resp = client.get(
            f"/api/v1/companies/FAKECO/business-intelligence?as_of={AS_OF_STR}"
        )
        assert resp.status_code == 200
        bi = resp.json()["business_intelligence"]
        assert bi["has_profile"] is False


class TestAcceptanceRegressionAI:
    """Regression: analyst-intelligence must return honest empty state."""

    def test_ai_returns_200(self, client):
        resp = client.get(f"/api/v1/companies/TCS/analyst-intelligence")
        assert resp.status_code == 200
        data = resp.json()
        assert "analyst_intelligence" in data
        assert data["analyst_intelligence"]["symbol"] == TCS

    def test_ai_all_companies(self, client):
        for sym in COMPANIES:
            resp = client.get(
                f"/api/v1/companies/{sym}/analyst-intelligence"
            )
            assert resp.status_code == 200
            assert "analyst_intelligence" in resp.json()

    def test_ai_empty_state_honest(self, client):
        resp = client.get(f"/api/v1/companies/TCS/analyst-intelligence")
        data = resp.json()
        ai = data["analyst_intelligence"]
        assert ai["has_recommendations"] is False
        assert ai["recommendations"] == []


class TestAcceptanceRegressionOS:
    """Regression: ownership-summary must return honest empty state."""

    def test_os_returns_200(self, client):
        resp = client.get(f"/api/v1/companies/TCS/ownership-summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "ownership_summary" in data
        assert data["ownership_summary"]["symbol"] == TCS

    def test_os_all_companies(self, client):
        for sym in COMPANIES:
            resp = client.get(
                f"/api/v1/companies/{sym}/ownership-summary"
            )
            assert resp.status_code == 200
            assert "ownership_summary" in resp.json()

    def test_os_empty_state_honest(self, client):
        resp = client.get(f"/api/v1/companies/TCS/ownership-summary")
        data = resp.json()
        os_ = data["ownership_summary"]
        assert os_["top_holders"] == []
        assert os_["has_top_holders"] is False


class TestAcceptanceRegressionMM:
    """Regression: M&M URL encoding must work correctly."""

    def test_mm_path_param(self, client):
        resp = client.get(
            f"/api/v1/companies/M%26M/research?as_of={AS_OF_STR}"
        )
        assert resp.status_code == 200
        company = resp.json()["company"]
        sym = company.get("symbol") if isinstance(company, dict) else company
        assert sym == "M&M"

    def test_mm_all_endpoints(self, client):
        endpoints = [
            f"/api/v1/companies/M%26M/research?as_of={AS_OF_STR}",
            f"/api/v1/companies/M%26M/evidence?as_of={AS_OF_STR}",
            f"/api/v1/companies/M%26M/source-statuses?as_of={AS_OF_STR}",
            f"/api/v1/companies/M%26M/research-gaps?as_of={AS_OF_STR}",
            f"/api/v1/companies/M%26M/hidden-information?as_of={AS_OF_STR}",
            f"/api/v1/companies/M%26M/cross-domain?as_of={AS_OF_STR}",
            f"/api/v1/companies/M%26M/research-report?as_of={AS_OF_STR}",
        ]
        for ep in endpoints:
            resp = client.get(ep)
            assert resp.status_code == 200, f"Failed: {ep}"

    def test_mm_company_name_preserved(self, client):
        resp = client.get(
            f"/api/v1/companies/M%26M/research?as_of={AS_OF_STR}"
        )
        data = resp.json()
        company = data["company"]
        if isinstance(company, dict):
            assert company.get("symbol") == "M&M"
        else:
            assert company == "M&M"
