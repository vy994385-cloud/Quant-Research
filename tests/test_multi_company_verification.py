from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from src.research.acquisition.evidence import (
    research_observations_to_evidence,
)
from src.research.acquisition.models import (
    ResearchCategory,
    ResearchObservation,
    ResearchQuestion,
    SourceCandidate,
)
from src.research.acquisition.validator import SourceValidator
from src.research.company_engine import run_company_research
from src.research.raw_archive import RawArchive
from src.research.synthesis.evidence import synthesize_evidence
from src.research.synthesis.models import (
    EvidenceDirection,
    EvidenceItem,
    EvidenceReliability,
    EvidenceType,
)
from src.verification.real_data import (
    COMPANIES,
    DEFAULT_AS_OF,
    DEFAULT_COMPANY,
    FailedSourcesProvider,
    MissingSourcesProvider,
    PartialSourcesProvider,
    RecordedFinancialProvider,
    RecordedMarketDataProvider,
    RecordedResearchSourceProvider,
    StaleSourcesProvider,
    run_multi_company_verification,
    run_source_scenario,
)

AS_OF = DEFAULT_AS_OF

FIXTURE_DIR = (
    Path(__file__).resolve().parents[1] / "fixtures" / "real_data"
)

NEW_COMPANIES = (
    "RELIANCE",
    "INFY",
    "HDFCBANK",
    "SUNPHARMA",
    "M&M",
)

DISTINCT_SECTORS = {
    "information technology",
    "energy / conglomerate",
    "banking / financials",
    "pharmaceuticals / healthcare",
    "automobiles",
}


@pytest.fixture(scope="module")
def multi_result(tmp_path_factory):
    archive_root = tmp_path_factory.mktemp("multi-company-archive")

    return run_multi_company_verification(
        archive_root=archive_root,
    )


def _material_events_question() -> ResearchQuestion:
    return ResearchQuestion(
        question_id="material-events",
        category=ResearchCategory.MATERIAL_EVENTS,
        question=(
            "What recent material events could reasonably "
            "affect the company's business, financial "
            "position, or future outlook?"
        ),
        priority=1,
    )


def _conflicting_source(
    source_id: str,
    title: str,
) -> SourceCandidate:
    available_at = AS_OF - timedelta(days=5)

    return SourceCandidate(
        source_id=source_id,
        source_name="Conflicting Source",
        source_type="NEWS",
        url=f"https://example.invalid/{source_id}",
        title=title,
        published_at=available_at,
        available_at=available_at,
        reliability_tier=2,
    )


class FailingFinancialProvider:
    """
    A recorded financial provider that always fails.

    Used to verify graceful degradation of the optional financial
    data source.
    """

    def get_annual_financials(
        self,
        symbol: str,
        start_date,
        end_date,
    ):
        raise RuntimeError(
            f"financial provider failed for {symbol}"
        )


# ---------------------------------------------------------------------
# Multi-company recorded providers
# ---------------------------------------------------------------------


@pytest.mark.parametrize("company", [*NEW_COMPANIES])
def test_recorded_market_provider_serves_real_bars(company):
    prefix = company.lower()
    provider = RecordedMarketDataProvider(
        FIXTURE_DIR / f"{prefix}_market.csv"
    )

    bars = provider.get_daily_prices(
        company,
        AS_OF.date() - timedelta(days=365),
        AS_OF.date(),
    )

    assert bars
    assert all(bar.symbol == company for bar in bars)
    assert all(bar.trading_date <= AS_OF.date() for bar in bars)
    assert all(bar.close > 0 for bar in bars)

    benchmark = provider.get_daily_prices(
        "^NSEI",
        AS_OF.date() - timedelta(days=365),
        AS_OF.date(),
    )

    assert benchmark
    assert all(bar.symbol == "^NSEI" for bar in benchmark)


@pytest.mark.parametrize("company", [*NEW_COMPANIES])
def test_recorded_financial_provider_serves_real_snapshots(company):
    prefix = company.lower()
    provider = RecordedFinancialProvider(
        FIXTURE_DIR / f"{prefix}_financials.json"
    )

    snapshots = provider.get_annual_financials(
        company,
        AS_OF.date() - timedelta(days=3650),
        AS_OF.date(),
    )

    assert len(snapshots) >= 4
    assert all(
        snapshot.symbol == company
        for snapshot in snapshots
    )
    assert all(
        snapshot.period_end <= AS_OF.date()
        for snapshot in snapshots
    )
    assert all(
        snapshot.revenue is not None
        for snapshot in snapshots
    )


