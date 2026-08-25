"""
O-TRACK O9 — structured side-by-side comparison output tests.

Pins:
- same-period financial alignment across companies;
- different coverage: missing periods / metrics become null cells;
- derived-metric rows carry units and never invent values;
- deterministic row and cell ordering;
- no winner/loser/score/ranking fields anywhere in the payload.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest
from pydantic import BaseModel, ConfigDict

from src.analysis.research_gaps import ResearchGap, ResearchGapResult
from src.research.company_intel.models import (
    CorporateIntelItem,
    DeepFinancialInsights,
    FinancialIntelligence,
    FinancialPeriod,
    IntelKind,
    DeepMetricObservation,
    ReportingPeriodType,
    SourceRef,
    SourceStatus,
)
from src.research.comparison import (
    CompanyComparison,
    build_company_comparison,
)

TZ = timezone.utc
AS_OF = datetime(2026, 8, 10, 12, tzinfo=TZ)


def ts(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, 12, tzinfo=TZ)


class _StubResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    company: str
    sector: str | None = None
    intelligence: object = None
    evidence_items: tuple = ()
    as_of: datetime = AS_OF


def _period(symbol: str, period_id: str, end: date, **metrics) -> FinancialPeriod:
    return FinancialPeriod(
        period_id=period_id,
        symbol=symbol,
        period_end=end,
        period_type=ReportingPeriodType.ANNUAL,
        metrics={k: v for k, v in metrics.items()},
    )


def _observation(
    symbol: str,
    metric: str,
    value,
    *,
    period_id: str = "FY2026",
    end: date = date(2026, 3, 31),
) -> DeepMetricObservation:
    return DeepMetricObservation(
        observation_id=f"{symbol}-{metric}-{period_id}",
        symbol=symbol,
        metric=metric,
        period_id=period_id,
        period_end=end,
        period_type=ReportingPeriodType.ANNUAL,
        consolidation="CONSOLIDATED",
        observation_type="DERIVED",
        unit="FRACTION",
        value=value,
    )


def _intel_item(symbol: str, item_id: str, kind: IntelKind) -> CorporateIntelItem:
    return CorporateIntelItem(
        item_id=item_id,
        symbol=symbol,
        kind=kind,
        title="Recorded item",
        source=SourceRef(
            source_name="unit-test",
            source_type="FILING",
            reliability_tier=1,
        ),
        published_at=ts(2026, 7, 1),
        available_at=ts(2026, 7, 2),
    )


class _StubCoverage(BaseModel):
    item_count: int = 0
    missing_categories: tuple = ()


class _StubQuality(BaseModel):
    conflict_count: int = 0


class _StubStatus(BaseModel):
    coverage: _StubCoverage = _StubCoverage()
    quality: _StubQuality = _StubQuality()


class _StubIntel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    financial_intelligence: object = None
    deep_financial_insights: object = None
    items: tuple = ()
    source_statuses: tuple = ()
    research_gaps: object = None
    status: _StubStatus = _StubStatus()


def _fi(symbol: str, periods) -> FinancialIntelligence:
    return FinancialIntelligence(
        symbol=symbol,
        as_of=AS_OF,
        period_count=len(periods),
        quarterly_count=sum(
            1 for p in periods if p.period_type == ReportingPeriodType.QUARTERLY
        ),
        semiannual_count=0,
        annual_count=sum(
            1 for p in periods if p.period_type == ReportingPeriodType.ANNUAL
        ),
        unknown_period_count=sum(
            1 for p in periods if p.period_type == ReportingPeriodType.UNKNOWN
        ),
        consolidated_count=len(periods),
        standalone_count=0,
        unknown_consolidation_count=0,
        statement_count=0,
        segment_count=0,
        subsidiary_count=0,
        periods=tuple(periods),
    )


def _result_a() -> _StubResult:
    fi = _fi(
        "AAA",
        (
            _period("AAA", "FY2025", date(2025, 3, 31), revenue=100),
            _period(
                "AAA",
                "FY2026",
                date(2026, 3, 31),
                revenue=120,
                net_profit=20,
            ),
        ),
    )
    insights = DeepFinancialInsights(
        symbol="AAA",
        as_of=AS_OF,
        observations=(
            _observation("AAA", "operating_margin", "0.25"),
        ),
    )
    intel = _StubIntel(
        financial_intelligence=fi,
        deep_financial_insights=insights,
        items=(
            _intel_item("AAA", "i-1", IntelKind.BUSINESS_EVENT),
            _intel_item("AAA", "i-2", IntelKind.BUSINESS_EVENT),
        ),
        source_statuses=(
            SourceStatus(source_name="filings", source_type="FILING", item_count=1),
            SourceStatus(source_name="news", source_type="NEWS", item_count=1, stale=True),
        ),
        research_gaps=ResearchGapResult(
            symbol="AAA",
            as_of=AS_OF,
            gaps=(
                ResearchGap(
                    gap_id="g-1",
                    symbol="AAA",
                    category="TECHNOLOGY",
                    gap="Limited technology evidence.",
                    status="PARTIALLY_KNOWN",
                ),
            ),
        ),
    )
    return _StubResult(company="AAA", sector="IT", intelligence=intel)


def _result_b() -> _StubResult:
    # Fewer periods, fewer metrics: exercises null-cell alignment.
    fi = _fi(
        "BBB",
        (
            _period(
                "BBB",
                "FY2026",
                date(2026, 3, 31),
                revenue=200,
            ),
        ),
    )
    insights = DeepFinancialInsights(
        symbol="BBB",
        as_of=AS_OF,
        observations=(),
    )
    intel = _StubIntel(
        financial_intelligence=fi,
        deep_financial_insights=insights,
        items=(),
        source_statuses=(SourceStatus(source_name="filings", source_type="FILING", item_count=1),),
        research_gaps=ResearchGapResult(
            symbol="BBB",
            as_of=AS_OF,
            gaps=(),
        ),
    )
    return _StubResult(
        company="BBB", sector="PHARMA", intelligence=intel
    )


@pytest.fixture()
def comparison() -> CompanyComparison:
    return build_company_comparison(
        [_result_a(), _result_b()], as_of=AS_OF
    )


class TestAlignmentAndNulls:
    def test_shared_period_aligned(self, comparison):
        row = next(
            r for r in comparison.rows if r.metric == "revenue@2026-03-31"
        )
        values = {c.symbol: c.value for c in row.cells}

        assert values == {"AAA": "120", "BBB": "200"}
        assert all(c.available for c in row.cells)
        assert all(c.unit == "INR" for c in row.cells)

    def test_missing_period_yields_null_cells(self, comparison):
        row = next(
            r for r in comparison.rows if r.metric == "revenue@2025-03-31"
        )
        by_symbol = {c.symbol: c for c in row.cells}

        assert by_symbol["AAA"].available is True
        assert by_symbol["BBB"].available is False
        assert by_symbol["BBB"].value is None
        assert by_symbol["BBB"].unit is None

    def test_missing_metric_within_period_null(self, comparison):
        row = next(
            r
            for r in comparison.rows
            if r.metric == "net_profit@2026-03-31"
        )
        by_symbol = {c.symbol: c for c in row.cells}

        assert by_symbol["AAA"].value == "20"
        assert by_symbol["BBB"].available is False

    def test_derived_row_carries_unit(self, comparison):
        row = next(
            r for r in comparison.rows if r.metric == "operating_margin"
        )
        by_symbol = {c.symbol: c for c in row.cells}

        assert by_symbol["AAA"].value == "0.25"
        assert by_symbol["AAA"].unit == "FRACTION"
        assert by_symbol["BBB"].available is False

    def test_profile_and_counts(self, comparison):
        sector = next(r for r in comparison.rows if r.metric == "sector")
        by_symbol = {c.symbol: c.value for c in sector.cells}
        assert by_symbol == {"AAA": "IT", "BBB": "PHARMA"}

        events = next(
            r for r in comparison.rows if r.metric == "business_events"
        )
        counts = {c.symbol: c.value for c in events.cells}
        assert counts == {"AAA": "2", "BBB": "0"}

        gaps = next(
            r
            for r in comparison.rows
            if r.metric == "research_gaps_partially_known"
        )
        counts = {c.symbol: c.value for c in gaps.cells}
        assert counts == {"AAA": "1", "BBB": "0"}


class TestDeterminismAndSafety:
    def test_rows_and_cells_deterministically_ordered(self, comparison):
        symbols_order = [c.symbol for c in comparison.companies]
        assert symbols_order == ["AAA", "BBB"]

        for row in comparison.rows:
            assert [c.symbol for c in row.cells] == symbols_order

        categories = [r.category for r in comparison.rows]
        order = [
            "PROFILE",
            "FINANCIALS",
            "DERIVED",
            "EVENTS",
            "EVIDENCE",
            "COVERAGE",
            "SOURCES",
        ]
        first_index = [order.index(c) for c in categories]
        assert first_index == sorted(first_index)

    def test_no_scores_or_winners_in_payload(self, comparison):
        payload = json.dumps(comparison.model_dump(mode="json"))

        for banned in ("winner", "loser", "score", "rank", "better"):
            assert banned not in payload.lower()

    def test_requires_two_distinct_companies(self):
        with pytest.raises(ValueError):
            build_company_comparison(
                [_result_a(), _result_a()], as_of=AS_OF
            )

    def test_naive_as_of_rejected(self):
        with pytest.raises(ValueError):
            build_company_comparison(
                [_result_a(), _result_b()],
                as_of=datetime(2026, 8, 10),
            )

    def test_round_trip_json(self, comparison):
        payload = comparison.model_dump(mode="json")
        revalidated = CompanyComparison.model_validate(payload)
        assert revalidated.row_count == comparison.row_count


@pytest.fixture(scope="module")
def recorded_pair(tmp_path_factory):
    from src.api.recorded_research import RecordedCompanyResearchService

    archive_root = tmp_path_factory.mktemp("o9-archive")
    service = RecordedCompanyResearchService(archive_root=archive_root)

    results = [
        service.run(symbol, as_of=AS_OF)
        for symbol in ("TCS", "INFY")
    ]
    return results


class TestRecordedPairComparison:
    def test_recorded_companies_compare(self, recorded_pair):
        comparison = build_company_comparison(
            recorded_pair, as_of=AS_OF
        )

        assert [c.symbol for c in comparison.companies] == [
            "INFY",
            "TCS",
        ]
        assert comparison.row_count > 10

        financials = [
            r for r in comparison.rows if r.category == "FINANCIALS"
        ]
        assert financials, "expected aligned financial rows"

    def test_recorded_comparison_deterministic(self, recorded_pair):
        first = build_company_comparison(recorded_pair, as_of=AS_OF)
        second = build_company_comparison(
            list(reversed(recorded_pair)), as_of=AS_OF
        )

        assert first.model_dump(mode="json") == second.model_dump(
            mode="json"
        )


class TestCompare20Expansion:
    """T1 expansion: coverage/conflict/freshness rows + PIT note."""

    def _coverage_rows(self, comparison):
        return {
            row.metric: row
            for row in comparison.rows
            if row.metric
            in {
                "coverage_items",
                "missing_categories",
                "conflicts_recorded",
                "newest_intel_published_at",
            }
        }

    def test_new_coverage_and_conflict_rows_present(self):
        intel = _StubIntel(
            status=_StubStatus(
                coverage=_StubCoverage(
                    item_count=7, missing_categories=("OWNERSHIP",)
                ),
                quality=_StubQuality(conflict_count=2),
            )
        )
        result_a = _StubResult(company="AAA", sector="IT", intelligence=intel)
        result_b = _StubResult(company="BBB", sector="IT", intelligence=intel)
        comparison = build_company_comparison(
            [result_a, result_b], as_of=AS_OF
        )
        rows = self._coverage_rows(comparison)

        assert set(rows) == {
            "coverage_items",
            "missing_categories",
            "conflicts_recorded",
            "newest_intel_published_at",
        }
        for cell in rows["coverage_items"].cells:
            assert cell.value == "7"
        for cell in rows["conflicts_recorded"].cells:
            assert cell.value == "2"

    def test_freshness_cell_null_when_no_dated_intel(self):
        intel = _StubIntel()  # no items -> no published stamps
        result_a = _StubResult(company="AAA", sector="IT", intelligence=intel)
        result_b = _StubResult(company="BBB", sector="IT", intelligence=intel)
        comparison = build_company_comparison(
            [result_a, result_b], as_of=AS_OF
        )
        row = next(
            r
            for r in comparison.rows
            if r.metric == "newest_intel_published_at"
        )
        for cell in row.cells:
            assert cell.available is False
            assert cell.value is None

    def test_pit_consistency_note(self):
        intel = _StubIntel()
        aligned = build_company_comparison(
            [
                _StubResult(company="AAA", sector="IT", intelligence=intel),
                _StubResult(company="BBB", sector="IT", intelligence=intel),
            ],
            as_of=AS_OF,
        )
        assert any("same point" in n for n in aligned.notes)

        drifted_as_of = AS_OF.replace(hour=8)
        mixed = build_company_comparison(
            [
                _StubResult(company="AAA", sector="IT", intelligence=intel),
                _StubResult(
                    company="BBB",
                    sector="IT",
                    intelligence=intel,
                    as_of=drifted_as_of,
                ),
            ],
            as_of=AS_OF,
        )
        assert any("Point-in-time notice" in n for n in mixed.notes)
        assert any("BBB" in n for n in mixed.notes if "Point-in-time" in n)
