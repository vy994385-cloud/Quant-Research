"""
O-TRACK capability exposure router.

Exposes already-built deterministic research engines through the
existing v1 API architecture. Every endpoint:

- runs an existing engine (no new analysis, no duplicate contracts —
  engine pydantic models are reused directly as response models);
- is deterministic (same inputs -> identical output);
- is PIT-safe (as_of honored; historical search keeps only
  provably-knowable evidence);
- is null-safe (missing data stays null);
- adds no scores, rankings, winners, or recommendations.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict, Field

from src.api.errors import MalformedRequestError
from src.api.query_utils import parse_as_of
from src.api.recorded_research import RecordedCompanyResearchService
from src.api.serializers import research_contract
from src.research.comparison import CompanyComparison, build_company_comparison
from src.research.discovery_feed import (
    DiscoveryFeed,
    FeedItemType,
    TrendingResult,
    build_discovery_feed,
    compute_trending,
)
from src.research.evidence import build_evidence_lineage
from src.research.evidence.search import (
    EvidenceSearchHit,
    EvidenceSearchQuery,
    search_evidence,
)
from src.research.export import ExportPackage, build_export_package
from src.screener.engine import (
    InvalidScreenError,
    execute_screen,
)
from src.screener.fields import (
    FIELD_REGISTRY,
    extract_company_fields,
)
from src.screener.results import (
    ScreenExecutionOutput,
    build_screen_output,
)


# ---------------------------------------------------------------------------
# Response envelopes (composition over existing engine models only)
# ---------------------------------------------------------------------------


class ScreenerFieldSpec(BaseModel):
    """One screener field exposed for filter/column discovery."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    category: str
    label: str
    description: str
    value_type: str
    unit: str | None = None
    available: bool
    availability_note: str | None = None


class ScreenerFieldCatalog(BaseModel):
    """Canonical catalog of real screener fields."""

    model_config = ConfigDict(extra="forbid")

    fields: tuple[ScreenerFieldSpec, ...] = ()
    available_count: int = Field(ge=0)
    unavailable_count: int = Field(ge=0)


class EvidenceSearchResponse(BaseModel):
    """Deterministic lexical evidence search across the universe."""

    model_config = ConfigDict(extra="forbid")

    query: EvidenceSearchQuery
    items: tuple[EvidenceSearchHit, ...] = ()
    hit_count: int = Field(ge=0)
    searched_count: int = Field(ge=0)
    symbols_searched: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class ScreenerRunRequest(BaseModel):
    """POST body: one screen definition plus optional columns."""

    model_config = ConfigDict(extra="forbid")

    definition: dict[str, Any]
    columns: list[str] | None = None


def _hit_order_key(hit: EvidenceSearchHit):
    stamp = (
        hit.published_at
        or hit.observation_at
        or hit.available_at
    )
    stamp_ts = stamp.timestamp() if stamp is not None else 0.0
    return (-stamp_ts, hit.evidence_id)


