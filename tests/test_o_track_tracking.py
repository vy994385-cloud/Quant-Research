"""
O-TRACK O6 — tracking / alert-output foundation tests.

Pins:
- deterministic change ids and fingerprints (same input => same id);
- duplicate detection yields identical, deduplicated outputs;
- canonical change-type vocabulary across every detection path;
- detected_at / effective_at / PIT eligibility / provenance fields;
- historical as_of windows exclude non-knowable recent events;
- screen entry/exit transitions;
- no predictive or advisory content anywhere.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.analysis.research_gaps import ResearchGap, ResearchGapResult
from src.research.company_intel.models import (
    CorporateIntelItem,
    IntelChange,
    SourceStatus,
    SourceRef,
)
from src.research.company_intel.semantics import (
    ChangeType,
    IntelCategory,
    IntelKind,
)
from src.tracking.models import (
    ChangeDomain,
    TrackedChangeType,
    TrackingChange,
    TrackingSeverity,
)
from src.tracking.research_changes import build_research_change_result
from src.tracking.screen_changes import build_screen_transition_changes

TZ = timezone.utc


def ts(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 12, tzinfo=TZ)


AS_OF = ts(2026, 8, 10)


class _StubIntel:
    def __init__(self, *, changes=(), items=(), source_statuses=(), research_gaps=None):
        self.changes = changes
        self.items = items
        self.source_statuses = source_statuses
        self.research_gaps = research_gaps


class _StubResult:
    def __init__(self, intelligence):
        self.company = "TCS"
        self.intelligence = intelligence
        self.evidence_items = ()


def _intel_change(
    *,
    item_id: str = "fin-1",
    kind: IntelKind = IntelKind.FINANCIAL_PERIOD,
    change_type: ChangeType = ChangeType.NEW,
) -> IntelChange:
    return IntelChange(
        change_type=change_type,
        item_id=item_id,
        kind=kind,
        title="Q4 results filed",
        description="A new financial period was recorded.",
        previous_checksum=None,
        current_checksum="ck-1",
        as_of=AS_OF,
        intel_category=(
            IntelCategory.FINANCIAL_DISCLOSURE
            if kind == IntelKind.FINANCIAL_PERIOD
            else None
        ),
        published_at=ts(2026, 7, 30),
        available_at=ts(2026, 7, 31),
    )


class TestDeterministicIdentity:
    def test_same_input_same_change_id_and_fingerprint(self):
        change_a = TrackingChange(
            change_id="TCS-x-1",
            symbol="TCS",
            domain=ChangeDomain.FINANCIAL,
            title="Revenue increased",
            current_value="1200",
            previous_value="1000",
            change_date=date(2026, 3, 31),
            as_of=AS_OF,
        )
        change_b = TrackingChange(
            change_id="TCS-x-1",
            symbol="TCS",
            domain=ChangeDomain.FINANCIAL,
            title="Revenue increased",
            current_value="1200",
            previous_value="1000",
            change_date=date(2026, 3, 31),
            as_of=AS_OF,
        )

        assert change_a.fingerprint == change_b.fingerprint
        assert len(change_a.fingerprint) == 16
        assert change_a.model_dump() == change_b.model_dump()

    def test_different_content_different_fingerprint(self):
        a = TrackingChange(
            change_id="c1",
            symbol="TCS",
            domain=ChangeDomain.FINANCIAL,
            title="Revenue increased",
            as_of=AS_OF,
        )
        b = TrackingChange(
            change_id="c1",
            symbol="TCS",
            domain=ChangeDomain.FINANCIAL,
            title="Revenue decreased",
            as_of=AS_OF,
        )

        assert a.fingerprint != b.fingerprint

    def test_research_result_build_is_idempotent(self):
        intelligence = _StubIntel(
            source_statuses=[
                SourceStatus(
                    source_name="filings",
                    source_type="COMPANY_FILINGS",
                    item_count=2,
                    stale=True,
                )
            ]
        )

        first = build_research_change_result(
            _StubResult(intelligence), AS_OF
        )
        second = build_research_change_result(
            _StubResult(intelligence), AS_OF
        )

        assert first.model_dump(mode="json") == second.model_dump(
            mode="json"
        )

    def test_duplicate_transitions_collapse(self):
        changes = build_screen_transition_changes(
            screen_hash="abcd1234efgh5678",
            screen_name="High margin filers",
            previous_symbols=("TCS", "INFY"),
            current_symbols=("TCS", "INFY"),
            as_of=AS_OF,
        )

        # No membership delta => no fabricated changes.
        assert changes == ()

    def test_screen_transition_ids_stable_across_runs(self):
        kwargs = dict(
            screen_hash="abcd1234efgh5678",
            screen_name="High margin filers",
            previous_symbols=("TCS",),
            current_symbols=("INFY", "WIPRO"),
            as_of=AS_OF,
        )

        first = build_screen_transition_changes(**kwargs)
        second = build_screen_transition_changes(**kwargs)

        assert first == second
        assert all(c.fingerprint for c in first)


class TestCanonicalChangeTypes:
    def test_financial_disclosure_type(self):
        result = build_research_change_result(
            _StubResult(_StubIntel(changes=[_intel_change()])),
            AS_OF,
        )

        financial = [
            c
            for c in result.changes
            if c.change_type == TrackedChangeType.NEW_FINANCIAL_DISCLOSURE
        ]

        assert len(financial) == 1
        assert financial[0].pit_eligible is True
        assert financial[0].detected_at == AS_OF
        assert financial[0].effective_at == ts(2026, 7, 31)

    def test_new_event_and_corporate_action_types(self):
        base = dict(
            symbol="TCS",
            kind=IntelKind.BUSINESS_EVENT,
            title="Factory expansion announced",
            description="Capacity increase at Pune plant.",
            published_at=ts(2026, 7, 1),
            available_at=ts(2026, 7, 2),
            effective_at=ts(2026, 7, 1),
            source=SourceRef(
                source_name="exchange",
                source_type="REGULATORY",
                reliability_tier=1,
                provenance_id="prov-ev",
            ),
            provenance_id="prov-ev",
        )

        event_item = CorporateIntelItem(item_id="ev-1", **base)
        action_base = dict(base)
        action_base["item_id"] = "ca-1"
        action_base["intel_category"] = IntelCategory.CORPORATE_ACTION
        action_item = CorporateIntelItem(**action_base)

        result = build_research_change_result(
            _StubResult(_StubIntel(items=(event_item, action_item))),
            AS_OF,
        )

        types = {c.change_type for c in result.changes}

        assert TrackedChangeType.NEW_EVENT in types
        assert TrackedChangeType.NEW_CORPORATE_ACTION in types

        event_change = next(
            c
            for c in result.changes
            if c.change_type == TrackedChangeType.NEW_EVENT
        )
        assert event_change.provenance_ids == ("prov-ev",)
        assert event_change.source_names == ("exchange",)

    def test_stale_source_type(self):
        result = build_research_change_result(
            _StubResult(
                _StubIntel(
                    source_statuses=[
                        SourceStatus(
                            source_name="old_wire",
                            source_type="NEWS",
                            item_count=1,
                            stale=True,
                            days_since_latest_published=150,
                        )
                    ]
                )
            ),
            AS_OF,
        )

        stale = [
            c
            for c in result.changes
            if c.change_type == TrackedChangeType.SOURCE_BECAME_STALE
        ]

        assert len(stale) == 1
        assert stale[0].current_value == "150"
        assert "No investment" not in stale[0].description

    def test_gap_state_change_type(self):
        gaps = ResearchGapResult(
            symbol="TCS",
            as_of=str(AS_OF),
            gaps=(
                ResearchGap(
                    gap_id="gap-ownership",
                    symbol="TCS",
                    category="OWNERSHIP",
                    gap="Ownership data unavailable",
                    status="UNAVAILABLE",
                    reason="Not recorded.",
                    priority="HIGH",
                ),
            ),
        )

        result = build_research_change_result(
            _StubResult(_StubIntel(research_gaps=gaps)),
            AS_OF,
        )

        gap_changes = [
            c
            for c in result.changes
            if c.change_type == TrackedChangeType.RESEARCH_GAP_CHANGED
        ]

        assert len(gap_changes) == 1
        assert gap_changes[0].severity == TrackingSeverity.SIGNIFICANT

    def test_every_change_carries_type_fingerprint_and_detection_time(self):
        result = build_research_change_result(
            _StubResult(
                _StubIntel(
                    changes=[_intel_change()],
                    source_statuses=[
                        SourceStatus(
                            source_name="s",
                            source_type="T",
                            item_count=1,
                            stale=True,
                        )
                    ],
                )
            ),
            AS_OF,
        )

        assert result.changes
        for change in result.changes:
            assert change.change_type is not None
            assert change.fingerprint
            assert change.detected_at == AS_OF


class TestHistoricalAsOf:
    def test_old_events_outside_window_are_excluded(self):
        old_event = CorporateIntelItem(
            item_id="ev-old",
            symbol="TCS",
            kind=IntelKind.BUSINESS_EVENT,
            title="Very old event",
            description="Recorded long ago.",
            published_at=ts(2024, 1, 1),
            available_at=ts(2024, 1, 1),
            source=SourceRef(
                source_name="archive",
                source_type="ARCHIVE",
                reliability_tier=3,
            ),
        )

        result = build_research_change_result(
            _StubResult(_StubIntel(items=(old_event,))),
            AS_OF,
        )

        assert result.change_count == 0
        assert any("No recent tracked changes" in n for n in result.notes)

    def test_detected_at_follows_requested_as_of(self):
        historical_as_of = ts(2026, 5, 1)

        result = build_research_change_result(
            _StubResult(
                _StubIntel(changes=[_intel_change()])
            ),
            historical_as_of,
        )

        for change in result.changes:
            assert change.detected_at == historical_as_of
            assert change.as_of == historical_as_of


class TestScreenTransitions:
    def test_entries_and_exits(self):
        changes = build_screen_transition_changes(
            screen_hash="abcdef0123456789",
            screen_name="Cash-rich balance sheets",
            previous_symbols=("TCS", "INFY"),
            current_symbols=("INFY", "WIPRO"),
            as_of=AS_OF,
        )

        entries = [
            c
            for c in changes
            if c.change_type == TrackedChangeType.SCREEN_ENTRY
        ]
        exits = [
            c
            for c in changes
            if c.change_type == TrackedChangeType.SCREEN_EXIT
        ]

        assert [c.symbol for c in entries] == ["WIPRO"]
        assert [c.symbol for c in exits] == ["TCS"]

    def test_no_advisory_wording(self):
        changes = build_screen_transition_changes(
            screen_hash="abcdef0123456789",
            screen_name="Any screen",
            previous_symbols=(),
            current_symbols=("TCS",),
            as_of=AS_OF,
        )

        forbidden = ("buy", "sell", "recommendation", "signal")
        for change in changes:
            blob = f"{change.title} {change.description}".lower()
            assert not any(word in blob for word in forbidden)

    def test_validation(self):
        with pytest.raises(ValueError):
            build_screen_transition_changes(
                screen_hash=" ",
                screen_name="x",
                previous_symbols=(),
                current_symbols=(),
                as_of=AS_OF,
            )

        with pytest.raises(ValueError):
            build_screen_transition_changes(
                screen_hash="abc",
                screen_name="x",
                previous_symbols=(),
                current_symbols=(),
                as_of=datetime(2026, 8, 10),
            )
