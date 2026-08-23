"""
O-TRACK O2 — canonical research-event identity regression tests.

Pins the dedupe guarantees:
- duplicate records of the same event merge into one canonical event;
- multiple sources of one event union their sources and provenance;
- opposing-direction records are never merged;
- output ids and ordering are deterministic;
- adapters preserve provenance from every recorded source shape.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.data.company.corporate_actions import (
    CorporateActionItem,
    CorporateActionType,
)
from src.data.company.news import CompanyNewsItem
from src.research.event_identity import (
    EventCandidateRecord,
    EventDirection,
    build_research_event_set,
    candidate_from_corporate_action,
    candidate_from_intel_item,
    candidate_from_news_item,
    compute_event_id,
    dedupe_research_events,
    normalize_event_title,
)
from src.research.company_intel.models import CorporateIntelItem, SourceRef
from src.research.company_intel.semantics import (
    IntelCategory,
    IntelKind,
    IntelDirection,
    VerificationStatus,
)

TZ = timezone.utc


def ts(year: int, month: int, day: int, hour: int = 12) -> datetime:
    return datetime(year, month, day, hour, tzinfo=TZ)


def _candidate(
    record_id: str,
    *,
    title: str = "Company wins large order",
    symbol: str = "TCS",
    category: str = "BUSINESS_EVENT",
    direction: EventDirection = EventDirection.UNKNOWN,
    source_name: str | None = "filing_a",
    provenance_id: str | None = "prov-a",
    published_at: datetime | None = None,
    available_at: datetime | None = None,
    event_date: date | None = date(2026, 5, 20),
) -> EventCandidateRecord:
    stamp = published_at or ts(2026, 5, 21)
    return EventCandidateRecord(
        symbol=symbol,
        title=title,
        category=category,
        record_id=record_id,
        description=f"description for {record_id}",
        event_date=event_date,
        direction=direction,
        verification_status="REPORTED",
        published_at=stamp,
        available_at=available_at or stamp,
        source_name=source_name,
        provenance_id=provenance_id,
    )


class TestDuplicateMerging:
    def test_duplicate_same_event_merges_to_one(self):
        events = dedupe_research_events(
            [
                _candidate("intel:1"),
                _candidate("news:1", source_name="wire_b"),
            ]
        )

        assert len(events) == 1
        assert sorted(events[0].member_ids) == ["intel:1", "news:1"]

    def test_same_event_multiple_sources_union(self):
        events = dedupe_research_events(
            [
                _candidate(
                    "intel:1",
                    source_name="exchange_filing",
                    provenance_id="prov-1",
                ),
                _candidate(
                    "news:9",
                    source_name="business_wire",
                    provenance_id="prov-2",
                ),
                _candidate(
                    "action:3",
                    source_name="exchange_filing",
                    provenance_id="prov-3",
                ),
            ]
        )

        assert len(events) == 1
        assert events[0].sources == (
            "business_wire",
            "exchange_filing",
        )
        assert events[0].provenance_ids == ("prov-1", "prov-2", "prov-3")

    def test_differing_provenance_is_unioned_not_discarded(self):
        events = dedupe_research_events(
            [
                _candidate("a:1", provenance_id="prov-x"),
                _candidate("b:2", provenance_id="prov-y"),
            ]
        )

        assert events[0].provenance_ids == ("prov-x", "prov-y")

    def test_different_dates_are_distinct_events(self):
        events = dedupe_research_events(
            [
                _candidate("a:1", event_date=date(2026, 5, 20)),
                _candidate("b:2", event_date=date(2026, 6, 20)),
            ]
        )

        assert len(events) == 2

    def test_title_normalization_drives_identity(self):
        assert (
            normalize_event_title("Company  WINS large-order!")
            == "company wins large order"
        )

        events = dedupe_research_events(
            [
                _candidate("a:1", title="Company wins LARGE order!"),
                _candidate("b:2", title="company  wins large order"),
            ]
        )

        assert len(events) == 1

    def test_symbol_scopes_identity(self):
        events = dedupe_research_events(
            [
                _candidate("a:1", symbol="TCS"),
                _candidate("b:2", symbol="INFY"),
            ]
        )

        assert len(events) == 2


class TestOpposingEvidence:
    def test_opposite_directions_never_merge(self):
        events = dedupe_research_events(
            [
                _candidate("a:1", direction=EventDirection.POSITIVE),
                _candidate("b:2", direction=EventDirection.NEGATIVE),
            ]
        )

        assert len(events) == 2
        directions = {e.direction for e in events}
        assert directions == {
            EventDirection.POSITIVE,
            EventDirection.NEGATIVE,
        }

    def test_neutral_joins_larger_side_without_flipping_direction(self):
        events = dedupe_research_events(
            [
                _candidate("p:1", direction=EventDirection.POSITIVE),
                _candidate("p:2", direction=EventDirection.POSITIVE),
                _candidate("n:1", direction=EventDirection.NEGATIVE),
                _candidate("u:1", direction=EventDirection.UNKNOWN),
            ]
        )

        assert len(events) == 2
        by_direction = {e.direction: e for e in events}
        assert set(by_direction) == {
            EventDirection.POSITIVE,
            EventDirection.NEGATIVE,
        }
        # The unknown member joins the larger POSITIVE side.
        assert "u:1" in by_direction[EventDirection.POSITIVE].member_ids

    def test_event_set_counts_opposing_pairs(self):
        result = build_research_event_set(
            [
                _candidate("a:1", direction=EventDirection.POSITIVE),
                _candidate("b:2", direction=EventDirection.NEGATIVE),
            ],
            symbol="TCS",
            as_of=ts(2026, 7, 1),
        )

        assert result.opposing_pairs_kept_separate == 1
        assert any("opposing" in note for note in result.notes)


class TestDeterminism:
    def test_ordering_is_deterministic_latest_first(self):
        candidates = [
            _candidate(
                "old:1",
                title="Event one",
                published_at=ts(2026, 1, 10),
            ),
            _candidate(
                "new:2",
                title="Event two",
                published_at=ts(2026, 3, 10),
            ),
            _candidate(
                "mid:3",
                title="Event three",
                published_at=ts(2026, 2, 10),
            ),
        ]

        first = dedupe_research_events(candidates)
        second = dedupe_research_events(list(reversed(candidates)))

        assert [e.event_id for e in first] == [
            e.event_id for e in second
        ]
        assert first[0].event == "Event two"

    def test_same_input_produces_identical_set(self):
        candidates = [_candidate(f"m:{i}") for i in range(4)]

        a = build_research_event_set(
            candidates, symbol="TCS", as_of=ts(2026, 7, 1)
        )
        b = build_research_event_set(
            list(reversed(candidates)),
            symbol="TCS",
            as_of=ts(2026, 7, 1),
        )

        assert a.events == b.events
        assert a.duplicate_records_merged == b.duplicate_records_merged

    def test_event_id_stable_across_calls(self):
        c = _candidate("x:1")
        assert compute_event_id(c) == compute_event_id(c)


class TestSetSemantics:
    def test_empty_input_notes_and_zero_count(self):
        result = build_research_event_set(
            [], symbol="TCS", as_of=ts(2026, 7, 1)
        )

        assert result.event_count == 0
        assert result.notes == ("No recorded events were knowable at as_of.",)

    def test_symbol_mismatch_rejected(self):
        with pytest.raises(ValueError):
            build_research_event_set(
                [_candidate("a:1", symbol="INFY")],
                symbol="TCS",
                as_of=ts(2026, 7, 1),
            )

    def test_naive_as_of_rejected(self):
        with pytest.raises(ValueError):
            build_research_event_set(
                [],
                symbol="TCS",
                as_of=datetime(2026, 7, 1),
            )

    def test_pit_eligible_requires_availability_on_all_members(self):
        stamped = _candidate("a:1")
        unstamped = EventCandidateRecord(
            **{
                **stamped.__dict__,
                "available_at": None,
            }
        )

        events = dedupe_research_events([stamped, unstamped])

        assert len(events) == 1
        assert events[0].pit_eligible is False


class TestSourceAdapters:
    def test_intel_item_adapter_preserves_lineage(self):
        item = CorporateIntelItem(
            item_id="ev-1",
            symbol="TCS",
            kind=IntelKind.BUSINESS_EVENT,
            intel_category=IntelCategory.CORPORATE_ACTION,
            title="Board approves buyback",
            description="Buyback approved at board meeting.",
            direction=IntelDirection.POSITIVE,
            verification_status=VerificationStatus.CONFIRMED,
            published_at=ts(2026, 4, 1),
            available_at=ts(2026, 4, 2),
            effective_at=ts(2026, 4, 1),
            source=SourceRef(
                source_name="exchange",
                source_type="REGULATORY",
                reliability_tier=1,
                provenance_id="prov-intel-1",
            ),
            provenance_id="prov-intel-1",
        )

        candidate = candidate_from_intel_item(item)

        assert candidate.record_id == "intel:ev-1"
        assert candidate.category == "CORPORATE_ACTION"
        assert candidate.source_name == "exchange"
        assert candidate.provenance_id == "prov-intel-1"
        assert candidate.verification_status == "CONFIRMED"
        assert candidate.direction == EventDirection.POSITIVE
        assert candidate.event_date == date(2026, 4, 1)

    def test_news_item_adapter_preserves_lineage(self):
        item = CompanyNewsItem(
            news_id="nw-1",
            symbol="TCS",
            headline="TCS expands in Europe",
            summary="Expansion announced.",
            published_at=ts(2026, 3, 5),
            available_at=ts(2026, 3, 6),
            source_name="newsroom",
            provenance_id="prov-news-1",
        )

        candidate = candidate_from_news_item(item)

        assert candidate.category == "NEWS"
        assert candidate.title == "TCS expands in Europe"
        assert candidate.provenance_id == "prov-news-1"

    def test_corporate_action_adapter_prefers_effective_date(self):
        item = CorporateActionItem(
            action_id="ca-1",
            symbol="TCS",
            action_type=CorporateActionType.DIVIDEND,
            title="Final dividend declared",
            announcement_date=date(2026, 4, 10),
            effective_date=date(2026, 6, 1),
            source_name="exchange",
            provenance_id="prov-ca-1",
            published_at=ts(2026, 4, 10),
            available_at=ts(2026, 4, 11),
        )

        candidate = candidate_from_corporate_action(item)

        assert candidate.event_date == date(2026, 6, 1)
        assert candidate.category == "CORPORATE_ACTION"
        assert candidate.provenance_id == "prov-ca-1"
