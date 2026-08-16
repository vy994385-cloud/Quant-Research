from __future__ import annotations

import json

import pytest

from src.research.company_intel import (
    RecordedIntelSourceProvider,
    build_company_intelligence_snapshot,
    candidate_to_raw_record,
    deduplicate_candidates,
)
from src.research.company_intel.models import IntelCandidate
from src.research.company_intel.sources import (
    IntelExtractor,
    IntelSourceValidator,
)
from src.research.company_intel.semantics import (
    IntelCategory,
    IntelKind,
    SemanticCategory,
    VerificationStatus,
)

from .conftest import AS_OF, ts


def make_candidate(
    *,
    candidate_id: str,
    company: str = "TCS",
    title: str = "Candidate",
    body: str = "Body",
    available_at=AS_OF,
    published_at=None,
    source_name: str = "recorded_intel_sources",
    source_type: str = "NEWS",
    source_url: str = "https://example.invalid/article",
    reliability_tier: int = 2,
    kind=IntelKind.BUSINESS_EVENT,
    verification_status=VerificationStatus.REPORTED,
) -> IntelCandidate:
    return IntelCandidate(
        candidate_id=candidate_id,
        company=company,
        source_name=source_name,
        source_type=source_type,
        source_url=source_url,
        title=title,
        body=body,
        published_at=published_at or available_at,
        available_at=available_at,
        reliability_tier=reliability_tier,
        kind=kind,
        verification_status=verification_status,
    )


def test_recorded_provider_filters_by_company():
    provider = RecordedIntelSourceProvider(
        [
            make_candidate(candidate_id="a", company="TCS"),
            make_candidate(candidate_id="b", company="INFY"),
        ],
    )

    results = provider.fetch("TCS", since=None, as_of=AS_OF)

    assert [c.candidate_id for c in results] == ["a"]


def test_recorded_provider_filters_future_at_as_of():
    provider = RecordedIntelSourceProvider(
        [
            make_candidate(
                candidate_id="future",
                available_at=ts(2026, 9, 1),
            ),
            make_candidate(
                candidate_id="known",
                available_at=ts(2026, 7, 1),
            ),
        ],
    )

    results = provider.fetch("TCS", since=None, as_of=AS_OF)

    assert [c.candidate_id for c in results] == ["known"]


def test_recorded_provider_include_future_keeps_future():
    provider = RecordedIntelSourceProvider(
        [
            make_candidate(
                candidate_id="future",
                available_at=ts(2026, 9, 1),
            ),
        ],
        include_future=True,
    )

    results = provider.fetch("TCS", since=None, as_of=AS_OF)

    assert [c.candidate_id for c in results] == ["future"]


def test_recorded_provider_since_filters_older_candidates():
    provider = RecordedIntelSourceProvider(
        [
            make_candidate(
                candidate_id="older",
                available_at=ts(2026, 6, 1),
            ),
            make_candidate(
                candidate_id="newer",
                available_at=ts(2026, 8, 1),
            ),
        ],
    )

    results = provider.fetch(
        "TCS",
        since=ts(2026, 7, 1),
        as_of=AS_OF,
    )

    assert [c.candidate_id for c in results] == ["newer"]


def test_recorded_provider_naive_as_of_raises():
    provider = RecordedIntelSourceProvider([])

    with pytest.raises(ValueError):
        provider.fetch(
            "TCS",
            since=None,
            as_of=AS_OF.replace(tzinfo=None),
        )


def test_from_json_accepts_list_and_object(tmp_path):
    as_list = tmp_path / "list.json"
    as_object = tmp_path / "object.json"

    as_list.write_text(
        json.dumps(
            [
                make_candidate(
                    candidate_id="a",
                ).model_dump(mode="json")
            ]
        ),
        encoding="utf-8",
    )
    as_object.write_text(
        json.dumps(
            {
                "candidates": [
                    make_candidate(
                        candidate_id="b",
                    ).model_dump(mode="json")
                ]
            }
        ),
        encoding="utf-8",
    )

    from_list = RecordedIntelSourceProvider.from_json(as_list)
    from_object = RecordedIntelSourceProvider.from_json(as_object)

    assert from_list.fetch("TCS", since=None, as_of=AS_OF)[0].candidate_id == "a"
    assert from_object.fetch("TCS", since=None, as_of=AS_OF)[0].candidate_id == "b"


def test_from_json_rejects_invalid_shape(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"nope": 1}), encoding="utf-8")

    with pytest.raises(ValueError):
        RecordedIntelSourceProvider.from_json(bad)


def test_validator_rejects_company_mismatch():
    validator = IntelSourceValidator()

    valid, reason = validator.validate(
        make_candidate(candidate_id="a", company="INFY"),
        company="TCS",
        as_of=AS_OF,
    )

    assert valid is False
    assert "does not match" in reason


def test_validator_rejects_naive_as_of():
    validator = IntelSourceValidator()

    with pytest.raises(ValueError):
        validator.validate(
            make_candidate(candidate_id="a"),
            company="TCS",
            as_of=AS_OF.replace(tzinfo=None),
        )


def test_validator_rejects_naive_available_at():
    validator = IntelSourceValidator()

    candidate = make_candidate(candidate_id="a")
    candidate = candidate.model_copy(
        update={"available_at": ts(2026, 7, 1).replace(tzinfo=None)}
    )

    valid, reason = validator.validate(
        candidate,
        company="TCS",
        as_of=AS_OF,
    )

    assert valid is False
    assert "timezone-aware" in reason


