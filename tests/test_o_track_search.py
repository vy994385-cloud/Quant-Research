"""
O-TRACK O8 — deterministic evidence search contract tests.

Pins:
- exact and partial lexical matching (AND semantics, no scores);
- claim text participates in the haystack;
- date-range, company, source, and category filters;
- PIT historical search keeps only provably-knowable items;
- empty-search behavior;
- full determinism of hits and ordering.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from src.research.evidence.models import (
    CanonicalEvidenceItem,
    EpistemicType,
    EvidenceClaim,
    EvidenceLineage,
)
from src.research.evidence.search import search_evidence

TZ = timezone.utc
AS_OF = datetime(2026, 8, 10, 12, tzinfo=TZ)


def _item(
    evidence_id: str,
    *,
    title: str = "Order book strengthens",
    explanation: str = "Large order win reported.",
    category: str = "BUSINESS_UPDATE",
    symbol: str = "TCS",
    published_at: datetime | None = None,
    available_at: datetime | None = None,
    observation_at: datetime | None = None,
    source_ids=("src-a",),
) -> CanonicalEvidenceItem:
    stamp = published_at or datetime(2026, 6, 1, tzinfo=TZ)
    return CanonicalEvidenceItem(
        evidence_id=evidence_id,
        symbol=symbol,
        title=title,
        explanation=explanation,
        evidence_type="BUSINESS_EVENT",
        direction="POSITIVE",
        confidence="0.8",
        reliability="HIGH",
        epistemic_type=EpistemicType.REPORTED,
        verification_status="REPORTED",
        observation_at=observation_at,
        published_at=published_at or stamp,
        available_at=(
            available_at if available_at is not None else stamp
        ),
        source_ids=tuple(source_ids),
        provenance_ids=(f"prov-{evidence_id}",),
        category=category,
    )


def _lineage(items=(), claims=()) -> EvidenceLineage:
    return EvidenceLineage(
        symbol="TCS",
        as_of=AS_OF,
        evidence=tuple(items),
        claims=tuple(claims),
    )


class TestLexicalMatching:
    def test_exact_title_match(self):
        result = search_evidence(
            _lineage([_item("ev-1", title="Board approves buyback")]),
            text="Board approves buyback",
        )

        assert result.hit_count == 1
        assert result.hits[0].evidence_id == "ev-1"

    def test_partial_term_match_is_substring_based(self):
        result = search_evidence(
            _lineage([_item("ev-1")]),
            text="orderbook",  # single token must appear verbatim
        )
        assert result.hit_count == 0

        result = search_evidence(
            _lineage([_item("ev-1")]),
            text="strengthens",
        )
        assert result.hit_count == 1

    def test_multiple_terms_require_all(self):
        items = [
            _item("ev-1"),
            _item(
                "ev-2",
                title="Order book weakens",
                explanation="Demand softened.",
            ),
        ]

        result = search_evidence(_lineage(items), text="order large")

        assert result.hit_count == 1
        assert result.hits[0].evidence_id == "ev-1"

    def test_claim_text_participates_in_search(self):
        claim = EvidenceClaim(
            claim_id="claim-9",
            symbol="TCS",
            text="Quantum computing research programme expanded",
            category="TECHNOLOGY",
            evidence_ids=("ev-tech",),
        )
        item = _item(
            "ev-tech",
            title="Technology update",
            explanation="Research summary.",
        )

        result = search_evidence(
            _lineage([item], [claim]),
            text="quantum",
        )

        assert result.hit_count == 1
        assert result.hits[0].matched_claim_ids == ("claim-9",)

    def test_case_insensitive(self):
        result = search_evidence(
            _lineage([_item("ev-1")]), text="ORDER Book"
        )

        assert result.hit_count == 1


class TestFilters:
    def test_company_filter_mismatch_yields_empty(self):
        result = search_evidence(
            _lineage([_item("ev-1")]),
            text="order",
            symbol="INFY",
        )

        assert result.hit_count == 0
        assert any(
            "No recorded evidence matched" in n for n in result.notes
        )

    def test_company_filter_match(self):
        result = search_evidence(
            _lineage([_item("ev-1"), _item("ev-2", symbol="INFY")]),
            text="order",
            symbol="infy",
        )

        assert [h.evidence_id for h in result.hits] == ["ev-2"]

    def test_date_range_filter(self):
        items = [
            _item(
                "old",
                title="Old order news",
                published_at=datetime(2025, 1, 10, tzinfo=TZ),
            ),
            _item(
                "new",
                title="New order news",
                published_at=datetime(2026, 7, 15, tzinfo=TZ),
            ),
        ]

        result = search_evidence(
            _lineage(items),
            text="order",
            published_from=date(2026, 1, 1),
            published_to=date(2026, 12, 31),
        )

        assert [h.evidence_id for h in result.hits] == ["new"]

    def test_undated_item_excluded_when_date_filter_present(self):
        item = CanonicalEvidenceItem(
            evidence_id="undated",
            symbol="TCS",
            title="Undated order note",
            explanation="No timestamps recorded.",
            evidence_type="BUSINESS_EVENT",
            direction="POSITIVE",
            confidence="0.5",
            reliability="MEDIUM",
            epistemic_type=EpistemicType.REPORTED,
            verification_status="UNVERIFIED",
            observation_at=None,
            published_at=None,
            available_at=None,
            source_ids=("src-a",),
            provenance_ids=("prov-undated",),
            category="BUSINESS_UPDATE",
        )

        result = search_evidence(
            _lineage([item]),
            text="order",
            published_from=date(2026, 1, 1),
        )

        assert result.hit_count == 0

    def test_source_and_category_filters(self):
        items = [
            _item("ev-1", source_ids=("exchange",)),
            _item(
                "ev-2",
                title="Other order item",
                source_ids=("newswire",),
                category="RISK",
            ),
        ]

        by_source = search_evidence(
            _lineage(items), text="order", source_id="exchange"
        )
        assert [h.evidence_id for h in by_source.hits] == ["ev-1"]

        by_category = search_evidence(
            _lineage(items), text="order", category="risk"
        )
        assert [h.evidence_id for h in by_category.hits] == ["ev-2"]


class TestPitSearch:
    def test_historical_cutoff_excludes_later_knowledge(self):
        def plain_item(evidence_id, *, title, available_at, observation_at=None, published_at=None):
            return CanonicalEvidenceItem(
                evidence_id=evidence_id,
                symbol="TCS",
                title=title,
                explanation="Order intake update.",
                evidence_type="BUSINESS_EVENT",
                direction="POSITIVE",
                confidence="0.7",
                reliability="HIGH",
                epistemic_type=EpistemicType.REPORTED,
                verification_status="REPORTED",
                observation_at=observation_at,
                published_at=published_at,
                available_at=available_at,
                source_ids=("src-a",),
                provenance_ids=(f"prov-{evidence_id}",),
                category="BUSINESS_UPDATE",
            )

        items = [
            plain_item(
                "knowable",
                title="Knowable order info",
                available_at=datetime(2026, 1, 5, tzinfo=TZ),
                published_at=datetime(2026, 1, 4, tzinfo=TZ),
            ),
            plain_item(
                "future",
                title="Future order info",
                available_at=datetime(2026, 12, 1, tzinfo=TZ),
                published_at=datetime(2026, 11, 30, tzinfo=TZ),
            ),
            plain_item(
                "unstampable",
                title="No availability order info",
                available_at=None,
                observation_at=datetime(2026, 2, 1, tzinfo=TZ),
            ),
        ]

        cutoff = datetime(2026, 6, 1, tzinfo=TZ)
        result = search_evidence(
            _lineage(items), text="order", as_of=cutoff
        )

        assert [h.evidence_id for h in result.hits] == ["knowable"]
        assert all(h.pit_eligible for h in result.hits)

    def test_naive_as_of_rejected(self):
        with pytest.raises(ValueError):
            search_evidence(
                _lineage(), as_of=datetime(2026, 6, 1)
            )


class TestEmptyAndDeterminism:
    def test_empty_query_returns_everything_deterministically(self):
        items = [
            _item("b-2"),
            _item("a-1", published_at=datetime(2026, 1, 1, tzinfo=TZ)),
            _item("c-3", published_at=datetime(2026, 6, 1, tzinfo=TZ)),
        ]

        result = search_evidence(_lineage(items))

        assert result.hit_count == 3
        assert [h.evidence_id for h in result.hits] == [
            "b-2",
            "c-3",
            "a-1",
        ]
        assert result.query.text_terms == ()

    def test_no_matches_notes(self):
        result = search_evidence(_lineage([_item("ev-1")]), text="zzz")

        assert result.hit_count == 0
        assert result.notes

    def test_search_is_deterministic(self):
        items = [_item(f"ev-{i}") for i in range(5)]

        first = search_evidence(_lineage(items), text="order")
        second = search_evidence(
            _lineage(tuple(reversed(items))), text="order"
        )

        assert first.model_dump(mode="json") == second.model_dump(
            mode="json"
        )


@pytest.fixture(scope="module")
def tcs_lineage(tmp_path_factory):
    from src.api.recorded_research import RecordedCompanyResearchService
    from src.research.evidence import build_evidence_lineage

    archive_root = tmp_path_factory.mktemp("o8-archive")
    service = RecordedCompanyResearchService(archive_root=archive_root)
    result = service.run("TCS", as_of=AS_OF)

    intel_items = (
        result.intelligence.items if result.intelligence else ()
    )
    return build_evidence_lineage(
        symbol=result.company,
        as_of=result.as_of,
        evidence_items=result.evidence_items,
        intel_items=intel_items,
        pit_filter=True,
    )


class TestRecordedLineageSearch:
    def test_recorded_lineage_searches_and_round_trips(
        self, tcs_lineage
    ):
        result = search_evidence(tcs_lineage)

        assert result.searched_count > 0
        assert result.hit_count == result.searched_count

        payload = result.model_dump(mode="json")
        revalidated = __import__(
            "src.research.evidence.search", fromlist=["x"]
        ).EvidenceSearchResult.model_validate(payload)
        assert revalidated.hit_count == result.hit_count

    def test_recorded_term_search_deterministic(self, tcs_lineage):
        first = search_evidence(tcs_lineage, text="the")
        second = search_evidence(tcs_lineage, text="THE")

        assert first.model_dump(mode="json") == second.model_dump(
            mode="json"
        )


class TestSearch20:
    """T1 expansion: phrases, tiers, snippets, observation windows."""

    def test_exact_phrase_filters_non_contiguous(self):
        result = search_evidence(
            _lineage(
                [
                    _item(
                        "ev-1",
                        title="Order strengthens book",
                    )
                ]
            ),
            text="order book",
        )
        # Terms match individually; the contiguous phrase must not.
        assert result.hit_count == 1

        phrase_result = search_evidence(
            _lineage(
                [
                    _item(
                        "ev-1",
                        title="Order strengthens book",
                    )
                ]
            ),
            text="order book",
            exact_phrase="order book",
        )
        assert phrase_result.hit_count == 0

    def test_exact_phrase_matches_contiguous(self):
        result = search_evidence(
            _lineage([_item("ev-1")]),
            text="",
            exact_phrase="Order book strengthens",
        )
        assert result.hit_count == 1
        assert result.query.exact_phrase == "Order book strengthens"

    def test_match_tier_title_when_all_terms_in_title(self):
        result = search_evidence(
            _lineage([_item("ev-1")]),
            text="order book",
        )
        assert result.hits[0].match_tier == "title"
        assert "title" in result.hits[0].matched_fields

    def test_match_tier_is_label_not_score(self):
        result = search_evidence(
            _lineage([_item("ev-1"), _item("ev-2", title="Other thing")]),
            text="order book",
        )
        for hit in result.hits:
            assert hit.match_tier in {"title", "text", "metadata"}
        _scan_forbidden(result.model_dump(mode="json"))

    def test_snippet_is_deterministic_excerpt(self):
        item = _item(
            "ev-1",
            explanation=(
                "Quarter after quarter the large order win pipeline "
                "keeps expanding across markets and verticals."
            ),
        )
        first = search_evidence(_lineage([item]), text="pipeline")
        second = search_evidence(_lineage([item]), text="pipeline")
        snippet = first.hits[0].snippet
        assert snippet is not None
        assert "pipeline" in snippet.lower()
        assert first.model_dump(mode="json") == second.model_dump(
            mode="json"
        )

    def test_observation_window_inclusive(self):
        inside = _item(
            "ev-in",
            observation_at=datetime(2026, 5, 5, tzinfo=TZ),
            published_at=datetime(2026, 5, 5, tzinfo=TZ),
        )
        outside = _item(
            "ev-out",
            observation_at=datetime(2024, 1, 1, tzinfo=TZ),
            published_at=datetime(2024, 1, 1, tzinfo=TZ),
        )
        from datetime import date as _date

        result = search_evidence(
            _lineage([inside, outside]),
            text="order",
            observation_from=_date(2026, 1, 1),
            observation_to=_date(2026, 12, 31),
        )
        ids = [hit.evidence_id for hit in result.hits]
        assert ids == ["ev-in"]

    def test_observation_window_excludes_unobserved(self):
        undated = _item("ev-x", observation_at=None)
        from datetime import date as _date

        result = search_evidence(
            _lineage([undated]),
            text="order",
            observation_from=_date(2020, 1, 1),
        )
        assert result.hit_count == 0


def _scan_forbidden(node, forbidden=None):
    if forbidden is None:
        forbidden = {"score", "ranking", "rank", "winner",
                     "recommendation", "rating"}
    if isinstance(node, dict):
        for key, value in node.items():
            assert key.lower() not in forbidden, key
            _scan_forbidden(value, forbidden)
    elif isinstance(node, list):
        for entry in node:
            _scan_forbidden(entry, forbidden)
