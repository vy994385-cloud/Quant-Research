"""
F8 — Professional Research Report router.

Exposes the professional report endpoint. Data is computed from the
recorded research result and F7 evidence lineage.

All endpoints are:
- PIT-safe (as_of parameter honored)
- Deterministic (same input → same output)
- Evidence-backed (no invented data)
- No scores, rankings, recommendations, or trading signals
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.api.errors import (
    InvalidAsOfError,
    UnknownCompanyError,
)
from src.api.f8_serializers import professional_report_contract
from src.api.f8_contracts import CompanyProfessionalReportResponse
from src.api.query_utils import parse_as_of
from src.api.recorded_research import RecordedCompanyResearchService
from src.research.evidence.lineage import build_evidence_lineage
from src.research.report.professional import build_professional_report


def create_f8_router(
    *,
    service: RecordedCompanyResearchService | None = None,
) -> APIRouter:
    """Build the F8 professional research report router."""

    service = service or RecordedCompanyResearchService()

    router = APIRouter(
        prefix="/api/v1",
        tags=["f8 professional report"],
    )

    def _run(symbol: str, as_of_str: str | None):
        normalized = service.validate_company(symbol)
        captured_at = parse_as_of(as_of_str)
        return service.run(normalized, as_of=captured_at)

    @router.get(
        "/companies/{symbol}/research-report",
        response_model=CompanyProfessionalReportResponse,
    )
    def company_research_report(
        symbol: str,
        as_of: str | None = Query(default=None),
    ) -> dict:
        result = _run(symbol, as_of)

        intel = result.intelligence
        intel_items = ()
        if intel is not None:
            intel_items = intel.items

        # Build F7 evidence lineage (source of truth)
        lineage = build_evidence_lineage(
            symbol=result.company,
            as_of=result.as_of,
            evidence_items=result.evidence_items,
            intel_items=intel_items,
            pit_filter=True,
        )

        # Extract research gaps from intelligence snapshot
        research_gaps = None
        if intel is not None and hasattr(intel, "research_gaps"):
            research_gaps = intel.research_gaps

        # Build professional report from lineage + full intelligence
        report = build_professional_report(
            lineage=lineage,
            company_name=service.company_name(result.company),
            intel_items=intel_items,
            intelligence=intel,
            research_gaps=research_gaps,
            acquisition=result.acquisition,
        )

        return professional_report_contract(
            report,
            company_name=service.company_name(result.company),
        )

    return router


__all__ = ["create_f8_router"]
