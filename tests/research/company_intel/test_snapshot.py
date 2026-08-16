from __future__ import annotations

from src.research.company_intel import (
    build_company_intelligence_snapshot,
)
from src.research.company_intel.semantics import (
    IntelKind,
)

from .conftest import AS_OF, make_item, ts


def test_snapshot_splits_items_by_kind():
    items = [
        make_item(
            item_id="e1",
            kind=IntelKind.BUSINESS_EVENT,
        ),
        make_item(
            item_id="m1",
            kind=IntelKind.MANAGEMENT_COMMENTARY,
        ),
        make_item(
            item_id="r1",
            kind=IntelKind.RISK_DEVELOPMENT,
        ),
        make_item(
            item_id="i1",
            kind=IntelKind.INDIRECT_INTELLIGENCE,
        ),
        make_item(
            item_id="f1",
            kind=IntelKind.FINANCIAL_PERIOD,
            semantic_category=None,
            verification_status="CONFIRMED",
            reliability_tier=1,
        ),
        make_item(
            item_id="o1",
            kind=IntelKind.OTHER,
        ),
    ]

    snapshot = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=items,
    )

    assert [i.item_id for i in snapshot.business_events] == ["e1"]
    assert [i.item_id for i in snapshot.management_commentary] == ["m1"]
    assert [i.item_id for i in snapshot.risk_intelligence] == ["r1"]
    assert [i.item_id for i in snapshot.indirect_intelligence] == ["i1"]
    assert [i.item_id for i in snapshot.financial_intelligence_items] == ["f1"]
    assert [i.item_id for i in snapshot.other_intelligence] == ["o1"]

    assert snapshot.item_count == 6
    assert snapshot.coverage["BUSINESS_EVENT"] == 1
    assert snapshot.coverage["FINANCIAL_PERIOD"] == 1


def test_snapshot_deduplicates_items_by_id():
    items = [
        make_item(item_id="dup", kind=IntelKind.BUSINESS_EVENT),
        make_item(
            item_id="dup",
            kind=IntelKind.BUSINESS_EVENT,
            description="different but same id",
        ),
    ]

    snapshot = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=items,
    )

    assert snapshot.item_count == 1
    assert len(snapshot.items) == 1
    assert any(
        "duplicate" in note
        for note in snapshot.notes
    )


def test_snapshot_excludes_future_items():
    items = [
        make_item(
            item_id="future",
            kind=IntelKind.BUSINESS_EVENT,
            available_at=ts(2026, 9, 1),
        ),
        make_item(
            item_id="known",
            kind=IntelKind.BUSINESS_EVENT,
            available_at=ts(2026, 7, 1),
        ),
    ]

    snapshot = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=items,
    )

    assert [i.item_id for i in snapshot.business_events] == [
        "known"
    ]


def test_snapshot_excludes_other_symbol_items():
    items = [
        make_item(item_id="tcs-item", symbol="TCS"),
        make_item(item_id="infy-item", symbol="INFY"),
    ]

    snapshot = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=items,
    )

    assert snapshot.item_count == 1
    assert snapshot.items[0].item_id == "tcs-item"


def test_snapshot_summaries():
    items = [
        make_item(
            item_id="a",
            kind=IntelKind.BUSINESS_EVENT,
            verification_status="CONFIRMED",
            reliability_tier=1,
        ),
        make_item(
            item_id="b",
            kind=IntelKind.RISK_DEVELOPMENT,
            verification_status="ALLEGED",
        ),
    ]

    snapshot = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=items,
    )

    assert snapshot.semantic_summary["FACT"] == 1
    assert snapshot.semantic_summary["ALLEGATION"] == 1
    assert snapshot.status_summary["CONFIRMED"] == 1
    assert snapshot.status_summary["ALLEGED"] == 1


def test_snapshot_tracks_sources_and_provenance():
    items = [
        make_item(
            item_id="a",
            source_name="source-alpha",
            provenance_id="prov-alpha",
        ),
        make_item(
            item_id="b",
            source_name="source-beta",
            provenance_id="prov-beta",
        ),
    ]

    snapshot = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=items,
        provenance_ids=("market-record", "financial-record"),
    )

    assert snapshot.source_ids == (
        "source-alpha",
        "source-beta",
    )
    assert set(snapshot.provenance_ids) == {
        "market-record",
        "financial-record",
        "prov-alpha",
        "prov-beta",
    }


def test_snapshot_item_is_known_at_as_of():
    items = [
        make_item(
            item_id="a",
            available_at=ts(2026, 7, 1),
        ),
    ]

    snapshot = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=items,
    )

    assert all(
        item.is_known_at(AS_OF)
        for item in snapshot.items
    )


def test_snapshot_is_deterministic():
    items = [
        make_item(
            item_id="b",
            available_at=ts(2026, 7, 1),
        ),
        make_item(
            item_id="a",
            available_at=ts(2026, 6, 1),
        ),
    ]

    first = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=items,
    )
    second = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=list(reversed(items)),
    )

    assert first == second


def test_snapshot_builds_timeline():
    items = [
        make_item(
            item_id="a",
            kind=IntelKind.BUSINESS_EVENT,
            available_at=ts(2026, 7, 1),
        ),
        make_item(
            item_id="b",
            kind=IntelKind.FINANCIAL_PERIOD,
            available_at=ts(2026, 6, 1),
        ),
    ]

    snapshot = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=items,
    )

    assert snapshot.timeline is not None
    assert [entry.entry_id for entry in snapshot.timeline.entries] == [
        "timeline:b",
        "timeline:a",
    ]
    assert snapshot.timeline.counts == {
        "FINANCIAL_DISCLOSURE": 1,
        "BUSINESS_NEWS": 1,
    }


def test_snapshot_builds_research_status():
    items = [
        make_item(
            item_id="a",
            kind=IntelKind.BUSINESS_EVENT,
            available_at=ts(2026, 7, 1),
        ),
    ]

    snapshot = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=items,
    )

    assert snapshot.status is not None
    assert snapshot.status.coverage.item_count == 1
    assert snapshot.status.freshness.stale is False
    assert snapshot.status.quality.conflict_count == 0
