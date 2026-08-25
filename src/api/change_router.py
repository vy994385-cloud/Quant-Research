"""
Research Change Radar / Evidence Delta / Context Snapshot router.

Exposes the recorded-path change-detection engines built on
``src.research.change``. Every endpoint:

- is deterministic (same inputs -> identical output);
- is PIT-safe (baseline must precede current; replay honors as_of);
- reports only what changed, what appeared, and what disappeared —
  never scores, ranks, winners, or recommendations.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from src.api.errors import MalformedRequestError
from src.api.query_utils import parse_as_of
from src.api.recorded_research import RecordedCompanyResearchService
from src.verification.real_data import COMPANIES
from src.research.change import (
    CalendarResponse,
    CoverageDeltaReport,
    EvidenceDeltaReport,
    ResearchChange,
    ResearchContextSnapshot,
    build_calendar,
    build_context_snapshot,
    build_coverage_delta,
    build_evidence_delta,
    build_symbol_changes,
    parse_context_id,
)


class ResearchChangesResponse(BaseModel):
    """What changed for one company between two as_of moments."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    baseline_as_of: datetime
    current_as_of: datetime
    change_count: int = Field(ge=0)
    changes: tuple[ResearchChange, ...]


def _parse_as_of_param(
    value: str | None,
    name: str,
) -> datetime | None:
    try:
        return parse_as_of(value)
    except Exception as exc:
        raise MalformedRequestError(
            f"{name} must be an ISO 8601 timestamp",
            details={name: value},
        ) from None


def _require_pair(
    baseline: datetime | None,
    current: datetime | None,
) -> tuple[datetime, datetime]:
    if current is None:
        raise MalformedRequestError(
            "current_as_of is required (ISO 8601, timezone-aware)",
        )
    if baseline is None:
        raise MalformedRequestError(
            "baseline_as_of is required (ISO 8601, timezone-aware)",
        )
    if baseline >= current:
        raise MalformedRequestError(
            "baseline_as_of must be strictly earlier than current_as_of",
            details={
                "baseline_as_of": baseline.isoformat(),
                "current_as_of": current.isoformat(),
            },
        )
    return baseline, current


def create_change_router(
    *,
    service: RecordedCompanyResearchService | None = None,
) -> APIRouter:
    """Build the research-change router."""

    service = service or RecordedCompanyResearchService()

    router = APIRouter(
        prefix="/api/v1",
        tags=["research change radar"],
    )

    @router.get("/research-changes", response_model=ResearchChangesResponse)
    def research_changes(
        symbol: str = Query(min_length=1),
        baseline_as_of: str | None = Query(default=None),
        current_as_of: str | None = Query(default=None),
    ) -> ResearchChangesResponse:
        base, curr = _require_pair(
            _parse_as_of_param(baseline_as_of, "baseline_as_of"),
            _parse_as_of_param(current_as_of, "current_as_of"),
        )
        before = service.run(symbol, as_of=base)
        after = service.run(symbol, as_of=curr)
        changes = build_symbol_changes(before, after)
        return ResearchChangesResponse(
            symbol=symbol.strip().upper(),
            baseline_as_of=base,
            current_as_of=curr,
            change_count=len(changes),
            changes=tuple(changes),
        )

    @router.get(
        "/research-delta",
        response_model=EvidenceDeltaReport,
    )
    def research_delta(
        symbol: str = Query(min_length=1),
        baseline_as_of: str | None = Query(default=None),
        current_as_of: str | None = Query(default=None),
    ) -> EvidenceDeltaReport:
        base, curr = _require_pair(
            _parse_as_of_param(baseline_as_of, "baseline_as_of"),
            _parse_as_of_param(current_as_of, "current_as_of"),
        )
        before = service.run(symbol, as_of=base)
        after = service.run(symbol, as_of=curr)
        return build_evidence_delta(before, after)

    @router.get(
        "/coverage/delta",
        response_model=CoverageDeltaReport,
    )
    def coverage_delta(
        symbol: str = Query(min_length=1),
        baseline_as_of: str | None = Query(default=None),
        current_as_of: str | None = Query(default=None),
    ) -> CoverageDeltaReport:
        base, curr = _require_pair(
            _parse_as_of_param(baseline_as_of, "baseline_as_of"),
            _parse_as_of_param(current_as_of, "current_as_of"),
        )
        before = service.run(symbol, as_of=base)
        after = service.run(symbol, as_of=curr)
        return build_coverage_delta(before, after)

    @router.get(
        "/research-context/{context_id}",
        response_model=ResearchContextSnapshot,
    )
    def research_context(context_id: str) -> ResearchContextSnapshot:
        try:
            symbol, as_of = parse_context_id(context_id)
        except ValueError as exc:
            raise MalformedRequestError(
                "invalid research-context id",
                details={"context_id": context_id},
            ) from None
        from src.verification.real_data import COMPANIES
        result = service.run(symbol, as_of=as_of)
        snapshot = build_context_snapshot(
            result,
            universe=tuple(sorted(COMPANIES)),
            requested_as_of=as_of,
        )
        if snapshot.context_id != context_id:
            raise MalformedRequestError(
                "research-context id does not match replayed state",
                details={"context_id": context_id},
            )
        return snapshot

    @router.get("/evidence/conflicts", response_model=list)
    def evidence_conflicts(
        symbol: str = Query(min_length=1),
        as_of: str | None = Query(default=None),
    ) -> list[dict]:
        when = _parse_as_of_param(as_of, "as_of")
        result = service.run(symbol, as_of=when)
        intel = result.intelligence
        conflicts = (
            list(intel.conflicts)
            if intel is not None and intel.conflicts
            else []
        )
        # Both sides are always returned; no side is ever a winner.
        return [conflict.model_dump(mode="json") for conflict in conflicts]

    @router.get("/calendar", response_model=CalendarResponse)
    def calendar(
        symbols: str = Query(default="all"),
        range_from: str | None = Query(default=None),
        range_to: str | None = Query(default=None),
    ) -> CalendarResponse:
        from_dt = _parse_as_of_param(range_from, "range_from")
        to_dt = _parse_as_of_param(range_to, "range_to")
        if from_dt is None or to_dt is None:
            raise MalformedRequestError(
                "range_from and range_to are required (ISO 8601)",
            )
        if from_dt > to_dt:
            raise MalformedRequestError(
                "range_from must not be after range_to",
            )

        if symbols.strip().lower() == "all":
            requested = list(COMPANIES)
        else:
            requested = [
                part.strip().upper()
                for part in symbols.split(",")
                if part.strip()
            ]
            if not requested:
                raise MalformedRequestError(
                    "symbols must be a comma-separated list or 'all'",
                )

        results_by_symbol: dict[str, object] = {}
        for sym in requested:
            results_by_symbol[sym] = service.run(sym, as_of=to_dt)

        return build_calendar(
            results_by_symbol,
            range_from=from_dt,
            range_to=to_dt,
        )

    return router
