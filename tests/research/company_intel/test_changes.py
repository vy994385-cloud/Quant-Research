from __future__ import annotations

from src.research.company_intel import (
    build_company_intelligence_snapshot,
    change_counts,
    detect_changes,
)
from src.research.company_intel.models import (
    SnapshotDiff,
)
from src.research.company_intel.semantics import (
    ChangeType,
    VerificationStatus,
)

from .conftest import AS_OF, make_item, ts


def test_change_type_new():
    before = []
    after = [
        make_item(
            item_id="a",
            title="Brand new item",
        ),
    ]

    diff = detect_changes(
        company="TCS",
        as_of=AS_OF,
        before=before,
        after=after,
    )

    assert len(diff.changes) == 1
    change = diff.changes[0]

    assert change.change_type == ChangeType.NEW
    assert change.item_id == "a"
    assert change.previous_checksum is None
    assert change.current_checksum == after[0].checksum


def test_change_type_unchanged():
    item = make_item(item_id="a")

    diff = detect_changes(
        company="TCS",
        as_of=AS_OF,
        before=[item],
        after=[item],
    )

    assert len(diff.changes) == 1
    assert diff.changes[0].change_type == ChangeType.UNCHANGED
    assert (
        diff.changes[0].previous_checksum
        == diff.changes[0].current_checksum
    )


def test_change_type_updated():
    before = [
        make_item(
            item_id="a",
            description="original",
        ),
    ]
    after = [
        make_item(
            item_id="a",
            description="revised",
        ),
    ]

    diff = detect_changes(
        company="TCS",
        as_of=AS_OF,
        before=before,
        after=after,
    )

    assert len(diff.changes) == 1
    assert diff.changes[0].change_type == ChangeType.UPDATED


def test_change_type_resolved():
    before = [
        make_item(
            item_id="a",
            verification_status=VerificationStatus.REPORTED,
        ),
    ]
    after = [
        make_item(
            item_id="a",
            verification_status=VerificationStatus.RESOLVED,
        ),
    ]

    diff = detect_changes(
        company="TCS",
        as_of=AS_OF,
        before=before,
        after=after,
    )

    assert len(diff.changes) == 1
    assert diff.changes[0].change_type == ChangeType.RESOLVED
    assert "resolved" in diff.changes[0].description


def test_change_type_conflicting():
    before = [
        make_item(
            item_id="a",
            verification_status=VerificationStatus.REPORTED,
        ),
    ]
    after = [
        make_item(
            item_id="a",
            verification_status=VerificationStatus.CONTRADICTED,
        ),
    ]

    diff = detect_changes(
        company="TCS",
        as_of=AS_OF,
        before=before,
        after=after,
    )

    assert len(diff.changes) == 1
    assert diff.changes[0].change_type == ChangeType.CONFLICTING
    assert "contradicted" in diff.changes[0].description


def test_change_counts():
    before = [
        make_item(item_id="a"),
    ]
    after = [
        make_item(item_id="a"),
        make_item(item_id="b", title="new"),
    ]

    diff = detect_changes(
        company="TCS",
        as_of=AS_OF,
        before=before,
        after=after,
    )

    assert diff.counts == {
        "UNCHANGED": 1,
        "NEW": 1,
    }
    assert change_counts(diff.changes) == diff.counts


def test_snapshot_with_previous_snapshot_records_changes():
    previous = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=ts(2026, 7, 1),
        items=[
            make_item(
                item_id="a",
                available_at=ts(2026, 7, 1),
            ),
        ],
    )

    current = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=[
            make_item(
                item_id="a",
                available_at=ts(2026, 7, 1),
            ),
            make_item(
                item_id="b",
                available_at=ts(2026, 8, 1),
            ),
        ],
        previous_snapshot=previous,
    )

    assert len(current.changes) == 2

    by_id = {c.item_id: c for c in current.changes}

    assert by_id["a"].change_type == ChangeType.UNCHANGED
    assert by_id["b"].change_type == ChangeType.NEW


def test_snapshot_without_previous_records_no_changes():
    current = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=[make_item(item_id="a")],
    )

    assert current.changes == ()