@pytest.mark.parametrize("company", [*NEW_COMPANIES])
def test_recorded_source_provider_serves_dated_disclosures(company):
    prefix = company.lower()
    provider = RecordedResearchSourceProvider(
        FIXTURE_DIR / f"{prefix}_sources.json"
    )

    candidates = provider.search(
        company,
        _material_events_question(),
        AS_OF,
    )

    assert candidates
    assert all(
        candidate.available_at is not None
        and candidate.available_at <= AS_OF
        for candidate in candidates
    )


# ---------------------------------------------------------------------
# End-to-end multi-company research through the real report pipeline
# ---------------------------------------------------------------------


def test_multi_company_covers_several_distinct_sectors(multi_result):
    sectors = set(multi_result.sectors)

    assert len(sectors) >= 5
    assert DISTINCT_SECTORS.issubset(sectors)

    companies = set(multi_result.companies)
    assert DEFAULT_COMPANY in companies
    assert companies == set(COMPANIES)


def test_full_real_data_path_produces_pit_safe_report_for_every_company(
    multi_result,
):
    for result in multi_result.results:
        assert result.report.symbol == result.company
        assert result.report.as_of == AS_OF
        assert result.report.evidence_narrative is not None

        assert len(result.market_ingestion.accepted) >= 200
        assert result.market_ingestion.rejected == []
        assert result.financial_record_count >= 4
        assert result.acquisition.sources_accepted >= 4
        assert result.acquisition.observations_created >= 4

        synthesis = result.report.evidence_synthesis
        assert synthesis is not None
        assert any(
            item.evidence_type == EvidenceType.ACQUIRED
            for item in synthesis.evidence
        )
        assert any(
            item.evidence_type == EvidenceType.FEATURE
            for item in synthesis.evidence
        )


def test_all_point_in_time_checks_pass_for_every_company(multi_result):
    assert multi_result.all_pit_checks_pass

    for company, checks in multi_result.pit_checks.items():
        assert checks["market_bars_all_known_at_as_of"] is True
        assert (
            checks["market_records_available_on_or_before_as_of"]
            is True
        )
        assert (
            checks["financial_period_ends_on_or_before_as_of"]
            is True
        )
        assert checks["accepted_sources_known_at_as_of"] is True
        assert checks["future_source_rejected"] is True
        assert checks["all_evidence_known_at_as_of"] is True
        assert (
            checks[
                "every_acquired_evidence_resolves_to_archived_source"
            ]
            is True
        )


def test_no_future_evidence_in_any_company_report(multi_result):
    for result in multi_result.results:
        synthesis = result.report.evidence_synthesis

        assert all(
            item.observation_at <= AS_OF
            for item in result.evidence_items
        )

        assert all(
            item.observation_at <= AS_OF
            for item in synthesis.evidence
        )

        for signal in result.report.signals:
            assert signal.observation_at <= AS_OF


def test_provenance_survives_through_final_output_for_every_company(
    multi_result,
):
    for result in multi_result.results:
        archive = RawArchive(result.archive_root)

        acquired = [
            item
            for item in result.evidence_items
            if item.evidence_type == EvidenceType.ACQUIRED
        ]

        assert acquired

        source_archive_id = (
            f"{result.company.lower()}_recorded_sources"
        )

        for item in acquired:
            assert len(item.source_ids) == 1
            source_id = item.source_ids[0]
            assert source_id in result.archived_source_ids

            record = archive.load(
                source_archive_id,
                source_id,
            )

            assert record.available_at is not None
            assert record.available_at <= AS_OF
            assert record.payload["source_id"] == source_id
            assert record.checksum

        synthesis = result.report.evidence_synthesis
        report_provenance = {
            source_id
            for item in synthesis.evidence
            for source_id in item.provenance_ids
        }

        assert result.market_provenance.record_id in report_provenance
        assert (
            result.financial_provenance.record_id
            in report_provenance
        )


def test_market_provenance_is_archived_for_every_company(multi_result):
    for result in multi_result.results:
        archive = RawArchive(result.archive_root)

        last_date = result.market_ingestion.accepted[-1].trading_date

        record = archive.load(
            "yahoo_finance_chart_recorded",
            f"{result.company}_{last_date}",
        )

        assert record.payload["symbol"] == result.company
        assert record.payload["trading_date"] == last_date.isoformat()
        assert record.available_at is not None
        assert record.available_at <= AS_OF


