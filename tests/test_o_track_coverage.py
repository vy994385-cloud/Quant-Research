"""
O-TRACK O4 — consolidated coverage / PIT / source output tests.

Pins:
- canonical status mapping from recorded gap statuses;
- grouped reasons instead of repeated near-identical warnings;
- source summary rows (empty, stale, provenance completeness);
- PIT summary passthrough including historical cutoff and future
  exclusion accounting;
- deterministic ordering everywhere.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.analysis.research_gaps import ResearchGap, ResearchGapResult
from src.research.company_intel.models import SourceStatus
from src.research.coverage_summary import (
    CompanyCoverageSummary,
    CoverageStatus,
    PitSummary,
    build_coverage_summary,
)

TZ = timezone.utc
AS_OF = datetime(2026, 8, 10, tzinfo=TZ)


def _gap(
    gap_id: str,
    category: str,
    *,
    status: str = "UNAVAILABLE",
    reason: str = "No recorded data was found.",
    priority: str = "MEDIUM",
) -> ResearchGap:
    return ResearchGap(
        gap_id=gap_id,
        symbol="TCS",
        category=category,
        gap=f"{category} detail",
        status=status,
        reason=reason,
        what_would_resolve="Record the underlying data.",
        sources_checked=("filings",),
        related_metrics=("metric_a", "metric_b"),
        priority=priority,
    )


def _source(
    name: str,
    *,
    items: int = 3,
    stale: bool = False,
    days: int | None = 5,
    provenance: bool = True,
) -> SourceStatus:
    return SourceStatus(
        source_name=name,
        source_type="COMPANY_FILINGS",
        item_count=items,
        categories=("FINANCIAL_DISCLOSURE",),
        latest_published_at=datetime(2026, 8, 1, tzinfo=TZ),
        latest_available_at=datetime(2026, 8, 2, tzinfo=TZ),
        days_since_latest_published=days,
        stale=stale,
        provenance_completeness=provenance,
    )


class TestStatusMapping:
    def test_all_recorded_statuses_map_canonically(self):
        result = build_coverage_summary(
            ResearchGapResult(
                symbol="TCS",
                as_of="2026-08-10",
                gaps=(
                    _gap("g1", "financials", status="KNOWN"),
                    _gap("g2", "ownership", status="PARTIALLY_KNOWN"),
                    _gap("g3", "news", status="UNAVAILABLE"),
                    _gap("g4", "guidance", status="STALE"),
                    _gap("g5", "strategy", status="CONFLICTING"),
                    _gap("g6", "esg", status="INSUFFICIENT_EVIDENCE"),
                ),
            ),
            (),
            symbol="TCS",
            as_of=AS_OF,
        )

        by_area = {a.area: a.status for a in result.areas}

        assert by_area["financials"] == CoverageStatus.AVAILABLE
        assert by_area["ownership"] == CoverageStatus.LIMITED
        assert by_area["news"] == CoverageStatus.MISSING
        assert by_area["guidance"] == CoverageStatus.STALE
        assert by_area["strategy"] == CoverageStatus.CONFLICTING
        assert by_area["esg"] == CoverageStatus.INSUFFICIENT

    def test_unknown_status_defaults_to_missing(self):
        result = build_coverage_summary(
            ResearchGapResult(
                symbol="TCS",
                as_of="2026-08-10",
                gaps=(_gap("g1", "mystery", status="SOMETHING_ELSE"),),
            ),
            (),
            symbol="TCS",
            as_of=AS_OF,
        )

        assert result.areas[0].status == CoverageStatus.MISSING

    def test_every_area_carries_pit_implication(self):
        result = build_coverage_summary(
            ResearchGapResult(
                symbol="TCS",
                as_of="2026-08-10",
                gaps=(
                    _gap("g1", "a", status="KNOWN"),
                    _gap("g2", "b", status="UNAVAILABLE"),
                ),
            ),
            (),
            symbol="TCS",
            as_of=AS_OF,
        )

        for area in result.areas:
            assert area.pit_implication
            assert "as_of" in area.pit_implication


class TestReasonGrouping:
    def test_repeated_reasons_collapse_into_one_group(self):
        result = build_coverage_summary(
            ResearchGapResult(
                symbol="TCS",
                as_of="2026-08-10",
                gaps=(
                    _gap("g1", "area_one", reason="Not disclosed."),
                    _gap("g2", "area_two", reason="Not disclosed."),
                    _gap("g3", "area_three", reason="Not disclosed."),
                    _gap("g4", "area_four", reason="Different reason."),
                ),
            ),
            (),
            symbol="TCS",
            as_of=AS_OF,
        )

        matching = [
            g for g in result.grouped_reasons if g.reason == "Not disclosed."
        ]

        assert len(matching) == 1
        assert matching[0].occurrence_count == 3
        assert matching[0].areas == (
            "area_one",
            "area_three",
            "area_two",
        )

    def test_groups_sorted_by_frequency_then_severity(self):
        result = build_coverage_summary(
            ResearchGapResult(
                symbol="TCS",
                as_of="2026-08-10",
                gaps=(
                    _gap("g1", "a1", reason="r1"),
                    _gap("g2", "a2", reason="r1"),
                    _gap("g3", "a3", reason="r2", status="CONFLICTING"),
                ),
            ),
            (),
            symbol="TCS",
            as_of=AS_OF,
        )

        assert result.grouped_reasons[0].reason == "r1"
        assert result.grouped_reasons[1].reason == "r2"

    def test_notes_name_the_top_issue_once(self):
        result = build_coverage_summary(
            ResearchGapResult(
                symbol="TCS",
                as_of="2026-08-10",
                gaps=(
                    _gap("g1", "a1", reason="r1"),
                    _gap("g2", "a2", reason="r1"),
                ),
            ),
            (),
            symbol="TCS",
            as_of=AS_OF,
        )

        top_notes = [n for n in result.notes if n.startswith("Most frequent")]
        assert len(top_notes) == 1
        assert "(2 area(s))" in top_notes[0]


class TestSourceSummary:
    def test_empty_source_list_is_reported_honestly(self):
        result = build_coverage_summary(
            None,
            (),
            symbol="TCS",
            as_of=AS_OF,
        )

        assert result.sources == ()
        assert result.source_count == 0
        assert any("No research sources" in n for n in result.notes)

    def test_stale_source_flags_freshness_and_count(self):
        result = build_coverage_summary(
            None,
            (_source("old_feed", stale=True, days=200), _source("fresh_feed")),
            symbol="TCS",
            as_of=AS_OF,
        )

        assert result.stale_source_count == 1
        stale_row = next(s for s in result.sources if s.source == "old_feed")
        assert stale_row.stale is True
        assert stale_row.freshness_days == 200

    def test_provenance_completeness_is_preserved(self):
        result = build_coverage_summary(
            None,
            (_source("src_a", provenance=True),),
            symbol="TCS",
            as_of=AS_OF,
        )

        assert result.sources[0].provenance_completeness is True

    def test_duplicate_sources_deduplicated(self):
        result = build_coverage_summary(
            None,
            (_source("dup"), _source("dup")),
            symbol="TCS",
            as_of=AS_OF,
        )

        assert result.source_count == 1


class TestPitSummary:
    def test_pit_passthrough_with_future_exclusion(self):
        pit = PitSummary(
            requested_as_of="2026-08-10T00:00:00+00:00",
            effective_as_of="2026-08-10T00:00:00+00:00",
            market_as_of="2026-08-09",
            evidence_included=42,
            future_evidence_excluded=7,
            sources_discovered=9,
            sources_accepted=6,
            pit_checks_passed=True,
        )

        result = build_coverage_summary(
            None,
            (),
            symbol="TCS",
            as_of=AS_OF,
            pit=pit,
        )

        assert result.pit.future_evidence_excluded == 7
        assert result.pit.evidence_included == 42
        assert result.pit.pit_checks_passed is True

    def test_pit_historical_cutoff_semantics(self):
        pit = PitSummary(
            requested_as_of="2024-01-01T00:00:00+00:00",
            effective_as_of="2024-01-01T00:00:00+00:00",
            evidence_included=3,
            future_evidence_excluded=100,
            sources_discovered=20,
            sources_accepted=4,
            pit_checks_passed=True,
        )

        result = build_coverage_summary(
            None,
            (),
            symbol="TCS",
            as_of=datetime(2024, 1, 1, tzinfo=TZ),
            pit=pit,
        )

        assert result.pit.effective_as_of.startswith("2024-01-01")
        assert (
            result.pit.future_evidence_excluded
            > result.pit.evidence_included
        )


class TestDeterminism:
    def test_same_input_same_output(self):
        gaps = ResearchGapResult(
            symbol="TCS",
            as_of="2026-08-10",
            gaps=(
                _gap("g1", "b_area"),
                _gap("g2", "a_area", status="CONFLICTING"),
            ),
        )
        sources = (_source("z_src"), _source("a_src", stale=True))

        first = build_coverage_summary(gaps, sources, symbol="TCS", as_of=AS_OF)
        second = build_coverage_summary(
            gaps, tuple(reversed(sources)), symbol="TCS", as_of=AS_OF
        )

        assert first.model_dump(mode="json") == second.model_dump(mode="json")

    def test_naive_as_of_rejected(self):
        with pytest.raises(ValueError):
            build_coverage_summary(
                None, (), symbol="TCS", as_of=datetime(2026, 8, 10)
            )

    def test_model_round_trips_through_api_contract_shape(self):
        result = build_coverage_summary(
            ResearchGapResult(
                symbol="TCS",
                as_of="2026-08-10",
                gaps=(_gap("g1", "financials"),),
            ),
            (_source("filings"),),
            symbol="TCS",
            as_of=AS_OF,
        )

        payload = result.model_dump(mode="json")
        revalidated = CompanyCoverageSummary.model_validate(payload)

        assert revalidated.symbol == "TCS"
