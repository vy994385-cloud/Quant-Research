"""
Analyst intelligence API endpoint.

Exposes analyst recommendations, rating changes, earnings
history, calendar events, and market valuation data.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from src.api.contracts import (
    CompanyAnalystIntelligenceContract,
    ContractAnalystIntelligence,
    ContractAnalystRatingChange,
    ContractAnalystRecommendation,
    ContractCalendarEvent,
    ContractEarningsSurprise,
    ContractMarketValuation,
)
from src.api.errors import UnknownCompanyError
from src.data.providers.yahoo_analyst import YahooAnalystProvider
from src.data.providers.yahoo_profile import YahooProfileProvider

router = APIRouter(
    prefix="/api/v1/companies",
    tags=["Phase 5A: Analyst Intelligence"],
)


@router.get(
    "/{symbol}/analyst-intelligence",
    response_model=CompanyAnalystIntelligenceContract,
)
async def get_analyst_intelligence(
    symbol: str,
) -> CompanyAnalystIntelligenceContract:
    """
    Get analyst intelligence for a company.

    Returns analyst recommendations, rating changes, earnings
    history, calendar events, and market valuation from Yahoo
    Finance quote summary modules.
    """

    normalized = symbol.strip().upper()

    profile_provider = YahooProfileProvider()
    try:
        profile = profile_provider.get_business_profile(normalized)
    except RuntimeError:
        profile = None

    if profile is None:
        raise UnknownCompanyError(
            f"Company {normalized} not found",
            details={"symbol": normalized},
        )

    provider = YahooAnalystProvider()
    intelligence = provider.get_analyst_intelligence(
        normalized
    )

    recommendations = [
        ContractAnalystRecommendation(
            period=r.period,
            strong_buy=r.strong_buy,
            buy=r.buy,
            hold=r.hold,
            sell=r.sell,
            strong_sell=r.strong_sell,
            total_analysts=r.total_analysts,
            consensus_score=(
                str(r.consensus_score)
                if r.consensus_score is not None
                else None
            ),
        )
        for r in intelligence.recommendations
    ]

    rating_changes = [
        ContractAnalystRatingChange(
            firm=rc.firm,
            analyst_name=rc.analyst_name,
            action=rc.action,
            from_grade=rc.from_grade,
            to_grade=rc.to_grade,
            date=str(rc.date) if rc.date else None,
        )
        for rc in intelligence.rating_changes
    ]

    earnings_surprises = [
        ContractEarningsSurprise(
            period_ending=(
                str(es.period_ending)
                if es.period_ending
                else None
            ),
            reported_eps=(
                str(es.reported_eps)
                if es.reported_eps is not None
                else None
            ),
            estimated_eps=(
                str(es.estimated_eps)
                if es.estimated_eps is not None
                else None
            ),
            surprise_amount=(
                str(es.surprise_amount)
                if es.surprise_amount is not None
                else None
            ),
            surprise_percentage=(
                str(es.surprise_percentage)
                if es.surprise_percentage is not None
                else None
            ),
            beat_estimate=es.beat_estimate,
        )
        for es in intelligence.earnings_surprises
    ]

    calendar_events = [
        ContractCalendarEvent(
            event_type=ce.event_type,
            event_date=(
                str(ce.event_date)
                if ce.event_date
                else None
            ),
            description=ce.description,
        )
        for ce in intelligence.calendar_events
    ]

    valuation = None
    if intelligence.valuation:
        v = intelligence.valuation
        valuation = ContractMarketValuation(
            symbol=v.symbol,
            market_cap=(
                str(v.market_cap) if v.market_cap is not None else None
            ),
            enterprise_value=(
                str(v.enterprise_value)
                if v.enterprise_value is not None
                else None
            ),
            trailing_pe=str(v.trailing_pe) if v.trailing_pe is not None else None,
            forward_pe=str(v.forward_pe) if v.forward_pe is not None else None,
            peg_ratio=str(v.peg_ratio) if v.peg_ratio is not None else None,
            price_to_book=(
                str(v.price_to_book) if v.price_to_book is not None else None
            ),
            price_to_sales=(
                str(v.price_to_sales) if v.price_to_sales is not None else None
            ),
            enterprise_to_revenue=(
                str(v.enterprise_to_revenue)
                if v.enterprise_to_revenue is not None
                else None
            ),
            enterprise_to_ebitda=(
                str(v.enterprise_to_ebitda)
                if v.enterprise_to_ebitda is not None
                else None
            ),
            dividend_yield=(
                str(v.dividend_yield) if v.dividend_yield is not None else None
            ),
            trailing_annual_dividend_yield=(
                str(v.trailing_annual_dividend_yield)
                if v.trailing_annual_dividend_yield is not None
                else None
            ),
            beta=str(v.beta) if v.beta is not None else None,
            fifty_two_week_high=(
                str(v.fifty_two_week_high)
                if v.fifty_two_week_high is not None
                else None
            ),
            fifty_two_week_low=(
                str(v.fifty_two_week_low)
                if v.fifty_two_week_low is not None
                else None
            ),
            fifty_day_average=(
                str(v.fifty_day_average)
                if v.fifty_day_average is not None
                else None
            ),
            two_hundred_day_average=(
                str(v.two_hundred_day_average)
                if v.two_hundred_day_average is not None
                else None
            ),
            avg_volume_10d=(
                str(v.avg_volume_10d) if v.avg_volume_10d is not None else None
            ),
            shares_outstanding=(
                str(v.shares_outstanding)
                if v.shares_outstanding is not None
                else None
            ),
            float_shares=(
                str(v.float_shares) if v.float_shares is not None else None
            ),
        )

    return CompanyAnalystIntelligenceContract(
        company={
            "symbol": normalized,
            "company_name": profile.company_name if profile else normalized,
            "sector": profile.sector if profile else None,
        },
        analyst_intelligence=ContractAnalystIntelligence(
            symbol=normalized,
            has_recommendations=intelligence.has_recommendations,
            has_rating_changes=intelligence.has_rating_changes,
            has_earnings_history=intelligence.has_earnings_history,
            recommendations=recommendations,
            rating_changes=rating_changes,
            earnings_surprises=earnings_surprises,
            calendar_events=calendar_events,
            valuation=valuation,
            recommendation_count=intelligence.recommendation_count,
            rating_change_count=intelligence.rating_change_count,
            earnings_surprise_count=intelligence.earnings_surprise_count,
            calendar_event_count=len(calendar_events),
        ),
    )