def test_multi_company_artifacts_are_reproducible(tmp_path):
    first = run_multi_company_verification(
        archive_root=tmp_path / "first",
    )
    second = run_multi_company_verification(
        archive_root=tmp_path / "second",
    )

    assert first.all_pit_checks_pass is True
    assert second.all_pit_checks_pass is True

    for first_result, second_result in zip(
        first.results,
        second.results,
    ):
        assert (
            first_result.to_artifact()
            == second_result.to_artifact()
        )


# ---------------------------------------------------------------------
# Source availability failure modes
# ---------------------------------------------------------------------


def test_missing_sources_still_produce_report(tmp_path):
    result = run_source_scenario(
        company="INFY",
        source_provider=MissingSourcesProvider(),
        archive_root=tmp_path / "archive",
    )

    assert result.acquisition.sources_discovered == 0
    assert result.acquisition.sources_accepted == 0
    assert result.acquisition.observations_created == 0
    assert result.acquisition.provider_failures == ()

    # The report is still produced from market + financial evidence.
    assert result.report.symbol == "INFY"
    assert result.report.as_of == AS_OF
    assert result.report.evidence_synthesis is not None
    assert result.report.evidence_narrative is not None

    synthesis = result.report.evidence_synthesis
    assert not any(
        item.evidence_type == EvidenceType.ACQUIRED
        for item in synthesis.evidence
    )
    assert any(
        item.evidence_type == EvidenceType.FEATURE
        for item in synthesis.evidence
    )

    assert all(result.pit_checks.values())


def test_stale_sources_remain_point_in_time_valid(tmp_path):
    result = run_source_scenario(
        company="RELIANCE",
        source_provider=StaleSourcesProvider(
            FIXTURE_DIR / "reliance_sources.json"
        ),
        archive_root=tmp_path / "archive",
    )

    # The stale-but-known disclosures are accepted.
    assert result.acquisition.sources_accepted >= 4
    assert all(
        source.available_at is not None
        and source.available_at <= AS_OF
        for source in result.acquisition.sources
    )

    # The evidence observation timestamp reflects the stale disclosure
    # date rather than a naive "now".
    assert result.evidence_items
    assert all(
        item.observation_at <= AS_OF
        for item in result.evidence_items
    )
    assert any(
        item.observation_at < AS_OF - timedelta(days=300)
        for item in result.evidence_items
    )

    # The future-dated candidate was rejected.
    assert not any(
        source.source_id.startswith("future-")
        for source in result.acquisition.sources
    )
    assert result.pit_checks["future_source_rejected"] is True

    assert result.report.symbol == "RELIANCE"
    assert all(result.pit_checks.values())


def test_failed_source_provider_degrades_gracefully(tmp_path):
    result = run_source_scenario(
        company="HDFCBANK",
        source_provider=FailedSourcesProvider(),
        archive_root=tmp_path / "archive",
    )

    # The failed optional provider is isolated and recorded.
    assert result.acquisition.provider_failed is True
    assert result.acquisition.provider_failures
    assert all(
        "failed-sources-provider" in failure
        for failure in result.acquisition.provider_failures
    )
    assert result.acquisition.sources_accepted == 0
    assert result.acquisition.observations_created == 0

    # The report is not corrupted.
    assert result.report.symbol == "HDFCBANK"
    assert result.report.as_of == AS_OF
    assert result.report.evidence_narrative is not None
    assert all(result.pit_checks.values())

    # Unrelated (market/financial) evidence remains trusted.
    synthesis = result.report.evidence_synthesis
    assert synthesis is not None
    assert not any(
        item.evidence_type == EvidenceType.ACQUIRED
        for item in synthesis.evidence
    )
    assert any(
        item.evidence_type == EvidenceType.FEATURE
        for item in synthesis.evidence
    )
    assert all(
        item.observation_at <= AS_OF
        for item in synthesis.evidence
    )


def test_failed_financial_provider_degrades_gracefully(tmp_path):
    result = run_source_scenario(
        company="SUNPHARMA",
        source_provider=MissingSourcesProvider(),
        financial_provider=FailingFinancialProvider(),
        archive_root=tmp_path / "archive",
    )

    assert result.financial_record_count == 0
    assert result.report.symbol == "SUNPHARMA"
    assert result.report.evidence_synthesis is not None
    assert result.report.evidence_narrative is not None
    assert result.market_ingestion.accepted
    assert all(result.pit_checks.values())


