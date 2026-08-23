"""
Events research API routes.

Exposes event analysis data through typed contracts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from src.api.contracts import (
    CompanyEventsContract,
    ContractEventAnalysis,
    ContractEventClassification,
    ContractEventCluster,
)
from src.api.query_utils import company_identity, parse_as_of


def _serialize_classification(c) -> ContractEventClassification:
    return ContractEventClassification(
        event_date=c.event_date,
        category=c.category,
        title=c.title,
        description=c.description,
        direction=c.direction,
        materiality=c.materiality,
        impact=c.impact,
        evidence_count=c.evidence_count,
        evidence_ids=list(c.evidence_ids),
    )


def _serialize_cluster(c) -> ContractEventCluster:
    return ContractEventCluster(
        cluster_id=c.cluster_id,
        category=c.category,
        event_count=c.event_count,
        date_range=c.date_range,
        titles=list(c.titles),
        overall_direction=c.overall_direction,
        overall_materiality=c.overall_materiality,
        explanation=c.explanation,
    )


def _serialize_analysis(result) -> ContractEventAnalysis:
    return ContractEventAnalysis(
        symbol=result.symbol,
        as_of=result.as_of,
        event_count=result.event_count,
        classifications=[
            _serialize_classification(c)
            for c in result.classifications
        ],
        clusters=[_serialize_cluster(c) for c in result.clusters],
        category_counts=result.category_counts,
        direction_counts=result.direction_counts,
        coverage=result.coverage,
        notes=list(result.notes),
    )


def create_events_router() -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/companies",
        tags=["events"],
    )

    @router.get(
        "/{symbol}/events",
        response_model=CompanyEventsContract,
    )
    async def get_event_analysis(
        symbol: str,
        as_of: str | None = Query(
            None,
            description="Point-in-time date (ISO format). Defaults to latest.",
        ),
    ) -> CompanyEventsContract:
        """
        Event analysis for a company.

        Returns categorized events, impact assessment, clustering,
        and direction analysis.
        """
        from src.analysis.event_analysis import analyze_events
        from src.data.company.events import CompanyEvent

        as_of_dt = (
            datetime.fromisoformat(as_of).replace(tzinfo=timezone.utc)
            if as_of
            else datetime.now(timezone.utc)
        )

        # Events require an external data provider.
        # For now, we accept an optional events query parameter
        # or return empty analysis.
        events: list[CompanyEvent] = []

        result = analyze_events(
            events=events,
            symbol=symbol,
            as_of=as_of_dt,
        )

        company_info = company_identity(symbol, as_of=as_of_dt)

        return CompanyEventsContract(
            company=company_info,
            events=_serialize_analysis(result),
        )

    return router
