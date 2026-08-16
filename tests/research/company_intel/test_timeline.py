from __future__ import annotations

from datetime import datetime

from src.research.company_intel import build_timeline, timeline_at
from src.research.company_intel.semantics import (
    IntelCategory,
    IntelKind,
)

from .conftest import AS_OF, make_item, ts


def test_timeline_at_prefers_published():
    item = make_item(
        item_id="a",
        published_at=ts(2026, 7, 9),
        available_at=ts(2026, 8, 1),
    ).model_copy(update={"effective_at": ts(2026, 7, 1)})

    assert timeline_at(item) == ts(2026, 7, 9)


def test_timeline_at_falls_back_to_effective():
    item = make_item(
        item_id="a",
        published_at=None,
        available_at=ts(2026, 8, 1),
    ).model_copy(
        update={
            "published_at": None,
            "effective_at": ts(2026, 7, 1),
        }
    )

    assert timeline_at(item) == ts(2026, 7, 1)


def test_timeline_at_falls_back_to_available():
    item = make_item(
        item_id="a",
        published_at=None,
        available_at=ts(2026, 8, 1),
    )

    assert timeline_at(item) == ts(2026, 8, 1)


def test_build_timeline_orders_by_timeline_at():
    later = make_item(
        item_id="later",
        published_at=ts(2026, 8, 1),
        available_at=ts(2026, 8, 1),
    )
    earlier = make_item(
        item_id="earlier",
        published_at=ts(2026, 7, 1),
        available_at=ts(2026, 7, 1),
    )

    timeline = build_timeline(
        [later, earlier],
        symbol="TCS",
        as_of=AS_OF,
    )

    assert [entry.entry_id for entry in timeline.entries] == [
        "timeline:earlier",
        "timeline:later",
    ]
    assert timeline.earliest_at == ts(2026, 7, 1)
    assert timeline.latest_at == ts(2026, 8, 1)


def test_build_timeline_breaks_ties_by_entry_id():
    first = make_item(
        item_id="zzz",
        published_at=ts(2026, 8, 1),
        available_at=ts(2026, 8, 1),
    )
    second = make_item(
        item_id="aaa",
        published_at=ts(2026, 8, 1),
        available_at=ts(2026, 8, 1),
    )

    timeline = build_timeline(
        [first, second],
        symbol="TCS",
        as_of=AS_OF,
    )

    assert [entry.entry_id for entry in timeline.entries] == [
        "timeline:aaa",
        "timeline:zzz",
    ]


def test_build_timeline_is_point_in_time_pure():
    future = make_item(
        item_id="future",
        published_at=ts(2026, 9, 1),
        available_at=ts(2026, 9, 1),
    )
    known = make_item(
        item_id="known",
        published_at=ts(2026, 7, 1),
        available_at=ts(2026, 7, 1),
    )

    timeline = build_timeline(
        [future, known],
        symbol="TCS",
        as_of=AS_OF,
    )

    assert [entry.entry_id for entry in timeline.entries] == [
        "timeline:known"
    ]


def test_build_timeline_filters_other_companies():
    other = make_item(
        item_id="other",
        symbol="INFY",
        published_at=ts(2026, 7, 1),
        available_at=ts(2026, 7, 1),
    )

    timeline = build_timeline([other], symbol="TCS", as_of=AS_OF)

    assert timeline.entries == ()
    assert timeline.notes == ("No evidence was knowable at as_of.",)


def test_build_timeline_counts_by_category():
    item = make_item(
        item_id="a",
        kind=IntelKind.FINANCIAL_PERIOD,
        published_at=ts(2026, 7, 1),
        available_at=ts(2026, 7, 1),
    )

    timeline = build_timeline([item], symbol="TCS", as_of=AS_OF)

    assert timeline.counts == {"FINANCIAL_DISCLOSURE": 1}


def test_build_timeline_uses_explicit_category_when_present():
    item = make_item(
        item_id="a",
        kind=IntelKind.FINANCIAL_PERIOD,
        published_at=ts(2026, 7, 1),
        available_at=ts(2026, 7, 1),
    ).model_copy(update={"intel_category": IntelCategory.CORPORATE_ACTION})

    timeline = build_timeline([item], symbol="TCS", as_of=AS_OF)

    assert timeline.entries[0].intel_category == IntelCategory.CORPORATE_ACTION


def test_build_timeline_requires_aware_as_of():
    import pytest

    item = make_item(
        item_id="a",
        published_at=ts(2026, 7, 1),
        available_at=ts(2026, 7, 1),
    )

    naive = datetime(2026, 8, 10, 12, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        build_timeline([item], symbol="TCS", as_of=naive)
