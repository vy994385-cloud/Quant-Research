"""
L3 production research API routes.

Small, focused APIRouter exposing the deterministic recorded research
path through an explicit product contract.

The router never talks to the network: it serves the recorded
verification path (fixtures -> providers -> archive -> acquisition ->
evidence -> report) and honors an explicit, timezone-aware as_of.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from src.api.contracts import (
    CompanyDiscoveryResponse,
    CompanyIntelligenceContract,
    CompanyRankingsContract,
    CompanyResearchContract,
    CompanyTimelineContract,
    CompanyDeepFinancialInsightsContract,
    CompanySourceStatusesContract,
    CompanyHiddenInformationContract,
    UniverseRankingsContract,
)
from src.api.errors import (
    InvalidAsOfError,
    InvalidHorizonError,
    UnknownCompanyError,
)
from src.api.recorded_research import (
    RecordedCompanyResearchService,
)
from src.api.serializers import (
    company_rankings_contract,
    deep_financial_insights_contract,
    discovery_item,
    hidden_information_contract,
    intelligence_contract,
    research_contract,
    source_statuses_contract,
    timeline_contract,
    universe_rankings_contract,
)

SUPPORTED_HORIZONS = ("INTRADAY", "SWING", "LONG_TERM")

_HORIZON_ALIASES = {
    "INTRADAY": "INTRADAY",
    "INTRA": "INTRADAY",
    "SWING": "SWING",
    "LONG_TERM": "LONG_TERM",
    "LONG-TERM": "LONG_TERM",
    "LONGTERM": "LONG_TERM",
}


def parse_as_of(value: str | None) -> datetime | None:
    """Parse and validate an optional as_of query parameter."""

    if value is None:
        return None

    text = value.strip()

    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise InvalidAsOfError(
            "as_of must be an ISO 8601 timestamp",
            details={"as_of": value},
        ) from None

    if parsed.tzinfo is None:
        if "T" in text:
            raise InvalidAsOfError(
                "as_of must include a timezone offset",
                details={"as_of": value},
            )

        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed


def _normalize_horizon(horizon: str) -> str:
    requested = horizon.strip().upper()

    normalized = _HORIZON_ALIASES.get(requested)

    if normalized is None:
        raise InvalidHorizonError(
            "unsupported ranking horizon",
            details={
                "horizon": horizon,
                "supported": list(SUPPORTED_HORIZONS),
            },
        )

    return normalized


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
                    sector=service.company_sector(symbol)
                    or "unknown",
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

    return router


__all__ = [
    "SUPPORTED_HORIZONS",
    "create_research_router",
    "parse_as_of",
]
