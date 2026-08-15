from datetime import datetime, timedelta, timezone
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
from src.research.raw_record import RawRecord
from src.research.synthesis.models import EvidenceType
from src.verification.real_data import (
    DEFAULT_COMPANY,
    RecordedFinancialProvider,
    RecordedMarketDataProvider,
    RecordedResearchSourceProvider,
    run_real_data_verification,
)

AS_OF = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)

FIXTURE_DIR = (
    Path(__file__).resolve().parents[1] / "fixtures" / "real_data"
)


@pytest.fixture(scope="module")
def verification_result(tmp_path_factory):
    archive_root = tmp_path_factory.mktemp("real-data-archive")

    return run_real_data_verification(
        archive_root=archive_root,
    )


@pytest.fixture(scope="module")
def contaminated_result(tmp_path_factory):
    archive_root = tmp_path_factory.mktemp("real-data-contaminated-archive")

    return run_real_data_verification(
        archive_root=archive_root,
        include_future_sources=True,
    )


def _observation(
    *,
    available_at: datetime | None,
    observation_id: str = "TCS:material-events:test-source",
) -> ResearchObservation:
    return ResearchObservation(
        observation_id=observation_id,
        company="TCS",
        category=ResearchCategory.MATERIAL_EVENTS,
        claim="Test claim from a recorded disclosure.",
        evidence_excerpt="Test excerpt.",
        source_id="test-source",
        reliability_tier=2,
        available_at=available_at,
        extracted_at=AS_OF,
        confidence=0.5,
    )


