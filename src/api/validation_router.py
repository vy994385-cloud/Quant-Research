"""
L6 backtest / validation API routes.

Small, focused APIRouter exposing deterministic backtest and
ranking-validation results through explicit response contracts.

The router never talks to the network: it serves the recorded
market-data fixtures and runs deterministic backtest + validation.
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.api.contracts import CompanyRankingsContract
from src.api.errors import UnknownCompanyError
from src.api.query_utils import company_info, normalize_horizon, parse_as_of
from src.api.recorded_research import RecordedCompanyResearchService
from src.api.recorded_validation import RecordedValidationService
from src.api.validation_contracts import (
    CompanyBacktestContract,
    UniverseValidationContract,
)


def _company_info(
    service: RecordedCompanyResearchService,
    symbol: str,
) -> dict:
    return company_info(service, symbol)


def create_validation_router(
    *,
    research_service: RecordedCompanyResearchService | None = None,
    validation_service: RecordedValidationService | None = None,
) -> APIRouter:
    """
    Build the L6 backtest / validation API router.

    Services default to the recorded data path. Tests inject
    services backed by temporary fixtures.
    """

    research_svc = research_service or RecordedCompanyResearchService()
    validation_svc = validation_service or RecordedValidationService(
        research_service=research_svc,
    )

    router = APIRouter(
        prefix="/api/v1",
        tags=["backtest validation"],
    )

    @router.get(
        "/companies/{symbol}/backtest",
        response_model=CompanyBacktestContract,
    )
    def company_backtest(
        symbol: str,
        horizon: str = Query(
            default="LONG_TERM",
            description="Ranking horizon (INTRADAY, SWING, LONG_TERM).",
        ),
        as_of: str | None = Query(
            default=None,
            description=(
                "Optional point-in-time timestamp (ISO 8601, "
                "timezone-aware). Defaults to the recorded as_of."
            ),
        ),
    ) -> dict:
        normalized = research_svc.validate_company(symbol)
        normalized_horizon = normalize_horizon(horizon)
        captured_at = parse_as_of(as_of)

        result = validation_svc.run(
            normalized,
            normalized_horizon,
            as_of=captured_at,
        )

        return {
            "company": _company_info(research_svc, normalized),
            "horizon": result["horizon"],
            "as_of": result["as_of"],
            "backtest": result["backtest"],
            "backtest_validation": result["backtest_validation"],
            "validation_quality": result["validation_quality"],
            "validation_report": result["validation_report"],
            "windows": result["windows"],
            "strategy_description": result["strategy_description"],
            "data_coverage": result["data_coverage"],
            "notes": result["notes"],
        }

    @router.get(
        "/validation/{horizon}",
        response_model=UniverseValidationContract,
    )
    def universe_validation(
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
        normalized_horizon = normalize_horizon(horizon)
        captured_at = parse_as_of(as_of)

        selected: tuple[str, ...] | None = None

        if symbols:
            selected_parts: list[str] = []
            for raw in symbols.split(","):
                s = raw.strip().upper()
                if not s:
                    continue
                research_svc.validate_company(s)
                selected_parts.append(s)
            selected = tuple(dict.fromkeys(selected_parts))

        results = validation_svc.run_universe(
            normalized_horizon,
            as_of=captured_at,
            symbols=selected,
        )

        serialized = []
        for result in results:
            serialized.append({
                "company": _company_info(
                    research_svc, result["symbol"]
                ),
                "horizon": result["horizon"],
                "as_of": result["as_of"],
                "backtest": result["backtest"],
                "backtest_validation": result["backtest_validation"],
                "validation_quality": result["validation_quality"],
                "validation_report": result["validation_report"],
                "windows": result["windows"],
                "strategy_description": result["strategy_description"],
                "data_coverage": result["data_coverage"],
                "notes": result["notes"],
            })

        return {
            "as_of": captured_at.isoformat() if captured_at else (
                results[0]["as_of"] if results else None
            ),
            "horizon": normalized_horizon,
            "count": len(serialized),
            "results": serialized,
        }

    return router


from src.api.query_utils import SUPPORTED_HORIZONS

__all__ = [
    "SUPPORTED_HORIZONS",
    "create_validation_router",
]
