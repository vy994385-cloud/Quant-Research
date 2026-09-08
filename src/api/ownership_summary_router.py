"""
Ownership summary API endpoint.

Exposes ownership breakdown with top holders from Yahoo
Finance shareHolderSummary module.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query

from src.api.contracts import (
    CompanyOwnershipSummaryContract,
    ContractOwnershipSummary,
    ContractTopHolder,
)
from src.api.errors import (
    ResearchDataUnavailableError,
)
from src.data.providers.yahoo_ownership import (
    YahooOwnershipProvider,
)
from src.data.providers.yahoo_profile import YahooProfileProvider

router = APIRouter(
    prefix="/api/v1/companies",
    tags=["Phase 5A: Ownership Summary"],
)


@router.get(
    "/{symbol}/ownership-summary",
    response_model=CompanyOwnershipSummaryContract,
)
async def get_ownership_summary(
    symbol: str,
) -> CompanyOwnershipSummaryContract:
    """
    Get complete ownership summary for a company.

    Returns ownership breakdown (promoter, institutional,
    public, insider) and top holders from Yahoo Finance
    shareHolderSummary module.
    """

    from src.api.recorded_research import RecordedCompanyResearchService

    normalized = symbol.strip().upper()

    profile_provider = YahooProfileProvider()
    try:
        profile = profile_provider.get_business_profile(normalized)
    except RuntimeError:
        profile = None

    if profile is None:
        # Live Yahoo data unavailable — return honest empty state
        _svc = RecordedCompanyResearchService()
        _cname = _svc.company_name(normalized)
        return CompanyOwnershipSummaryContract(
            company={
                "symbol": normalized,
                "company_name": _cname or normalized,
                "sector": _svc.company_sector(normalized),
            },
            ownership_summary=ContractOwnershipSummary(
                symbol=normalized,
                period_end="",
            ),
        )

    provider = YahooOwnershipProvider()
    today = date.today()

    summary = provider.get_ownership_summary(
        normalized, today, today
    )

    if summary is None:
        raise ResearchDataUnavailableError(
            f"Ownership summary not available for {normalized}",
            details={"symbol": normalized},
        )

    top_holders = [
        ContractTopHolder(
            holder_name=th.holder_name,
            holder_type=th.holder_type,
            shares_held=(
                str(th.shares_held) if th.shares_held is not None else None
            ),
            share_percentage=(
                str(th.share_percentage)
                if th.share_percentage is not None
                else None
            ),
            date_reported=(
                str(th.date_reported) if th.date_reported is not None else None
            ),
        )
        for th in summary.top_holders
    ]

    return CompanyOwnershipSummaryContract(
        company={
            "symbol": normalized,
            "company_name": profile.company_name if profile else normalized,
            "sector": profile.sector if profile else None,
        },
        ownership_summary=ContractOwnershipSummary(
            symbol=normalized,
            period_end=str(summary.period_end),
            promoter_percentage=str(summary.promoter_percentage) if summary.promoter_percentage is not None else None,
            institutional_percentage=str(summary.institutional_percentage) if summary.institutional_percentage is not None else None,
            public_percentage=str(summary.public_percentage) if summary.public_percentage is not None else None,
            insider_percentage=str(summary.insider_percentage) if summary.insider_percentage is not None else None,
            top_holders=top_holders,
            has_top_holders=summary.has_top_holders,
            holder_count=summary.holder_count,
        ),
    )
