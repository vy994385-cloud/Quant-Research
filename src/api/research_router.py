"""
L3 production research API routes.

Small, focused APIRouter exposing the deterministic recorded research
path through an explicit product contract.

The router never talks to the network: it serves the recorded
verification path (fixtures -> providers -> archive -> acquisition ->
evidence -> report) and honors an explicit, timezone-aware as_of.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query

from src.api.query_utils import (
    SUPPORTED_HORIZONS,
    clean_sector,
    parse_as_of,
)

# Re-export for backward compatibility
# (other routers historically imported from here)

from src.api.contracts import (
    CompanyCrossDomainContract,
    CompanyDiscoveryResponse,
    CompanyIntelligenceContract,
    CompanyRankingsContract,
    CompanyResearchContract,
    CompanyResearchGapsContract,
    CompanyTimelineContract,
    CompanyDeepFinancialInsightsContract,
    CompanySourceStatusesContract,
    CompanyHiddenInformationContract,
    UniverseRankingsContract,
)
from src.api.errors import (
    UnknownCompanyError,
)
from src.api.recorded_research import (
    RecordedCompanyResearchService,
)
from src.api.serializers import (
    company_rankings_contract,
    cross_domain_contract,
    deep_financial_insights_contract,
    discovery_item,
    hidden_information_contract,
    intelligence_contract,
    research_contract,
    research_gaps_contract,
    source_statuses_contract,
    timeline_contract,
    universe_rankings_contract,
)

SUPPORTED_HORIZONS  # re-exported from query_utils


def _normalize_horizon(horizon: str) -> str:
    from src.api.query_utils import normalize_horizon
    return normalize_horizon(horizon)


def _select_symbols(service, symbols: str | None) -> tuple[str, ...]:
    if not symbols:
        return service.companies

    selected: list[str] = []

    for raw in symbols.split(","):
        symbol = raw.strip().upper()

        if not symbol:
            continue

        selected.append(service.validate_company(symbol))

    if not selected:
        raise UnknownCompanyError(
            "no symbols were supplied",
            details={"symbols": symbols},
        )

    return tuple(dict.fromkeys(selected))


def _run_all(
    service,
    symbols: tuple[str, ...],
    as_of: datetime | None,
) -> list:
    results = []

    for symbol in symbols:
        results.append(
            service.run(symbol, as_of=as_of)
        )

    return results


def create_research_router(
    *,
    service: RecordedCompanyResearchService | None = None,
) -> APIRouter:
    """
    Build the L3 research API router.

    `service` defaults to the recorded research service writing to
    the repository data archive. Tests inject a service backed by a
    temporary archive.
    """

    service = service or RecordedCompanyResearchService()

    router = APIRouter(
        prefix="/api/v1",
        tags=["research contract"],
    )

    @router.get(
        "/companies",
        response_model=CompanyDiscoveryResponse,
    )
    def list_companies() -> dict:
        results = []

        for symbol in service.companies:
            results.append(
                discovery_item(
                    symbol,
                    # Unknown sector is null — never a sentinel string.
                    sector=clean_sector(service.company_sector(symbol)),
                    company_name=service.company_name(symbol),
                    research_available=(
                        service.research_available(symbol)
                    ),
                )
            )

        return {
            "count": len(results),
            "results": results,
        }

    @router.get(
        "/companies/{symbol}/research",
        response_model=CompanyResearchContract,
    )
    def company_research(
        symbol: str,
        as_of: str | None = Query(
            default=None,
            description=(
                "Optional point-in-time timestamp (ISO 8601, "
                "timezone-aware). Defaults to the recorded as_of."
            ),
        ),
    ) -> dict:
        normalized = service.validate_company(symbol)
        captured_at = parse_as_of(as_of)

        result = service.run(
            normalized,
            as_of=captured_at,
        )

        return research_contract(
            result,
            company_name=service.company_name(normalized),
        )

    @router.get(
        "/companies/{symbol}/intelligence",
        response_model=CompanyIntelligenceContract,
    )
    def company_intelligence(
        symbol: str,
        as_of: str | None = Query(
            default=None,
            description=(
                "Optional point-in-time timestamp (ISO 8601, "
                "timezone-aware). Defaults to the recorded as_of."
            ),
        ),
    ) -> dict:
        normalized = service.validate_company(symbol)
        captured_at = parse_as_of(as_of)

        result = service.run(
            normalized,
            as_of=captured_at,
        )

        return intelligence_contract(
            result,
            company_name=service.company_name(normalized),
        )

    @router.get(
        "/companies/{symbol}/timeline",
        response_model=CompanyTimelineContract,
    )
    def company_timeline(
        symbol: str,
        as_of: str | None = Query(
            default=None,
            description=(
                "Optional point-in-time timestamp (ISO 8601, "
                "timezone-aware). Defaults to the recorded as_of."
            ),
        ),
    ) -> dict:
        normalized = service.validate_company(symbol)
        captured_at = parse_as_of(as_of)

        result = service.run(
            normalized,
            as_of=captured_at,
        )

        return timeline_contract(
            result,
            company_name=service.company_name(normalized),
        )

    @router.get(
        "/companies/{symbol}/rankings",
        response_model=CompanyRankingsContract,
    )
    def company_rankings(
        symbol: str,
        as_of: str | None = Query(
            default=None,
            description=(
                "Optional point-in-time timestamp (ISO 8601, "
                "timezone-aware). Defaults to the recorded as_of."
            ),
        ),
    ) -> dict:
        normalized = service.validate_company(symbol)
        captured_at = parse_as_of(as_of)

        result = service.run(
            normalized,
            as_of=captured_at,
        )

        return company_rankings_contract(
            result,
            company_name=service.company_name(normalized),
        )

    @router.get(
        "/rankings/{horizon}",
        response_model=UniverseRankingsContract,
    )
    def universe_rankings(
        horizon: str,
        as_of: str | None = Query(
            default=None,
            description=(
                "Optional point-in-time timestamp (ISO 8601, "
                "timezone-aware). Defaults to the recorded as_of."
            ),
        ),
        symbols: str | None = Query(
            default=None,
            description=(
                "Optional comma-separated subset of the supported "
                "companies. Defaults to the full verified universe."
            ),
        ),
    ) -> dict:
        normalized_horizon = _normalize_horizon(horizon)
        captured_at = parse_as_of(as_of)

        selected = _select_symbols(service, symbols)

        results = _run_all(
            service,
            selected,
            captured_at,
        )

        return universe_rankings_contract(
            results,
            horizon=normalized_horizon,
            company_names={
                symbol: service.company_name(symbol)
                for symbol in selected
            },
        )

    @router.get(
        "/companies/{symbol}/deep-financial-insights",
        response_model=CompanyDeepFinancialInsightsContract,
    )
    def company_deep_financial_insights(
        symbol: str,
        as_of: str | None = Query(
            default=None,
            description=(
                "Optional point-in-time timestamp (ISO 8601, "
                "timezone-aware). Defaults to the recorded as_of."
            ),
        ),
    ) -> dict:
        normalized = service.validate_company(symbol)
        captured_at = parse_as_of(as_of)

        result = service.run(
            normalized,
            as_of=captured_at,
        )

        return deep_financial_insights_contract(
            result,
            company_name=service.company_name(normalized),
        )

    @router.get(
        "/companies/{symbol}/source-statuses",
        response_model=CompanySourceStatusesContract,
    )
    def company_source_statuses(
        symbol: str,
        as_of: str | None = Query(
            default=None,
            description=(
                "Optional point-in-time timestamp (ISO 8601, "
                "timezone-aware). Defaults to the recorded as_of."
            ),
        ),
    ) -> dict:
        normalized = service.validate_company(symbol)
        captured_at = parse_as_of(as_of)

        result = service.run(
            normalized,
            as_of=captured_at,
        )

        return source_statuses_contract(
            result,
            company_name=service.company_name(normalized),
        )

    @router.get(
        "/companies/{symbol}/hidden-information",
        response_model=CompanyHiddenInformationContract,
    )
    def company_hidden_information(
        symbol: str,
        as_of: str | None = Query(
            default=None,
            description=(
                "Optional point-in-time timestamp (ISO 8601, "
                "timezone-aware). Defaults to the recorded as_of."
            ),
        ),
    ) -> dict:
        normalized = service.validate_company(symbol)
        captured_at = parse_as_of(as_of)

        result = service.run(
            normalized,
            as_of=captured_at,
        )

        return hidden_information_contract(
            result,
            company_name=service.company_name(normalized),
        )

    @router.get(
        "/companies/{symbol}/cross-domain",
        response_model=CompanyCrossDomainContract,
    )
    def company_cross_domain(
        symbol: str,
        as_of: str | None = Query(
            default=None,
            description=(
                "Optional point-in-time timestamp (ISO 8601, "
                "timezone-aware). Defaults to the recorded as_of."
            ),
        ),
    ) -> dict:
        normalized = service.validate_company(symbol)
        captured_at = parse_as_of(as_of)

        result = service.run(
            normalized,
            as_of=captured_at,
        )

        return cross_domain_contract(
            result,
            company_name=service.company_name(normalized),
        )

    @router.get(
        "/companies/{symbol}/research-gaps",
        response_model=CompanyResearchGapsContract,
    )
    def company_research_gaps(
        symbol: str,
        as_of: str | None = Query(
            default=None,
            description=(
                "Optional point-in-time timestamp (ISO 8601, "
                "timezone-aware). Defaults to the recorded as_of."
            ),
        ),
    ) -> dict:
        normalized = service.validate_company(symbol)
        captured_at = parse_as_of(as_of)

        result = service.run(
            normalized,
            as_of=captured_at,
        )

        return research_gaps_contract(
            result,
            company_name=service.company_name(normalized),
        )

    return router


__all__ = [
    "SUPPORTED_HORIZONS",
    "create_research_router",
    "parse_as_of",
]