def test_conflicting_sources_are_retained_not_discarded(tmp_path):
    sources = [
        _conflicting_source(
            "mm-conflict-strong",
            "M&M quarterly revenue rose sharply and profit growth "
            "accelerated in results",
        ),
        _conflicting_source(
            "mm-conflict-weak",
            "M&M quarterly revenue fell sharply and profit declined "
            "in results",
        ),
    ]

    result = run_source_scenario(
        company="M&M",
        source_provider=RecordedResearchSourceProvider(
            FIXTURE_DIR / "m&m_sources.json"
        ),
        archive_root=tmp_path / "archive",
    )

    # A full recorded company still works end to end with conflict
    # present in the broader evidence base.
    assert result.acquisition.sources_accepted >= 4
    assert result.report.evidence_synthesis is not None
    assert all(result.pit_checks.values())

    # The conflicting candidates both survive the validator.
    validator = SourceValidator()

    assert validator.validate(sources[0], AS_OF) is True
    assert validator.validate(sources[1], AS_OF) is True


def test_conflicting_directional_evidence_is_flagged(tmp_path):
    positive = EvidenceItem(
        evidence_id="POSITIVE-FEATURE",
        symbol="M&M",
        evidence_type=EvidenceType.FEATURE,
        title="Positive feature evidence",
        explanation="Validated positive feature.",
        direction=EvidenceDirection.POSITIVE,
        confidence=Decimal("0.80"),
        reliability=EvidenceReliability.PRIMARY,
        observation_at=AS_OF - timedelta(days=1),
    )

    negative = EvidenceItem(
        evidence_id="NEGATIVE-SIGNAL",
        symbol="M&M",
        evidence_type=EvidenceType.SIGNAL,
        title="Negative signal evidence",
        explanation="Validated negative signal.",
        direction=EvidenceDirection.NEGATIVE,
        confidence=Decimal("0.80"),
        reliability=EvidenceReliability.PRIMARY,
        observation_at=AS_OF - timedelta(days=1),
    )

    synthesis = synthesize_evidence(
        symbol="M&M",
        as_of=AS_OF,
        evidence=[positive, negative],
    )

    assert synthesis.conflict_detected is True
    assert synthesis.direction == EvidenceDirection.MIXED
    assert len(synthesis.evidence) == 2
    assert positive in synthesis.evidence
    assert negative in synthesis.evidence


def test_partial_source_coverage_is_safe(tmp_path):
    result = run_source_scenario(
        company="INFY",
        source_provider=PartialSourcesProvider(
            FIXTURE_DIR / "infy_sources.json"
        ),
        archive_root=tmp_path / "archive",
    )

    # Only the subset of valid sources became evidence.
    assert result.acquisition.sources_accepted >= 3
    assert result.acquisition.sources_discovered > (
        result.acquisition.sources_accepted
    )
    assert result.acquisition.observations_created >= 3

    # Future and naive candidates were rejected before evidence.
    assert not any(
        "future-" in item.evidence_id
        for item in result.evidence_items
    )
    assert not any(
        "naive-" in item.evidence_id
        for item in result.evidence_items
    )
    assert all(
        item.observation_at <= AS_OF
        for item in result.evidence_items
    )

    assert result.report.symbol == "INFY"
    assert result.report.evidence_narrative is not None
    assert all(result.pit_checks.values())


# ---------------------------------------------------------------------
# Point-in-time integrity regression guards
# ---------------------------------------------------------------------


def _observation(
    *,
    company: str,
    available_at: datetime | None,
    source_id: str = "test-source",
) -> ResearchObservation:
    return ResearchObservation(
        observation_id=f"{company}:material-events:{source_id}",
        company=company,
        category=ResearchCategory.MATERIAL_EVENTS,
        claim="Test claim from a recorded disclosure.",
        evidence_excerpt="Test excerpt.",
        source_id=source_id,
        reliability_tier=2,
        available_at=available_at,
        extracted_at=AS_OF,
        confidence=0.5,
    )


def test_future_observation_never_becomes_evidence_for_any_company():
    future = _observation(
        company="RELIANCE",
        available_at=AS_OF + timedelta(days=4),
        source_id="future-source",
    )

    items = research_observations_to_evidence(
        [future],
        symbol="RELIANCE",
        as_of=AS_OF,
    )

    assert items == ()

    report = run_company_research(
        symbol="RELIANCE",
        as_of=AS_OF,
        features=[],
        acquired_observations=[future],
    )

    synthesis = report.evidence_synthesis
    assert synthesis is not None
    assert synthesis.evidence == ()


