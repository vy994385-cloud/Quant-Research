"""
Real-data research verification.

Proves that the existing research pipeline can produce a trustworthy,
reproducible research result for a real company from real recorded
market, financial, and company-disclosure evidence while preserving
strict point-in-time integrity.

The recorded fixtures are NOT invented. They were captured from the
allowed existing provider architecture:

- tcs_market.csv      : real TCS + ^NSEI daily OHLCV bars replayed
                        from the raw archive captured from the Yahoo
                        Finance provider (see
                        scripts/capture_real_data_fixtures.py).
- tcs_financials.json : real TCS annual financials captured from the
                        Yahoo Finance fundamentals provider.
- tcs_sources.json    : real, dated TCS disclosures curated from
                        public NSE/BSE reporting and press coverage,
                        plus one deliberately future-dated candidate
                        used to verify the point-in-time gate.

No scraping is introduced and no provenance layer is bypassed.
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
SOURCE_ARCHIVE_SOURCE_ID = "tcs_recorded_sources"

BENCHMARK_SYMBOL = "^NSEI"


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


class RecordedMarketDataProvider(MarketDataProvider):
    """
    Replays the recorded real TCS/^NSEI OHLCV fixture through the
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
    Replays the recorded real TCS annual financials fixture.
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


class RecordedResearchSourceProvider(ResearchSourceProvider):
    """
    Replays recorded real TCS source candidates.

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

        self._include_future = include_future

        self._sources: list[SourceCandidate] = []
        self._categories: dict[str, frozenset[str]] = {}

        for entry in data["sources"]:
            categories = frozenset(
                entry.pop("categories", [])
            )

            source = SourceCandidate.model_validate(entry)

            self._sources.append(source)
            self._categories[source.source_id] = categories

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


@dataclass(frozen=True)
class RealDataVerificationResult:
    """
    Complete, reproducible result of the real-data research path.
    """

    company: str
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

    def to_artifact(self) -> dict[str, object]:
        return {
            "company": self.company,
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
            source_id=SOURCE_ARCHIVE_SOURCE_ID,
            record_id=source.source_id,
            retrieved_at=as_of,
            published_at=source.published_at,
            available_at=source.available_at,
            payload=source.model_dump(mode="json"),
            dataset_id="tcs_recorded_sources",
            request_metadata={
                "company": company,
                "as_of": as_of.isoformat(),
            },
        )

        archive.save(record)
        archived.append(record.record_id)

    return tuple(archived)


def run_real_data_verification(
    *,
    company: str = DEFAULT_COMPANY,
    as_of: datetime | None = None,
    archive_root: str | Path,
    fixture_dir: str | Path | None = None,
    include_future_sources: bool = False,
) -> RealDataVerificationResult:
    """
    Run the complete real-data research path and return the result.

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

    if not normalized:
        raise ValueError("company cannot be empty")

    if normalized != DEFAULT_COMPANY:
        raise ValueError(
            "the recorded fixtures only cover the real company "
            f"{DEFAULT_COMPANY}; received {normalized}. "
            "Record a fixture for the requested company first."
        )

    captured_at = as_of or DEFAULT_AS_OF

    if captured_at.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    fixtures = Path(
        fixture_dir or DEFAULT_FIXTURE_DIR
    )

    archive_root_path = Path(archive_root)

    market_provider = RecordedMarketDataProvider(
        fixtures / "tcs_market.csv"
    )

    financial_provider = RecordedFinancialProvider(
        fixtures / "tcs_financials.json"
    )

    service = RealCompanyResearchService(
        market_provider=market_provider,
        financial_provider=financial_provider,
        archive_root=archive_root_path,
        benchmark_symbol=BENCHMARK_SYMBOL,
    )

    base_result = service.run(
        normalized,
        retrieved_at=captured_at,
    )

    source_provider = RecordedResearchSourceProvider(
        fixtures / "tcs_sources.json",
        include_future=include_future_sources,
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

    archive = RawArchive(archive_root_path)

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

    market_bars = list(base_result.market_ingestion.accepted)

    pit_checks = {
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
        "future_source_rejected": (
            not any(
                source.source_id == "tcs-future-event-fixture"
                for source in acquisition.sources
            )
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

    return RealDataVerificationResult(
        company=normalized,
        as_of=captured_at,
        fixture_dir=fixtures,
        archive_root=archive_root_path,
        report=report,
        base_report=base_result.report,
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
    )


__all__ = [
    "BENCHMARK_SYMBOL",
    "DEFAULT_AS_OF",
    "DEFAULT_COMPANY",
    "DEFAULT_FIXTURE_DIR",
    "RealDataVerificationResult",
    "RecordedFinancialProvider",
    "RecordedMarketDataProvider",
    "RecordedResearchSourceProvider",
    "run_real_data_verification",
]
