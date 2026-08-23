"""
F7 — Canonical Evidence Lineage router.

Exposes the evidence lineage endpoints. Data is computed from the
recorded research result at the router level.

All endpoints are:
- PIT-safe (as_of parameter honored)
- Deterministic (same input → same output)
- Evidence-backed (no invented data)
- No scores, rankings, recommendations, or trading signals
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Query

from src.api.errors import (
    InvalidAsOfError,
    UnknownCompanyError,
)
from src.api.f7_contracts import (
    CompanyEvidenceContract,
    CompanyEvidenceDetailContract,
)
from src.api.f7_serializers import (
    evidence_detail_contract,
    evidence_lineage_contract,
)
from src.api.query_utils import parse_as_of
from src.api.recorded_research import RecordedCompanyResearchService
from src.research.evidence.lineage import build_evidence_lineage


def create_f7_router(
    *,
    service: RecordedCompanyResearchService | None = None,
) -> APIRouter:
    """Build the F7 canonical evidence lineage router."""

    service = service or RecordedCompanyResearchService()

    router = APIRouter(
        prefix="/api/v1",
        tags=["f7 evidence lineage"],
    )

    def _run(symbol: str, as_of_str: str | None):
        normalized = service.validate_company(symbol)
        captured_at = parse_as_of(as_of_str)
        return service.run(normalized, as_of=captured_at)

    @router.get(
        "/companies/{symbol}/evidence",
        response_model=CompanyEvidenceContract,
    )
    def company_evidence(
        symbol: str,
        as_of: str | None = Query(default=None),
        category: str | None = Query(default=None),
        evidence_kind: str | None = Query(default=None),
        verification_status: str | None = Query(default=None),
        source_id: str | None = Query(default=None),
        confidence_min: float | None = Query(default=None),
        confidence_max: float | None = Query(default=None),
        claim_id: str | None = Query(default=None),
        evidence_id: str | None = Query(default=None),
        limit: int | None = Query(default=None),
    ) -> dict:
        result = _run(symbol, as_of)

        intel = result.intelligence
        intel_items = ()
        if intel is not None:
            intel_items = intel.items

        lineage = build_evidence_lineage(
            symbol=result.company,
            as_of=result.as_of,
            evidence_items=result.evidence_items,
            intel_items=intel_items,
            pit_filter=True,
        )

        # Apply additional filters
        filtered_evidence = _apply_filters(
            lineage.evidence,
            category=category,
            evidence_kind=evidence_kind,
            verification_status=verification_status,
            source_id=source_id,
            confidence_min=confidence_min,
            confidence_max=confidence_max,
            claim_id=claim_id,
            evidence_id=evidence_id,
        )

        # Rebuild lineage with filtered evidence
        from src.research.evidence.models import EvidenceLineage

        filtered_lineage = EvidenceLineage(
            symbol=lineage.symbol,
            as_of=lineage.as_of,
            evidence=filtered_evidence,
            claims=lineage.claims,
            source_profiles=lineage.source_profiles,
            source_records=lineage.source_records,
            epistemic_type_counts=lineage.epistemic_type_counts,
            verification_status_counts=lineage.verification_status_counts,
            evidence_type_counts=lineage.evidence_type_counts,
            direction_counts=lineage.direction_counts,
            total_evidence=len(filtered_evidence),
            total_claims=lineage.total_claims,
            total_sources=lineage.total_sources,
            total_provenance=lineage.total_provenance,
            pit_filtered_count=lineage.pit_filtered_count,
            notes=lineage.notes,
        )

        # Apply limit
        if limit is not None and limit > 0:
            filtered_lineage = EvidenceLineage(
                symbol=filtered_lineage.symbol,
                as_of=filtered_lineage.as_of,
                evidence=filtered_lineage.evidence[:limit],
                claims=filtered_lineage.claims,
                source_profiles=filtered_lineage.source_profiles,
                source_records=filtered_lineage.source_records,
                epistemic_type_counts=filtered_lineage.epistemic_type_counts,
                verification_status_counts=filtered_lineage.verification_status_counts,
                evidence_type_counts=filtered_lineage.evidence_type_counts,
                direction_counts=filtered_lineage.direction_counts,
                total_evidence=min(limit, filtered_lineage.total_evidence),
                total_claims=filtered_lineage.total_claims,
                total_sources=filtered_lineage.total_sources,
                total_provenance=filtered_lineage.total_provenance,
                pit_filtered_count=filtered_lineage.pit_filtered_count,
                notes=filtered_lineage.notes,
            )

        return evidence_lineage_contract(
            filtered_lineage,
            company_name=service.company_name(result.company),
        )

    @router.get(
        "/companies/{symbol}/evidence/{evidence_id}",
        response_model=CompanyEvidenceDetailContract,
    )
    def company_evidence_detail(
        symbol: str,
        evidence_id: str,
        as_of: str | None = Query(default=None),
    ) -> dict:
        result = _run(symbol, as_of)

        intel = result.intelligence
        intel_items = ()
        if intel is not None:
            intel_items = intel.items

        lineage = build_evidence_lineage(
            symbol=result.company,
            as_of=result.as_of,
            evidence_items=result.evidence_items,
            intel_items=intel_items,
            pit_filter=True,
        )

        detail = evidence_detail_contract(
            lineage,
            evidence_id=evidence_id,
            company_name=service.company_name(result.company),
        )

        if detail is None:
            from src.api.errors import ResearchDataUnavailableError

            raise ResearchDataUnavailableError(
                f"evidence item not found: {evidence_id}",
                details={
                    "symbol": result.company,
                    "evidence_id": evidence_id,
                },
            )

        return detail

    return router


def _apply_filters(
    evidence: tuple,
    *,
    category: str | None = None,
    evidence_kind: str | None = None,
    verification_status: str | None = None,
    source_id: str | None = None,
    confidence_min: float | None = None,
    confidence_max: float | None = None,
    claim_id: str | None = None,
    evidence_id: str | None = None,
) -> tuple:
    """Apply query parameter filters to evidence items."""

    filtered = list(evidence)

    if category is not None:
        normalized_category = category.strip().upper()
        filtered = [
            item
            for item in filtered
            if item.category.upper() == normalized_category
        ]

    if evidence_kind is not None:
        normalized_kind = evidence_kind.strip().upper()
        filtered = [
            item
            for item in filtered
            if item.evidence_type.upper() == normalized_kind
        ]

    if verification_status is not None:
        normalized_status = verification_status.strip().upper()
        filtered = [
            item
            for item in filtered
            if item.verification_status.upper() == normalized_status
        ]

    if source_id is not None:
        normalized_source = source_id.strip().lower()
        filtered = [
            item
            for item in filtered
            if normalized_source in [
                s.lower() for s in item.source_ids
            ]
        ]

    if confidence_min is not None:
        min_conf = Decimal(str(confidence_min))
        filtered = [
            item
            for item in filtered
            if Decimal(item.confidence) >= min_conf
        ]

    if confidence_max is not None:
        max_conf = Decimal(str(confidence_max))
        filtered = [
            item
            for item in filtered
            if Decimal(item.confidence) <= max_conf
        ]

    if claim_id is not None:
        normalized_claim = claim_id.strip()
        filtered = [
            item
            for item in filtered
            if normalized_claim in item.evidence_id
        ]

    if evidence_id is not None:
        normalized_evidence = evidence_id.strip()
        filtered = [
            item
            for item in filtered
            if item.evidence_id == normalized_evidence
        ]

    return tuple(filtered)


__all__ = ["create_f7_router"]
