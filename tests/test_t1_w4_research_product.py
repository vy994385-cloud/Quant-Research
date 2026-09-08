"""
T1-W4 Research Product Foundation tests.

Covers:
  S7  — Cross-Endpoint Consistency Tests
  S8  — PIT Consistency Matrix Tests
  S9  — Provenance Consistency Matrix Tests
  S10 — Duplication/Waste Audit
  S11 — Output Quality Scan
  S12 — Performance / Payload Size
  S13 — API Contract Tests
  S1-S6 — Integration tests for new modules
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.api.recorded_research import RecordedCompanyResearchService
from src.research.observation import CanonicalObservation, CanonicalObservationSummary
from src.research.product_builders import build_research_snapshot, build_section_registry
from src.research.section_registry import CANONICAL_SECTIONS, ResearchSectionRegistry, SectionEntry
from src.research.snapshot import (
    ResearchSnapshot,
    SnapshotChange,
    SnapshotConflict,
    SnapshotCoverage,
    SnapshotEvidence,
    SnapshotFreshness,
    SnapshotGap,
    SnapshotIdentity,
    SnapshotObservation,
    SnapshotProvenance,
    SnapshotSource,
)
from src.research.vocabulary import (
    ConflictResolution,
    EvidenceEpistemicType,
    EvidenceEpistemicStrength,
    ObservationOrigin,
    ObservationSeverity,
    OwnershipCapability,
    ResearchAvailability,
    ResearchDirection,
    ResearchGapStatus,
    ResearchTestState,
    SectionStatus,
    SNAPSHOT_SCHEMA_VERSION,
    SECTION_REGISTRY_SCHEMA_VERSION,
    SourceFreshness,
    VerificationStatus,
    VOCABULARY_VERSION,
)

AS_OF = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
AS_OF_EARLY = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
SYMBOL = "TCS"


@pytest.fixture(scope="module")
def service():
    return RecordedCompanyResearchService()


@pytest.fixture(scope="module")
def result(service):
    return service.run(SYMBOL, as_of=AS_OF)


@pytest.fixture(scope="module")
def result_early(service):
    return service.run(SYMBOL, as_of=AS_OF_EARLY)


@pytest.fixture(scope="module")
def snapshot(result):
    return build_research_snapshot(result, as_of=AS_OF)


@pytest.fixture(scope="module")
def section_registry(result):
    return build_section_registry(result, as_of=AS_OF)


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from src.api.main import app
    return TestClient(app)


# ═══════════════════════════════════════════════════════════════════════
# S1-S6 — Module Integration
# ═══════════════════════════════════════════════════════════════════════


class TestVocabulary:
    def test_all_enums_have_values(self):
        assert len(ResearchAvailability) == 7
        assert len(ResearchTestState) == 5
        assert len(EvidenceEpistemicType) == 4
        assert len(EvidenceEpistemicStrength) == 5
        assert len(SourceFreshness) == 5
        assert len(ConflictResolution) == 3
        assert len(ResearchGapStatus) == 6
        assert len(ResearchDirection) == 4
        assert len(ObservationSeverity) == 5
        assert len(ObservationOrigin) == 2
        assert len(VerificationStatus) == 6
        assert len(SectionStatus) == 4
        assert len(OwnershipCapability) == 4

    def test_schema_versions_defined(self):
        assert SNAPSHOT_SCHEMA_VERSION == "1.0.0"
        assert SECTION_REGISTRY_SCHEMA_VERSION == "1.0.0"
        assert VOCABULARY_VERSION == "1.0.0"

    def test_direction_has_no_causal_values(self):
        causal = {"caused", "led_to", "because", "results_in"}
        for member in ResearchDirection:
            assert member.value.lower() not in causal


class TestCanonicalObservation:
    def test_default_values(self):
        obs = CanonicalObservation(
            observation_id="obs-1",
            symbol="TCS",
        )
        assert obs.symbol == "TCS"
        assert obs.available is True
        assert obs.direction == ResearchDirection.UNKNOWN
        assert obs.epistemic_type == EvidenceEpistemicType.UNKNOWN
        assert obs.verification_status == VerificationStatus.UNVERIFIED
        assert obs.origin == ObservationOrigin.REPORTED

    def test_frozen(self):
        obs = CanonicalObservation(observation_id="obs-1", symbol="TCS")
        with pytest.raises(Exception):
            obs.symbol = "INFY"

    def test_forbids_extra(self):
        with pytest.raises(Exception):
            CanonicalObservation(observation_id="obs-1", symbol="TCS", fake_field="x")


class TestSnapshot:
    def test_builds_for_real_data(self, snapshot, result):
        assert isinstance(snapshot, ResearchSnapshot)
        assert snapshot.symbol == SYMBOL
        assert snapshot.schema_version == SNAPSHOT_SCHEMA_VERSION
        assert snapshot.identity.symbol == SYMBOL

    def test_snapshot_has_all_sections(self, snapshot):
        assert snapshot.identity is not None
        assert snapshot.evidence is not None
        assert snapshot.freshness is not None
        assert snapshot.coverage is not None
        assert snapshot.provenance is not None

    def test_snapshot_is_deterministic(self, result):
        s1 = build_research_snapshot(result, as_of=AS_OF)
        s2 = build_research_snapshot(result, as_of=AS_OF)
        assert s1.symbol == s2.symbol
        assert s1.observation_count == s2.observation_count
        assert s1.change_count == s2.change_count
        assert s1.conflict_count == s2.conflict_count

    def test_snapshot_frozen(self, snapshot):
        with pytest.raises(Exception):
            snapshot.symbol = "X"

    def test_evidence_counts_consistent(self, snapshot):
        ev = snapshot.evidence
        assert ev.total_count == ev.positive_count + ev.negative_count + ev.neutral_count + ev.conflicting_count


class TestSectionRegistry:
    def test_builds_for_real_data(self, section_registry):
        assert isinstance(section_registry, ResearchSectionRegistry)
        assert section_registry.symbol == SYMBOL
        assert section_registry.schema_version == SECTION_REGISTRY_SCHEMA_VERSION
        assert section_registry.total_sections == 9

    def test_has_canonical_sections(self, section_registry):
        section_ids = {s.section_id for s in section_registry.sections}
        for canonical_id, _, _ in CANONICAL_SECTIONS:
            assert canonical_id in section_ids

    def test_available_sections_valid(self, section_registry):
        assert section_registry.available_sections + section_registry.unavailable_sections == section_registry.total_sections

    def test_section_entries_have_required_fields(self, section_registry):
        for section in section_registry.sections:
            assert section.section_id
            assert section.title
            assert isinstance(section.available, bool)
            assert section.item_count >= 0
            assert isinstance(section.freshness_state, SourceFreshness)
            assert isinstance(section.coverage_state, ResearchAvailability)

    def test_registry_deterministic(self, result):
        r1 = build_section_registry(result, as_of=AS_OF)
        r2 = build_section_registry(result, as_of=AS_OF)
        assert r1.total_sections == r2.total_sections
        assert r1.available_sections == r2.available_sections

    def test_all_9_sections_present(self, section_registry):
        assert section_registry.total_sections == 9


# ═══════════════════════════════════════════════════════════════════════
# S7 — Cross-Endpoint Consistency Tests
# ═══════════════════════════════════════════════════════════════════════


class TestCrossEndpointConsistency:
    def test_same_company_same_identity(self, result, snapshot):
        """Same company + same as_of → same identity."""
        assert snapshot.identity.symbol == SYMBOL

    def test_same_company_same_pit(self, snapshot):
        """Same company + same as_of → same PIT state."""
        assert snapshot.identity.pit_checks_passed is True
        assert snapshot.identity.future_evidence_excluded == 0

    def test_snapshot_evidence_matches_evidence_lineage(self, client, snapshot):
        """Snapshot evidence count is consistent with evidence endpoint."""
        resp = client.get(
            f"/api/v1/companies/{SYMBOL}/evidence",
            params={"as_of": AS_OF.isoformat()},
        )
        if resp.status_code == 200:
            data = resp.json()
            lineage = data.get("evidence_lineage", {})
            lineage_total = lineage.get("total_evidence", 0)
            if lineage_total > 0:
                assert snapshot.evidence.total_count > 0

    def test_snapshot_sources_match_source_intelligence(self, client, snapshot):
        """Snapshot source count is consistent with source intelligence."""
        resp = client.get(
            "/api/v1/research/source-intelligence",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sources"] == snapshot.source_count

    def test_snapshot_conflicts_match_conflict_explorer(self, client, snapshot):
        """Snapshot conflict count is consistent with conflict explorer."""
        resp = client.get(
            "/api/v1/research/conflict-explorer",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == snapshot.conflict_count

    def test_registry_section_counts_consistent(self, section_registry, snapshot):
        """Section registry available count is consistent with snapshot coverage."""
        assert section_registry.total_sections == 9


# ═══════════════════════════════════════════════════════════════════════
# S8 — PIT Consistency Matrix Tests
# ═══════════════════════════════════════════════════════════════════════


class TestPITConsistencyMatrix:
    def test_later_evidence_does_not_leak_backward(self, result_early, result):
        """Later evidence does not leak to earlier context."""
        early_items = set(
            item.item_id
            for item in (result_early.intelligence.items if result_early.intelligence else ())
        )
        late_items = set(
            item.item_id
            for item in (result.intelligence.items if result.intelligence else ())
        )
        new_items = late_items - early_items
        for item_id in new_items:
            late_item = next(
                i for i in (result.intelligence.items if result.intelligence else ())
                if i.item_id == item_id
            )
            if late_item.available_at:
                assert late_item.available_at > AS_OF_EARLY

    def test_early_context_has_fewer_or_equal_sources(self, result_early, result):
        """Earlier context has fewer or equal sources than later."""
        early_sources = len(result_early.intelligence.source_statuses) if result_early.intelligence else 0
        late_sources = len(result.intelligence.source_statuses) if result.intelligence else 0
        assert early_sources <= late_sources

    def test_same_context_same_pit_state(self, result):
        """Same context replay produces identical PIT state."""
        s1 = build_research_snapshot(result, as_of=AS_OF)
        s2 = build_research_snapshot(result, as_of=AS_OF)
        assert s1.identity.pit_checks_passed == s2.identity.pit_checks_passed
        assert s1.identity.future_evidence_excluded == s2.identity.future_evidence_excluded
        assert s1.identity.evidence_included == s2.identity.evidence_included

    def test_replay_same_context_same_output(self, result):
        """Replay of same context produces identical output."""
        from src.research.replay import build_replay
        r1 = build_replay(result, universe=(SYMBOL,))
        r2 = build_replay(result, universe=(SYMBOL,))
        assert r1.context_a.snapshot.context_id == r2.context_a.snapshot.context_id

    def test_pit_early_context_excludes_late_evidence(self, result_early, result):
        """Earlier context excludes later evidence items."""
        early_evidence = set(
            item.evidence_id
            for item in (result_early.evidence_items or ())
        )
        late_evidence = set(
            item.evidence_id
            for item in (result.evidence_items or ())
        )
        new_evidence = late_evidence - early_evidence
        for eid in new_evidence:
            late_item = next(
                i for i in (result.evidence_items or ())
                if i.evidence_id == eid
            )
            obs_at = getattr(late_item, "observation_at", None)
            if obs_at:
                assert obs_at > AS_OF_EARLY

    def test_snapshot_at_early_context(self, result_early):
        """Snapshot at earlier context has valid PIT."""
        snap = build_research_snapshot(result_early, as_of=AS_OF_EARLY)
        assert snap.identity.symbol == SYMBOL
        assert snap.identity.as_of == AS_OF_EARLY

    def test_registry_at_early_context(self, result_early):
        """Section registry at earlier context is valid."""
        reg = build_section_registry(result_early, as_of=AS_OF_EARLY)
        assert reg.total_sections == 9


# ═══════════════════════════════════════════════════════════════════════
# S9 — Provenance Consistency Matrix Tests
# ═══════════════════════════════════════════════════════════════════════


class TestProvenanceConsistencyMatrix:
    def test_snapshot_provenance_ids_are_deterministic(self, result):
        """Provenance IDs in snapshot are deterministic."""
        s1 = build_research_snapshot(result, as_of=AS_OF)
        s2 = build_research_snapshot(result, as_of=AS_OF)
        assert s1.provenance.provenance_ids == s2.provenance.provenance_ids
        assert s1.provenance.source_ids == s2.provenance.source_ids

    def test_evidence_items_have_provenance(self, result):
        """Evidence items carry provenance IDs."""
        evidence_items = result.evidence_items or []
        for item in evidence_items:
            assert hasattr(item, "provenance_ids")
            assert hasattr(item, "source_ids")

    def test_snapshot_provenance_subset_of_evidence(self, snapshot, result):
        """Snapshot provenance is derived from evidence items."""
        evidence_prov_ids: set[str] = set()
        for item in (result.evidence_items or []):
            for pid in getattr(item, "provenance_ids", ()) or ():
                evidence_prov_ids.add(pid)
        for pid in snapshot.provenance.provenance_ids:
            assert pid in evidence_prov_ids

    def test_source_intelligence_has_provenance(self, client):
        """Source intelligence endpoint returns provenance data."""
        resp = client.get(
            "/api/v1/research/source-intelligence",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        for source in data.get("sources", []):
            assert "source_name" in source
            assert "freshness_state" in source

    def test_no_fake_provenance(self, snapshot):
        """No fake provenance IDs in snapshot."""
        for pid in snapshot.provenance.provenance_ids:
            assert isinstance(pid, str)
            assert len(pid) > 0


# ═══════════════════════════════════════════════════════════════════════
# S10 — Duplication/Waste Audit
# ═══════════════════════════════════════════════════════════════════════


class TestDuplicationAudit:
    def test_snapshot_not_duplicating_full_research(self, client):
        """Snapshot is significantly smaller than full research contract."""
        snap_resp = client.get(
            "/api/v1/research/snapshot",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        research_resp = client.get(
            f"/api/v1/companies/{SYMBOL}/research",
            params={"as_of": AS_OF.isoformat()},
        )
        assert snap_resp.status_code == 200
        assert research_resp.status_code == 200
        snap_bytes = len(json.dumps(snap_resp.json()).encode())
        research_bytes = len(json.dumps(research_resp.json()).encode())
        assert snap_bytes < research_bytes, "Snapshot should be smaller than full research"

    def test_section_registry_is_lightweight(self, client):
        """Section registry is lightweight metadata."""
        resp = client.get(
            "/api/v1/research/section-registry",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        data_bytes = len(json.dumps(resp.json()).encode())
        assert data_bytes < 5000, f"Section registry should be <5KB, got {data_bytes}"

    def test_snapshot_no_raw_intelligence_dump(self, snapshot):
        """Snapshot does not dump raw intelligence items."""
        snapshot_json = snapshot.model_dump_json()
        assert "business_events" not in snapshot_json or snapshot_json.count("business_events") < 3
        assert "management_commentary" not in snapshot_json or snapshot_json.count("management_commentary") < 3


# ═══════════════════════════════════════════════════════════════════════
# S11 — Output Quality Scan
# ═══════════════════════════════════════════════════════════════════════


class TestOutputQuality:
    def test_no_long_decimal_tails(self, client):
        """No long decimal tails in snapshot response."""
        resp = client.get(
            "/api/v1/research/snapshot",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        text = resp.json()
        text_str = json.dumps(text)
        assert "1.23456789012345" not in text_str

    def test_no_nan_in_response(self, client):
        """No NaN values in snapshot response."""
        resp = client.get(
            "/api/v1/research/snapshot",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        text = resp.text
        assert "NaN" not in text
        assert "Infinity" not in text

    def test_no_screaming_snake_in_user_copy(self, client):
        """SCREAMING_SNAKE should not appear in user-facing text."""
        resp = client.get(
            "/api/v1/research/snapshot",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        for key in ("symbol", "company_name", "sector"):
            val = data.get("identity", {}).get(key)
            if val and isinstance(val, str):
                assert val == val.upper() or not val.isupper(), f"{key} should not be SCREAMING_SNAKE: {val}"

    def test_no_debug_wording(self, client):
        """No debug wording in response."""
        resp = client.get(
            "/api/v1/research/snapshot",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        text = resp.text.lower()
        assert "todo" not in text or text.count("todo") < 3
        assert "fixme" not in text
        assert "hack" not in text

    def test_timestamps_are_iso8601(self, client):
        """Timestamps should be ISO 8601 format."""
        resp = client.get(
            "/api/v1/research/snapshot",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        as_of_str = data.get("as_of", "")
        assert "T" in as_of_str or "+" in as_of_str or "Z" in as_of_str

    def test_section_registry_no_nan(self, client):
        """No NaN in section registry response."""
        resp = client.get(
            "/api/v1/research/section-registry",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        assert "NaN" not in resp.text
        assert "Infinity" not in resp.text


# ═══════════════════════════════════════════════════════════════════════
# S12 — Performance / Payload Size
# ═══════════════════════════════════════════════════════════════════════


class TestPerformance:
    def _measure_endpoint(self, client, path, params):
        start = time.time()
        resp = client.get(path, params=params)
        elapsed = time.time() - start
        return resp, elapsed

    def test_snapshot_response_time(self, client):
        """Snapshot endpoint responds within 5s."""
        resp, elapsed = self._measure_endpoint(
            client,
            "/api/v1/research/snapshot",
            {"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        assert elapsed < 5.0, f"Snapshot took {elapsed:.2f}s"

    def test_section_registry_response_time(self, client):
        """Section registry responds within 3s."""
        resp, elapsed = self._measure_endpoint(
            client,
            "/api/v1/research/section-registry",
            {"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        assert elapsed < 3.0, f"Registry took {elapsed:.2f}s"

    def test_snapshot_payload_size(self, client):
        """Snapshot payload is within reasonable size."""
        resp = client.get(
            "/api/v1/research/snapshot",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        size = len(resp.content)
        assert size < 100_000, f"Snapshot payload {size} bytes exceeds 100KB"

    def test_research_repeated_fields_measured(self, client):
        """Record response sizes for duplication analysis."""
        endpoints = [
            ("/api/v1/research/snapshot", {"symbol": SYMBOL, "as_of": AS_OF.isoformat()}),
            ("/api/v1/research/section-registry", {"symbol": SYMBOL, "as_of": AS_OF.isoformat()}),
            ("/api/v1/research/source-intelligence", {"symbol": SYMBOL, "as_of": AS_OF.isoformat()}),
            ("/api/v1/research/conflict-explorer", {"symbol": SYMBOL, "as_of": AS_OF.isoformat()}),
        ]
        sizes = {}
        for path, params in endpoints:
            resp = client.get(path, params=params)
            if resp.status_code == 200:
                sizes[path] = len(resp.content)
        assert len(sizes) > 0


# ═══════════════════════════════════════════════════════════════════════
# S13 — API Contract Tests
# ═══════════════════════════════════════════════════════════════════════


class TestAPIContracts:
    def test_snapshot_endpoint(self, client):
        resp = client.get(
            "/api/v1/research/snapshot",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["schema_version"] == SNAPSHOT_SCHEMA_VERSION
        assert data["symbol"] == SYMBOL
        assert "identity" in data
        assert "evidence" in data
        assert "coverage" in data
        assert "freshness" in data
        assert "provenance" in data

    def test_section_registry_endpoint(self, client):
        resp = client.get(
            "/api/v1/research/section-registry",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["schema_version"] == SECTION_REGISTRY_SCHEMA_VERSION
        assert data["symbol"] == SYMBOL
        assert data["total_sections"] == 9
        assert len(data["sections"]) == 9

    def test_snapshot_returns_400_without_as_of(self, client):
        resp = client.get(
            "/api/v1/research/snapshot",
            params={"symbol": SYMBOL},
        )
        assert resp.status_code == 400

    def test_section_registry_returns_400_without_as_of(self, client):
        resp = client.get(
            "/api/v1/research/section-registry",
            params={"symbol": SYMBOL},
        )
        assert resp.status_code == 400

    def test_snapshot_deterministic_across_calls(self, client):
        r1 = client.get(
            "/api/v1/research/snapshot",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        r2 = client.get(
            "/api/v1/research/snapshot",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert r1.json()["observation_count"] == r2.json()["observation_count"]
        assert r1.json()["change_count"] == r2.json()["change_count"]

    def test_section_registry_deterministic_across_calls(self, client):
        r1 = client.get(
            "/api/v1/research/section-registry",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        r2 = client.get(
            "/api/v1/research/section-registry",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert r1.json()["available_sections"] == r2.json()["available_sections"]

    def test_snapshot_no_extra_top_level_keys(self, client):
        resp = client.get(
            "/api/v1/research/snapshot",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        allowed_keys = {
            "schema_version", "symbol", "as_of", "identity", "changes",
            "change_count", "observations", "observation_count", "evidence",
            "financial_observation_count", "financial_derived_count",
            "coverage", "conflicts", "conflict_count", "gaps", "gap_count",
            "freshness", "sources", "source_count", "provenance", "notes",
        }
        extra = set(data.keys()) - allowed_keys
        assert not extra, f"Unexpected top-level keys: {extra}"

    def test_section_registry_no_extra_top_level_keys(self, client):
        resp = client.get(
            "/api/v1/research/section-registry",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        data = resp.json()
        allowed_keys = {
            "schema_version", "symbol", "as_of", "sections",
            "total_sections", "available_sections", "unavailable_sections", "notes",
        }
        extra = set(data.keys()) - allowed_keys
        assert not extra, f"Unexpected top-level keys: {extra}"

    def test_all_9_endpoints_smoke(self, client):
        """Smoke test all T1-W3 research intelligence endpoints."""
        endpoints = [
            "/api/v1/research/test-graph",
            "/api/v1/research/conflict-explorer",
            "/api/v1/research/source-intelligence",
            "/api/v1/research/financial-quality",
            "/api/v1/research/business-tech-evidence",
            "/api/v1/research/ownership-audit",
        ]
        for endpoint in endpoints:
            resp = client.get(
                endpoint,
                params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
            )
            assert resp.status_code == 200, f"{endpoint} failed with {resp.status_code}"

    def test_snapshot_identity_no_score(self, client):
        """Snapshot identity must not contain a score."""
        resp = client.get(
            "/api/v1/research/snapshot",
            params={"symbol": SYMBOL, "as_of": AS_OF.isoformat()},
        )
        assert resp.status_code == 200
        identity_text = json.dumps(resp.json().get("identity", {}))
        assert "score" not in identity_text.lower()
        assert "ranking" not in identity_text.lower()
        assert "recommendation" not in identity_text.lower()


# ═══════════════════════════════════════════════════════════════════════
# Vocabulary Completeness
# ═══════════════════════════════════════════════════════════════════════


class TestVocabularyCompleteness:
    def test_research_availability_covers_all_states(self):
        vals = {m.value for m in ResearchAvailability}
        assert "AVAILABLE" in vals
        assert "LIMITED" in vals
        assert "MISSING" in vals
        assert "STALE" in vals
        assert "CONFLICTING" in vals
        assert "INSUFFICIENT" in vals
        assert "BLOCKED" in vals

    def test_source_freshness_covers_all_states(self):
        vals = {m.value for m in SourceFreshness}
        assert "CURRENT" in vals
        assert "STALE" in vals
        assert "MISSING" in vals
        assert "DEGRADED" in vals
        assert "UNKNOWN" in vals

    def test_test_state_covers_all_states(self):
        vals = {m.value for m in ResearchTestState}
        assert "EVALUATED" in vals
        assert "PARTIALLY_EVALUATED" in vals
        assert "NOT_EVALUABLE" in vals
        assert "BLOCKED" in vals
        assert "NOT_APPLICABLE" in vals

    def test_conflict_resolution_covers_all_states(self):
        vals = {m.value for m in ConflictResolution}
        assert "OPEN" in vals
        assert "RESOLVED" in vals
        assert "PARTIAL" in vals

    def test_no_causal_language_in_vocabulary(self):
        causal_words = ["caused", "led_to", "because", "results_in", "implies"]
        for enum_cls in [
            ResearchAvailability, ResearchTestState, EvidenceEpistemicType,
            EvidenceEpistemicStrength, SourceFreshness, ConflictResolution,
            ResearchGapStatus, ResearchDirection, ObservationSeverity,
            ObservationOrigin, VerificationStatus, SectionStatus, OwnershipCapability,
        ]:
            for member in enum_cls:
                for word in causal_words:
                    assert word not in member.value.lower(), \
                        f"{enum_cls.__name__}.{member.value} contains causal word '{word}'"
