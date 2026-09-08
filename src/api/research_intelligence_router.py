"""
Research Intelligence API router.

Exposes the T1-W3 research intelligence hardening capabilities:
  - Change Graph
  - Research Test Graph
  - Conflict Explorer 2.0
  - Source Intelligence
  - Historical Replay
  - Financial Quality
  - Business/Tech Evidence
  - Ownership Audit
  - Alert Events
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from src.api.errors import MalformedRequestError
from src.api.query_utils import parse_as_of
from src.api.recorded_research import RecordedCompanyResearchService, COMPANY_NAMES
from src.research.alert_contract import AlertEventContract, build_alert_events
from src.research.business_tech_evidence import (
    BusinessTechReport,
    build_business_tech_evidence,
)
from src.research.change import build_symbol_changes
from src.research.change_graph import ChangeGraph, build_change_graph
from src.research.conflict_explorer import (
    ConflictExplorerReport,
    build_conflict_explorer,
)
from src.research.evidence.lineage import build_evidence_lineage
from src.research.financial_quality import (
    FinancialQualityReport,
    build_financial_quality,
)
from src.research.ownership_audit import OwnershipAuditReport, build_ownership_audit
from src.research.product_builders import build_research_snapshot, build_section_registry
from src.research.replay import FullReplayResult, build_replay
from src.research.section_registry import ResearchSectionRegistry
from src.research.snapshot import ResearchSnapshot
from src.research.source_intelligence import (
    SourceIntelligenceReport,
    build_source_intelligence,
)
from src.research.test_graph import ResearchTestGraph, build_research_test_graph


def _parse_as_of_param(value: str | None, name: str) -> datetime | None:
    try:
        return parse_as_of(value)
    except Exception as exc:
        raise MalformedRequestError(
            f"{name} must be an ISO 8601 timestamp",
            details={name: value},
        ) from None


def _require_as_of(value: str | None, name: str) -> datetime:
    dt = _parse_as_of_param(value, name)
    if dt is None:
        raise MalformedRequestError(f"{name} is required (ISO 8601, timezone-aware)")
    return dt


def create_research_intelligence_router(
    *,
    service: RecordedCompanyResearchService | None = None,
) -> APIRouter:
    """Build the research intelligence router."""

    service = service or RecordedCompanyResearchService()

    router = APIRouter(
        prefix="/api/v1",
        tags=["research intelligence"],
    )

    @router.get("/research/change-graph", response_model=ChangeGraph)
    def change_graph(
        symbol: str = Query(min_length=1),
        baseline_as_of: str | None = Query(default=None),
        current_as_of: str | None = Query(default=None),
    ) -> ChangeGraph:
        base = _require_as_of(baseline_as_of, "baseline_as_of")
        curr = _require_as_of(current_as_of, "current_as_of")
        if base >= curr:
            raise MalformedRequestError("baseline_as_of must be before current_as_of")

        before = service.run(symbol, as_of=base)
        after = service.run(symbol, as_of=curr)
        changes = build_symbol_changes(before, after)
        return build_change_graph(changes, symbol=symbol, as_of=curr)

    @router.get("/research/test-graph", response_model=ResearchTestGraph)
    def test_graph(
        symbol: str = Query(min_length=1),
        as_of: str | None = Query(default=None),
    ) -> ResearchTestGraph:
        when = _require_as_of(as_of, "as_of")
        result = service.run(symbol, as_of=when)
        intel = result.intelligence

        evidence_items = result.evidence_items or ()
        intel_items = intel.items if intel else ()
        source_statuses = intel.source_statuses if intel else ()
        gaps = intel.research_gaps.gaps if intel and intel.research_gaps else ()
        conflicts = intel.conflicts if intel else ()
        deep_fin = intel.deep_financial_insights if intel else None
        fin_periods = ()
        if intel and intel.financial_intelligence:
            fin_periods = intel.financial_intelligence.periods

        evidence_source_ids = set()
        for item in evidence_items:
            evidence_source_ids.update(item.source_ids)

        return build_research_test_graph(
            symbol=symbol,
            as_of=when,
            evidence_items=evidence_items,
            evidence_source_ids=evidence_source_ids,
            financial_periods=fin_periods,
            intel_items=intel_items,
            conflicts=conflicts,
            gaps=gaps,
            source_statuses=source_statuses,
            deep_financial_insights=deep_fin,
        )

    @router.get("/research/conflict-explorer", response_model=ConflictExplorerReport)
    def conflict_explorer(
        symbol: str = Query(min_length=1),
        as_of: str | None = Query(default=None),
    ) -> ConflictExplorerReport:
        when = _require_as_of(as_of, "as_of")
        result = service.run(symbol, as_of=when)
        intel = result.intelligence
        conflicts = intel.conflicts if intel else ()

        return build_conflict_explorer(
            symbol=symbol,
            as_of=when,
            conflicts=conflicts,
        )

    @router.get("/research/source-intelligence", response_model=SourceIntelligenceReport)
    def source_intelligence(
        symbol: str = Query(min_length=1),
        as_of: str | None = Query(default=None),
    ) -> SourceIntelligenceReport:
        when = _require_as_of(as_of, "as_of")
        result = service.run(symbol, as_of=when)
        intel = result.intelligence

        source_statuses = intel.source_statuses if intel else ()
        evidence_items = result.evidence_items or ()

        prov_ids = set()
        for item in evidence_items:
            prov_ids.update(item.provenance_ids)

        return build_source_intelligence(
            symbol=symbol,
            as_of=when,
            source_statuses=source_statuses,
            evidence_items=evidence_items,
            provenance_ids=prov_ids,
        )

    @router.get("/research/replay", response_model=FullReplayResult)
    def research_replay(
        symbol: str = Query(min_length=1),
        as_of_a: str | None = Query(default=None, alias="as_of_a"),
        as_of_b: str | None = Query(default=None, alias="as_of_b"),
    ) -> FullReplayResult:
        when_a = _require_as_of(as_of_a, "as_of_a")
        result_a = service.run(symbol, as_of=when_a)
        result_b = None
        if as_of_b:
            when_b = _require_as_of(as_of_b, "as_of_b")
            result_b = service.run(symbol, as_of=when_b)

        from src.verification.real_data import COMPANIES
        return build_replay(
            result_a,
            result_b,
            universe=tuple(sorted(COMPANIES)),
        )

    @router.get("/research/financial-quality", response_model=FinancialQualityReport)
    def financial_quality(
        symbol: str = Query(min_length=1),
        as_of: str | None = Query(default=None),
    ) -> FinancialQualityReport:
        when = _require_as_of(as_of, "as_of")
        result = service.run(symbol, as_of=when)
        intel = result.intelligence

        fin_periods = ()
        if intel and intel.financial_intelligence:
            fin_periods = intel.financial_intelligence.periods

        prov_ids = set()
        for item in (result.evidence_items or ()):
            prov_ids.update(item.provenance_ids)

        return build_financial_quality(
            symbol=symbol,
            as_of=when,
            financial_periods=fin_periods,
            evidence_items=result.evidence_items or (),
            provenance_ids=prov_ids,
        )

    @router.get("/research/business-tech-evidence", response_model=BusinessTechReport)
    def business_tech(
        symbol: str = Query(min_length=1),
        as_of: str | None = Query(default=None),
    ) -> BusinessTechReport:
        when = _require_as_of(as_of, "as_of")
        result = service.run(symbol, as_of=when)
        intel = result.intelligence

        intel_items = intel.items if intel else ()

        return build_business_tech_evidence(
            symbol=symbol,
            as_of=when,
            intel_items=intel_items,
            evidence_items=result.evidence_items or (),
        )

    @router.get("/research/ownership-audit", response_model=OwnershipAuditReport)
    def ownership_audit(
        symbol: str = Query(min_length=1),
        as_of: str | None = Query(default=None),
    ) -> OwnershipAuditReport:
        when = _require_as_of(as_of, "as_of")
        result = service.run(symbol, as_of=when)
        intel = result.intelligence
        intel_items = intel.items if intel else ()

        return build_ownership_audit(
            symbol=symbol,
            as_of=when,
            intel_items=intel_items,
        )

    @router.get("/research/alert-events", response_model=AlertEventContract)
    def alert_events(
        symbol: str = Query(min_length=1),
        baseline_as_of: str | None = Query(default=None),
        current_as_of: str | None = Query(default=None),
    ) -> AlertEventContract:
        base = _require_as_of(baseline_as_of, "baseline_as_of")
        curr = _require_as_of(current_as_of, "current_as_of")
        if base >= curr:
            raise MalformedRequestError("baseline_as_of must be before current_as_of")

        before = service.run(symbol, as_of=base)
        after = service.run(symbol, as_of=curr)
        changes = build_symbol_changes(before, after)

        ctx_id = None
        try:
            from src.research.change import context_id_for
            ctx_id = context_id_for(symbol, curr)
        except Exception:
            pass

        return build_alert_events(
            symbol=symbol,
            as_of=curr,
            changes=changes,
            context_id=ctx_id,
        )

    @router.get("/research/snapshot", response_model=ResearchSnapshot)
    def research_snapshot(
        symbol: str = Query(min_length=1),
        as_of: str | None = Query(default=None),
    ) -> ResearchSnapshot:
        when = _require_as_of(as_of, "as_of")
        result = service.run(symbol, as_of=when)
        return build_research_snapshot(result, as_of=when)

    @router.get("/research/section-registry", response_model=ResearchSectionRegistry)
    def research_section_registry(
        symbol: str = Query(min_length=1),
        as_of: str | None = Query(default=None),
    ) -> ResearchSectionRegistry:
        when = _require_as_of(as_of, "as_of")
        result = service.run(symbol, as_of=when)
        return build_section_registry(result, as_of=when)

    return router


__all__ = ["create_research_intelligence_router"]
