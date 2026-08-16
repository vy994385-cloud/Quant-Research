from __future__ import annotations

from src.research.company_intel import (
    build_evidence_links,
    detect_evidence_conflicts,
)
from src.research.company_intel.semantics import (
    EvidenceRelationship,
    EvidenceStance,
    IntelKind,
)

from .conftest import AS_OF, make_item


def test_stance_conflict_is_detected():
    items = [
        make_item(
            item_id="management-demand",
            kind=IntelKind.MANAGEMENT_COMMENTARY,
            topic="demand_environment",
            stance=EvidenceStance.SUPPORTIVE,
            title="Management: demand remains strong",
        ),
        make_item(
            item_id="order-intake-decline",
            kind=IntelKind.BUSINESS_EVENT,
            topic="demand_environment",
            stance=EvidenceStance.CONTRARY,
            source_name="other-source",
            title="Order intake declines",
        ),
    ]

    conflicts = detect_evidence_conflicts(
        items,
        as_of=AS_OF,
    )

    assert len(conflicts) == 1

    conflict = conflicts[0]

    assert conflict.topic == "demand_environment"
    assert conflict.management_involved is True
    assert {
        conflict.first.item_id,
        conflict.second.item_id,
    } == {
        "management-demand",
        "order-intake-decline",
    }
    assert (
        conflict.first.verification_status.value
        == "REPORTED"
    )
    assert (
        conflict.second.verification_status.value
        == "REPORTED"
    )


def test_conflict_does_not_auto_conclude_management_wrong():
    items = [
        make_item(
            item_id="management-demand",
            kind=IntelKind.MANAGEMENT_COMMENTARY,
            topic="demand_environment",
            stance=EvidenceStance.SUPPORTIVE,
        ),
        make_item(
            item_id="order-intake-decline",
            topic="demand_environment",
            stance=EvidenceStance.CONTRARY,
            source_name="other-source",
        ),
    ]

    conflicts = detect_evidence_conflicts(
        items,
        as_of=AS_OF,
    )

    assert len(conflicts) == 1
    assert "no side is auto-concluded" in (
        conflicts[0].description
    )


def test_same_source_conflicting_stances_are_not_conflicted():
    items = [
        make_item(
            item_id="a",
            topic="t",
            stance=EvidenceStance.SUPPORTIVE,
            source_name="shared",
        ),
        make_item(
            item_id="b",
            topic="t",
            stance=EvidenceStance.CONTRARY,
            source_name="shared",
        ),
    ]

    conflicts = detect_evidence_conflicts(
        items,
        as_of=AS_OF,
    )

    assert conflicts == ()


def test_explicit_conflicts_with_produces_one_conflict():
    items = [
        make_item(
            item_id="a",
            topic="topic-a",
            stance=EvidenceStance.SUPPORTIVE,
            conflicts_with=("b",),
        ),
        make_item(
            item_id="b",
            topic="topic-a",
            stance=EvidenceStance.CONTRARY,
        ),
    ]

    conflicts = detect_evidence_conflicts(
        items,
        as_of=AS_OF,
    )

    assert len(conflicts) == 1
    assert conflicts[0].conflict_id.endswith(":a:b")


def test_future_item_never_enters_conflicts():
    items = [
        make_item(
            item_id="future",
            topic="t",
            stance=EvidenceStance.CONTRARY,
            source_name="other-source",
            available_at=AS_OF.replace(month=9),
        ),
        make_item(
            item_id="known",
            topic="t",
            stance=EvidenceStance.SUPPORTIVE,
        ),
    ]

    conflicts = detect_evidence_conflicts(
        items,
        as_of=AS_OF,
    )

    assert conflicts == ()


def test_build_evidence_links():
    items = [
        make_item(
            item_id="a",
            supports=("b",),
            conflicts_with=("c",),
        ),
        make_item(item_id="b"),
        make_item(item_id="c"),
        make_item(item_id="missing-target"),
    ]

    links = build_evidence_links(
        items,
        as_of=AS_OF,
    )

    relationships = {
        (link.subject_id, link.object_id, link.relationship)
        for link in links
    }

    assert (
        "a",
        "b",
        EvidenceRelationship.SUPPORTS,
    ) in relationships
    assert (
        "a",
        "c",
        EvidenceRelationship.CONTRADICTS,
    ) in relationships


def test_evidence_links_ignore_missing_targets():
    items = [
        make_item(
            item_id="a",
            supports=("not-present",),
        ),
    ]

    links = build_evidence_links(
        items,
        as_of=AS_OF,
    )

    assert links == ()