def create_capability_router(
    *,
    service: RecordedCompanyResearchService | None = None,
) -> APIRouter:
    """Build the O-track capability exposure router."""

    service = service or RecordedCompanyResearchService()

    router = APIRouter(
        prefix="/api/v1",
        tags=["research capability"],
    )

    def _captured(as_of_str: str | None) -> datetime:
        captured = parse_as_of(as_of_str)
        if captured is None:
            from src.api.recorded_research import DEFAULT_AS_OF

            captured = DEFAULT_AS_OF
        return captured

    def _universe_results(captured: datetime) -> dict[str, object]:
        results: dict[str, object] = {}
        for symbol in service.companies:
            if not service.research_available(symbol):
                continue
            results[symbol] = service.run(
                symbol, as_of=captured
            )
        return dict(sorted(results.items()))

    def _lineage_for(result):
        intel = result.intelligence
        intel_items = intel.items if intel is not None else ()
        return build_evidence_lineage(
            symbol=result.company,
            as_of=result.as_of,
            evidence_items=result.evidence_items,
            intel_items=intel_items,
            pit_filter=True,
        )

    # ── Discover ──────────────────────────────────────────────────

    @router.get(
        "/discovery",
        response_model=DiscoveryFeed,
    )
    def discovery_feed(
        as_of: str | None = Query(default=None),
        item_types: str | None = Query(
            default=None,
            description=(
                "Comma-separated feed item types to include "
                "(defaults to all types)."
            ),
        ),
        limit_per_symbol: int | None = Query(
            default=None,
            ge=1,
        ),
    ) -> DiscoveryFeed:
        captured = _captured(as_of)

        type_filter: tuple[FeedItemType, ...] | None = None
        if item_types:
            wanted = [
                part.strip().upper()
                for part in item_types.split(",")
                if part.strip()
            ]
            valid = {t.value for t in FeedItemType}
            unknown = [t for t in wanted if t not in valid]
            if unknown:
                raise MalformedRequestError(
                    "unknown discovery feed item type",
                    details={
                        "unknown": sorted(set(unknown)),
                        "supported": sorted(valid),
                    },
                )
            type_filter = tuple(FeedItemType(t) for t in wanted)

        feed = build_discovery_feed(
            list(_universe_results(captured).values()),
            as_of=captured,
            item_types=type_filter,
            limit_per_symbol=limit_per_symbol,
        )
        return feed

    @router.get(
        "/discovery/trending",
        response_model=TrendingResult,
    )
    def discovery_trending(
        as_of: str | None = Query(default=None),
        window_days: int = Query(default=30, ge=1, le=365),
    ) -> TrendingResult:
        captured = _captured(as_of)
        feed = build_discovery_feed(
            list(_universe_results(captured).values()),
            as_of=captured,
        )
        return compute_trending(feed, window_days=window_days)

    # ── Screener ──────────────────────────────────────────────────

    @router.get(
        "/screener/fields",
        response_model=ScreenerFieldCatalog,
    )
    def screener_fields() -> ScreenerFieldCatalog:
        specs = tuple(
            ScreenerFieldSpec(
                name=definition.name,
                category=definition.category.value,
                label=definition.label,
                description=definition.description,
                value_type=definition.value_type,
                unit=definition.unit,
                available=definition.available,
                availability_note=definition.availability_note,
            )
            for definition in sorted(
                FIELD_REGISTRY.values(), key=lambda d: d.name
            )
        )
        return ScreenerFieldCatalog(
            fields=specs,
            available_count=sum(1 for s in specs if s.available),
            unavailable_count=sum(1 for s in specs if not s.available),
        )

    @router.post(
        "/screener",
        response_model=ScreenExecutionOutput,
    )
    def run_screener(request: ScreenerRunRequest) -> ScreenExecutionOutput:
        captured = _captured(None)

        try:
            from src.screener.engine import ScreenDefinition

            definition = ScreenDefinition.from_dict(
                request.definition
            )

            field_rows = {
                symbol: extract_company_fields(result)
                for symbol, result in _universe_results(
                    captured
                ).items()
            }

            execution = execute_screen(definition, field_rows)
            return build_screen_output(
                definition,
                execution,
                field_rows,
                requested_columns=request.columns,
                company_names={
                    s: service.company_name(s)
                    for s in field_rows
                },
                sectors=dict(service.sectors),
            )
        except InvalidScreenError as exc:
            raise MalformedRequestError(
                exc.message,
                details=dict(exc.details),
            ) from None

    # ── Compare ───────────────────────────────────────────────────

    @router.get(
        "/companies/compare",
        response_model=CompanyComparison,
    )
    def compare_companies(
        symbols: str = Query(
            description=(
                "Comma-separated list of two or more distinct "
                "company symbols."
            ),
        ),
        as_of: str | None = Query(default=None),
    ) -> CompanyComparison:
        captured = _captured(as_of)

        requested = [
            part.strip().upper()
            for part in symbols.split(",")
            if part.strip()
        ]

        validated: list[str] = []
        for symbol in requested:
            normalized = service.validate_company(symbol)
            if normalized not in validated:
                validated.append(normalized)

        if len(validated) < 2:
            raise MalformedRequestError(
                "comparison requires at least two distinct companies",
                details={"symbols": validated},
            )

        results = [service.run(s, as_of=captured) for s in validated]

        return build_company_comparison(
            results,
            as_of=captured,
            company_names={
                s: service.company_name(s) for s in validated
            },
        )

    # ── Evidence search ───────────────────────────────────────────

    @router.get(
        "/evidence/search",
        response_model=EvidenceSearchResponse,
    )
    def evidence_search(
        q: str = Query(default="", description="Lexical AND terms."),
        symbol: str | None = Query(default=None),
        category: str | None = Query(default=None),
        source_id: str | None = Query(default=None),
        published_from: date | None = Query(default=None),
        published_to: date | None = Query(default=None),
        as_of: str | None = Query(default=None),
    ) -> EvidenceSearchResponse:
        captured = parse_as_of(as_of)

        if symbol is not None:
            targets = [service.validate_company(symbol)]
        else:
            targets = [
                s for s in service.companies
                if service.research_available(s)
            ]

        query = EvidenceSearchQuery(
            text_terms=tuple(
                part
                for part in q.split()
                if part
            ),
            symbol=symbol.upper() if symbol else None,
            category=category,
            source_id=source_id,
            published_from=published_from,
            published_to=published_to,
            as_of=captured,
        )

        hits: list[EvidenceSearchHit] = []
        searched = 0
        notes: list[str] = []

        for target in targets:
            result = service.run(target, as_of=captured)
            lineage = _lineage_for(result)

            outcome = search_evidence(
                lineage,
                text=q,
                symbol=None,
                category=category,
                source_id=source_id,
                published_from=published_from,
                published_to=published_to,
                as_of=captured,
            )

            searched += outcome.searched_count
            hits.extend(outcome.hits)
            notes.extend(outcome.notes)

        hits.sort(key=_hit_order_key)

        return EvidenceSearchResponse(
            query=query,
            items=tuple(hits),
            hit_count=len(hits),
            searched_count=searched,
            symbols_searched=tuple(sorted(targets)),
            notes=tuple(notes[:1]) if notes else (),
        )

    # ── Export ────────────────────────────────────────────────────

    @router.get(
        "/companies/{symbol}/export",
        response_model=ExportPackage,
    )
    def export_company(
        symbol: str,
        as_of: str | None = Query(default=None),
    ) -> ExportPackage:
        normalized = service.validate_company(symbol)
        captured = _captured(as_of)
        result = service.run(normalized, as_of=captured)

        research_payload = research_contract(
            result,
            company_name=service.company_name(normalized),
        )

        fields_row = extract_company_fields(result)
        fields_row = {"symbol": normalized, **fields_row}

        package = build_export_package(
            {
                "research.json": research_payload,
                "screener_fields.csv": [fields_row],
            },
            as_of=result.as_of,
        )
        return package

    return router


__all__ = ["create_capability_router"]
