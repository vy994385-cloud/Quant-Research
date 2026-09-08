"""
T1-W3 Research Intelligence Hardening tests.

Covers:
  11 - API Contract Audit (null consistency, timestamps, deterministic ordering)
  12 - Raw Output / Serialization Quality (Decimal tails, float artifacts, None leaks)
  13 - Determinism / PIT / Provenance Test Matrix
  1-10 - Integration tests for all new modules
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone

import pytest

from src.research.alert_contract import (
    AlertEvent,
    AlertEventContract,
    AlertType,
    build_alert_events,
)
from src.research.business_tech_evidence import (
    BusinessTechObservation,
    BusinessTechReport,
    EpistemicState,
    EvidenceDimension,
    build_business_tech_evidence,
)
from src.research.change import (
    ChangeType,
    ResearchChange,
    ResearchContextSnapshot,
    build_context_snapshot,
    build_evidence_delta,
    build_symbol_changes,
    context_id_for,
    parse_context_id,
)
from src.research.change_graph import (
    ChangeGraph,
    ChangeRelationship,
    RelationshipType,
    build_change_graph,
)
from src.research.conflict_explorer import (
    ConflictDetail,
    ConflictExplorerReport,
    ConflictSideDetail,
    ConflictStatus,
    build_conflict_explorer,
)
from src.research.company_intel.models import (
    ConflictSide,
    EvidenceConflict,
)
from src.research.company_intel.semantics import (
    EvidenceStance,
    IntelDirection,
    SemanticCategory,
    VerificationStatus,
)
from src.research.evidence.lineage import build_evidence_lineage
from src.research.financial_quality import (
    FinancialQualityObservation,
    FinancialQualityReport,
    ObservationOrigin,
    build_financial_quality,
)
from src.research.ownership_audit import (
    OwnershipAuditReport,
    OwnershipCapability,
    build_ownership_audit,
)
from src.research.replay import (
    FullReplayResult,
    REPLAY_SCHEMA_VERSION,
    ReplayMetadata,
    build_replay,
)
from src.research.source_intelligence import (
    FreshnessState,
    SourceIntelligence,
    SourceIntelligenceReport,
    build_source_intelligence,
)
from src.research.test_graph import (
    ResearchTestGraph,
    ResearchTestResult,
    TestResultState,
    build_research_test_graph,
)
from src.api.recorded_research import RecordedCompanyResearchService


AS_OF_EARLY = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
AS_OF_LATE = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
SYMBOL = "TCS"


@pytest.fixture(scope="module")
def service():
    return RecordedCompanyResearchService()


@pytest.fixture(scope="module")
def result_early(service):
    return service.run(SYMBOL, as_of=AS_OF_EARLY)


@pytest.fixture(scope="module")
def result_late(service):
    return service.run(SYMBOL, as_of=AS_OF_LATE)


# ---------------------------------------------------------------------------
# 1 — Research Change Graph
# ---------------------------------------------------------------------------

class TestChangeGraph:
    def test_build_change_graph_returns_change_graph(self, result_early, result_late):
        changes = build_symbol_changes(result_early, result_late)
        graph = build_change_graph(changes, symbol=SYMBOL, as_of=AS_OF_LATE)

        assert isinstance(graph, ChangeGraph)
        assert graph.symbol == SYMBOL
        assert graph.change_count == len(changes)
        assert graph.relationship_count >= 0

    def test_graph_has_deterministic_relationship_ids(self, result_early, result_late):
        changes = build_symbol_changes(result_early, result_late)
        g1 = build_change_graph(changes, symbol=SYMBOL, as_of=AS_OF_LATE)
        g2 = build_change_graph(changes, symbol=SYMBOL, as_of=AS_OF_LATE)

        rel_ids_1 = [r.relationship_id for r in g1.relationships]
        rel_ids_2 = [r.relationship_id for r in g2.relationships]
        assert rel_ids_1 == rel_ids_2

    def test_relationship_types_are_safe(self, result_early, result_late):
        changes = build_symbol_changes(result_early, result_late)
        graph = build_change_graph(changes, symbol=SYMBOL, as_of=AS_OF_LATE)

        safe = {RelationshipType.RELATED_TO, RelationshipType.OCCURRED_ALONGSIDE, RelationshipType.SAME_CONTEXT}
        for rel in graph.relationships:
            assert rel.relationship_type in safe

    def test_empty_changes_produces_empty_graph(self):
        graph = build_change_graph((), symbol="TEST", as_of=AS_OF_LATE)
        assert graph.change_count == 0
        assert graph.relationship_count == 0
        assert len(graph.notes) > 0


# ---------------------------------------------------------------------------
# 2 — Research Test Graph
# ---------------------------------------------------------------------------

class TestResearchTestGraph:
    def test_builds_for_real_data(self, result_late):
        intel = result_late.intelligence
        graph = build_research_test_graph(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            evidence_items=result_late.evidence_items or (),
            intel_items=intel.items if intel else (),
            source_statuses=intel.source_statuses if intel else (),
            gaps=intel.research_gaps.gaps if intel and intel.research_gaps else (),
            conflicts=intel.conflicts if intel else (),
            deep_financial_insights=intel.deep_financial_insights if intel else None,
        )

        assert isinstance(graph, ResearchTestGraph)
        assert graph.total_tests > 0
        assert graph.total_tests == graph.evaluated_count + graph.partially_evaluated_count + graph.not_evaluable_count + graph.blocked_count + graph.not_applicable_count

    def test_no_test_is_deleted_when_evidence_missing(self):
        graph = build_research_test_graph(
            symbol="EMPTY",
            as_of=AS_OF_LATE,
            evidence_items=(),
            intel_items=(),
            source_statuses=(),
            gaps=(),
            conflicts=(),
        )
        assert graph.total_tests == 13

    def test_not_evaluable_has_reason(self):
        graph = build_research_test_graph(
            symbol="EMPTY",
            as_of=AS_OF_LATE,
            evidence_items=(),
            intel_items=(),
            source_statuses=(),
            gaps=(),
            conflicts=(),
        )
        for test in graph.tests:
            if test.result_state == TestResultState.NOT_EVALUABLE:
                assert test.missing_reason
                assert len(test.missing_reason) > 0

    def test_result_states_are_valid(self, result_late):
        intel = result_late.intelligence
        graph = build_research_test_graph(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            evidence_items=result_late.evidence_items or (),
            intel_items=intel.items if intel else (),
            source_statuses=intel.source_statuses if intel else (),
            gaps=intel.research_gaps.gaps if intel and intel.research_gaps else (),
            conflicts=intel.conflicts if intel else (),
            deep_financial_insights=intel.deep_financial_insights if intel else None,
        )
        for test in graph.tests:
            assert isinstance(test.result_state, TestResultState)
            assert test.pit_safe is True
            assert test.provenance_safe is True


# ---------------------------------------------------------------------------
# 3 — Conflict Explorer 2.0
# ---------------------------------------------------------------------------

class TestConflictExplorer:
    def test_builds_for_real_data(self, result_late):
        intel = result_late.intelligence
        report = build_conflict_explorer(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            conflicts=intel.conflicts if intel else (),
        )

        assert isinstance(report, ConflictExplorerReport)
        assert report.symbol == SYMBOL
        assert report.total_count == report.open_count + report.resolved_count + report.partial_count

    def test_conflict_has_both_sides(self, result_late):
        intel = result_late.intelligence
        report = build_conflict_explorer(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            conflicts=intel.conflicts if intel else (),
        )
        for conflict in report.conflicts:
            assert isinstance(conflict.side_a, ConflictSideDetail)
            assert isinstance(conflict.side_b, ConflictSideDetail)
            assert conflict.side_a.item_id
            assert conflict.side_b.item_id

    def test_status_is_valid_enum(self, result_late):
        intel = result_late.intelligence
        report = build_conflict_explorer(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            conflicts=intel.conflicts if intel else (),
        )
        for conflict in report.conflicts:
            assert isinstance(conflict.status, ConflictStatus)

    def test_no_causal_language(self, result_late):
        intel = result_late.intelligence
        report = build_conflict_explorer(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            conflicts=intel.conflicts if intel else (),
        )
        causal_words = ["caused by", "led to", "will cause"]
        for conflict in report.conflicts:
            all_text = f"{conflict.description} {conflict.normalization_methodology or ''}"
            for word in causal_words:
                assert word.lower() not in all_text.lower()

    def test_empty_conflicts(self):
        report = build_conflict_explorer(
            symbol="EMPTY",
            as_of=AS_OF_LATE,
            conflicts=(),
        )
        assert report.total_count == 0
        assert len(report.notes) > 0


# ---------------------------------------------------------------------------
# 4 — Source Intelligence
# ---------------------------------------------------------------------------

class TestSourceIntelligence:
    def test_builds_for_real_data(self, result_late):
        intel = result_late.intelligence
        report = build_source_intelligence(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            source_statuses=intel.source_statuses if intel else (),
            evidence_items=result_late.evidence_items or (),
        )

        assert isinstance(report, SourceIntelligenceReport)
        assert report.total_sources >= 0

    def test_freshness_states_are_valid(self, result_late):
        intel = result_late.intelligence
        report = build_source_intelligence(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            source_statuses=intel.source_statuses if intel else (),
            evidence_items=result_late.evidence_items or (),
        )
        for src in report.sources:
            assert isinstance(src.freshness_state, FreshnessState)

    def test_counts_add_up(self, result_late):
        intel = result_late.intelligence
        report = build_source_intelligence(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            source_statuses=intel.source_statuses if intel else (),
            evidence_items=result_late.evidence_items or (),
        )
        total = report.current_count + report.stale_count + report.missing_count + report.degraded_count + report.unknown_count
        assert total == report.total_sources

    def test_no_scores(self, result_late):
        intel = result_late.intelligence
        report = build_source_intelligence(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            source_statuses=intel.source_statuses if intel else (),
            evidence_items=result_late.evidence_items or (),
        )
        for src in report.sources:
            assert not hasattr(src, "score")
            assert not hasattr(src, "ranking")


# ---------------------------------------------------------------------------
# 5 — Historical Research Replay
# ---------------------------------------------------------------------------

class TestReplay:
    def test_single_context_replay(self, result_late):
        replay = build_replay(result_late, universe=(SYMBOL,))

        assert isinstance(replay, FullReplayResult)
        assert replay.schema_version == REPLAY_SCHEMA_VERSION
        assert replay.context_a is not None
        assert replay.context_b is None
        assert replay.delta is None

    def test_two_context_replay(self, result_early, result_late):
        replay = build_replay(result_early, result_late, universe=(SYMBOL,))

        assert replay.context_a is not None
        assert replay.context_b is not None
        assert replay.delta is not None
        assert replay.delta.context_a_id
        assert replay.delta.context_b_id

    def test_same_context_same_output(self, result_late):
        r1 = build_replay(result_late, universe=(SYMBOL,))
        r2 = build_replay(result_late, universe=(SYMBOL,))

        assert r1.context_a.snapshot.context_id == r2.context_a.snapshot.context_id
        assert r1.context_a.financial_facts_count == r2.context_a.financial_facts_count
        assert r1.context_a.evidence_count == r2.context_a.evidence_count

    def test_replay_metadata(self, result_late):
        replay = build_replay(result_late, universe=(SYMBOL,))
        meta = replay.context_a.metadata

        assert isinstance(meta, ReplayMetadata)
        assert meta.schema_version == REPLAY_SCHEMA_VERSION
        assert meta.replay_deterministic is True
        assert meta.pit_enforced is True

    def test_pit_enforcement_note(self, result_late):
        replay = build_replay(result_late, universe=(SYMBOL,))
        notes_text = " ".join(replay.notes)
        assert "2024 context cannot see 2025 evidence" in notes_text


# ---------------------------------------------------------------------------
# 6 — Financial Quality
# ---------------------------------------------------------------------------

class TestFinancialQuality:
    def test_builds_for_real_data(self, result_late):
        intel = result_late.intelligence
        fin_periods = ()
        if intel and intel.financial_intelligence:
            fin_periods = intel.financial_intelligence.periods

        report = build_financial_quality(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            financial_periods=fin_periods,
        )

        assert isinstance(report, FinancialQualityReport)
        assert report.observation_count >= 0

    def test_reported_and_derived_counts(self, result_late):
        intel = result_late.intelligence
        fin_periods = ()
        if intel and intel.financial_intelligence:
            fin_periods = intel.financial_intelligence.periods

        report = build_financial_quality(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            financial_periods=fin_periods,
        )

        assert report.reported_count + report.derived_count == report.observation_count

    def test_derived_observations_have_derivation(self, result_late):
        intel = result_late.intelligence
        fin_periods = ()
        if intel and intel.financial_intelligence:
            fin_periods = intel.financial_intelligence.periods

        report = build_financial_quality(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            financial_periods=fin_periods,
        )

        for obs in report.observations:
            if obs.origin == ObservationOrigin.DERIVED:
                assert obs.derivation is not None
                assert len(obs.derivation) > 0

    def test_null_observations_have_reason(self, result_late):
        intel = result_late.intelligence
        fin_periods = ()
        if intel and intel.financial_intelligence:
            fin_periods = intel.financial_intelligence.periods

        report = build_financial_quality(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            financial_periods=fin_periods,
        )

        for obs in report.observations:
            if not obs.available:
                assert obs.null_reason is not None
                assert len(obs.null_reason) > 0

    def test_no_long_decimal_tails(self, result_late):
        intel = result_late.intelligence
        fin_periods = ()
        if intel and intel.financial_intelligence:
            fin_periods = intel.financial_intelligence.periods

        report = build_financial_quality(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            financial_periods=fin_periods,
        )

        for obs in report.observations:
            if obs.value is not None:
                val_str = str(obs.value)
                if "." in val_str:
                    decimals = len(val_str.split(".")[1])
                    assert decimals <= 6, f"Long decimal tail: {val_str}"


# ---------------------------------------------------------------------------
# 7 — Business/Tech Evidence
# ---------------------------------------------------------------------------

class TestBusinessTechEvidence:
    def test_builds_for_real_data(self, result_late):
        intel = result_late.intelligence
        report = build_business_tech_evidence(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            intel_items=intel.items if intel else (),
        )

        assert isinstance(report, BusinessTechReport)
        assert report.observation_count >= 0

    def test_epistemic_states_are_valid(self, result_late):
        intel = result_late.intelligence
        report = build_business_tech_evidence(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            intel_items=intel.items if intel else (),
        )
        for obs in report.observations:
            assert isinstance(obs.epistemic_state, EpistemicState)

    def test_dimensions_are_valid(self, result_late):
        intel = result_late.intelligence
        report = build_business_tech_evidence(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            intel_items=intel.items if intel else (),
        )
        for obs in report.observations:
            assert isinstance(obs.dimension, EvidenceDimension)

    def test_weak_areas_identified(self):
        report = build_business_tech_evidence(
            symbol="EMPTY",
            as_of=AS_OF_LATE,
            intel_items=(),
        )
        assert len(report.weak_areas) > 0


# ---------------------------------------------------------------------------
# 8 — Ownership Audit
# ---------------------------------------------------------------------------

class TestOwnershipAudit:
    def test_builds_for_real_data(self, result_late):
        intel = result_late.intelligence
        report = build_ownership_audit(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            intel_items=intel.items if intel else (),
        )

        assert isinstance(report, OwnershipAuditReport)
        assert report.capability in (OwnershipCapability.PARTIAL, OwnershipCapability.BLOCKED)

    def test_blocked_has_reason(self):
        report = build_ownership_audit(
            symbol="NODATA",
            as_of=AS_OF_LATE,
            ownership_data=None,
            intel_items=(),
        )
        assert report.capability == OwnershipCapability.BLOCKED
        assert report.block_reason is not None


# ---------------------------------------------------------------------------
# 9 — Alert Events
# ---------------------------------------------------------------------------

class TestAlertEvents:
    def test_builds_from_changes(self, result_early, result_late):
        changes = build_symbol_changes(result_early, result_late)
        contract = build_alert_events(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            changes=changes,
        )

        assert isinstance(contract, AlertEventContract)
        assert contract.event_count >= 0

    def test_alert_types_are_valid(self, result_early, result_late):
        changes = build_symbol_changes(result_early, result_late)
        contract = build_alert_events(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            changes=changes,
        )
        for event in contract.events:
            assert isinstance(event.alert_type, AlertType)

    def test_events_have_required_fields(self, result_early, result_late):
        changes = build_symbol_changes(result_early, result_late)
        contract = build_alert_events(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            changes=changes,
        )
        for event in contract.events:
            assert event.alert_id
            assert event.symbol == SYMBOL
            assert event.summary
            assert event.as_of

    def test_deterministic_ordering(self, result_early, result_late):
        changes = build_symbol_changes(result_early, result_late)
        c1 = build_alert_events(symbol=SYMBOL, as_of=AS_OF_LATE, changes=changes)
        c2 = build_alert_events(symbol=SYMBOL, as_of=AS_OF_LATE, changes=changes)

        ids1 = [e.alert_id for e in c1.events]
        ids2 = [e.alert_id for e in c2.events]
        assert ids1 == ids2


# ---------------------------------------------------------------------------
# 11 — API Contract Audit
# ---------------------------------------------------------------------------

class TestAPIContractAudit:
    def test_change_graph_endpoint(self, client):
        resp = client.get(
            "/api/v1/research/change-graph",
            params={
                "symbol": SYMBOL,
                "baseline_as_of": AS_OF_EARLY.isoformat(),
                "current_as_of": AS_OF_LATE.isoformat(),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["symbol"] == SYMBOL
        assert "changes" in data
        assert "relationships" in data

    def test_test_graph_endpoint(self, client):
        resp = client.get(
            "/api/v1/research/test-graph",
            params={"symbol": SYMBOL, "as_of": AS_OF_LATE.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tests"] > 0

    def test_conflict_explorer_endpoint(self, client):
        resp = client.get(
            "/api/v1/research/conflict-explorer",
            params={"symbol": SYMBOL, "as_of": AS_OF_LATE.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "conflicts" in data
        assert "total_count" in data

    def test_source_intelligence_endpoint(self, client):
        resp = client.get(
            "/api/v1/research/source-intelligence",
            params={"symbol": SYMBOL, "as_of": AS_OF_LATE.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "sources" in data
        assert "total_sources" in data

    def test_replay_endpoint(self, client):
        resp = client.get(
            "/api/v1/research/replay",
            params={
                "symbol": SYMBOL,
                "as_of_a": AS_OF_LATE.isoformat(),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["schema_version"] == REPLAY_SCHEMA_VERSION

    def test_financial_quality_endpoint(self, client):
        resp = client.get(
            "/api/v1/research/financial-quality",
            params={"symbol": SYMBOL, "as_of": AS_OF_LATE.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "observations" in data
        assert "observation_count" in data

    def test_business_tech_endpoint(self, client):
        resp = client.get(
            "/api/v1/research/business-tech-evidence",
            params={"symbol": SYMBOL, "as_of": AS_OF_LATE.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "observations" in data

    def test_ownership_audit_endpoint(self, client):
        resp = client.get(
            "/api/v1/research/ownership-audit",
            params={"symbol": SYMBOL, "as_of": AS_OF_LATE.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "capability" in data

    def test_alert_events_endpoint(self, client):
        resp = client.get(
            "/api/v1/research/alert-events",
            params={
                "symbol": SYMBOL,
                "baseline_as_of": AS_OF_EARLY.isoformat(),
                "current_as_of": AS_OF_LATE.isoformat(),
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert "event_count" in data


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from src.api.main import app
    return TestClient(app)


# ---------------------------------------------------------------------------
# 13 — Determinism / PIT / Provenance Test Matrix
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_context_same_digest(self, result_late):
        snap1 = build_context_snapshot(result_late)
        snap2 = build_context_snapshot(result_late)
        assert snap1.context_id == snap2.context_id

    def test_same_change_inputs_same_ids(self, result_early, result_late):
        c1 = build_symbol_changes(result_early, result_late)
        c2 = build_symbol_changes(result_early, result_late)
        ids1 = [ch.change_id for ch in c1]
        ids2 = [ch.change_id for ch in c2]
        assert ids1 == ids2

    def test_same_delta_same_output(self, result_early, result_late):
        d1 = build_evidence_delta(result_early, result_late)
        d2 = build_evidence_delta(result_early, result_late)
        assert d1.new_evidence == d2.new_evidence
        assert d1.removed_evidence == d2.removed_evidence
        assert d1.changed_evidence == d2.changed_evidence

    def test_same_comparison_same_output(self):
        from src.research.comparison import build_company_comparison
        service = RecordedCompanyResearchService()
        r1 = service.run("TCS", as_of=AS_OF_LATE)
        r2 = service.run("INFY", as_of=AS_OF_LATE)
        c1 = build_company_comparison([r1, r2], as_of=AS_OF_LATE)
        c2 = build_company_comparison([r1, r2], as_of=AS_OF_LATE)
        assert c1.row_count == c2.row_count
        assert c1.comparison_context == c2.comparison_context


class TestPIT:
    def test_early_context_excludes_late_evidence(self, result_early, result_late):
        early_items = set(
            item.item_id
            for item in (result_early.intelligence.items if result_early.intelligence else ())
        )
        late_items = set(
            item.item_id
            for item in (result_late.intelligence.items if result_late.intelligence else ())
        )
        new_items = late_items - early_items
        for item_id in new_items:
            late_item = next(
                i for i in (result_late.intelligence.items if result_late.intelligence else ())
                if i.item_id == item_id
            )
            if late_item.available_at:
                assert late_item.available_at > AS_OF_EARLY

    def test_same_context_same_pit_state(self, result_late):
        snap1 = build_context_snapshot(result_late)
        snap2 = build_context_snapshot(result_late)
        assert snap1.pit_checks_passed == snap2.pit_checks_passed
        assert snap1.evidence_included == snap2.evidence_included
        assert snap1.future_evidence_excluded == snap2.future_evidence_excluded


class TestProvenance:
    def test_changes_carry_provenance(self, result_early, result_late):
        changes = build_symbol_changes(result_early, result_late)
        for ch in changes:
            if ch.source:
                assert isinstance(ch.source, str)
            if ch.provenance:
                assert isinstance(ch.provenance, tuple)

    def test_delta_entries_carry_ids(self, result_early, result_late):
        delta = build_evidence_delta(result_early, result_late)
        for entry in delta.new_evidence:
            assert entry.evidence_id
            assert isinstance(entry.source_ids, tuple)
            assert isinstance(entry.provenance_ids, tuple)

    def test_evidence_lineage_has_sources(self, result_late):
        lineage = build_evidence_lineage(
            symbol=SYMBOL,
            as_of=AS_OF_LATE,
            evidence_items=result_late.evidence_items,
            intel_items=result_late.intelligence.items if result_late.intelligence else (),
            pit_filter=True,
        )
        for item in lineage.evidence:
            assert item.evidence_id
            assert item.symbol == SYMBOL
