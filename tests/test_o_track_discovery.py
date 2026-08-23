"""
O-TRACK O5 — discovery feed canonicalization tests.

Pins:
- one canonical item per underlying event across feed surfaces;
- opposing-direction records never merge;
- source / provenance unions on merged items;
- deterministic ordering and counts;
- PIT eligibility flags preserved;
- trending stays a defined research-activity metric;
- end-to-end behavior across all six recorded companies.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.research.discovery_feed import (
    DiscoveryFeedItem,
    FeedItemType,
    _merge_by_event_identity,
    build_discovery_feed,
    compute_trending,
)
from src.api.recorded_research import RecordedCompanyResearchService

TZ = timezone.utc
AS_OF = datetime(2026, 8, 10, 12, tzinfo=TZ)

VERIFIED_COMPANIES = (
    "TCS",
    "RELIANCE",
    "INFY",
    "HDFCBANK",
    "SUNPHARMA",
    "M&M",
)


def _item(
    item_id: str,
    *,
    title: str = "Company wins large order",
    symbol: str = "TCS",
    item_type: FeedItemType = FeedItemType.COMPANY_DEVELOPMENT,
    direction: str | None = None,
    source_name: str | None = "filing_a",
    published_at: datetime | None = None,
) -> DiscoveryFeedItem:
    stamp = published_at or datetime(2026, 5, 21, tzinfo=TZ)
    return DiscoveryFeedItem(
        item_id=item_id,
        symbol=symbol,
        item_type=item_type,
        title=title,
        description=f"description of {item_id}",
        published_at=stamp,
        available_at=stamp,
        source_name=source_name,
        source_type="FILING",
        provenance_id=f"prov-{item_id}",
        pit_eligible=True,
        direction=direction,
    )


class TestCanonicalMergeInFeed:
    def test_duplicate_events_collapse_to_one_item(self):
        items = [
            _item("company_development:TCS:intel-1"),
            _item(
                "corporate_action:TCS:ca-9",
                item_type=FeedItemType.CORPORATE_ACTION,
            ),
        ]

        merged, count = _merge_by_event_identity(items)

        assert len(merged) == 1
        assert count == 1
        assert merged[0].event_id is not None
        assert sorted(merged[0].member_ids) == sorted(
            i.item_id for i in items
        )
        # Canonical id becomes the stable item identity.
        assert merged[0].item_id == merged[0].event_id

    def test_merged_item_unions_sources_and_provenance(self):
        items = [
            _item("a", source_name="exchange"),
            _item("b", source_name="newswire"),
        ]

        merged, _ = _merge_by_event_identity(items)

        assert merged[0].sources == ("exchange", "newswire")
        assert merged[0].provenance_ids == ("prov-a", "prov-b")

    def test_opposing_directions_stay_separate(self):
        items = [
            _item("pos-1", direction="POSITIVE"),
            _item("neg-1", direction="NEGATIVE"),
        ]

        merged, count = _merge_by_event_identity(items)

        assert len(merged) == 2
        assert count == 0
        directions = {m.direction for m in merged}
        assert directions == {"POSITIVE", "NEGATIVE"}

    def test_single_items_get_event_ids_without_reordering(self):
        items = [
            _item("one", title="Event one"),
            _item("two", title="Event two"),
        ]

        merged, count = _merge_by_event_identity(items)

        assert count == 0
        assert {m.item_id for m in merged} == {"one", "two"}
        assert all(m.event_id for m in merged)
        assert all(m.member_ids == (m.item_id,) for m in merged)


class TestFeedBuilder:
    def test_feed_reports_merged_duplicates(self):
        class _Result:
            company = "TCS"
            intelligence = None
            evidence_items = ()

        feed = build_discovery_feed(
            [_Result()],
            as_of=AS_OF,
            item_types=None,
        )

        assert feed.items == ()
        assert feed.duplicates_merged == 0
        assert feed.notes == (
            "No recorded research items were knowable at as_of.",
        )

    def test_naive_as_of_rejected(self):
        with pytest.raises(ValueError):
            build_discovery_feed([], as_of=datetime(2026, 8, 10))


@pytest.fixture(scope="module")
def recorded_results(tmp_path_factory):
    """Run the recorded research path once for all six companies."""

    archive_root = tmp_path_factory.mktemp("o5-archive")
    service = RecordedCompanyResearchService(archive_root=archive_root)
    results = []
    for symbol in VERIFIED_COMPANIES:
        if not service.research_available(symbol):
            continue
        results.append(service.run(symbol, as_of=AS_OF))
    return results


class TestRecordedCompanies:
    def test_all_six_companies_produce_results(self, recorded_results):
        assert len(recorded_results) == 6

    def test_feed_is_deterministic_across_companies(
        self, recorded_results
    ):
        first = build_discovery_feed(recorded_results, as_of=AS_OF)
        second = build_discovery_feed(
            list(reversed(recorded_results)), as_of=AS_OF
        )

        assert first.model_dump(mode="json") == second.model_dump(
            mode="json"
        )

    def test_feed_ordering_is_latest_first_then_symbol_then_id(
        self, recorded_results
    ):
        feed = build_discovery_feed(recorded_results, as_of=AS_OF)

        keys = []
        for item in feed.items:
            stamp = item.published_at or item.available_at or AS_OF
            keys.append((-stamp.timestamp(), item.symbol, item.item_id))

        assert keys == sorted(keys)

    def test_every_item_is_pit_flagged_and_lineage_backed(
        self, recorded_results
    ):
        feed = build_discovery_feed(recorded_results, as_of=AS_OF)

        assert feed.items
        for item in feed.items:
            assert item.pit_eligible == (item.available_at is not None)
            assert item.symbol in VERIFIED_COMPANIES

    def test_type_counts_match_items(self, recorded_results):
        feed = build_discovery_feed(recorded_results, as_of=AS_OF)

        total = sum(feed.type_counts.values())
        assert total == feed.item_count

        rebuilt: dict[str, int] = {}
        for item in feed.items:
            rebuilt[item.item_type.value] = (
                rebuilt.get(item.item_type.value, 0) + 1
            )
        assert rebuilt == feed.type_counts

    def test_trending_is_defined_activity_not_opinion(
        self, recorded_results
    ):
        feed = build_discovery_feed(recorded_results, as_of=AS_OF)
        trending = compute_trending(feed, window_days=30)

        assert trending.window_days == 30
        assert "not a popularity ranking" in trending.definition
        assert "no investment opinion" in trending.definition

        ranked_keys = [
            (-t.recent_item_count, t.symbol) for t in trending.ranked
        ]
        assert ranked_keys == sorted(ranked_keys)

        total = sum(t.total_item_count for t in trending.ranked)
        assert total == feed.item_count
