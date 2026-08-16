"""
Real-data research verification.

Proves that the existing research pipeline can produce a trustworthy,
reproducible research result for real companies from real recorded
market, financial, and company-disclosure evidence while preserving
strict point-in-time integrity.

The recorded fixtures are NOT invented. They were captured from the
allowed existing provider architecture:

- {company}_market.csv      : real daily OHLCV bars for the company
                              plus the ^NSEI benchmark, captured from
                              the Yahoo Finance market provider (see
                              scripts/capture_real_data_fixtures.py and
                              scripts/capture_multi_company_fixtures.py).
- {company}_financials.json : real annual financials captured from the
                              Yahoo Finance fundamentals provider.
- {company}_sources.json    : real, dated company disclosures curated
                              from public NSE/BSE reporting and press
                              coverage, plus (for TCS) one deliberately
                              future-dated candidate used to verify the
                              point-in-time gate.

Companies span several sectors of the Indian market:

- TCS       information technology
- RELIANCE  energy / conglomerate
- INFY      information technology
- HDFCBANK  banking / financials
- SUNPHARMA pharmaceuticals / healthcare
- M&M       automobiles

No scraping is introduced and no provenance layer is bypassed.

The same verification path also exercises graceful degradation when
research sources are missing, stale, failed, conflicting, or only
partially available.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.analysis.financial_trends_engine import analyze_financial_trends
from src.api.real_company_research import RealCompanyResearchService
from src.data.company.financials import FinancialSnapshot
from src.data.models import PriceBar
from src.data.providers.base import MarketDataProvider
from src.data.providers.csv_provider import CSVMarketDataProvider
from src.research.acquisition.agent import DeterministicResearchAgent
from src.research.acquisition.evidence import (
    research_observations_to_evidence,
)
from src.research.acquisition.models import (
    ResearchCategory,
    ResearchQuestion,
    SourceCandidate,
)
from src.research.acquisition.planner import ResearchPlanner
from src.research.acquisition.providers import ResearchSourceProvider
from src.research.acquisition.runner import (
    AcquisitionResult,
    ResearchAcquisitionRunner,
)
from src.research.acquisition.validator import SourceValidator
from src.research.company_engine import run_company_research
from src.research.company_intel import (
    CompanyIntelligenceSnapshot,
    CompanyTimeline,
    PeriodicUpdateEngine,
    RecordedIntelSourceProvider,
    build_company_intelligence_snapshot,
    derived_metric_items,
    financial_periods_from_snapshots,
    financial_periods_to_items,
    intel_items_from_observations,
)
from src.research.provenance import DataProvenance
from src.research.raw_archive import RawArchive
from src.research.raw_record import RawRecord
from src.research.synthesis.models import EvidenceItem, EvidenceType

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE_DIR = REPO_ROOT / "fixtures" / "real_data"

DEFAULT_COMPANY = "TCS"
DEFAULT_AS_OF = datetime(
    2026,
    8,
    10,
    12,
    0,
    tzinfo=timezone.utc,
)

MARKET_SOURCE_ID = "yahoo_finance_chart_recorded"

BENCHMARK_SYMBOL = "^NSEI"

COMPANY_SECTORS: dict[str, str] = {
    "TCS": "information technology",
    "RELIANCE": "energy / conglomerate",
    "INFY": "information technology",
    "HDFCBANK": "banking / financials",
    "SUNPHARMA": "pharmaceuticals / healthcare",
    "M&M": "automobiles",
}

COMPANIES: tuple[str, ...] = tuple(
    sorted(COMPANY_SECTORS)
)


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


def _fixture_names(company: str) -> tuple[str, str, str]:
    prefix = company.strip().upper().lower()

    return (
        f"{prefix}_market.csv",
        f"{prefix}_financials.json",
        f"{prefix}_sources.json",
    )


def _source_archive_source_id(company: str) -> str:
    return f"{company.strip().upper().lower()}_recorded_sources"


class RecordedMarketDataProvider(MarketDataProvider):
    """
    Replays the recorded real OHLCV fixture through the
    existing CSV adapter.

    Exposes a source_name so the raw archive records honest
    provenance for the replay.
    """

    source_name = MARKET_SOURCE_ID

    def __init__(
        self,
        market_csv: str | Path,
    ) -> None:
        self._csv = CSVMarketDataProvider(market_csv)

    def get_daily_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[PriceBar]:
        return self._csv.get_daily_prices(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )


class RecordedFinancialProvider:
    """
    Replays the recorded real annual financials fixture.
    """

    def __init__(
        self,
        financials_json: str | Path,
    ) -> None:
        data = json.loads(
            Path(financials_json).read_text(encoding="utf-8")
        )

        self._snapshots = [
            FinancialSnapshot.model_validate(snapshot)
            for snapshot in data["snapshots"]
        ]

    def get_annual_financials(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[FinancialSnapshot]:
        normalized = symbol.strip().upper()

        return [
            snapshot
            for snapshot in self._snapshots
            if (
                snapshot.symbol.strip().upper() == normalized
                and start_date <= snapshot.period_end <= end_date
            )
        ]


class StaticSourcesProvider(ResearchSourceProvider):
    """
    Replays an explicit list of recorded source candidates.

    Honors the point-in-time contract exactly like the recorded
    fixture provider: a candidate without a timezone-aware
    available_at or available after `as_of` is never returned
    unless `include_future=True` is set (in which case the
    downstream SourceValidator gate must reject it).
    """

    def __init__(
        self,
        sources: list[SourceCandidate],
        *,
        categories: dict[str, frozenset[str]] | None = None,
        include_future: bool = False,
    ) -> None:
        self._sources = list(sources)
        self._categories = categories
        self._include_future = include_future

    def search(
        self,
        company: str,
        question: ResearchQuestion,
        as_of: datetime,
    ) -> list[SourceCandidate]:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

        results: list[SourceCandidate] = []

        for source in self._sources:
            if self._categories is not None:
                if question.category.value not in self._categories[
                    source.source_id
                ]:
                    continue

            if not self._include_future:
                if source.available_at is None:
                    continue

                if source.available_at > as_of:
                    continue

            results.append(source)

        return results


class RecordedResearchSourceProvider(StaticSourcesProvider):
    """
    Replays recorded real source candidates loaded from a fixture.

    By default the provider honors the point-in-time contract and
    never returns a candidate that was unavailable after `as_of`.

    With `include_future=True` the provider also returns recorded
    future-dated candidates so that the downstream SourceValidator
    gate can be verified against contaminated discovery data.
    """

    def __init__(
        self,
        sources_json: str | Path,
        *,
        include_future: bool = False,
    ) -> None:
        data = json.loads(
            Path(sources_json).read_text(encoding="utf-8")
        )

        sources: list[SourceCandidate] = []
        categories: dict[str, frozenset[str]] = {}

        for entry in data["sources"]:
            categories_fixture = frozenset(
                entry.pop("categories", [])
            )

            source = SourceCandidate.model_validate(entry)

            sources.append(source)
            categories[source.source_id] = categories_fixture

        super().__init__(
            sources,
            categories=categories,
            include_future=include_future,
        )


@dataclass(frozen=True)
class RealDataVerificationResult:
    """
    Complete, reproducible result of the real-data research path.
    """

    company: str
    sector: str
    as_of: datetime
    fixture_dir: Path
    archive_root: Path

    report: object
    base_report: object

    market_ingestion: object
    financial_record_count: int

    acquisition: AcquisitionResult
    evidence_items: tuple[EvidenceItem, ...]

    market_provenance: DataProvenance
    financial_provenance: DataProvenance
    archived_source_ids: tuple[str, ...]

    context_result: object
    feature_snapshot: object

    pit_checks: dict[str, object] = field(default_factory=dict)

    analysis: object | None = None

    intelligence: CompanyIntelligenceSnapshot | None = None

    def evidence_ids(self) -> list[str]:
        return [
            item.evidence_id
            for item in self.evidence_items
        ]

    def acquired_evidence_ids(self) -> list[str]:
        return [
            item.evidence_id
            for item in self.evidence_items
            if item.evidence_type == EvidenceType.ACQUIRED
        ]

    def _intelligence_artifact_summary(self) -> dict[str, object]:
        if self.intelligence is None:
            return {}

        financial = self.intelligence.financial_intelligence
        timeline = self.intelligence.timeline
        status = self.intelligence.status

        return {
            "item_count": self.intelligence.item_count,
            "financial_period_count": (
                financial.period_count
                if financial is not None
                else 0
            ),
            "conflict_count": len(self.intelligence.conflicts),
            "evidence_link_count": len(
                self.intelligence.evidence_links
            ),
            "change_count": len(self.intelligence.changes),
            "coverage": self.intelligence.coverage,
            "semantic_summary": (
                self.intelligence.semantic_summary
            ),
            "status_summary": self.intelligence.status_summary,
            "source_ids": list(self.intelligence.source_ids),
            "provenance_ids": list(
                self.intelligence.provenance_ids
            ),
            "insufficient_evidence_notes": list(
                self.intelligence.insufficient_evidence_notes
            ),
            "timeline": (
                {
                    "entry_count": len(timeline.entries),
                    "counts": timeline.counts,
                    "latest_at": (
                        timeline.latest_at.isoformat()
                        if timeline.latest_at is not None
                        else None
                    ),
                    "earliest_at": (
                        timeline.earliest_at.isoformat()
                        if timeline.earliest_at is not None
                        else None
                    ),
                }
                if timeline is not None
                else None
            ),
            "research_status": (
                {
                    "stale": status.freshness.stale,
                    "days_since_latest_published": (
                        status.freshness.days_since_latest_published
                    ),
                    "item_count": status.coverage.item_count,
                    "missing_categories": list(
                        status.coverage.missing_categories
                    ),
                    "conflict_count": status.quality.conflict_count,
                    "evidence_link_count": (
                        status.quality.evidence_link_count
                    ),
                    "deduplicated_count": (
                        status.quality.deduplicated_count
                    ),
                }
                if status is not None
                else None
            ),
        }

    def to_artifact(self) -> dict[str, object]:
        return {
            "company": self.company,
            "sector": self.sector,
            "as_of": _as_utc(self.as_of).isoformat(),
            "market_archive_records": len(
                self.market_ingestion.accepted
            ),
            "market_rejected_count": len(
                self.market_ingestion.rejected
            ),
            "financial_record_count": self.financial_record_count,
            "sources_discovered": self.acquisition.sources_discovered,
            "sources_accepted": self.acquisition.sources_accepted,
            "observations_created": self.acquisition.observations_created,
            "evidence_items": len(self.evidence_items),
            "acquired_evidence_ids": self.acquired_evidence_ids(),
            "archived_source_ids": list(self.archived_source_ids),
            "pit_checks": self.pit_checks,
            "intelligence": (
                self._intelligence_artifact_summary()
            ),
            "provenance": {
                "market": {
                    "source": self.market_provenance.source,
                    "dataset_id": self.market_provenance.dataset_id,
                    "record_id": self.market_provenance.record_id,
                    "retrieved_at": (
                        self.market_provenance.retrieved_at.isoformat()
                    ),
                    "available_at": (
                        self.market_provenance.available_at.isoformat()
                        if self.market_provenance.available_at
                        is not None
                        else None
                    ),
                },
                "financial": {
                    "source": self.financial_provenance.source,
                    "dataset_id": self.financial_provenance.dataset_id,
                    "record_id": self.financial_provenance.record_id,
                    "retrieved_at": (
                        self.financial_provenance.retrieved_at.isoformat()
                    ),
                    "available_at": (
                        self.financial_provenance.available_at.isoformat()
                        if self.financial_provenance.available_at
                        is not None
                        else None
                    ),
                },
            },
        }

    def write_artifact(
        self,
        path: str | Path,
    ) -> Path:
        artifact = self.to_artifact()

        artifact["artifact_checksum"] = hashlib.sha256(
            json.dumps(
                artifact,
                sort_keys=True,
                default=str,
            ).encode("utf-8")
        ).hexdigest()

        target = Path(path)

        target.parent.mkdir(parents=True, exist_ok=True)

        target.write_text(
            json.dumps(
                artifact,
                indent=2,
                sort_keys=True,
                default=str,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return target


def _archive_sources(
    archive: RawArchive,
    sources: list[SourceCandidate],
    *,
    company: str,
    as_of: datetime,
) -> tuple[str, ...]:
    archived: list[str] = []

    for source in sources:
        record = RawRecord(
            source_id=_source_archive_source_id(company),
            record_id=source.source_id,
            retrieved_at=as_of,
            published_at=source.published_at,
            available_at=source.available_at,
            payload=source.model_dump(mode="json"),
            dataset_id=f"{company.lower()}_recorded_sources",
            request_metadata={
                "company": company,
                "as_of": as_of.isoformat(),
            },
        )

        archive.save(record)
        archived.append(record.record_id)

    return tuple(archived)


def _build_pit_checks(
    *,
    company: str,
    captured_at: datetime,
    base_result,
    acquisition: AcquisitionResult,
    evidence_items: tuple[EvidenceItem, ...],
    archived_source_ids: tuple[str, ...],
) -> dict[str, object]:
    market_bars = list(base_result.market_ingestion.accepted)

    return {
        "market_bars_all_known_at_as_of": all(
            bar.trading_date <= captured_at.date()
            for bar in market_bars
        ),
        "market_records_available_on_or_before_as_of": (
            base_result.market_provenance.available_at
            is not None
            and base_result.market_provenance.available_at
            <= captured_at
        ),
        "financial_period_ends_on_or_before_as_of": all(
            snapshot.period_end <= captured_at.date()
            for snapshot in base_result.financial_snapshots
        ),
        "accepted_sources_known_at_as_of": all(
            source.available_at is not None
            and source.available_at <= captured_at
            for source in acquisition.sources
        ),
        "future_source_rejected": not any(
            source.available_at is not None
            and source.available_at > captured_at
            for source in acquisition.sources
        ),
        "all_evidence_known_at_as_of": all(
            item.observation_at <= captured_at
            for item in evidence_items
        ),
        "every_acquired_evidence_resolves_to_archived_source": all(
            source_id in archived_source_ids
            for item in evidence_items
            if item.evidence_type == EvidenceType.ACQUIRED
            for source_id in item.source_ids
        ),
    }


def _timeline_is_chronological(timeline: CompanyTimeline) -> bool:
    """Entries must be sorted by the same deterministic key used to
    build the timeline: (timeline_at, entry_id)."""
    keys = [
        (
            entry.timeline_at.isoformat()
            if entry.timeline_at is not None
            else "",
            entry.entry_id,
        )
        for entry in timeline.entries
    ]
    return keys == sorted(keys)


def _build_intelligence_snapshot(
    *,
    company: str,
    captured_at: datetime,
    observations: tuple,
    financial_snapshots: list[FinancialSnapshot],
    provenance_ids: tuple[str, ...],
    fixture_dir: Path,
) -> CompanyIntelligenceSnapshot:
    """
    Build the deep company intelligence snapshot for one company.

    Combines:
    - financial periods derived from the recorded financial snapshots;
    - intelligence items derived from acquisition observations;
    - recorded intel feed items replayed from {company}_intel.json
      (skipped when the fixture is absent).

    Everything is filtered to the point-in-time `captured_at`.
    """

    intel_items: list = []

    intel_path = (
        fixture_dir / f"{company.strip().upper().lower()}_intel.json"
    )

    if intel_path.exists():
        provider = RecordedIntelSourceProvider.from_json(intel_path)

        update = PeriodicUpdateEngine(
            providers=[provider],
        ).run(
            company,
            as_of=captured_at,
        )

        intel_items.extend(update.items)

    observation_items = intel_items_from_observations(
        observations,
        as_of=captured_at,
    )

    periods = financial_periods_from_snapshots(
        financial_snapshots,
        as_of=captured_at,
        default_available_at=captured_at,
    )

    period_items = financial_periods_to_items(
        periods,
        as_of=captured_at,
        provenance_id=(
            provenance_ids[1] if len(provenance_ids) > 1 else None
        ),
    )

    metric_items = derived_metric_items(
        periods,
        as_of=captured_at,
        provenance_id=(
            provenance_ids[1] if len(provenance_ids) > 1 else None
        ),
    )

    items = [
        *observation_items,
        *period_items,
        *metric_items,
        *intel_items,
    ]

    return build_company_intelligence_snapshot(
        symbol=company,
        as_of=captured_at,
        captured_at=captured_at,
        items=items,
        financial_periods=periods,
        provenance_ids=provenance_ids,
    )


def _run_verification_path(
    *,
    company: str,
    captured_at: datetime,
    fixture_dir: Path,
    archive_root: Path,
    market_provider: MarketDataProvider,
    financial_provider,
    source_provider: ResearchSourceProvider,
) -> RealDataVerificationResult:
    """
    Run the complete real-data research path for one company and
    return the result.

    Path verified:

        company
        -> recorded provider (market / financial / research sources)
        -> raw archive + provenance
        -> acquisition -> ResearchObservation
        -> EvidenceItem
        -> evidence synthesis
        -> company report / intelligence
    """

    normalized = company.strip().upper()

    service = RealCompanyResearchService(
        market_provider=market_provider,
        financial_provider=financial_provider,
        archive_root=archive_root,
        benchmark_symbol=BENCHMARK_SYMBOL,
    )

    base_result = service.run(
        normalized,
        retrieved_at=captured_at,
    )

    runner = ResearchAcquisitionRunner(
        planner=ResearchPlanner(),
        providers=[source_provider],
        validator=SourceValidator(),
        agent=DeterministicResearchAgent(),
    )

    acquisition = runner.run(
        company=normalized,
        as_of=captured_at,
        extracted_at=captured_at,
    )

    archive = RawArchive(archive_root)

    archived_source_ids = _archive_sources(
        archive,
        acquisition.sources,
        company=normalized,
        as_of=captured_at,
    )

    evidence_items = research_observations_to_evidence(
        acquisition.observations,
        symbol=normalized,
        as_of=captured_at,
    )

    report = run_company_research(
        symbol=normalized,
        as_of=captured_at,
        features=list(base_result.feature_snapshot.features),
        trend_summaries=analyze_financial_trends(
            list(base_result.financial_snapshots)
        ),
        company_snapshot=base_result.analysis.company_intelligence,
        financial_snapshots=list(
            base_result.financial_snapshots
        ),
        market_snapshot=base_result.analysis.market_snapshot,
        provenance_ids=(
            base_result.market_provenance.record_id or "",
            base_result.financial_provenance.record_id or "",
        ),
        acquired_observations=acquisition.observations,
    )

    pit_checks = _build_pit_checks(
        company=normalized,
        captured_at=captured_at,
        base_result=base_result,
        acquisition=acquisition,
        evidence_items=evidence_items,
        archived_source_ids=archived_source_ids,
    )

    intelligence = _build_intelligence_snapshot(
        company=normalized,
        captured_at=captured_at,
        observations=acquisition.observations,
        financial_snapshots=list(
            base_result.financial_snapshots
        ),
        provenance_ids=(
            base_result.market_provenance.record_id or "",
            base_result.financial_provenance.record_id or "",
        ),
        fixture_dir=fixture_dir,
    )

    pit_checks["intelligence_items_known_at_as_of"] = all(
        item.is_known_at(captured_at)
        for item in intelligence.items
    )
    pit_checks["no_future_intelligence_items"] = not any(
        item.available_at is not None
        and item.available_at > captured_at
        for item in intelligence.items
    )
    pit_checks["financial_periods_known_at_as_of"] = all(
        period.is_known_at(captured_at)
        for period in (
            intelligence.financial_intelligence.periods
            if intelligence.financial_intelligence is not None
            else ()
        )
    )

    timeline = intelligence.timeline

    pit_checks["timeline_entries_known_at_as_of"] = (
        all(
            entry.available_at is not None
            and entry.available_at <= captured_at
            for entry in timeline.entries
        )
        if timeline is not None
        else True
    )
    pit_checks["no_future_timeline_entries"] = not any(
        entry.timeline_at is not None
        and entry.timeline_at > captured_at
        for entry in (
            timeline.entries if timeline is not None else ()
        )
    )
    pit_checks["timeline_is_chronological"] = (
        _timeline_is_chronological(timeline)
        if timeline is not None
        else True
    )

    return RealDataVerificationResult(
        company=normalized,
        sector=COMPANY_SECTORS[normalized],
        as_of=captured_at,
        fixture_dir=fixture_dir,
        archive_root=archive_root,
        report=report,
        base_report=base_result.report,
        analysis=base_result.analysis,
        market_ingestion=base_result.market_ingestion,
        financial_record_count=len(
            base_result.financial_snapshots
        ),
        acquisition=acquisition,
        evidence_items=evidence_items,
        market_provenance=base_result.market_provenance,
        financial_provenance=base_result.financial_provenance,
        archived_source_ids=archived_source_ids,
        context_result=base_result.context_result,
        feature_snapshot=base_result.feature_snapshot,
        pit_checks=pit_checks,
        intelligence=intelligence,
    )


def run_real_data_verification(
    *,
    company: str = DEFAULT_COMPANY,
    as_of: datetime | None = None,
    archive_root: str | Path,
    fixture_dir: str | Path | None = None,
    include_future_sources: bool = False,
) -> RealDataVerificationResult:
    """
    Run the complete real-data research path for a recorded company
    and return the result.
    """

    normalized = company.strip().upper()

    if not normalized:
        raise ValueError("company cannot be empty")

    if normalized not in COMPANY_SECTORS:
        raise ValueError(
            "the recorded fixtures only cover the real companies "
            f"{', '.join(COMPANIES)}; received {normalized}. "
            "Record a fixture for the requested company first."
        )

    captured_at = as_of or DEFAULT_AS_OF

    if captured_at.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    fixtures = Path(
        fixture_dir or DEFAULT_FIXTURE_DIR
    )

    archive_root_path = Path(archive_root)

    market_csv, financials_json, sources_json = _fixture_names(
        normalized
    )

    market_provider = RecordedMarketDataProvider(
        fixtures / market_csv
    )

    financial_provider = RecordedFinancialProvider(
        fixtures / financials_json
    )

    source_provider = RecordedResearchSourceProvider(
        fixtures / sources_json,
        include_future=include_future_sources,
    )

    return _run_verification_path(
        company=normalized,
        captured_at=captured_at,
        fixture_dir=fixtures,
        archive_root=archive_root_path,
        market_provider=market_provider,
        financial_provider=financial_provider,
        source_provider=source_provider,
    )


@dataclass(frozen=True)
class MultiCompanyVerificationResult:
    """
    Aggregated result of the multi-company real-data research path.
    """

    as_of: datetime
    fixture_dir: Path
    archive_root: Path
    results: tuple[RealDataVerificationResult, ...]

    @property
    def companies(self) -> tuple[str, ...]:
        return tuple(result.company for result in self.results)

    @property
    def sectors(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    result.sector
                    for result in self.results
                }
            )
        )

    @property
    def pit_checks(self) -> dict[str, dict[str, object]]:
        return {
            result.company: result.pit_checks
            for result in self.results
        }

    @property
    def all_pit_checks_pass(self) -> bool:
        return all(
            all(
                value is True
                for value in result.pit_checks.values()
            )
            for result in self.results
        )


def run_multi_company_verification(
    *,
    companies: list[str] | tuple[str, ...] | None = None,
    as_of: datetime | None = None,
    archive_root: str | Path,
    fixture_dir: str | Path | None = None,
) -> MultiCompanyVerificationResult:
    """
    Run the complete real-data research path for several recorded
    Indian companies across different sectors.
    """

    selected = tuple(
        company.strip().upper()
        for company in (companies or COMPANIES)
    )

    unknown = [
        company
        for company in selected
        if company not in COMPANY_SECTORS
    ]

    if unknown:
        raise ValueError(
            "the recorded fixtures only cover the real companies "
            f"{', '.join(COMPANIES)}; received {', '.join(unknown)}."
        )

    captured_at = as_of or DEFAULT_AS_OF

    if captured_at.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    fixtures = Path(
        fixture_dir or DEFAULT_FIXTURE_DIR
    )

    archive_root_path = Path(archive_root)

    results: list[RealDataVerificationResult] = []

    for company in selected:
        results.append(
            run_real_data_verification(
                company=company,
                as_of=captured_at,
                archive_root=archive_root_path,
                fixture_dir=fixtures,
            )
        )

    return MultiCompanyVerificationResult(
        as_of=captured_at,
        fixture_dir=fixtures,
        archive_root=archive_root_path,
        results=tuple(results),
    )


class MissingSourcesProvider(ResearchSourceProvider):
    """
    A recorded research source provider that finds nothing.
    """

    def search(
        self,
        company: str,
        question: ResearchQuestion,
        as_of: datetime,
    ) -> list[SourceCandidate]:
        return []


class StaleSourcesProvider(StaticSourcesProvider):
    """
    Replays recorded sources whose disclosures are much older than
    the research as-of (still point-in-time valid), plus one
    future-dated candidate that must be rejected downstream.
    """

    def __init__(
        self,
        sources_json: str | Path,
        *,
        stale_shift_days: int = 365,
    ) -> None:
        data = json.loads(
            Path(sources_json).read_text(encoding="utf-8")
        )

        sources: list[SourceCandidate] = []
        categories: dict[str, frozenset[str]] = {}

        for index, entry in enumerate(data["sources"]):
            categories_fixture = frozenset(
                entry.pop("categories", [])
            )

            source = SourceCandidate.model_validate(entry)

            published_at = source.published_at
            available_at = source.available_at

            if published_at is not None:
                published_at = published_at - timedelta(
                    days=stale_shift_days
                )

            if available_at is not None:
                available_at = available_at - timedelta(
                    days=stale_shift_days
                )

            stale = SourceCandidate(
                **{
                    **source.model_dump(mode="json"),
                    "source_id": f"stale-{source.source_id}",
                    "published_at": published_at,
                    "available_at": available_at,
                }
            )

            sources.append(stale)
            categories[stale.source_id] = categories_fixture

        future = SourceCandidate(
            source_id=f"future-{sources_json.stem}",
            source_name="PIT Verification Fixture",
            source_type="NEWS",
            url="https://example.invalid/stale-future",
            title="Future-dated disclosure fixture used to verify point-in-time rejection of stale-provider discovery",
            published_at=(
                DEFAULT_AS_OF + timedelta(days=4)
            ),
            available_at=(
                DEFAULT_AS_OF + timedelta(days=4)
            ),
            reliability_tier=2,
        )

        categories[future.source_id] = frozenset(
            {"material_events"}
        )

        super().__init__(
            [*sources, future],
            categories=categories,
            include_future=True,
        )


class PartialSourcesProvider(StaticSourcesProvider):
    """
    Replays sources where coverage is only partially available:

    - valid sources for some research questions
    - no sources for other questions
    - one future-dated candidate that must be rejected
    - one naive (timezone-naive) candidate that must be rejected
    """

    def __init__(
        self,
        sources_json: str | Path,
    ) -> None:
        data = json.loads(
            Path(sources_json).read_text(encoding="utf-8")
        )

        sources: list[SourceCandidate] = []
        categories: dict[str, frozenset[str]] = {}

        for index, entry in enumerate(data["sources"]):
            categories_fixture = frozenset(
                entry.pop("categories", [])
            )

            source = SourceCandidate.model_validate(entry)

            # Keep only a subset of the recorded disclosures so
            # coverage is partial.
            if index % 2 != 0:
                continue

            sources.append(source)
            categories[source.source_id] = categories_fixture

        future = SourceCandidate(
            source_id=f"partial-future-{sources_json.stem}",
            source_name="PIT Verification Fixture",
            source_type="NEWS",
            url="https://example.invalid/partial-future",
            title="Future-dated disclosure fixture used to verify partial-provider point-in-time rejection",
            published_at=(
                DEFAULT_AS_OF + timedelta(days=4)
            ),
            available_at=(
                DEFAULT_AS_OF + timedelta(days=4)
            ),
            reliability_tier=2,
        )

        naive = SourceCandidate(
            source_id=f"partial-naive-{sources_json.stem}",
            source_name="PIT Verification Fixture",
            source_type="NEWS",
            url="https://example.invalid/partial-naive",
            title="Naive-timestamp disclosure fixture used to verify partial-provider timestamp rejection",
            published_at=datetime(
                2026,
                8,
                1,
                12,
                0,
            ),
            available_at=datetime(
                2026,
                8,
                1,
                12,
                0,
            ),
            reliability_tier=2,
        )

        categories[future.source_id] = frozenset(
            {"material_events"}
        )
        categories[naive.source_id] = frozenset(
            {"material_events"}
        )

        super().__init__(
            [*sources, future, naive],
            categories=categories,
            include_future=True,
        )


class FailedSourcesProvider(ResearchSourceProvider):
    """
    A recorded research source provider that always fails.

    Used to verify graceful degradation: a failed optional source
    provider must not corrupt the report or cause unrelated evidence
    to become trusted.
    """

    source_name = "failed-sources-provider"

    def search(
        self,
        company: str,
        question: ResearchQuestion,
        as_of: datetime,
    ) -> list[SourceCandidate]:
        raise RuntimeError(
            f"recorded source provider failed for {company}"
        )


def run_source_scenario(
    *,
    company: str,
    source_provider: ResearchSourceProvider,
    as_of: datetime | None = None,
    archive_root: str | Path,
    fixture_dir: str | Path | None = None,
    market_provider: MarketDataProvider | None = None,
    financial_provider=None,
) -> RealDataVerificationResult:
    """
    Run the complete real-data research path for a recorded company
    using an arbitrary recorded source provider.

    Used to verify that company research works when sources are
    missing, stale, failed, conflicting, or only partially available.

    `market_provider` and `financial_provider` default to the
    recorded fixtures for the company; injectable so that provider
    failure paths can also be verified.
    """

    normalized = company.strip().upper()

    if not normalized:
        raise ValueError("company cannot be empty")

    if normalized not in COMPANY_SECTORS:
        raise ValueError(
            "the recorded fixtures only cover the real companies "
            f"{', '.join(COMPANIES)}; received {normalized}."
        )

    captured_at = as_of or DEFAULT_AS_OF

    if captured_at.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    fixtures = Path(
        fixture_dir or DEFAULT_FIXTURE_DIR
    )

    archive_root_path = Path(archive_root)

    if market_provider is None or financial_provider is None:
        market_csv, financials_json, _ = _fixture_names(normalized)

    if market_provider is None:
        market_provider = RecordedMarketDataProvider(
            fixtures / market_csv
        )

    if financial_provider is None:
        financial_provider = RecordedFinancialProvider(
            fixtures / financials_json
        )

    return _run_verification_path(
        company=normalized,
        captured_at=captured_at,
        fixture_dir=fixtures,
        archive_root=archive_root_path,
        market_provider=market_provider,
        financial_provider=financial_provider,
        source_provider=source_provider,
    )


__all__ = [
    "BENCHMARK_SYMBOL",
    "COMPANIES",
    "COMPANY_SECTORS",
    "DEFAULT_AS_OF",
    "DEFAULT_COMPANY",
    "DEFAULT_FIXTURE_DIR",
    "FailedSourcesProvider",
    "MissingSourcesProvider",
    "MultiCompanyVerificationResult",
    "PartialSourcesProvider",
    "RealDataVerificationResult",
    "RecordedFinancialProvider",
    "RecordedMarketDataProvider",
    "RecordedResearchSourceProvider",
    "StaleSourcesProvider",
    "StaticSourcesProvider",
    "run_multi_company_verification",
    "run_real_data_verification",
    "run_source_scenario",
]
