"""
Canonical Research Observation Contract (T1-W4).

Defines the standardized observation interface that all research
observations should implement or map to. This is additive — existing
models keep their local definitions. This provides the canonical
shape for cross-cutting concerns.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.research.vocabulary import (
    EvidenceEpistemicType,
    ObservationOrigin,
    ObservationSeverity,
    ResearchDirection,
    VerificationStatus,
)


class CanonicalObservation(BaseModel):
    """
    Canonical observation contract.

    Every observation should preserve, where supported:
    - identification
    - metric/domain
    - period
    - value/unit
    - direction
    - epistemic type
    - verification
    - confidence/reliability
    - temporal (as_of, effective_date, published_at, available_at)
    - source/provenance
    - derivation
    - limitations

    Missing remains null. Never fabricate zero.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # ── Identification ────────────────────────────────────────────
    observation_id: str = Field(min_length=1, description="Unique observation identifier")
    symbol: str = Field(min_length=1, description="Company ticker symbol")

    # ── Metric / Domain ───────────────────────────────────────────
    metric: str = Field(default="", description="Metric name or label")
    domain: str = Field(default="", description="Research domain (financial, business, technology, etc)")
    category: str = Field(default="", description="Observation category")

    # ── Period ────────────────────────────────────────────────────
    period: str = Field(default="", description="Period description (e.g. '2024-03-31', '2023-2024')")
    period_end: date | None = Field(default=None, description="Period end date")

    # ── Value ─────────────────────────────────────────────────────
    value: Decimal | None = Field(default=None, description="Observation value")
    unit: str = Field(default="", description="Unit of measurement (INR, FRACTION, etc)")
    available: bool = Field(default=True, description="Whether the value is available")
    null_reason: str | None = Field(default=None, description="Reason if value is null")

    # ── Direction / Severity ──────────────────────────────────────
    direction: ResearchDirection = Field(default=ResearchDirection.UNKNOWN)
    severity: ObservationSeverity = Field(default=ObservationSeverity.LOW)

    # ── Epistemic / Verification ──────────────────────────────────
    epistemic_type: EvidenceEpistemicType = Field(default=EvidenceEpistemicType.UNKNOWN)
    verification_status: VerificationStatus = Field(default=VerificationStatus.UNVERIFIED)
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    reliability: str = Field(default="", description="Source reliability tier")

    # ── Temporal ──────────────────────────────────────────────────
    as_of: datetime | None = Field(default=None, description="Research context timestamp")
    effective_date: datetime | None = Field(default=None, description="When observation became effective")
    published_at: datetime | None = Field(default=None, description="When published by source")
    available_at: datetime | None = Field(default=None, description="When available for PIT filtering")

    # ── Source / Provenance ───────────────────────────────────────
    source_ids: tuple[str, ...] = Field(default=())
    provenance_ids: tuple[str, ...] = Field(default=())
    source_name: str | None = Field(default=None, description="Primary source name")

    # ── Derivation / Limitations ──────────────────────────────────
    derivation: str | None = Field(default=None, description="Human-readable derivation formula")
    derivation_inputs: tuple[str, ...] = Field(default=(), description="Input observation IDs")
    limitations: str | None = Field(default=None, description="Known limitations")

    # ── Change Tracking ───────────────────────────────────────────
    origin: ObservationOrigin = Field(default=ObservationOrigin.REPORTED)
    previous_value: Decimal | None = Field(default=None)
    delta: Decimal | None = Field(default=None)
    delta_pct: Decimal | None = Field(default=None)


class CanonicalObservationSummary(BaseModel):
    """Aggregate summary of observations for a company."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str
    as_of: datetime
    total_count: int = Field(ge=0)
    available_count: int = Field(ge=0)
    unavailable_count: int = Field(ge=0)
    reported_count: int = Field(ge=0)
    derived_count: int = Field(ge=0)
    direction_counts: dict[str, int] = Field(default_factory=dict)
    domain_counts: dict[str, int] = Field(default_factory=dict)
    epistemic_counts: dict[str, int] = Field(default_factory=dict)
    severity_counts: dict[str, int] = Field(default_factory=dict)
    notes: tuple[str, ...] = Field(default=())
