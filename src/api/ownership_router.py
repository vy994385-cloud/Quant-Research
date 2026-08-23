"""
Ownership research API routes.

Exposes ownership analysis data through typed contracts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from src.api.contracts import (
    CompanyOwnershipContract,
    ContractOwnershipAnalysis,
    ContractOwnershipPeriod,
    ContractOwnershipSignal,
    ContractOwnershipTrend,
)
from src.api.query_utils import company_identity, parse_as_of


def _serialize_period(p) -> ContractOwnershipPeriod:
    return ContractOwnershipPeriod(
        period_end=p.period_end,
        promoter_pct=p.promoter_pct,
        institutional_pct=p.institutional_pct,
        public_pct=p.public_pct,
        pledge_pct=p.pledge_pct,
        concentration_ratio=p.concentration_ratio,
        coverage_pct=p.coverage_pct,
        evidence_count=p.evidence_count,
    )


def _serialize_trend(t) -> ContractOwnershipTrend:
    return ContractOwnershipTrend(
        metric=t.metric,
        direction=t.direction,
        periods_analyzed=t.periods_analyzed,
        first_period=t.first_period,
        last_period=t.last_period,
        first_value=t.first_value,
        last_value=t.last_value,
        change=t.change,
        change_pct=t.change_pct,
        min_value=t.min_value,
        max_value=t.max_value,
        explanation=t.explanation,
    )


def _serialize_signal(s) -> ContractOwnershipSignal:
    return ContractOwnershipSignal(
        signal_id=s.signal_id,
        signal_type=s.signal_type,
        direction=s.direction,
        severity=s.severity,
        title=s.title,
        description=s.description,
        current_value=s.current_value,
        previous_value=s.previous_value,
        change=s.change,
        evidence_ids=list(s.evidence_ids),
        explanation=s.explanation,
    )


def _serialize_analysis(result) -> ContractOwnershipAnalysis:
    return ContractOwnershipAnalysis(
        symbol=result.symbol,
        as_of=result.as_of,
        snapshot_count=result.snapshot_count,
        periods=[_serialize_period(p) for p in result.periods],
        trends=[_serialize_trend(t) for t in result.trends],
        signals=[_serialize_signal(s) for s in result.signals],
        coverage=result.coverage,
        notes=list(result.notes),
    )


def create_ownership_router() -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/companies",
        tags=["ownership"],
    )

    @router.get(
        "/{symbol}/ownership",
        response_model=CompanyOwnershipContract,
    )
    async def get_ownership_analysis(
        symbol: str,
        as_of: str | None = Query(
            None,
            description="Point-in-time date (ISO format). Defaults to latest.",
        ),
    ) -> CompanyOwnershipContract:
        """
        Ownership analysis for a company.

        Returns ownership breakdown, trends, signals, and
        concentration analysis.
        """
        from src.analysis.ownership_analysis import analyze_ownership
        from src.data.providers.yahoo_ownership import (
            YahooOwnershipProvider,
        )

        provider = YahooOwnershipProvider()

        as_of_dt = (
            datetime.fromisoformat(as_of).replace(tzinfo=timezone.utc)
            if as_of
            else datetime.now(timezone.utc)
        )

        end_date = as_of_dt.date()
        from datetime import date, timedelta

        start_date = end_date - timedelta(days=365 * 5)

        snapshots = provider.get_ownership_snapshots(
            symbol, start_date, end_date
        )

        result = analyze_ownership(
            snapshots=snapshots,
            symbol=symbol,
            as_of=as_of_dt,
        )

        company_info = company_identity(symbol, as_of=as_of_dt)

        return CompanyOwnershipContract(
            company=company_info,
            ownership=_serialize_analysis(result),
        )

    return router
