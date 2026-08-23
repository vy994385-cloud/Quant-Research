"""
F7 — Canonical Evidence Lineage serializers.

Serialization functions that convert the internal lineage models
to the API contract dictionaries.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from src.api.query_utils import utc_iso as _utc_iso


def _source_profile(profile) -> dict:
    return {
        "source_id": profile.source_id,
        "name": profile.name,
        "source_type": profile.source_type,
        "tier": profile.tier,
        "domain": profile.domain,
        "official": profile.official,
        "requires_confirmation": profile.requires_confirmation,
        "reliability_tier": profile.reliability_tier,
    }


def _source_record(record) -> dict:
    return {
        "source": record.source,
        "source_url": record.source_url,
        "retrieved_at": _utc_iso(record.retrieved_at),
        "published_at": _utc_iso(record.published_at),
        "available_at": _utc_iso(record.available_at),
        "dataset_id": record.dataset_id,
        "record_id": record.record_id,
        "checksum": record.checksum,
    }


def _evidence_item(item) -> dict:
    return {
        "evidence_id": item.evidence_id,
        "symbol": item.symbol,
        "title": item.title,
        "explanation": item.explanation,
        "evidence_type": item.evidence_type,
        "direction": item.direction,
        "confidence": item.confidence,
        "reliability": item.reliability,
        "epistemic_type": item.epistemic_type.value
        if hasattr(item.epistemic_type, "value")
        else str(item.epistemic_type),
        "verification_status": item.verification_status,
        "observation_at": _utc_iso(item.observation_at),
        "published_at": _utc_iso(item.published_at),
        "available_at": _utc_iso(item.available_at),
        "source_ids": list(item.source_ids),
        "provenance_ids": list(item.provenance_ids),
        "source": _source_profile(item.source_info)
        if item.source_info is not None
        else None,
        "source_records": [
            _source_record(rec) for rec in item.source_records
        ],
        "category": item.category,
        "topic": item.topic,
        "derivation": item.derivation,
    }


def _claim(claim) -> dict:
    return {
        "claim_id": claim.claim_id,
        "symbol": claim.symbol,
        "text": claim.text,
        "category": claim.category,
        "epistemic_type": claim.epistemic_type.value
        if hasattr(claim.epistemic_type, "value")
        else str(claim.epistemic_type),
        "confidence": claim.confidence,
        "verification_status": claim.verification_status,
        "evidence_ids": list(claim.evidence_ids),
        "source_ids": list(claim.source_ids),
        "observation_at": _utc_iso(claim.observation_at),
    }


def evidence_lineage_contract(
    lineage,
    *,
    company_name: str | None,
    as_of_override: str | None = None,
) -> dict[str, Any]:
    """
    Serialize an EvidenceLineage to the API contract dictionary.
    """

    return {
        "company": {
            "symbol": lineage.symbol,
            "company_name": company_name,
            "as_of": as_of_override or _utc_iso(lineage.as_of),
        },
        "evidence_lineage": {
            "symbol": lineage.symbol,
            "as_of": _utc_iso(lineage.as_of),
            "evidence": [
                _evidence_item(item) for item in lineage.evidence
            ],
            "claims": [
                _claim(c) for c in lineage.claims
            ],
            "source_profiles": [
                _source_profile(sp)
                for sp in lineage.source_profiles
            ],
            "source_records": [
                _source_record(sr)
                for sr in lineage.source_records
            ],
            "epistemic_type_counts": dict(
                lineage.epistemic_type_counts
            ),
            "verification_status_counts": dict(
                lineage.verification_status_counts
            ),
            "evidence_type_counts": dict(
                lineage.evidence_type_counts
            ),
            "direction_counts": dict(
                lineage.direction_counts
            ),
            "total_evidence": lineage.total_evidence,
            "total_claims": lineage.total_claims,
            "total_sources": lineage.total_sources,
            "total_provenance": lineage.total_provenance,
            "pit_filtered_count": lineage.pit_filtered_count,
            "notes": list(lineage.notes),
        },
    }


def evidence_detail_contract(
    lineage,
    *,
    evidence_id: str,
    company_name: str | None,
) -> dict[str, Any] | None:
    """
    Serialize a single evidence item with full lineage detail.
    """

    for item in lineage.evidence:
        if item.evidence_id == evidence_id:
            return {
                "company": {
                    "symbol": lineage.symbol,
                    "company_name": company_name,
                    "as_of": _utc_iso(lineage.as_of),
                },
                "evidence_item": _evidence_item(item),
                "related_claims": [
                    _claim(c)
                    for c in lineage.claims
                    if evidence_id in c.evidence_ids
                ],
                "related_evidence": [
                    _evidence_item(other)
                    for other in lineage.evidence
                    if other.evidence_id != evidence_id
                    and (
                        set(other.source_ids) & set(item.source_ids)
                        or set(other.provenance_ids)
                        & set(item.provenance_ids)
                    )
                ],
            }

    return None


__all__ = [
    "evidence_detail_contract",
    "evidence_lineage_contract",
]
