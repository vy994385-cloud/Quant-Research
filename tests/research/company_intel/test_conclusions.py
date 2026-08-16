from __future__ import annotations

from src.research.company_intel import (
    build_company_intelligence_snapshot,
    conclusion_gate,
    insufficient_evidence_message,
)
from src.research.company_intel.semantics import (
    SemanticCategory,
    VerificationStatus,
)

from .conftest import AS_OF, make_item


def test_conclusion_requires_two_confirmed_items():
    items = [
        make_item(
            item_id="a",
            verification_status="CONFIRMED",
            reliability_tier=1,
        ),
    ]

    gate = conclusion_gate(items)

    assert gate.supported is False
    assert gate.reason == (
        "Insufficient evidence for a firm conclusion."
    )


def test_conclusion_requires_distinct_sources():
    items = [
        make_item(
            item_id="a",
            verification_status="CONFIRMED",
            reliability_tier=1,
            source_name="only-source",
        ),
        make_item(
            item_id="b",
            verification_status="CONFIRMED",
            reliability_tier=1,
            source_name="only-source",
        ),
    ]

    gate = conclusion_gate(items)

    assert gate.supported is False
    assert gate.reason == insufficient_evidence_message()


def test_conclusion_supported_with_distinct_reliable_sources():
    items = [
        make_item(
            item_id="a",
            verification_status="CONFIRMED",
            reliability_tier=1,
            source_name="source-a",
        ),
        make_item(
            item_id="b",
            verification_status="CONFIRMED",
            reliability_tier=1,
            source_name="source-b",
        ),
    ]

    gate = conclusion_gate(items)

    assert gate.supported is True
    assert gate.reason == ""


def test_conclusion_ignores_low_reliability_confirmed_items():
    items = [
        make_item(
            item_id="a",
            verification_status="CONFIRMED",
            reliability_tier=4,
            source_name="source-a",
        ),
        make_item(
            item_id="b",
            verification_status="CONFIRMED",
            reliability_tier=4,
            source_name="source-b",
        ),
    ]

    gate = conclusion_gate(items)

    assert gate.supported is False


def test_snapshot_drops_unsupported_conclusion_with_message():
    items = [
        make_item(
            item_id="conclusion",
            semantic_category=SemanticCategory.CONCLUSION,
            verification_status="CONFIRMED",
            reliability_tier=1,
        ),
    ]

    snapshot = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=items,
    )

    assert snapshot.item_count == 0
    assert snapshot.insufficient_evidence_notes == (
        "Insufficient evidence for a firm conclusion.",
    )
    assert any(
        "conclusion" in note
        for note in snapshot.notes
    )


def test_snapshot_keeps_supported_conclusion():
    items = [
        make_item(
            item_id="conclusion",
            semantic_category=SemanticCategory.CONCLUSION,
            verification_status="CONFIRMED",
            reliability_tier=1,
        ),
        make_item(
            item_id="support-a",
            verification_status="CONFIRMED",
            reliability_tier=1,
            source_name="source-a",
        ),
        make_item(
            item_id="support-b",
            verification_status="CONFIRMED",
            reliability_tier=1,
            source_name="source-b",
        ),
    ]

    snapshot = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=items,
    )

    assert snapshot.item_count == 3
    assert snapshot.insufficient_evidence_notes == ()
    assert snapshot.semantic_summary["CONCLUSION"] == 1


def test_snapshot_conclusion_gate_uses_only_confirmed_pool():
    items = [
        make_item(
            item_id="conclusion",
            semantic_category=SemanticCategory.CONCLUSION,
            verification_status="CONFIRMED",
            reliability_tier=1,
        ),
        make_item(
            item_id="support-a",
            verification_status="CONFIRMED",
            reliability_tier=1,
            source_name="source-a",
        ),
        make_item(
            item_id="support-b",
            verification_status="REPORTED",
            reliability_tier=1,
            source_name="source-b",
        ),
    ]

    snapshot = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=items,
    )

    # support-b is only REPORTED: the conclusion gate fails.
    assert snapshot.item_count == 2
    assert snapshot.insufficient_evidence_notes == (
        "Insufficient evidence for a firm conclusion.",
    )


def test_verification_statuses_are_never_silently_upgraded():
    statuses = {
        "CONFIRMED",
        "REPORTED",
        "ALLEGED",
        "UNVERIFIED",
        "CONTRADICTED",
        "RESOLVED",
    }

    assert VerificationStatus.CONFIRMED.value in statuses
    assert VerificationStatus.ALLEGED.value in statuses
    assert VerificationStatus.REPORTED.value in statuses
