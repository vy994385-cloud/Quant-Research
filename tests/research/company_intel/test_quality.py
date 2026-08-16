from __future__ import annotations

from src.research.company_intel import (
    build_coverage_status,
    build_freshness,
    build_quality_status,
    build_research_status,
)
from src.research.company_intel.models import EvidenceConflict
from src.research.company_intel.semantics import (
    BusinessEventType,
    IntelKind,
)

from .conftest import AS_OF, make_item, ts


def test_freshness_empty_is_stale():
    status = build_freshness([], as_of=AS_OF)

    assert status.stale is True
    assert status.latest_published_at is None
    assert status.notes == ("No evidence was knowable at as_of.",)


def test_freshness_within_90_days_is_fresh():
    item = make_item(
        item_id="a",
        published_at=ts(2026, 8, 1),
        available_at=ts(2026, 8, 1),
    )

    status = build_freshness([item], as_of=AS_OF)

    assert status.stale is False
    assert status.days_since_latest_published == 9
    assert status.latest_published_at == ts(2026, 8, 1)


def test_freshness_older_than_90_days_is_stale():
    item = make_item(
        item_id="a",
        published_at=ts(2026, 4, 1),
        available_at=ts(2026, 4, 1),
    )

    status = build_freshness([item], as_of=AS_OF)

    assert status.stale is True
    assert any("90 days" in note for note in status.notes)


def test_freshness_uses_latest_available_when_published_missing():
    item = make_item(
        item_id="a",
        published_at=None,
        available_at=ts(2026, 8, 9),
    ).model_copy(update={"published_at": None})

    status = build_freshness([item], as_of=AS_OF)

    assert status.days_since_latest_available == 1
    assert status.days_since_latest_published is None


def test_freshness_deduplicates_timestamps():
    items = [
        make_item(
            item_id=item_id,
            published_at=ts(2026, 8, 1),
            available_at=ts(2026, 8, 1),
        )
        for item_id in ("a", "b", "c")
    ]

    status = build_freshness(items, as_of=AS_OF)

    assert status.days_since_latest_published == 9


def test_coverage_totals_and_counts():
    items = [
        make_item(
            item_id="a",
            kind=IntelKind.FINANCIAL_PERIOD,
            published_at=ts(2026, 7, 1),
            available_at=ts(2026, 7, 1),
        ),
        make_item(
            item_id="b",
            kind=IntelKind.BUSINESS_EVENT,
            published_at=ts(2026, 7, 2),
            available_at=ts(2026, 7, 2),
        ).model_copy(
            update={"event_type": BusinessEventType.BOARD_MEETING}
        ),
    ]

    coverage = build_coverage_status(items, symbol="TCS", as_of=AS_OF)

    assert coverage.item_count == 2
    assert coverage.by_kind == {"FINANCIAL_PERIOD": 1, "BUSINESS_EVENT": 1}
    assert coverage.by_category == {
        "FINANCIAL_DISCLOSURE": 1,
        "CORPORATE_ACTION": 1,
    }


def test_coverage_lists_missing_categories():
    item = make_item(
        item_id="a",
        kind=IntelKind.FINANCIAL_PERIOD,
        published_at=ts(2026, 7, 1),
        available_at=ts(2026, 7, 1),
    )

    coverage = build_coverage_status([item], symbol="TCS", as_of=AS_OF)

    assert "FINANCIAL_DISCLOSURE" not in coverage.missing_categories
    assert "BUSINESS_NEWS" in coverage.missing_categories
    assert "REGULATORY_LEGAL" in coverage.missing_categories
    assert any("No evidence available" in note for note in coverage.notes)


def test_coverage_ignores_other_companies_and_future_items():
    other = make_item(
        item_id="other",
        symbol="INFY",
        published_at=ts(2026, 7, 1),
        available_at=ts(2026, 7, 1),
    )
    future = make_item(
        item_id="future",
        published_at=ts(2026, 9, 1),
        available_at=ts(2026, 9, 1),
    )

    coverage = build_coverage_status(
        [other, future],
        symbol="TCS",
        as_of=AS_OF,
    )

    assert coverage.item_count == 0


def test_quality_counts_conflicts_and_provenance():
    item = make_item(
        item_id="a",
        published_at=ts(2026, 7, 1),
        available_at=ts(2026, 7, 1),
        source_name="src-a",
        provenance_id="prov-a",
    )

    quality = build_quality_status(
        [item],
        symbol="TCS",
        as_of=AS_OF,
        conflicts=[_conflict()],
        evidence_links=[],
        deduplicated_count=2,
        insufficient_evidence_notes=["Too thin to conclude."],
    )

    assert quality.conflict_count == 1
    assert quality.deduplicated_count == 2
    assert quality.source_id_count == 1
    assert quality.provenance_id_count == 1
    assert quality.insufficient_evidence_notes == ("Too thin to conclude.",)
    assert any("never" in note for note in quality.notes)


def test_quality_notes_dedup_only_when_deduped():
    item = make_item(
        item_id="a",
        published_at=ts(2026, 7, 1),
        available_at=ts(2026, 7, 1),
    )

    quality = build_quality_status(
        [item],
        symbol="TCS",
        as_of=AS_OF,
        conflicts=[],
        evidence_links=[],
        deduplicated_count=0,
        insufficient_evidence_notes=[],
    )

    assert any("Duplicate" in note for note in quality.notes) is False


def test_quality_counts_only_known_items_for_provenance():
    item = make_item(
        item_id="a",
        published_at=ts(2026, 7, 1),
        available_at=ts(2026, 7, 1),
        source_name="src-a",
        provenance_id="prov-a",
    )
    future = make_item(
        item_id="future",
        published_at=ts(2026, 9, 1),
        available_at=ts(2026, 9, 1),
        source_name="src-future",
        provenance_id="prov-future",
    )

    quality = build_quality_status(
        [item, future],
        symbol="TCS",
        as_of=AS_OF,
        conflicts=[],
        evidence_links=[],
        deduplicated_count=0,
        insufficient_evidence_notes=[],
    )

    assert quality.source_id_count == 1


def test_research_status_aggregates_all_three():
    item = make_item(
        item_id="a",
        kind=IntelKind.FINANCIAL_PERIOD,
        published_at=ts(2026, 8, 1),
        available_at=ts(2026, 8, 1),
    )

    status = build_research_status(
        company="TCS",
        as_of=AS_OF,
        items=[item],
        conflicts=[_conflict()],
    )

    assert status.company == "TCS"
    assert status.freshness.stale is False
    assert status.coverage.item_count == 1
    assert status.quality.conflict_count == 1


def _conflict() -> EvidenceConflict:
    return EvidenceConflict(
        conflict_id="conflict-1",
        symbol="TCS",
        topic="growth",
        description="Two disclosures disagree.",
        management_involved=False,
        first={
            "item_id": "a",
            "title": "First",
            "semantic_category": "FACT",
            "verification_status": "CONFIRMED",
            "stance": "SUPPORTIVE",
            "direction": "POSITIVE",
            "source_name": "src-a",
            "excerpt": "Growth is strong.",
        },
        second={
            "item_id": "b",
            "title": "Second",
            "semantic_category": "FACT",
            "verification_status": "CONFIRMED",
            "stance": "CONTRARY",
            "direction": "NEGATIVE",
            "source_name": "src-b",
            "excerpt": "Growth is weak.",
        },
        as_of=AS_OF,
    )
