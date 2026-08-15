from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

from src.analysis.financial_trends_engine import analyze_financial_trends
from src.data.ingestion.daily_prices import DailyPriceIngestion
from src.data.ingestion.validator import IngestionResult
from src.data.company.financials import FinancialSnapshot
from src.data.providers.base import MarketDataProvider
from src.research.company_engine import run_company_research
from src.research.context_builder import (
    ContextObservation,
    ContextBuildResult,
    ResearchContextBuilder,
)
from src.research.features.snapshot import FeatureSnapshotBuilder
from src.research.features.market import market_observation_to_context
from src.research.market_engine import run_market_research
from src.research.market_observations import build_market_observations
from src.research.provenance import DataProvenance
from src.research.raw_archive import RawArchive


MARKET_LOOKBACK_DAYS = 365
FINANCIAL_LOOKBACK_DAYS = 3650


class _ValidatedArchivedMarketProvider(MarketDataProvider):
    """Provider adapter that makes validation and archival mandatory."""

    def __init__(
        self,
        provider: MarketDataProvider,
        archive: RawArchive,
        *,
        retrieved_at: datetime,
    ) -> None:
        self._ingestion = DailyPriceIngestion(provider, archive)
        self._retrieved_at = retrieved_at
        self.results: dict[tuple[str, date, date], IngestionResult] = {}

    def get_daily_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list:
        key = (symbol.strip().upper(), start_date, end_date)

        if key not in self.results:
            self.results[key] = self._ingestion.ingest(
                symbol=key[0],
                start_date=start_date,
                end_date=end_date,
                retrieved_at=self._retrieved_at,
                dataset_id="yahoo_finance_chart",
                request_metadata={
                    "symbol": key[0],
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            )

        return self.results[key].accepted


class _CachedFinancialProvider:
    """Avoid a second provider request when reports need raw inputs."""

    def __init__(self, provider) -> None:
        self._provider = provider
        self.results: dict[tuple[str, date, date], list] = {}

    def get_annual_financials(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list:
        key = (symbol.strip().upper(), start_date, end_date)

        if key not in self.results:
            self.results[key] = self._provider.get_annual_financials(
                symbol=key[0],
                start_date=start_date,
                end_date=end_date,
            )

        return self.results[key]


@dataclass(frozen=True)
class RealCompanyResearchResult:
    analysis: object
    report: object
    feature_snapshot: object
    context_result: ContextBuildResult
    market_ingestion: IngestionResult
    financial_record_count: int
    financial_snapshots: tuple[FinancialSnapshot, ...]
    market_provenance: DataProvenance
    financial_provenance: DataProvenance
    retrieved_at: datetime


class RealCompanyResearchService:
    """Thin orchestration layer for the existing real-company engines."""

    def __init__(
        self,
        *,
        market_provider: MarketDataProvider,
        financial_provider,
        archive_root: str | Path,
        benchmark_symbol: str = "^NSEI",
    ) -> None:
        self._market_provider = market_provider
        self._financial_provider = financial_provider
        self._archive_root = Path(archive_root)
        self._benchmark_symbol = benchmark_symbol

    def run(
        self,
        symbol: str,
        *,
        retrieved_at: datetime | None = None,
    ) -> RealCompanyResearchResult:
        normalized = symbol.strip().upper()

        if not normalized:
            raise ValueError("symbol cannot be empty")

        captured_at = retrieved_at or datetime.now(timezone.utc)

        if captured_at.tzinfo is None:
            raise ValueError("retrieved_at must be timezone-aware")

        end_date = captured_at.date()
        market_start = end_date - timedelta(days=MARKET_LOOKBACK_DAYS)
        financial_start = end_date - timedelta(days=FINANCIAL_LOOKBACK_DAYS)

        market_provider = _ValidatedArchivedMarketProvider(
            self._market_provider,
            RawArchive(self._archive_root),
            retrieved_at=captured_at,
        )
        financial_provider = _CachedFinancialProvider(
            self._financial_provider,
        )

        with NamedTemporaryFile(
            mode="w",
            suffix=".csv",
            delete=False,
        ) as handle:
            handle.write("symbol\n")
            handle.write(f"{normalized}\n")
            universe_file = handle.name

        try:
            market_result = run_market_research(
                provider=market_provider,
                financial_provider=financial_provider,
                universe_file=universe_file,
                benchmark_symbol=self._benchmark_symbol,
                start_date=market_start,
                end_date=end_date,
                financial_start_date=financial_start,
                max_workers=1,
            )
        finally:
            Path(universe_file).unlink(missing_ok=True)

        if not market_result.results:
            raise RuntimeError(
                f"No usable validated market data was returned for {normalized}."
            )

        analysis = market_result.results[0]
        market_key = (normalized, market_start, end_date)
        market_ingestion = market_provider.results.get(market_key)

        if market_ingestion is None or not market_ingestion.accepted:
            raise RuntimeError(
                f"No accepted market observations were returned for {normalized}."
            )

        financial_key = (normalized, financial_start, end_date)
        financials = financial_provider.results.get(financial_key, [])

        market_provenance = DataProvenance(
            source="yahoo_finance_market",
            source_url=None,
            retrieved_at=captured_at,
            published_at=None,
            available_at=captured_at,
            dataset_id="yahoo_finance_chart",
            record_id=f"{normalized}_market_{captured_at.isoformat()}",
        )
        financial_provenance = DataProvenance(
            source="yahoo_finance_financials",
            source_url=None,
            retrieved_at=captured_at,
            published_at=None,
            available_at=captured_at,
            dataset_id="yahoo_finance_fundamentals",
            record_id=f"{normalized}_financials_{captured_at.isoformat()}",
        )

        market_observation = build_market_observations(
            symbol=normalized,
            bars=market_ingestion.accepted,
            available_at=captured_at,
        )[-1]
        market_context = market_observation_to_context(
            market_observation,
        )
        financial_context = self._financial_context(financials)

        context_result = ResearchContextBuilder().build(
            symbol=normalized,
            as_of=captured_at,
            observations=(
                ContextObservation(
                    value=dict(market_context.observations),
                    provenance=market_provenance,
                    domain="market",
                    observation_id=market_provenance.record_id or "market",
                ),
                ContextObservation(
                    value=financial_context,
                    provenance=financial_provenance,
                    domain="fundamentals",
                    observation_id=(
                        financial_provenance.record_id or "financials"
                    ),
                ),
            ),
        )

        feature_snapshot = FeatureSnapshotBuilder().build(
            context_result.context,
            calculated_at=captured_at,
            provenance_ids=(
                market_provenance.record_id or "",
                financial_provenance.record_id or "",
            ),
        )

        report = run_company_research(
            symbol=normalized,
            as_of=captured_at,
            features=list(feature_snapshot.features),
            trend_summaries=analyze_financial_trends(financials),
            company_snapshot=analysis.company_intelligence,
            financial_snapshots=financials,
            market_snapshot=analysis.market_snapshot,
            provenance_ids=(
                financial_provenance.record_id or "",
                market_provenance.record_id or "",
            ),
        )

        return RealCompanyResearchResult(
            analysis=analysis,
            report=report,
            feature_snapshot=feature_snapshot,
            context_result=context_result,
            market_ingestion=market_ingestion,
            financial_record_count=len(financials),
            financial_snapshots=tuple(financials),
            market_provenance=market_provenance,
            financial_provenance=financial_provenance,
            retrieved_at=captured_at,
        )

    @staticmethod
    def _financial_context(financials: list) -> dict[str, object]:
        if not financials:
            return {}

        ordered = sorted(
            financials,
            key=lambda snapshot: snapshot.period_end,
        )
        current = ordered[-1]
        previous = ordered[-2] if len(ordered) > 1 else None
        values = current.model_dump()
        values.pop("symbol", None)
        values.pop("period_end", None)

        if previous is not None:
            for name, value in previous.model_dump().items():
                if name not in {"symbol", "period_end"}:
                    values[f"previous_{name}"] = value

        return values
