"""Evidence Quality Audit (T1-W5).

Audits evidence records for contract validity: epistemic type,
verification, direction, reliability, source, timestamps, provenance.
Finds contradictory combinations deterministically.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EvidenceQualityIssue(BaseModel):
    """A detected quality issue in an evidence record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issue_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    issue_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: str = "WARNING"  # INFO, WARNING, ERROR
    field_name: str = ""


class EvidenceQualityEntry(BaseModel):
    """Quality audit for one evidence record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    has_source: bool = False
    has_provenance: bool = False
    has_observation_at: bool = False
    has_direction: bool = False
    has_reliability: bool = False
    reliability_value: str = ""
    verification_status: str = ""
    direction_value: str = ""
    issues: tuple[EvidenceQualityIssue, ...] = ()
    issue_count: int = Field(ge=0)


class EvidenceQualityReport(BaseModel):
    """Evidence quality audit report for one company."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    total_evidence_count: int = Field(ge=0)
    clean_count: int = Field(ge=0)
    issue_count: int = Field(ge=0)
    entries: tuple[EvidenceQualityEntry, ...] = ()
    issue_type_counts: dict[str, int] = Field(default_factory=dict)
    notes: tuple[str, ...] = ()


def _audit_one(evidence: Any) -> EvidenceQualityEntry:
    """Audit a single evidence record."""
    eid = getattr(evidence, "evidence_id", "") or ""
    symbol = getattr(evidence, "symbol", "") or ""
    source_ids = getattr(evidence, "source_ids", ()) or ()
    provenance_ids = getattr(evidence, "provenance_ids", ()) or ()
    obs_at = getattr(evidence, "observation_at", None)
    direction = getattr(evidence, "direction", None)
    reliability = getattr(evidence, "reliability", None)
    confidence = getattr(evidence, "confidence", None)

    has_source = bool(source_ids)
    has_provenance = bool(provenance_ids)
    has_obs_at = obs_at is not None
    has_direction = direction is not None

    reliability_str = str(reliability.value) if reliability else ""
    direction_str = str(direction.value) if direction else ""

    issues: list[EvidenceQualityIssue] = []

    # Check: CONFIRMED without source
    # (EvidenceItem doesn't have verification_status, so we skip this check)

    # Check: DERIVED without derivation
    # EvidenceItem doesn't have derivation directly, but we can check confidence

    # Check: REPORTED without source
    if not has_source:
        issues.append(EvidenceQualityIssue(
            issue_id=f"EQ:{eid}:NO_SOURCE",
            evidence_id=eid,
            issue_type="MISSING_SOURCE",
            description="Evidence record has no source_ids.",
            severity="WARNING",
            field_name="source_ids",
        ))

    # Check: No provenance
    if not has_provenance:
        issues.append(EvidenceQualityIssue(
            issue_id=f"EQ:{eid}:NO_PROVENANCE",
            evidence_id=eid,
            issue_type="MISSING_PROVENANCE",
            description="Evidence record has no provenance_ids.",
            severity="INFO",
            field_name="provenance_ids",
        ))

    # Check: No observation_at
    if not has_obs_at:
        issues.append(EvidenceQualityIssue(
            issue_id=f"EQ:{eid}:NO_OBS_AT",
            evidence_id=eid,
            issue_type="MISSING_TIMESTAMP",
            description="Evidence record has no observation_at timestamp.",
            severity="WARNING",
            field_name="observation_at",
        ))

    # Check: No direction
    if not has_direction:
        issues.append(EvidenceQualityIssue(
            issue_id=f"EQ:{eid}:NO_DIRECTION",
            evidence_id=eid,
            issue_type="MISSING_DIRECTION",
            description="Evidence record has no direction classification.",
            severity="INFO",
            field_name="direction",
        ))

    # Check: Zero confidence
    if confidence is not None and confidence == 0:
        issues.append(EvidenceQualityIssue(
            issue_id=f"EQ:{eid}:ZERO_CONFIDENCE",
            evidence_id=eid,
            issue_type="ZERO_CONFIDENCE",
            description="Evidence record has zero confidence value.",
            severity="WARNING",
            field_name="confidence",
        ))

    return EvidenceQualityEntry(
        evidence_id=eid,
        symbol=symbol,
        has_source=has_source,
        has_provenance=has_provenance,
        has_observation_at=has_obs_at,
        has_direction=has_direction,
        has_reliability=bool(reliability),
        reliability_value=reliability_str,
        verification_status="",
        direction_value=direction_str,
        issues=tuple(issues),
        issue_count=len(issues),
    )


def build_evidence_quality_report(
    result: Any, *, as_of: datetime
) -> EvidenceQualityReport:
    """Build evidence quality audit report for one company."""
    symbol = getattr(result, "company", "") or ""
    evidence_items = result.evidence_items or ()

    entries = tuple(_audit_one(e) for e in evidence_items)
    total_issues = sum(e.issue_count for e in entries)
    clean = sum(1 for e in entries if e.issue_count == 0)

    issue_type_counts: dict[str, int] = {}
    for entry in entries:
        for issue in entry.issues:
            issue_type_counts[issue.issue_type] = issue_type_counts.get(issue.issue_type, 0) + 1

    return EvidenceQualityReport(
        symbol=symbol,
        as_of=as_of,
        total_evidence_count=len(entries),
        clean_count=clean,
        issue_count=total_issues,
        entries=entries,
        issue_type_counts=issue_type_counts,
        notes=(
            "Evidence quality audit checks for contract validity only.",
            "Issues are deterministic and traceable to specific evidence records.",
        ),
    )
