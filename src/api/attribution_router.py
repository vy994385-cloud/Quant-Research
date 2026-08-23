"""
Price attribution research API routes.

Exposes price-move attribution data through typed contracts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from src.api.contracts import (
    CompanyAttributionContract,
    ContractAttributionCandidate,
    ContractPriceAttribution,
    ContractPriceMove,
)
from src.api.query_utils import company_identity, parse_as_of


def _serialize_price_move(pm) -> ContractPriceMove | None:
    if pm is None:
        return None
    return ContractPriceMove(
        from_date=pm.from_date,
        to_date=pm.to_date,
        from_close=pm.from_close,
        to_close=pm.to_close,
        absolute_change=pm.absolute_change,
        percentage_change=pm.percentage_change,
        direction=pm.direction,
        trading_days=pm.trading_days,
    )


def _serialize_candidate(c) -> ContractAttributionCandidate:
    return ContractAttributionCandidate(
        candidate_id=c.candidate_id,
        category=c.category,
        direction=c.direction,
        confidence=c.confidence,
        title=c.title,
        description=c.description,
        supporting_evidence=list(c.supporting_evidence),
        confidence_score=c.confidence_score,
        explanation=c.explanation,
    )


def _serialize_attribution(result) -> ContractPriceAttribution:
    return ContractPriceAttribution(
        symbol=result.symbol,
        as_of=result.as_of,
        price_move=_serialize_price_move(result.price_move),
        candidates=[_serialize_candidate(c) for c in result.candidates],
        total_candidates=result.total_candidates,
        high_confidence_count=result.high_confidence_count,
        medium_confidence_count=result.medium_confidence_count,
        low_confidence_count=result.low_confidence_count,
        coverage=result.coverage,
        notes=list(result.notes),
        disclaimer=result.disclaimer,
    )


def create_attribution_router() -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/companies",
        tags=["attribution"],
    )

    @router.get(
        "/{symbol}/price-attribution",
        response_model=CompanyAttributionContract,
    )
    async def get_price_attribution(
        symbol: str,
        as_of: str | None = Query(
            None,
            description="Point-in-time date (ISO format). Defaults to latest.",
        ),
        lookback_days: int = Query(
            30,
            description="Lookback period in calendar days.",
            ge=1,
            le=365,
        ),
    ) -> CompanyAttributionContract:
        """
        Price-move attribution for a company.

        Returns evidence-based candidate explanations for the
        observed price movement. Attribution is correlational,
        never causal.
        """
        from src.analysis.price_attribution import attribute_price_move
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

        start_date = end_date - timedelta(days=lookback_days + 30)

        bars = provider.get_daily_prices(symbol, start_date, end_date)

        result = attribute_price_move(
            bars=bars,
            symbol=symbol,
            as_of=as_of_dt,
            lookback_days=lookback_days,
        )

        company_info = company_identity(symbol, as_of=as_of_dt)

        return CompanyAttributionContract(
            company=company_info,
            attribution=_serialize_attribution(result),
        )

    return router