def test_naive_timestamp_observation_never_trusted():
    naive = _observation(
        company="SUNPHARMA",
        available_at=datetime(2026, 8, 1, 12, 0),
        source_id="naive-source",
    )

    items = research_observations_to_evidence(
        [naive],
        symbol="SUNPHARMA",
        as_of=AS_OF,
    )

    assert items == ()

    report = run_company_research(
        symbol="SUNPHARMA",
        as_of=AS_OF,
        features=[],
        acquired_observations=[naive],
    )

    synthesis = report.evidence_synthesis
    assert synthesis is not None
    assert synthesis.evidence == ()


def test_observation_for_another_company_never_enters_report():
    other = _observation(
        company="TCS",
        available_at=AS_OF - timedelta(days=1),
        source_id="other-company-source",
    )

    items = research_observations_to_evidence(
        [other],
        symbol="RELIANCE",
        as_of=AS_OF,
    )

    assert items == ()

    report = run_company_research(
        symbol="RELIANCE",
        as_of=AS_OF,
        features=[],
        acquired_observations=[other],
    )

    synthesis = report.evidence_synthesis
    assert synthesis is not None
    assert all(
        item.symbol == "RELIANCE"
        for item in synthesis.evidence
    )


def test_all_companies_reject_naive_and_future_sources(tmp_path):
    for company in NEW_COMPANIES:
        prefix = company.lower()
        provider = RecordedResearchSourceProvider(
            FIXTURE_DIR / f"{prefix}_sources.json"
        )

        candidates = provider.search(
            company,
            _material_events_question(),
            AS_OF,
        )

        assert all(
            candidate.available_at.tzinfo is not None
            for candidate in candidates
        )
        assert all(
            candidate.available_at <= AS_OF
            for candidate in candidates
        )


# ---------------------------------------------------------------------
# Deep company intelligence
# ---------------------------------------------------------------------


def test_every_company_builds_an_intelligence_snapshot(multi_result):
    for result in multi_result.results:
        intelligence = result.intelligence

        assert intelligence is not None
        assert intelligence.company == result.company
        assert intelligence.as_of == AS_OF
        assert intelligence.item_count >= 5
        assert intelligence.source_ids

        financial = intelligence.financial_intelligence
        assert financial is not None
        assert financial.period_count >= 1

        assert all(
            item.is_known_at(AS_OF)
            for item in intelligence.items
        )


def test_intelligence_pit_checks_pass_for_every_company(multi_result):
    for company, checks in multi_result.pit_checks.items():
        assert checks["intelligence_items_known_at_as_of"] is True
        assert checks["no_future_intelligence_items"] is True
        assert checks["financial_periods_known_at_as_of"] is True


def test_no_future_intelligence_items(multi_result):
    for result in multi_result.results:
        intelligence = result.intelligence

        assert all(
            item.available_at is not None
            and item.available_at <= AS_OF
            for item in intelligence.items
        )

        periods = (
            intelligence.financial_intelligence.periods
            if intelligence.financial_intelligence is not None
            else ()
        )

        assert all(
            period.is_known_at(AS_OF)
            for period in periods
        )


def test_intelligence_snapshot_contains_no_conclusion(multi_result):
    for result in multi_result.results:
        intelligence = result.intelligence

        for item in intelligence.items:
            assert item.semantic_category.value != "CONCLUSION"

        assert intelligence.coverage
        assert intelligence.semantic_summary
        assert intelligence.status_summary


def test_timeline_pit_checks_pass_for_every_company(multi_result):
    for company, checks in multi_result.pit_checks.items():
        assert checks["timeline_entries_known_at_as_of"] is True
        assert checks["no_future_timeline_entries"] is True
        assert checks["timeline_is_chronological"] is True


def test_every_company_builds_a_chronological_timeline(multi_result):
    for result in multi_result.results:
        intelligence = result.intelligence

        assert intelligence is not None
        assert intelligence.timeline is not None

        timeline = intelligence.timeline
        assert timeline.company == result.company

        stamps = [
            entry.timeline_at
            for entry in timeline.entries
            if entry.timeline_at is not None
        ]

        assert stamps == sorted(stamps)

        assert all(
            entry.symbol == result.company
            for entry in timeline.entries
        )
        assert all(
            entry.available_at is not None
            and entry.available_at <= AS_OF
            for entry in timeline.entries
        )


def test_every_company_builds_research_status(multi_result):
    for result in multi_result.results:
        intelligence = result.intelligence

        assert intelligence is not None
        assert intelligence.status is not None

        status = intelligence.status
        timeline = intelligence.timeline

        assert status.company == result.company
        assert status.coverage.item_count == (
            len(timeline.entries)
            if timeline is not None
            else 0
        )
        assert status.freshness.stale is False
        assert status.quality.conflict_count >= 0
