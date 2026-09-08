"""
Research Snapshot Contract (T1-W4).

Deterministic ResearchSnapshot that consolidates all research outputs
for a company at a given as_of, making the frontend able to render
research without recomputing data independently.

Sections:
- snapshot: company identity + PIT
- changes: what changed
- observations: key observations
- evidence: evidence summary
- financials: financial snapshot
- coverage: coverage status
- conflicts: conflict summary
- gaps: gap summary
- freshness: source freshness
- sources: source summary
- provenance: provenance summary
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.research.vocabulary import (
    ConflictResolution,
    ResearchAvailability,
    ResearchDirection,
    ResearchGapStatus,
    SNAPSHOT_SCHEMA_VERSION,
    SourceFreshness,
)


# ── Sub-sections ──────────────────────────────────────────────────────


class SnapshotIdentity(BaseModel):
    """Company identity and PIT accounting."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    company_name: str | None = None
    sector: str | None = None
    as_of: datetime
    effective_as_of: datetime
    market_as_of: datetime | None = None
    requested_as_of: datetime | None = None
    pit_checks_passed: bool = False
    future_evidence_excluded: int = Field(default=0, ge=0)
    evidence_included: int = Field(default=0, ge=0)


class SnapshotChange(BaseModel):
    """One research change record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    change_id: str
    change_type: str
    title: str
    description: str = ""
    source: str = ""
    before: str | None = None
    after: str | None = None
    why_changed: str | None = None
    pit_eligible: bool = True


class SnapshotObservation(BaseModel):
    """One key observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str
    metric: str
    domain: str = ""
    value: str | None = None
    unit: str = ""
    direction: ResearchDirection = ResearchDirection.UNKNOWN
    epistemic_type: str = "UNKNOWN"
    available: bool = True
    null_reason: str | None = None
    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()


class SnapshotEvidence(BaseModel):
    """Evidence summary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_count: int = Field(default=0, ge=0)
    positive_count: int = Field(default=0, ge=0)
    negative_count: int = Field(default=0, ge=0)
    neutral_count: int = Field(default=0, ge=0)
    conflicting_count: int = Field(default=0, ge=0)
    direction: ResearchDirection = ResearchDirection.UNKNOWN
    epistemic_counts: dict[str, int] = Field(default_factory=dict)
    evidence_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()


class SnapshotCoverageArea(BaseModel):
    """One coverage area."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    area: str
    status: ResearchAvailability = ResearchAvailability.MISSING
    item_count: int = Field(default=0, ge=0)
    detail: str = ""


class SnapshotCoverage(BaseModel):
    """Coverage summary per research area."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    area_count: int = Field(default=0, ge=0)
    available_count: int = Field(default=0, ge=0)
    limited_count: int = Field(default=0, ge=0)
    missing_count: int = Field(default=0, ge=0)
    stale_count: int = Field(default=0, ge=0)
    conflicting_count: int = Field(default=0, ge=0)
    areas: tuple[SnapshotCoverageArea, ...] = ()
    notes: tuple[str, ...] = ()


class SnapshotConflict(BaseModel):
    """One conflict summary record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    conflict_id: str
    topic: str
    status: ConflictResolution = ConflictResolution.OPEN
    side_a_summary: str = ""
    side_b_summary: str = ""


class SnapshotGap(BaseModel):
    """One research gap record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    gap_id: str
    category: str
    description: str
    status: ResearchGapStatus = ResearchGapStatus.UNAVAILABLE
    severity: str = "LOW"


class SnapshotFreshness(BaseModel):
    """Source freshness summary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    current_count: int = Field(default=0, ge=0)
    stale_count: int = Field(default=0, ge=0)
    missing_count: int = Field(default=0, ge=0)
    degraded_count: int = Field(default=0, ge=0)
    unknown_count: int = Field(default=0, ge=0)
    total_sources: int = Field(default=0, ge=0)


class SnapshotSource(BaseModel):
    """One source record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_name: str
    freshness: SourceFreshness = SourceFreshness.UNKNOWN
    evidence_count: int = Field(default=0, ge=0)
    categories: tuple[str, ...] = ()
    pit_eligible: bool = False


class SnapshotProvenance(BaseModel):
    """Provenance summary."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    total_provenance: int = Field(default=0, ge=0)
    total_sources: int = Field(default=0, ge=0)
    provenance_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()


# ── Main Snapshot ─────────────────────────────────────────────────────


class ResearchSnapshot(BaseModel):
    """
    Deterministic ResearchSnapshot.

    Consolidates all research outputs for a company at a given as_of.
    The frontend can render this without recomputing data independently.

    No company score. No overall quality metric.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(default=SNAPSHOT_SCHEMA_VERSION)
    symbol: str = Field(min_length=1)
    as_of: datetime

    # ── Identity & PIT ────────────────────────────────────────────
    identity: SnapshotIdentity

    # ── Changes ───────────────────────────────────────────────────
    changes: tuple[SnapshotChange, ...] = ()
    change_count: int = Field(default=0, ge=0)

    # ── Observations ──────────────────────────────────────────────
    observations: tuple[SnapshotObservation, ...] = ()
    observation_count: int = Field(default=0, ge=0)

    # ── Evidence ──────────────────────────────────────────────────
    evidence: SnapshotEvidence

    # ── Financial ─────────────────────────────────────────────────
    financial_observation_count: int = Field(default=0, ge=0)
    financial_derived_count: int = Field(default=0, ge=0)

    # ── Coverage ──────────────────────────────────────────────────
    coverage: SnapshotCoverage

    # ── Conflicts ─────────────────────────────────────────────────
    conflicts: tuple[SnapshotConflict, ...] = ()
    conflict_count: int = Field(default=0, ge=0)

    # ── Gaps ──────────────────────────────────────────────────────
    gaps: tuple[SnapshotGap, ...] = ()
    gap_count: int = Field(default=0, ge=0)

    # ── Freshness ─────────────────────────────────────────────────
    freshness: SnapshotFreshness

    # ── Sources ───────────────────────────────────────────────────
    sources: tuple[SnapshotSource, ...] = ()
    source_count: int = Field(default=0, ge=0)

    # ── Provenance ────────────────────────────────────────────────
    provenance: SnapshotProvenance

    # ── Notes ─────────────────────────────────────────────────────
    notes: tuple[str, ...] = ()
