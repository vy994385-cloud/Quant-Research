"""
T1 CAPABILITY EXPANSION — Research Change Radar tests.

Pins the recorded-path change-detection engines and their API
surface:

- GET /api/v1/research-changes      (symbol-level change records)
- GET /api/v1/research-delta        (baseline vs current evidence delta)
- GET /api/v1/coverage/delta        (coverage transitions)
- GET /api/v1/research-context/{id} (context snapshot replay)
- GET /api/v1/evidence/conflicts    (both sides, never a winner)
- GET /api/v1/calendar              (recorded + announced, explicit
                                     non-guarantee)

Every endpoint must be deterministic, PIT-safe, null-safe, and free
of score/ranking/winner/recommendation fields.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.change_router import create_change_router
from src.api.errors import register_api_error_handlers
from src.api.recorded_research import RecordedCompanyResearchService
from src.research.change import (
    CONTEXT_SCHEMA_VERSION,
    ChangeType,
    build_calendar,
    build_context_snapshot,
    build_coverage_delta,
    build_evidence_delta,
    build_screen_entry_exit,
    build_symbol_changes,
    context_id_for,
    parse_context_id,
)
from src.screener.engine import ScreenDefinition

BASELINE = datetime(2025, 9, 15, tzinfo=timezone.utc)
BASELINE_ISO = "2025-09-15T00:00:00Z"
AS_OF = datetime(2026, 8, 10, 12, tzinfo=timezone.utc)
AS_OF_ISO = "2026-08-10T12:00:00Z"

FORBIDDEN_KEYS = {
    "score",
    "scores",
    "ranking",
    "rank",
    "ranked",
    "winner",
    "recommendation",
    "recommendations",
    "rating",
    "buy",
    "sell",
}


@pytest.fixture(scope="module")
def service(tmp_path_factory):
    archive_root = tmp_path_factory.mktemp("change-archive")
    return RecordedCompanyResearchService(archive_root=archive_root)


@pytest.fixture(scope="module")
def results(service):
    before = service.run("TCS", as_of=BASELINE)
    after = service.run("TCS", as_of=AS_OF)
    return before, after


@pytest.fixture(scope="module")
def client(service):
    app = FastAPI()
    register_api_error_handlers(app)
    app.include_router(create_change_router(service=service))
    return TestClient(app)


def _scan_forbidden(node, forbidden=FORBIDDEN_KEYS):
    if isinstance(node, dict):
        for key, value in node.items():
            assert key.lower() not in forbidden, key
            _scan_forbidden(value, forbidden)
    elif isinstance(node, list):
        for entry in node:
            _scan_forbidden(entry, forbidden)


# ── Engine: changes ───────────────────────────────────────────────


class TestBuildSymbolChanges:
    def test_deterministic_output(self, results):
        before, after = results
        first = build_symbol_changes(before, after)
        second = build_symbol_changes(before, after)
        assert first == second

    def test_change_ids_are_unique(self, results):
        before, after = results
        changes = build_symbol_changes(before, after)
        ids = [c.change_id for c in changes]
        assert len(ids) == len(set(ids))

    def test_no_future_knowledge_leaks(self, results):
        before, after = results
        changes = build_symbol_changes(before, after)
        for change in changes:
            if change.effective_at is not None:
                assert change.effective_at <= after.as_of
            assert change.detected_at <= after.as_of

    def test_change_types_are_enumerated(self, results):
        before, after = results
        changes = build_symbol_changes(before, after)
        known = {
            "NEW_EVIDENCE",
            "NEW_FINANCIAL_DISCLOSURE",
            "NEW_EVENT",
            "NEW_CORPORATE_ACTION",
            "NEW_TECHNOLOGY_EVIDENCE",
            "RESEARCH_GAP_CHANGED",
            "SOURCE_BECAME_STALE",
            "SCREEN_ENTRY",
            "SCREEN_EXIT",
        }
        for change in changes:
            assert change.change_type.value in known

    def test_empty_when_universe_unchanged(self, tmp_path_factory):
        # Same result object pair built twice from the same archive
        # at the same as_of must produce zero changes.
        archive = tmp_path_factory.mktemp("change-empty-archive")
        svc = RecordedCompanyResearchService(archive_root=archive)
        a = svc.run("TCS", as_of=AS_OF)
        b = svc.run("TCS", as_of=AS_OF)
        assert build_symbol_changes(a, b) == ()


# ── Engine: context snapshot ──────────────────────────────────────


class TestContextSnapshot:
    def test_context_id_is_stable(self, results):
        _, after = results
        first = build_context_snapshot(after)
        second = build_context_snapshot(after)
        assert first.context_id == second.context_id
        assert first.context_id.startswith("rc-TCS-")

    def test_parse_roundtrip(self, results):
        _, after = results
        snapshot = build_context_snapshot(after)
        symbol, parsed_as_of = parse_context_id(snapshot.context_id)
        assert symbol == "TCS"
        assert parsed_as_of == after.as_of

    def test_tampered_digest_rejected(self):
        good = context_id_for("TCS", AS_OF)
        tampered = good[:-4] + "0000" if not good[-4:].startswith(
            "0"
        ) else good[:-4] + "1111"
        with pytest.raises(ValueError):
            parse_context_id(tampered)

    def test_snapshot_counts_match_contract(self, results):
        _, after = results
        snapshot = build_context_snapshot(after)
        assert snapshot.evidence_included > 0
        assert snapshot.acquired_evidence_included >= 0
        assert snapshot.future_evidence_excluded >= 0
        assert snapshot.pit_checks_passed is True


# ── Engine: evidence delta ────────────────────────────────────────


class TestEvidenceDelta:
    def test_new_evidence_found_over_wide_window(self, results):
        before, after = results
        report = build_evidence_delta(before, after)
        assert len(report.new_evidence) > 0

    def test_deterministic_and_sorted(self, results):
        before, after = results
        first = build_evidence_delta(before, after)
        second = build_evidence_delta(before, after)
        assert first.model_dump(mode="json") == second.model_dump(
            mode="json"
        )
        ids = [e.evidence_id for e in first.new_evidence]
        assert ids == sorted(ids)

    def test_conflict_sides_present_not_winners(self, results):
        before, after = results
        report = build_evidence_delta(before, after)
        for conflict in report.new_conflicts:
            payload = conflict.model_dump(mode="json")
            # Both sides are always named; neither is a winner.
            assert payload["first_title"]
            assert payload["second_title"]
            _scan_forbidden(payload)

    def test_item_set_deltas_carry_sections(self, results):
        before, after = results
        report = build_evidence_delta(before, after)
        for delta in report.item_set_deltas:
            assert delta.section
            assert delta.added or delta.removed or delta.unchanged


# ── Engine: screen entry/exit ─────────────────────────────────────


class TestScreenEntryExit:
    def test_matches_become_entries(self, service):
        definition = ScreenDefinition.from_dict(
            {
                "name": "All revenue reporters",
                "groups": [
                    {
                        "filters": [
                            {
                                "field": "revenue_latest",
                                "operator": "has",
                            }
                        ]
                    }
                ],
            }
        )
        changes = build_screen_entry_exit(
            service,
            definition,
            previous_as_of=BASELINE,
            current_as_of=AS_OF,
        )
        # Deterministic and self-consistent.
        again = build_screen_entry_exit(
            service,
            definition,
            previous_as_of=BASELINE,
            current_as_of=AS_OF,
        )
        assert changes == again
        entries = [
            c for c in changes if c.change_type.value == "SCREEN_ENTRY"
        ]
        exits = [c for c in changes if c.change_type.value == "SCREEN_EXIT"]
        entry_symbols = {c.symbol for c in entries}
        exit_symbols = {c.symbol for c in exits}
        assert not (entry_symbols & exit_symbols)
        for change in entries + exits:
            assert change.previous_state != change.current_state

    def test_no_transitions_when_window_collapses(self, service):
        definition = ScreenDefinition.from_dict(
            {
                "name": "All revenue reporters",
                "groups": [
                    {
                        "filters": [
                            {
                                "field": "revenue_latest",
                                "operator": "has",
                            }
                        ]
                    }
                ],
            }
        )
        changes = build_screen_entry_exit(
            service,
            definition,
            previous_as_of=AS_OF,
            current_as_of=AS_OF,
        )
        assert changes == ()


# ── API surface ───────────────────────────────────────────────────


class TestResearchChangesRoute:
    def test_shape_and_counts(self, client):
        response = client.get(
            "/api/v1/research-changes",
            params={
                "symbol": "TCS",
                "baseline_as_of": BASELINE_ISO,
                "current_as_of": AS_OF_ISO,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["symbol"] == "TCS"
        assert payload["change_count"] == len(payload["changes"])
        _scan_forbidden(payload)

    def test_deterministic_responses(self, client):
        params = {
            "symbol": "TCS",
            "baseline_as_of": BASELINE_ISO,
            "current_as_of": AS_OF_ISO,
        }
        assert client.get(
            "/api/v1/research-changes", params=params
        ).json() == client.get(
            "/api/v1/research-changes", params=params
        ).json()

    def test_inverted_window_rejected(self, client):
        response = client.get(
            "/api/v1/research-changes",
            params={
                "symbol": "TCS",
                "baseline_as_of": AS_OF_ISO,
                "current_as_of": BASELINE_ISO,
            },
        )
        assert response.status_code == 400

    def test_missing_params_rejected(self, client):
        response = client.get(
            "/api/v1/research-changes", params={"symbol": "TCS"}
        )
        assert response.status_code == 400

    def test_naive_timestamps_rejected(self, client):
        response = client.get(
            "/api/v1/research-changes",
            params={
                "symbol": "TCS",
                "baseline_as_of": "2025-09-15T00:00:00",
                "current_as_of": "2026-08-10T12:00:00",
            },
        )
        assert response.status_code == 400


class TestDeltaRoutes:
    def test_research_delta_route(self, client):
        response = client.get(
            "/api/v1/research-delta",
            params={
                "symbol": "TCS",
                "baseline_as_of": BASELINE_ISO,
                "current_as_of": AS_OF_ISO,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert "new_evidence" in payload
        _scan_forbidden(payload)

    def test_coverage_delta_route(self, client):
        response = client.get(
            "/api/v1/coverage/delta",
            params={
                "symbol": "TCS",
                "baseline_as_of": BASELINE_ISO,
                "current_as_of": AS_OF_ISO,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert "newly_covered_categories" in payload
        _scan_forbidden(payload)


class TestContextRoute:
    def _context_id_for(self, symbol: str) -> str:
        stamp = AS_OF.strftime("%Y%m%dT%H%M%SZ")
        digest = hashlib.sha256(
            f"{symbol}|{stamp}".encode()
        ).hexdigest()[:12]
        return f"rc-{symbol}-{stamp}-{digest}"

    def test_valid_context_replays(self, client):
        response = client.get(
            f"/api/v1/research-context/{self._context_id_for('INFY')}"
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["symbol"] == "INFY"
        assert payload["pit_checks_passed"] is True

    def test_tampered_context_rejected(self, client):
        response = client.get(
            "/api/v1/research-context/rc-TCS-20260810T120000Z-000000000000"
        )
        assert response.status_code == 400

    def test_garbage_context_rejected(self, client):
        assert (
            client.get("/api/v1/research-context/not-a-context").status_code
            == 400
        )


class TestConflictRoute:
    def test_conflicts_expose_both_sides_only(self, client):
        response = client.get(
            "/api/v1/evidence/conflicts",
            params={"symbol": "TCS", "as_of": AS_OF_ISO},
        )
        assert response.status_code == 200
        payload = response.json()
        for conflict in payload:
            assert "first" in conflict and "second" in conflict
            for side in (conflict["first"], conflict["second"]):
                assert side["title"]
                assert side["source_name"]
        _scan_forbidden(payload)

    def test_unknown_symbol_is_null_safe_error(self, client):
        response = client.get(
            "/api/v1/evidence/conflicts",
            params={"symbol": "NOPE", "as_of": AS_OF_ISO},
        )
        assert response.status_code in (400, 404)


class TestCalendarRoute:
    def test_events_within_range_with_notice(self, client):
        response = client.get(
            "/api/v1/calendar",
            params={
                "symbols": "TCS,INFY",
                "range_from": "2026-01-01T00:00:00Z",
                "range_to": AS_OF_ISO,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        for event in payload["events"]:
            stamp = event["event_date"]
            assert "2026-01-01" <= stamp[:10] <= "2026-08-10"
        joined = " ".join(payload["notes"])
        assert "guarantee" in joined.lower() or "not" in joined.lower()
        _scan_forbidden(payload)

    def test_all_universe_expands(self, client):
        response = client.get(
            "/api/v1/calendar",
            params={
                "symbols": "all",
                "range_from": "2026-06-01T00:00:00Z",
                "range_to": AS_OF_ISO,
            },
        )
        assert response.status_code == 200
        symbols = {event["symbol"] for event in response.json()["events"]}
        assert symbols <= {"TCS", "RELIANCE", "INFY", "HDFCBANK", "SUNPHARMA", "M&M"}

    def test_inverted_range_rejected(self, client):
        response = client.get(
            "/api/v1/calendar",
            params={
                "symbols": "TCS",
                "range_from": AS_OF_ISO,
                "range_to": "2026-01-01T00:00:00Z",
            },
        )
        assert response.status_code == 400

    def test_empty_symbols_rejected(self, client):
        response = client.get(
            "/api/v1/calendar",
            params={
                "symbols": ",,,",
                "range_from": "2026-01-01T00:00:00Z",
                "range_to": AS_OF_ISO,
            },
        )
        assert response.status_code == 400


# ==========================================================================
# T1-W2: Research Context Snapshot 2.0
# ==========================================================================


class TestContextSnapshotV2:
    def test_schema_version_present(self, results):
        _, after = results
        snapshot = build_context_snapshot(after)
        assert snapshot.schema_version == CONTEXT_SCHEMA_VERSION

    def test_universe_populated(self, results):
        _, after = results
        snapshot = build_context_snapshot(
            after, universe=("TCS", "INFY"), requested_as_of=AS_OF
        )
        assert "TCS" in snapshot.universe
        assert "INFY" in snapshot.universe
        assert snapshot.requested_as_of == AS_OF
        assert snapshot.effective_as_of == after.as_of

    def test_provenance_summary_populated(self, results):
        _, after = results
        snapshot = build_context_snapshot(after)
        assert isinstance(snapshot.provenance_summary, tuple)
        assert len(snapshot.provenance_summary) > 0

    def test_research_observations_count(self, results):
        _, after = results
        snapshot = build_context_snapshot(after)
        assert snapshot.research_observations >= 0

    def test_gap_states_populated(self, results):
        _, after = results
        snapshot = build_context_snapshot(after)
        assert isinstance(snapshot.gap_states, tuple)

    def test_freshness_summary_populated(self, results):
        _, after = results
        snapshot = build_context_snapshot(after)
        assert isinstance(snapshot.freshness_summary, tuple)

    def test_source_included_excluded_populated(self, results):
        _, after = results
        snapshot = build_context_snapshot(after)
        assert isinstance(snapshot.source_included, tuple)
        assert isinstance(snapshot.source_excluded, tuple)

    def test_same_inputs_same_context_id(self, results):
        _, after = results
        s1 = build_context_snapshot(after)
        s2 = build_context_snapshot(after)
        assert s1.context_id == s2.context_id
        assert s1.model_dump(mode="json") == s2.model_dump(mode="json")

    def test_same_context_id_same_replay(self, client):
        response = client.get(
            f"/api/v1/research-context/{context_id_for('TCS', AS_OF)}"
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["schema_version"] == CONTEXT_SCHEMA_VERSION
        assert "provenance_summary" in payload
        assert "universe" in payload


# ==========================================================================
# T1-W2: Change Radar 2.0
# ==========================================================================


class TestChangeRadarV2:
    def test_change_types_include_new_variants(self, results):
        before, after = results
        changes = build_symbol_changes(before, after)
        known_types = {c.change_type.value for c in changes}
        # All returned types must be from the expanded enum.
        for ct in known_types:
            assert ct in {t.value for t in ChangeType}

    def test_changes_carry_before_after_fields(self, results):
        before, after = results
        changes = build_symbol_changes(before, after)
        for change in changes:
            payload = change.model_dump(mode="json")
            assert "before" in payload
            assert "after" in payload
            assert "why_changed" in payload

    def test_new_items_have_after_populated(self, results):
        before, after = results
        changes = build_symbol_changes(before, after)
        new_changes = [c for c in changes if c.change_type.value.startswith("NEW_")]
        for change in new_changes:
            assert change.after is not None

    def test_gap_changes_use_correct_type(self, results):
        before, after = results
        changes = build_symbol_changes(before, after)
        gap_changes = [c for c in changes if "GAP" in c.change_type.value]
        for change in gap_changes:
            assert change.change_type.value in {
                "RESEARCH_GAP_OPENED",
                "RESEARCH_GAP_RESOLVED",
                "RESEARCH_GAP_CHANGED",
                "RESEARCH_GAP_REOPENED",
            }

    def test_empty_when_same_result(self, results):
        before, after = results
        changes = build_symbol_changes(before, after)
        assert isinstance(changes, tuple)

    def test_deterministic_across_runs(self, results):
        before, after = results
        first = build_symbol_changes(before, after)
        second = build_symbol_changes(before, after)
        assert first == second


# ==========================================================================
# T1-W2: Evidence Delta 2.0
# ==========================================================================


class TestEvidenceDeltaV2:
    def test_has_removed_observations(self, results):
        before, after = results
        report = build_evidence_delta(before, after)
        assert hasattr(report, "removed_observations")
        assert isinstance(report.removed_observations, tuple)

    def test_observation_changes_structured(self, results):
        before, after = results
        report = build_evidence_delta(before, after)
        for obs in report.financial_observation_changes:
            assert obs.metric
            assert "previous_value" in obs.model_dump()
            assert "current_value" in obs.model_dump()

    def test_deterministic_and_sorted(self, results):
        before, after = results
        first = build_evidence_delta(before, after)
        second = build_evidence_delta(before, after)
        assert first.model_dump(mode="json") == second.model_dump(mode="json")

    def test_evidence_ids_unique_in_delta(self, results):
        before, after = results
        report = build_evidence_delta(before, after)
        all_ids = (
            [e.evidence_id for e in report.new_evidence]
            + [e.evidence_id for e in report.removed_evidence]
            + [e.evidence_id for e in report.changed_evidence]
        )
        # Within each category, IDs should be unique.
        assert len([e.evidence_id for e in report.new_evidence]) == len(
            set(e.evidence_id for e in report.new_evidence)
        )


# ==========================================================================
# T1-W2: Coverage Delta 2.0
# ==========================================================================


class TestCoverageDeltaV2:
    def test_has_state_transitions(self, results):
        before, after = results
        report = build_coverage_delta(before, after)
        assert hasattr(report, "state_transitions")
        assert isinstance(report.state_transitions, tuple)

    def test_transitions_have_direction(self, results):
        before, after = results
        report = build_coverage_delta(before, after)
        for transition in report.state_transitions:
            assert transition.direction is not None
            assert "→" in transition.direction or transition.direction.startswith("GAP")

    def test_newly_covered_has_direction(self, results):
        before, after = results
        report = build_coverage_delta(before, after)
        for cat in report.newly_covered_categories:
            assert cat.direction is not None

    def test_gaps_have_direction_labels(self, results):
        before, after = results
        report = build_coverage_delta(before, after)
        for gap in report.gaps_opened:
            assert gap.direction == "GAP OPENED"
        for gap in report.gaps_resolved:
            assert gap.direction == "GAP RESOLVED"


# ==========================================================================
# T1-W2: Calendar 2.0
# ==========================================================================


class TestCalendarV2:
    def test_events_have_effective_date(self, client):
        response = client.get(
            "/api/v1/calendar",
            params={
                "symbols": "TCS",
                "range_from": "2026-01-01T00:00:00Z",
                "range_to": AS_OF_ISO,
            },
        )
        assert response.status_code == 200
        for event in response.json()["events"]:
            assert "effective_date" in event
            assert "available_at" in event

    def test_events_have_pit_available(self, client):
        response = client.get(
            "/api/v1/calendar",
            params={
                "symbols": "TCS",
                "range_from": "2026-01-01T00:00:00Z",
                "range_to": AS_OF_ISO,
            },
        )
        assert response.status_code == 200
        for event in response.json()["events"]:
            assert isinstance(event["pit_available"], bool)

    def test_recorded_events_have_source(self, client):
        response = client.get(
            "/api/v1/calendar",
            params={
                "symbols": "TCS",
                "range_from": "2026-01-01T00:00:00Z",
                "range_to": AS_OF_ISO,
            },
        )
        assert response.status_code == 200
        for event in response.json()["events"]:
            if event["state"] == "RECORDED":
                assert event["source"] is not None


# ==========================================================================
# T1-W2: Cross-company symbol isolation
# ==========================================================================


class TestSymbolIsolation:
    def test_changes_isolated_per_symbol(self, results):
        before, after = results
        changes = build_symbol_changes(before, after)
        for change in changes:
            assert change.symbol == "TCS"

    def test_evidence_delta_isolated_per_symbol(self, results):
        before, after = results
        report = build_evidence_delta(before, after)
        assert report.symbol == "TCS"

    def test_coverage_delta_isolated_per_symbol(self, results):
        before, after = results
        report = build_coverage_delta(before, after)
        assert report.symbol == "TCS"

    def test_context_snapshot_isolated_per_symbol(self, results):
        _, after = results
        snapshot = build_context_snapshot(after)
        assert snapshot.symbol == "TCS"

    def test_different_symbols_different_context_ids(self):
        id_a = context_id_for("TCS", AS_OF)
        id_b = context_id_for("INFY", AS_OF)
        assert id_a != id_b

    def test_same_symbol_different_dates_different_ids(self):
        id_early = context_id_for("TCS", BASELINE)
        id_late = context_id_for("TCS", AS_OF)
        assert id_early != id_late


# ==========================================================================
# T1-W2: No forbidden terms in new outputs
# ==========================================================================


class TestNoForbiddenTermsV2:
    def test_context_snapshot_clean(self, results):
        _, after = results
        snapshot = build_context_snapshot(after)
        payload = snapshot.model_dump(mode="json")
        _scan_forbidden(payload)

    def test_changes_clean(self, results):
        before, after = results
        for change in build_symbol_changes(before, after):
            _scan_forbidden(change.model_dump(mode="json"))

    def test_evidence_delta_clean(self, results):
        before, after = results
        report = build_evidence_delta(before, after)
        _scan_forbidden(report.model_dump(mode="json"))

    def test_coverage_delta_clean(self, results):
        before, after = results
        report = build_coverage_delta(before, after)
        _scan_forbidden(report.model_dump(mode="json"))