def _future_observation() -> ResearchObservation:
    return _observation(
        observation_id="TCS:material-events:future-source",
        available_at=datetime(
            2026,
            8,
            14,
            12,
            0,
            tzinfo=timezone.utc,
        ),
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


def test_recorded_market_provider_serves_real_tcs_and_nsei_bars():
    provider = RecordedMarketDataProvider(
        FIXTURE_DIR / "tcs_market.csv"
    )

    bars = provider.get_daily_prices(
        "TCS",
        AS_OF.date() - timedelta(days=365),
        AS_OF.date(),
    )

    assert bars
    assert all(bar.symbol == "TCS" for bar in bars)
    assert all(bar.trading_date <= AS_OF.date() for bar in bars)
    assert all(bar.close > 0 for bar in bars)

    benchmark = provider.get_daily_prices(
        "^NSEI",
        AS_OF.date() - timedelta(days=365),
        AS_OF.date(),
    )

    assert benchmark
    assert all(bar.symbol == "^NSEI" for bar in benchmark)


def test_recorded_financial_provider_serves_real_tcs_snapshots():
    provider = RecordedFinancialProvider(
        FIXTURE_DIR / "tcs_financials.json"
    )

    snapshots = provider.get_annual_financials(
        "TCS",
        AS_OF.date() - timedelta(days=3650),
        AS_OF.date(),
    )

    assert len(snapshots) >= 4
    assert all(snapshot.symbol == "TCS" for snapshot in snapshots)
    assert all(
        snapshot.period_end <= AS_OF.date()
        for snapshot in snapshots
    )
    assert all(snapshot.revenue is not None for snapshot in snapshots)


def test_recorded_source_provider_honors_point_in_time_contract():
    provider = RecordedResearchSourceProvider(
        FIXTURE_DIR / "tcs_sources.json"
    )

    candidates = provider.search(
        "TCS",
        _material_events_question(),
        AS_OF,
    )

    ids = {candidate.source_id for candidate in candidates}

    assert "tcs-future-event-fixture" not in ids
    assert "tcs-board-meeting-june22" in ids
    assert all(
        candidate.available_at is not None
        and candidate.available_at <= AS_OF
        for candidate in candidates
    )


def test_full_real_data_path_produces_pit_safe_report(
    verification_result,
):
    result = verification_result

    assert result.company == "TCS"
    assert result.as_of == AS_OF

    # Real recorded market data was validated and archived.
    assert len(result.market_ingestion.accepted) >= 200
    assert result.market_ingestion.rejected == []

    # Real recorded financials were preserved.
    assert result.financial_record_count >= 4

    # Acquisition discovered real TCS disclosures.
    assert result.acquisition.sources_discovered >= 4
    assert result.acquisition.observations_created >= 4

    # Every observation became a point-in-time-safe EvidenceItem.
    assert result.evidence_items
    assert all(
        item.observation_at <= AS_OF
        for item in result.evidence_items
    )

    # The report carries the acquired evidence into synthesis.
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

    # The report is produced for the real company.
    assert result.report.symbol == "TCS"
    assert result.report.as_of == AS_OF
    assert result.report.evidence_narrative is not None


def test_all_point_in_time_checks_pass(verification_result):
    checks = verification_result.pit_checks

    assert checks["market_bars_all_known_at_as_of"] is True
    assert (
        checks["market_records_available_on_or_before_as_of"]
        is True
    )
    assert checks["financial_period_ends_on_or_before_as_of"] is True
    assert checks["accepted_sources_known_at_as_of"] is True
    assert checks["future_source_rejected"] is True
    assert checks["all_evidence_known_at_as_of"] is True
    assert (
        checks[
            "every_acquired_evidence_resolves_to_archived_source"
        ]
        is True
    )


def test_future_dated_source_is_rejected_downstream(
    contaminated_result,
):
    result = contaminated_result

    # The future-dated candidate was discovered ...
    assert result.acquisition.sources_discovered > (
        result.acquisition.sources_accepted
    )

    # ... but rejected before it could become evidence.
    assert result.acquisition.sources_accepted == 4
    assert all(
        source.source_id != "tcs-future-event-fixture"
        for source in result.acquisition.sources
    )
    assert result.pit_checks["future_source_rejected"] is True
    assert not any(
        "tcs-future-event-fixture" in item.evidence_id
        for item in result.evidence_items
    )


def test_validator_rejects_future_dated_source():
    validator = SourceValidator()

    future = SourceCandidate(
        source_id="future-source",
        source_name="PIT Verification Fixture",
        source_type="NEWS",
        url="https://example.invalid/future-source",
        title="Future-dated disclosure.",
        available_at=datetime(
            2026,
            8,
            14,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        reliability_tier=2,
    )

    assert validator.validate(future, AS_OF) is False
    assert validator.validate_many([future], AS_OF) == []


def test_future_dated_observation_never_becomes_evidence():
    items = research_observations_to_evidence(
        [_future_observation()],
        symbol="TCS",
        as_of=AS_OF,
    )

    assert items == ()


def test_future_dated_observation_never_reaches_synthesis():
    report = run_company_research(
        symbol="TCS",
        as_of=AS_OF,
        features=[],
        acquired_observations=[_future_observation()],
    )

    synthesis = report.evidence_synthesis

    assert synthesis is not None
    assert synthesis.evidence == ()


def test_insufficient_provenance_cannot_become_trusted_evidence():
    no_availability = _observation(available_at=None)
    naive_availability = _observation(
        available_at=datetime(2026, 8, 5, 12, 0),
    )

    items = research_observations_to_evidence(
        [no_availability, naive_availability],
        symbol="TCS",
        as_of=AS_OF,
    )

    assert items == ()

    report = run_company_research(
        symbol="TCS",
        as_of=AS_OF,
        features=[],
        acquired_observations=[
            no_availability,
            naive_availability,
        ],
    )

    synthesis = report.evidence_synthesis

    assert synthesis is not None
    assert synthesis.evidence == ()


def test_source_provenance_survives_through_final_output(
    verification_result,
):
    result = verification_result

    # Every acquired evidence item's source id resolves to an
    # archived raw record that preserves the source metadata.
    archive = RawArchive(result.archive_root)

    acquired = [
        item
        for item in result.evidence_items
        if item.evidence_type == EvidenceType.ACQUIRED
    ]

    assert acquired

    for item in acquired:
        assert len(item.source_ids) == 1

        source_id = item.source_ids[0]

        assert source_id in result.archived_source_ids

        record = archive.load(
            "tcs_recorded_sources",
            source_id,
        )

        assert record.available_at is not None
        assert record.available_at <= AS_OF
        assert record.payload["source_id"] == source_id
        assert record.payload["url"]

    # The report's provenance identifiers include the archived
    # market and financial record identifiers.
    synthesis = result.report.evidence_synthesis

    assert synthesis is not None

    report_provenance = {
        source_id
        for item in synthesis.evidence
        for source_id in item.provenance_ids
    }

    assert result.market_provenance.record_id in report_provenance
    assert result.financial_provenance.record_id in report_provenance


def test_market_provenance_is_archived_with_real_payload(
    verification_result,
):
    result = verification_result

    archive = RawArchive(result.archive_root)

    market_record = archive.load(
        "yahoo_finance_chart_recorded",
        "TCS_2026-08-07",
    )

    assert market_record.payload["symbol"] == "TCS"
    assert market_record.payload["trading_date"] == "2026-08-07"
    assert market_record.available_at is not None
    assert market_record.available_at <= AS_OF


def test_archived_sources_preserve_real_disclosure_metadata(
    verification_result,
):
    result = verification_result

    archive = RawArchive(result.archive_root)

    record = archive.load(
        "tcs_recorded_sources",
        "tcs-q1fy27-results",
    )

    assert record.available_at is not None
    assert record.published_at is not None
    assert record.published_at <= record.available_at
    assert record.available_at <= AS_OF
    assert record.payload["source_type"] == "NEWS"
    assert record.payload["url"].startswith("https://")
    assert record.checksum

    # Re-saving the identical raw record is a no-op (immutability).
    archive.save(record)


def test_verifier_rejects_unrecorded_company(tmp_path):
    with pytest.raises(ValueError, match="only cover the real company"):
        run_real_data_verification(
            company="INFY",
            archive_root=tmp_path / "archive",
        )


def test_verification_is_reproducible_and_writes_artifact(
    tmp_path,
):
    first_archive = tmp_path / "first"
    second_archive = tmp_path / "second"

    first = run_real_data_verification(
        archive_root=first_archive,
    )
    second = run_real_data_verification(
        archive_root=second_archive,
    )

    first_artifact = first.to_artifact()
    second_artifact = second.to_artifact()

    assert first_artifact == second_artifact

    path = first.write_artifact(tmp_path / "artifact.json")

    assert path.exists()

    content = path.read_text(encoding="utf-8")

    assert f'"company": "{DEFAULT_COMPANY}"' in content
    assert '"artifact_checksum"' in content