def test_validator_rejects_future_available_at():
    validator = IntelSourceValidator()

    valid, reason = validator.validate(
        make_candidate(
            candidate_id="future",
            available_at=ts(2026, 9, 1),
        ),
        company="TCS",
        as_of=AS_OF,
    )

    assert valid is False
    assert "not knowable" in reason


def test_validator_accepts_known_candidate():
    validator = IntelSourceValidator()

    valid, reason = validator.validate(
        make_candidate(
            candidate_id="known",
            available_at=ts(2026, 7, 1),
        ),
        company="TCS",
        as_of=AS_OF,
    )

    assert valid is True
    assert reason == ""


def test_deduplicate_candidates_by_content_identity():
    first = make_candidate(
        candidate_id="a",
        title="Same story",
        source_url="https://example.invalid/story",
    )
    duplicate = make_candidate(
        candidate_id="b",
        title="  same story  ",
        source_url="https://example.invalid/story",
    )

    deduped, removed = deduplicate_candidates([first, duplicate])

    assert removed == 1
    assert len(deduped) == 1
    assert deduped[0].candidate_id == "a"


def test_deduplicate_keeps_distinct_sources():
    a = make_candidate(
        candidate_id="a",
        title="Same story",
        source_name="source-a",
        source_url="https://example.invalid/a",
    )
    b = make_candidate(
        candidate_id="b",
        title="Same story",
        source_name="source-b",
        source_url="https://example.invalid/b",
    )

    deduped, removed = deduplicate_candidates([a, b])

    assert removed == 0
    assert len(deduped) == 2


def test_candidate_to_raw_record_archives_candidate():
    candidate = make_candidate(candidate_id="candidate-1")

    record = candidate_to_raw_record(
        candidate,
        retrieved_at=AS_OF,
    )

    assert record.source_id == "recorded_intel_sources"
    assert record.record_id == "candidate-1"
    assert record.available_at == AS_OF
    assert record.payload["title"] == "Candidate"


def test_extractor_builds_point_in_time_item():
    extractor = IntelExtractor()

    item = extractor.extract(
        make_candidate(
            candidate_id="candidate-1",
            available_at=ts(2026, 7, 1),
            kind=IntelKind.MANAGEMENT_COMMENTARY,
            verification_status=VerificationStatus.REPORTED,
        ),
        company="TCS",
        as_of=AS_OF,
    )

    assert item is not None
    assert item.item_id == "TCS:candidate-1"
    assert item.symbol == "TCS"
    assert item.kind == IntelKind.MANAGEMENT_COMMENTARY
    assert (
        item.verification_status
        == VerificationStatus.REPORTED
    )
    assert item.is_known_at(AS_OF)
    assert (
        item.semantic_category
        == SemanticCategory.OBSERVATION
    )


def test_extractor_rejects_future_candidate():
    extractor = IntelExtractor()

    item = extractor.extract(
        make_candidate(
            candidate_id="future",
            available_at=ts(2026, 9, 1),
        ),
        company="TCS",
        as_of=AS_OF,
    )

    assert item is None


def test_validator_rejects_published_after_available():
    validator = IntelSourceValidator()

    candidate = make_candidate(candidate_id="a")
    candidate = candidate.model_copy(
        update={"published_at": ts(2026, 8, 11)}
    )

    valid, reason = validator.validate(
        candidate,
        company="TCS",
        as_of=AS_OF,
    )

    assert valid is False
    assert "publication order is broken" in reason


def test_validator_accepts_published_before_available():
    validator = IntelSourceValidator()

    candidate = make_candidate(candidate_id="a")
    candidate = candidate.model_copy(
        update={
            "published_at": ts(2026, 7, 1),
            "available_at": ts(2026, 7, 2),
        }
    )

    valid, reason = validator.validate(
        candidate,
        company="TCS",
        as_of=AS_OF,
    )

    assert valid is True


def test_extractor_carries_explicit_intel_category():
    extractor = IntelExtractor()

    candidate = make_candidate(
        candidate_id="category",
        available_at=ts(2026, 7, 1),
    ).model_copy(
        update={"intel_category": IntelCategory.REGULATORY_LEGAL}
    )

    item = extractor.extract(
        candidate,
        company="TCS",
        as_of=AS_OF,
    )

    assert item is not None
    assert item.intel_category == IntelCategory.REGULATORY_LEGAL


def test_extractor_leaves_category_defaulting_to_snapshot():
    extractor = IntelExtractor()

    item = extractor.extract(
        make_candidate(
            candidate_id="commentary",
            available_at=ts(2026, 7, 1),
            kind=IntelKind.MANAGEMENT_COMMENTARY,
        ),
        company="TCS",
        as_of=AS_OF,
    )

    assert item is not None
    assert item.intel_category is None

    snapshot = build_company_intelligence_snapshot(
        symbol="TCS",
        as_of=AS_OF,
        items=[item],
    )

    assert snapshot.timeline is not None
    assert (
        snapshot.timeline.entries[0].intel_category
        == IntelCategory.MANAGEMENT_STATEMENT
    )


def test_extractor_rejects_company_mismatch():
    extractor = IntelExtractor()

    item = extractor.extract(
        make_candidate(candidate_id="a", company="INFY"),
        company="TCS",
        as_of=AS_OF,
    )

    assert item is None
