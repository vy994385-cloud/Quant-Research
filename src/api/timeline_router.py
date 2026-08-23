"""
Research timeline API routes.

Exposes the research timeline data through typed contracts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from src.api.contracts import (
    CompanyResearchTimelineContract,
    ContractResearchTimeline,
    ContractResearchTimelineEntry,
    ContractResearchTimelineSummary,
)
from src.api.query_utils import company_identity, parse_as_of


def _serialize_entry(e) -> ContractResearchTimelineEntry:
    return ContractResearchTimelineEntry(
        entry_id=e.entry_id,
        entry_type=e.entry_type,
        date=e.date,
        title=e.title,
        description=e.description,
        direction=e.direction,
        materiality=e.materiality,
        category=e.category,
        supporting_data=dict(e.supporting_data),
        evidence_count=e.evidence_count,
    )


def _serialize_summary(s) -> ContractResearchTimelineSummary:
    return ContractResearchTimelineSummary(
        total_entries=s.total_entries,
        event_count=s.event_count,
        price_count=s.price_count,
        ownership_count=s.ownership_count,
        management_count=s.management_count,
        volume_count=s.volume_count,
        positive_count=s.positive_count,
        negative_count=s.negative_count,
        neutral_count=s.neutral_count,
        high_materiality_count=s.high_materiality_count,
        date_range=s.date_range,
        earliest_date=s.earliest_date,
        latest_date=s.latest_date,
    )


def _serialize_timeline(result) -> ContractResearchTimeline:
    return ContractResearchTimeline(
        symbol=result.symbol,
        as_of=result.as_of,
        entries=[_serialize_entry(e) for e in result.entries],
        summary=_serialize_summary(result.summary),
        notes=list(result.notes),
    )


def create_timeline_router() -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/companies",
        tags=["timeline"],
    )

    @router.get(
        "/{symbol}/research-timeline",
        response_model=CompanyResearchTimelineContract,
    )
    async def get_research_timeline(
        symbol: str,
        as_of: str | None = Query(
            None,
            description="Point-in-time date (ISO format). Defaults to latest.",
        ),
    ) -> CompanyResearchTimelineContract:
        """
        Research timeline for a company.

        Returns a chronological merge of events, price movements,
        ownership changes, management changes, and volume patterns.
        """
        from src.analysis.research_timeline import build_research_timeline
        from src.data.providers.yahoo_provider import (
            YahooFinanceMarketDataProvider,
        )

        provider = YahooFinanceMarketDataProvider()

        as_of_dt = (
            datetime.fromisoformat(as_of).replace(tzinfo=timezone.utc)
            if as_of
            else datetime.now(timezone.utc)
        )

        end_date = as_of_dt.date()
        from datetime import timedelta

        start_date = end_date - timedelta(days=365)

        bars = provider.get_daily_prices(symbol, start_date, end_date)

        result = build_research_timeline(
            symbol=symbol,
            as_of=as_of_dt,
            price_bars=bars,
        )

        company_info = company_identity(symbol, as_of=as_of_dt)

        return CompanyResearchTimelineContract(
            company=company_info,
            timeline=_serialize_timeline(result),
        )

    return router
