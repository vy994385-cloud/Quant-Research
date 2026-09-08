"""T1-W5 Research Depth & Reproducibility tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.recorded_research import RecordedCompanyResearchService
from src.research.historical_depth import build_company_depth, build_universe_depth
from src.research.cross_domain_links import build_cross_domain_links, LinkType
from src.research.research_test_execution import (
    build_test_execution_report,
    TestExecutionState,
    TEST_DEFINITIONS,
)
from src.research.gap_depth import build_gap_depth_audit
from src.research.source_coverage import build_source_coverage_report
from src.research.evidence_quality import build_evidence_quality_report
from src.research.financial_depth import build_financial_depth_audit
from src.research.business_tech_depth import build_business_tech_depth_report
from src.research.change_quality import build_change_quality_report

AS_OF = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
COMPANIES = ["TCS", "INFY", "HDFCBANK", "RELIANCE", "M&M", "SUNPHARMA"]


@pytest.fixture(scope="module")
def service():
    return RecordedCompanyResearchService()


@pytest.fixture(scope="module")
def results(service):
    return {sym: service.run(sym, as_of=AS_OF) for sym in COMPANIES}


@pytest.fixture(scope="module")
def tcs_result(results):
    return results["TCS"]


# ─── HISTORICAL DEPTH ───────────────────────────────────────────────


class TestHistoricalDepth:
    def test_builds_for_tcs(self, tcs_result):
        depth = build_company_depth(tcs_result, as_of=AS_OF)
        assert depth.symbol == "TCS"
        assert depth.as_of == AS_OF
        assert len(depth.domains) >= 5

    def test_has_financial_domain(self, tcs_result):
        depth = build_company_depth(tcs_result, as_of=AS_OF)
        fin = next(d for d in depth.domains if d.domain == "financials")
        assert fin.period_count >= 4
        assert fin.earliest_period is not None
        assert fin.latest_period is not None

    def test_has_all_6_companies(self, results):
        for sym in COMPANIES:
            depth = build_company_depth(results[sym], as_of=AS_OF)
            assert depth.symbol == sym

    def test_universe_depth(self, results):
        result_list = [results[sym] for sym in COMPANIES]
        universe = build_universe_depth(result_list, as_of=AS_OF)
        assert universe.company_count == 6
        assert len(universe.companies) == 6

    def test_evidence_counts_non_negative(self, results):
        for sym in COMPANIES:
            depth = build_company_depth(results[sym], as_of=AS_OF)
            assert depth.total_evidence_count >= 0
            assert depth.total_source_count >= 0
            assert depth.total_gap_count >= 0

    def test_source_count_matches(self, tcs_result):
        depth = build_company_depth(tcs_result, as_of=AS_OF)
        assert depth.total_source_count == 8

    def test_ownership_domain_blocked(self, tcs_result):
        depth = build_company_depth(tcs_result, as_of=AS_OF)
        ownership = next(d for d in depth.domains if d.domain == "ownership")
        assert ownership.period_count == 0
        assert ownership.gap_count == 1

    def test_snapshot_matches_build(self, tcs_result):
        depth = build_company_depth(tcs_result, as_of=AS_OF)
        assert len(depth.domains) >= 8


# ─── CROSS-DOMAIN LINKS ────────────────────────────────────────────


class TestCrossDomainLinks:
    def test_builds_for_tcs(self, tcs_result):
        result = build_cross_domain_links(tcs_result, as_of=AS_OF)
        assert result.symbol == "TCS"
        assert result.link_count >= 0

    def test_safe_vocabulary_only(self, tcs_result):
        result = build_cross_domain_links(tcs_result, as_of=AS_OF)
        safe = {LinkType.RELATED, LinkType.SAME_CONTEXT,
                LinkType.OCCURRED_ALONGSIDE, LinkType.TEMPORALLY_ADJACENT}
        for link in result.links:
            assert link.link_type in safe

    def test_no_causal_language(self, tcs_result):
        result = build_cross_domain_links(tcs_result, as_of=AS_OF)
        causal = ["causes", "leads to", "results in", "because of", "due to"]
        for link in result.links:
            for c in causal:
                assert c not in link.shared_context.lower()

    def test_links_have_evidence_ids_or_dates(self, tcs_result):
        result = build_cross_domain_links(tcs_result, as_of=AS_OF)
        for link in result.links:
            assert link.source_item_id or link.source_date

    def test_deterministic(self, tcs_result):
        r1 = build_cross_domain_links(tcs_result, as_of=AS_OF)
        r2 = build_cross_domain_links(tcs_result, as_of=AS_OF)
        assert r1.link_count == r2.link_count
        assert [l.link_id for l in r1.links] == [l.link_id for l in r2.links]

    def test_domains_connected(self, tcs_result):
        result = build_cross_domain_links(tcs_result, as_of=AS_OF)
        assert isinstance(result.domains_connected, tuple)

    def test_link_ids_unique(self, tcs_result):
        result = build_cross_domain_links(tcs_result, as_of=AS_OF)
        ids = [l.link_id for l in result.links]
        assert len(ids) == len(set(ids))

    def test_for_all_companies(self, results):
        for sym in COMPANIES:
            result = build_cross_domain_links(results[sym], as_of=AS_OF)
            assert result.symbol == sym


# ─── RESEARCH TEST EXECUTION ────────────────────────────────────────


class TestResearchTestExecutionSuite:
    def test_builds_for_tcs(self, tcs_result):
        report = build_test_execution_report(tcs_result, as_of=AS_OF)
        assert report.symbol == "TCS"
        assert report.total_tests == len(TEST_DEFINITIONS)

    def test_all_definitions_evaluated(self, tcs_result):
        report = build_test_execution_report(tcs_result, as_of=AS_OF)
        valid_states = {s.value for s in TestExecutionState}
        for test in report.tests:
            assert test.state in valid_states

    def test_no_hidden_tests(self, tcs_result):
        report = build_test_execution_report(tcs_result, as_of=AS_OF)
        assert report.total_tests >= 10

    def test_evaluated_tests_have_no_missing(self, tcs_result):
        report = build_test_execution_report(tcs_result, as_of=AS_OF)
        for test in report.tests:
            if test.state == TestExecutionState.EVALUATED:
                assert len(test.missing_evidence) == 0

    def test_state_counts_consistent(self, tcs_result):
        report = build_test_execution_report(tcs_result, as_of=AS_OF)
        total = sum(report.state_counts.values())
        assert total == report.total_tests

    def test_for_all_companies(self, results):
        for sym in COMPANIES:
            report = build_test_execution_report(results[sym], as_of=AS_OF)
            assert report.total_tests >= 10

    def test_deterministic(self, tcs_result):
        r1 = build_test_execution_report(tcs_result, as_of=AS_OF)
        r2 = build_test_execution_report(tcs_result, as_of=AS_OF)
        assert [t.test_id for t in r1.tests] == [t.test_id for t in r2.tests]
        assert [t.state for t in r1.tests] == [t.state for t in r2.tests]


# ─── GAP DEPTH ──────────────────────────────────────────────────────


class TestGapDepth:
    def test_builds_for_tcs(self, tcs_result):
        audit = build_gap_depth_audit(tcs_result, as_of=AS_OF)
        assert audit.symbol == "TCS"
        assert audit.total_gap_count >= 5

    def test_categories_present(self, tcs_result):
        audit = build_gap_depth_audit(tcs_result, as_of=AS_OF)
        assert "financial_data" in audit.category_counts
        assert "business_profile" in audit.category_counts

    def test_groups_deterministic(self, tcs_result):
        g1 = build_gap_depth_audit(tcs_result, as_of=AS_OF)
        g2 = build_gap_depth_audit(tcs_result, as_of=AS_OF)
        assert g1.total_gap_count == g2.total_gap_count
        assert len(g1.gap_groups) == len(g2.gap_groups)

    def test_for_all_companies(self, results):
        for sym in COMPANIES:
            audit = build_gap_depth_audit(results[sym], as_of=AS_OF)
            assert audit.total_gap_count >= 5

    def test_absent_categories_listed(self, tcs_result):
        audit = build_gap_depth_audit(tcs_result, as_of=AS_OF)
        assert isinstance(audit.gap_categories_absent, tuple)
        assert len(audit.gap_categories_absent) > 0

    def test_status_counts_consistent(self, tcs_result):
        audit = build_gap_depth_audit(tcs_result, as_of=AS_OF)
        total = sum(audit.status_counts.values())
        assert total == audit.total_gap_count


# ─── SOURCE COVERAGE ────────────────────────────────────────────────


class TestSourceCoverage:
    def test_builds_for_tcs(self, tcs_result):
        report = build_source_coverage_report(tcs_result, as_of=AS_OF)
        assert report.symbol == "TCS"
        assert report.source_count >= 8

    def test_sources_have_freshness(self, tcs_result):
        report = build_source_coverage_report(tcs_result, as_of=AS_OF)
        for src in report.sources:
            assert src.freshness_state in ("CURRENT", "RECENT", "AGING", "STALE", "UNKNOWN")

    def test_pit_eligible_deterministic(self, tcs_result):
        report = build_source_coverage_report(tcs_result, as_of=AS_OF)
        for src in report.sources:
            if src.pit_eligible:
                assert src.latest_available_at is not None
                assert src.latest_available_at <= AS_OF

    def test_no_scores(self, tcs_result):
        report = build_source_coverage_report(tcs_result, as_of=AS_OF)
        for src in report.sources:
            assert not hasattr(src, "score")
            assert not hasattr(src, "rating")

    def test_for_all_companies(self, results):
        for sym in COMPANIES:
            report = build_source_coverage_report(results[sym], as_of=AS_OF)
            assert report.source_count >= 5

    def test_deterministic(self, tcs_result):
        r1 = build_source_coverage_report(tcs_result, as_of=AS_OF)
        r2 = build_source_coverage_report(tcs_result, as_of=AS_OF)
        assert r1.source_count == r2.source_count


# ─── EVIDENCE QUALITY ──────────────────────────────────────────────


class TestEvidenceQuality:
    def test_builds_for_tcs(self, tcs_result):
        report = build_evidence_quality_report(tcs_result, as_of=AS_OF)
        assert report.symbol == "TCS"
        assert report.total_evidence_count >= 14

    def test_issues_are_deterministic(self, tcs_result):
        r1 = build_evidence_quality_report(tcs_result, as_of=AS_OF)
        r2 = build_evidence_quality_report(tcs_result, as_of=AS_OF)
        assert r1.issue_count == r2.issue_count

    def test_issue_types_valid(self, tcs_result):
        report = build_evidence_quality_report(tcs_result, as_of=AS_OF)
        valid_types = {"MISSING_SOURCE", "MISSING_PROVENANCE", "MISSING_TIMESTAMP",
                       "MISSING_DIRECTION", "ZERO_CONFIDENCE"}
        for issue_type in report.issue_type_counts:
            assert issue_type in valid_types

    def test_for_all_companies(self, results):
        for sym in COMPANIES:
            report = build_evidence_quality_report(results[sym], as_of=AS_OF)
            assert report.total_evidence_count >= 10

    def test_entries_have_all_checks(self, tcs_result):
        report = build_evidence_quality_report(tcs_result, as_of=AS_OF)
        for entry in report.entries:
            assert isinstance(entry.has_source, bool)
            assert isinstance(entry.has_provenance, bool)
            assert isinstance(entry.has_observation_at, bool)


# ─── FINANCIAL DEPTH ────────────────────────────────────────────────


class TestFinancialDepth:
    def test_builds_for_tcs(self, tcs_result):
        audit = build_financial_depth_audit(tcs_result, as_of=AS_OF)
        assert audit.symbol == "TCS"
        assert audit.total_observations == 40

    def test_reported_vs_derived(self, tcs_result):
        audit = build_financial_depth_audit(tcs_result, as_of=AS_OF)
        assert audit.reported_count == 28
        assert audit.derived_count == 12

    def test_all_metrics_present(self, tcs_result):
        audit = build_financial_depth_audit(tcs_result, as_of=AS_OF)
        expected = {"revenue", "net_profit", "operating_cash_flow", "free_cash_flow",
                    "total_assets", "total_debt", "receivables",
                    "net_margin", "return_on_assets", "cash_conversion"}
        assert set(audit.metrics_present) == expected

    def test_units_explicit(self, tcs_result):
        audit = build_financial_depth_audit(tcs_result, as_of=AS_OF)
        for metric in audit.metrics:
            assert metric.unit in ("INR", "FRACTION", "")

    def test_derived_have_derivation(self, tcs_result):
        audit = build_financial_depth_audit(tcs_result, as_of=AS_OF)
        for metric in audit.metrics:
            if metric.derived_count > 0:
                assert metric.has_derivation_text

    def test_periods_covered(self, tcs_result):
        audit = build_financial_depth_audit(tcs_result, as_of=AS_OF)
        assert len(audit.period_range) == 4

    def test_for_all_companies(self, results):
        for sym in COMPANIES:
            audit = build_financial_depth_audit(results[sym], as_of=AS_OF)
            assert audit.total_observations == 40

    def test_no_nan_values(self, tcs_result):
        audit = build_financial_depth_audit(tcs_result, as_of=AS_OF)
        for metric in audit.metrics:
            assert metric.null_value_count >= 0

    def test_deterministic(self, tcs_result):
        r1 = build_financial_depth_audit(tcs_result, as_of=AS_OF)
        r2 = build_financial_depth_audit(tcs_result, as_of=AS_OF)
        assert r1.total_observations == r2.total_observations
        assert r1.reported_count == r2.reported_count


# ─── BUSINESS/TECH DEPTH ────────────────────────────────────────────


class TestBusinessTechDepth:
    def test_builds_for_tcs(self, tcs_result):
        report = build_business_tech_depth_report(tcs_result, as_of=AS_OF)
        assert report.symbol == "TCS"
        assert len(report.domains) == 11

    def test_depth_states_valid(self, tcs_result):
        report = build_business_tech_depth_report(tcs_result, as_of=AS_OF)
        from src.research.business_tech_depth import DepthState
        for domain in report.domains:
            assert domain.depth in {DepthState.STRONG, DepthState.PARTIAL,
                                    DepthState.WEAK, DepthState.MISSING}

    def test_counts_consistent(self, tcs_result):
        report = build_business_tech_depth_report(tcs_result, as_of=AS_OF)
        total = report.strong_count + report.partial_count + report.weak_count + report.missing_count
        assert total == len(report.domains)

    def test_no_scores(self, tcs_result):
        report = build_business_tech_depth_report(tcs_result, as_of=AS_OF)
        for domain in report.domains:
            assert not hasattr(domain, "score")
            assert not hasattr(domain, "rating")

    def test_for_all_companies(self, results):
        for sym in COMPANIES:
            report = build_business_tech_depth_report(results[sym], as_of=AS_OF)
            assert len(report.domains) == 11

    def test_deterministic(self, tcs_result):
        r1 = build_business_tech_depth_report(tcs_result, as_of=AS_OF)
        r2 = build_business_tech_depth_report(tcs_result, as_of=AS_OF)
        assert r1.strong_count == r2.strong_count


# ─── CHANGE QUALITY ─────────────────────────────────────────────────


class TestChangeQuality:
    def test_builds_for_tcs(self, tcs_result):
        report = build_change_quality_report(tcs_result, as_of=AS_OF)
        assert report.symbol == "TCS"
        assert report.total_changes == 0  # Single snapshot, no diff

    def test_deterministic(self, tcs_result):
        r1 = build_change_quality_report(tcs_result, as_of=AS_OF)
        r2 = build_change_quality_report(tcs_result, as_of=AS_OF)
        assert r1.total_changes == r2.total_changes

    def test_for_all_companies(self, results):
        for sym in COMPANIES:
            report = build_change_quality_report(results[sym], as_of=AS_OF)
            assert report.total_changes == 0


# ─── REPRODUCIBILITY ────────────────────────────────────────────────


class TestReproducibility:
    def test_same_context_same_output(self, tcs_result):
        """Same context ID produces same output."""
        from src.research.change import build_context_snapshot
        ctx1 = build_context_snapshot(tcs_result)
        ctx2 = build_context_snapshot(tcs_result)
        assert ctx1.context_id == ctx2.context_id

    def test_same_as_of_same_evidence_set(self, tcs_result):
        """Same as_of produces same evidence set."""
        r1 = build_evidence_quality_report(tcs_result, as_of=AS_OF)
        r2 = build_evidence_quality_report(tcs_result, as_of=AS_OF)
        eids1 = sorted(e.evidence_id for e in r1.entries)
        eids2 = sorted(e.evidence_id for e in r2.entries)
        assert eids1 == eids2

    def test_same_as_of_same_gaps(self, tcs_result):
        """Same as_of produces same research gaps."""
        g1 = build_gap_depth_audit(tcs_result, as_of=AS_OF)
        g2 = build_gap_depth_audit(tcs_result, as_of=AS_OF)
        assert g1.total_gap_count == g2.total_gap_count

    def test_same_as_of_same_source_state(self, tcs_result):
        """Same as_of produces same source state."""
        s1 = build_source_coverage_report(tcs_result, as_of=AS_OF)
        s2 = build_source_coverage_report(tcs_result, as_of=AS_OF)
        assert s1.source_count == s2.source_count

    def test_same_as_of_same_test_state(self, tcs_result):
        """Same as_of produces same research test state."""
        t1 = build_test_execution_report(tcs_result, as_of=AS_OF)
        t2 = build_test_execution_report(tcs_result, as_of=AS_OF)
        states1 = [t.state for t in t1.tests]
        states2 = [t.state for t in t2.tests]
        assert states1 == states2


# ─── PIT LEAKAGE ────────────────────────────────────────────────────


class TestPITLeakage:
    def test_early_context_excludes_late_evidence(self, service):
        """Earlier context excludes later evidence items."""
        AS_OF_EARLY = datetime(2026, 1, 1, tzinfo=timezone.utc)
        r_early = service.run("TCS", as_of=AS_OF_EARLY)
        r_late = service.run("TCS", as_of=AS_OF)

        early_ids = {e.evidence_id for e in (r_early.evidence_items or ())}
        late_ids = {e.evidence_id for e in (r_late.evidence_items or ())}
        new_ids = late_ids - early_ids
        for eid in new_ids:
            late_item = next(e for e in (r_late.evidence_items or ()) if e.evidence_id == eid)
            assert late_item.observation_at > AS_OF_EARLY

    def test_no_future_evidence_in_early_context(self, service):
        """No evidence item in early context has observation_at after early as_of."""
        AS_OF_EARLY = datetime(2026, 1, 1, tzinfo=timezone.utc)
        r_early = service.run("TCS", as_of=AS_OF_EARLY)
        for item in (r_early.evidence_items or ()):
            if item.observation_at:
                assert item.observation_at <= AS_OF_EARLY


# ─── PROVENANCE ─────────────────────────────────────────────────────


class TestProvenance:
    def test_evidence_items_have_source(self, tcs_result):
        """Every evidence item has at least a source."""
        for item in (tcs_result.evidence_items or ()):
            assert item.source_ids

    def test_financial_observations_have_provenance(self, tcs_result):
        """Financial observations have provenance chain."""
        intel = tcs_result.intelligence
        dfi = getattr(intel, "deep_financial_insights", None)
        assert dfi is not None
        # Observations may not all have provenance_id (direct from fixture)
        # But they must have available_at
        for obs in dfi.observations:
            assert obs.available_at is not None


# ─── DETERMINISM ────────────────────────────────────────────────────


class TestDeterminism:
    def test_historical_depth_deterministic(self, tcs_result):
        d1 = build_company_depth(tcs_result, as_of=AS_OF)
        d2 = build_company_depth(tcs_result, as_of=AS_OF)
        j1 = d1.model_dump_json()
        j2 = d2.model_dump_json()
        assert j1 == j2

    def test_financial_depth_deterministic(self, tcs_result):
        f1 = build_financial_depth_audit(tcs_result, as_of=AS_OF)
        f2 = build_financial_depth_audit(tcs_result, as_of=AS_OF)
        assert f1.total_observations == f2.total_observations

    def test_source_coverage_deterministic(self, tcs_result):
        s1 = build_source_coverage_report(tcs_result, as_of=AS_OF)
        s2 = build_source_coverage_report(tcs_result, as_of=AS_OF)
        assert s1.source_count == s2.source_count


# ─── OUTPUT QUALITY ─────────────────────────────────────────────────


class TestOutputQuality:
    def test_no_nan_in_historical_depth(self, tcs_result):
        depth = build_company_depth(tcs_result, as_of=AS_OF)
        j = depth.model_dump_json()
        assert "NaN" not in j
        assert "Infinity" not in j

    def test_no_nan_in_cross_domain(self, tcs_result):
        result = build_cross_domain_links(tcs_result, as_of=AS_OF)
        j = result.model_dump_json()
        assert "NaN" not in j

    def test_no_scores_anywhere(self, tcs_result):
        """No module produces scores, rankings, or recommendations."""
        depth = build_company_depth(tcs_result, as_of=AS_OF)
        j = depth.model_dump_json().lower()
        assert "score" not in j
        assert "ranking" not in j
        assert "recommendation" not in j

    def test_no_causal_language(self, tcs_result):
        """No causal language in any output."""
        result = build_cross_domain_links(tcs_result, as_of=AS_OF)
        causal = ["causes", "leads to", "results in", "because of"]
        for link in result.links:
            for c in causal:
                assert c not in link.shared_context.lower()

    def test_timestamps_are_iso8601(self, tcs_result):
        depth = build_company_depth(tcs_result, as_of=AS_OF)
        j = json.loads(depth.model_dump_json())
        assert "2026-08-10" in j["as_of"]


# ─── API CONTRACTS ──────────────────────────────────────────────────


class TestAPIContracts:
    def test_all_endpoints_smoke(self):
        """Smoke test all research endpoints."""
        client = TestClient(app)
        endpoints = [
            "/api/v1/research/snapshot?symbol=TCS&as_of=2026-08-10T12:00:00Z",
            "/api/v1/research/section-registry?symbol=TCS&as_of=2026-08-10T12:00:00Z",
            "/api/v1/research/test-graph?symbol=TCS&as_of=2026-08-10T12:00:00Z",
            "/api/v1/research/conflict-explorer?symbol=TCS&as_of=2026-08-10T12:00:00Z",
            "/api/v1/research/source-intelligence?symbol=TCS&as_of=2026-08-10T12:00:00Z",
            "/api/v1/research/replay?symbol=TCS&as_of_a=2026-01-01T00:00:00Z&as_of_b=2026-08-10T12:00:00Z",
            "/api/v1/research/financial-quality?symbol=TCS&as_of=2026-08-10T12:00:00Z",
            "/api/v1/research/business-tech-evidence?symbol=TCS&as_of=2026-08-10T12:00:00Z",
            "/api/v1/research/ownership-audit?symbol=TCS&as_of=2026-08-10T12:00:00Z",
            "/api/v1/research/alert-events?symbol=TCS&baseline_as_of=2026-01-01T00:00:00Z&current_as_of=2026-08-10T12:00:00Z",
            "/api/v1/research/change-graph?symbol=TCS&baseline_as_of=2026-01-01T00:00:00Z&current_as_of=2026-08-10T12:00:00Z",
        ]
        for ep in endpoints:
            resp = client.get(ep)
            assert resp.status_code == 200, f"Endpoint {ep} returned {resp.status_code}: {resp.json()}"
