"""
Business / Technology Evidence Depth.

Audits business and technology research engines.
Identifies where data supports:
  - business developments
  - customer evidence
  - management commentary
  - competitive evidence
  - technology activity
  - AI/cloud/platform evidence
  - R&D/innovation evidence

Normalizes output so every observation retains:
  type, direction, epistemic state, as_of, effective/published date,
  source, provenance

Does not expand into unsupported research.
Explicitly catalogues weak/partial areas.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceDimension(str, Enum):
    BUSINESS_DEVELOPMENTS = "BUSINESS_DEVELOPMENTS"
    CUSTOMER_EVIDENCE = "CUSTOMER_EVIDENCE"
    MANAGEMENT_COMMENTARY = "MANAGEMENT_COMMENTARY"
    COMPETITIVE_EVIDENCE = "COMPETITIVE_EVIDENCE"
    TECHNOLOGY_ACTIVITY = "TECHNOLOGY_ACTIVITY"
    AI_CLOUD_PLATFORM = "AI_CLOUD_PLATFORM"
    RD_INNOVATION = "RD_INNOVATION"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    RISK_INTELLIGENCE = "RISK_INTELLIGENCE"
    FINANCIAL_INTELLIGENCE = "FINANCIAL_INTELLIGENCE"


class EpistemicState(str, Enum):
    STRONG = "STRONG"
    PARTIAL = "PARTIAL"
    WEAK = "WEAK"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class BusinessTechObservation(BaseModel):
    """One normalized business/technology evidence observation."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    dimension: EvidenceDimension
    epistemic_state: EpistemicState

    title: str = Field(min_length=1)
    description: str = ""
    direction: str = "UNKNOWN"

    effective_date: datetime | None = None
    published_date: datetime | None = None
    available_at: datetime | None = None

    source_name: str | None = None
    source_type: str | None = None
    provenance_id: str | None = None
    item_id: str | None = None

    notes: tuple[str, ...] = ()

    @field_validator("effective_date", "published_date", "available_at")
    @classmethod
    def _require_aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return v


class BusinessTechReport(BaseModel):
    """Complete business/technology evidence depth report."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    observations: tuple[BusinessTechObservation, ...] = ()
    observation_count: int = Field(ge=0)

    dimension_summary: dict[str, int] = Field(default_factory=dict)
    epistemic_summary: dict[str, int] = Field(default_factory=dict)

    strong_count: int = Field(ge=0)
    partial_count: int = Field(ge=0)
    weak_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)

    weak_areas: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def _require_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return v


def _classify_epistemic(
    item,
    has_source: bool,
    has_timestamp: bool,
) -> EpistemicState:
    """Classify epistemic state based on evidence properties."""
    has_description = bool(getattr(item, "description", "") or getattr(item, "excerpt", ""))
    status = getattr(item, "verification_status", None)
    status_val = status.value if hasattr(status, "value") else str(status) if status else ""

    if status_val in ("CONFIRMED", "VERIFIED") and has_source and has_timestamp:
        return EpistemicState.STRONG
    if has_source and has_description:
        return EpistemicState.PARTIAL
    if has_source or has_timestamp:
        return EpistemicState.WEAK
    return EpistemicState.MISSING


def _item_to_observation(
    item,
    *,
    symbol: str,
    as_of: datetime,
    dimension: EvidenceDimension,
) -> BusinessTechObservation:
    """Convert an intel item to a normalized BusinessTechObservation."""

    source = getattr(item, "source", None)
    source_name = getattr(source, "source_name", None)
    source_type = getattr(source, "source_type", None)

    has_source = bool(source_name)
    has_timestamp = item.available_at is not None

    epistemic = _classify_epistemic(item, has_source, has_timestamp)

    direction_val = "UNKNOWN"
    direction = getattr(item, "direction", None)
    if direction is not None:
        direction_val = direction.value if hasattr(direction, "value") else str(direction)

    return BusinessTechObservation(
        observation_id=f"bte-{item.item_id}",
        symbol=symbol,
        dimension=dimension,
        epistemic_state=epistemic,
        title=getattr(item, "title", ""),
        description=getattr(item, "description", ""),
        direction=direction_val,
        effective_date=getattr(item, "effective_at", None),
        published_date=getattr(item, "published_at", None),
        available_at=getattr(item, "available_at", None),
        source_name=source_name,
        source_type=source_type,
        provenance_id=getattr(item, "provenance_id", None),
        item_id=getattr(item, "item_id", None),
    )


def _dimension_for_item(item) -> EvidenceDimension:
    """Map an intel item to its evidence dimension."""
    intel_cat = getattr(item, "intel_category", None)
    if intel_cat is not None:
        cat_val = intel_cat.value if hasattr(intel_cat, "value") else str(intel_cat)
        mapping = {
            "BUSINESS_UPDATE": EvidenceDimension.BUSINESS_DEVELOPMENTS,
            "CUSTOMER": EvidenceDimension.CUSTOMER_EVIDENCE,
            "MANAGEMENT": EvidenceDimension.MANAGEMENT_COMMENTARY,
            "COMPETITIVE": EvidenceDimension.COMPETITIVE_EVIDENCE,
            "PRODUCT_BUSINESS_UPDATE": EvidenceDimension.TECHNOLOGY_ACTIVITY,
            "CORPORATE_ACTION": EvidenceDimension.CORPORATE_ACTION,
            "FINANCIAL_PERIOD": EvidenceDimension.FINANCIAL_INTELLIGENCE,
            "RISK": EvidenceDimension.RISK_INTELLIGENCE,
        }
        if cat_val in mapping:
            return mapping[cat_val]

    kind = getattr(item, "kind", None)
    if kind is not None:
        kind_val = kind.value if hasattr(kind, "value") else str(kind)
        if "TECH" in kind_val.upper():
            return EvidenceDimension.TECHNOLOGY_ACTIVITY
        if "BUSINESS" in kind_val.upper():
            return EvidenceDimension.BUSINESS_DEVELOPMENTS
        if "RISK" in kind_val.upper():
            return EvidenceDimension.RISK_INTELLIGENCE

    return EvidenceDimension.BUSINESS_DEVELOPMENTS


def build_business_tech_evidence(
    *,
    symbol: str,
    as_of: datetime,
    intel_items: tuple = (),
    evidence_items: tuple = (),
) -> BusinessTechReport:
    """
    Build a normalized business/technology evidence depth report.

    Only catalogues evidence that actually exists.
    Does not expand into unsupported research.
    """

    observations: list[BusinessTechObservation] = []

    for item in intel_items:
        dimension = _dimension_for_item(item)
        obs = _item_to_observation(
            item,
            symbol=symbol,
            as_of=as_of,
            dimension=dimension,
        )
        observations.append(obs)

    observations.sort(key=lambda o: (o.dimension.value, o.observation_id))

    # Summary
    dim_summary: dict[str, int] = {}
    epi_summary: dict[str, int] = {}
    for obs in observations:
        dim_summary[obs.dimension.value] = dim_summary.get(obs.dimension.value, 0) + 1
        epi_summary[obs.epistemic_state.value] = epi_summary.get(obs.epistemic_state.value, 0) + 1

    strong = sum(1 for o in observations if o.epistemic_state == EpistemicState.STRONG)
    partial = sum(1 for o in observations if o.epistemic_state == EpistemicState.PARTIAL)
    weak = sum(1 for o in observations if o.epistemic_state == EpistemicState.WEAK)
    missing = sum(1 for o in observations if o.epistemic_state == EpistemicState.MISSING)

    # Identify weak areas
    all_dimensions = {d.value for d in EvidenceDimension}
    covered = {o.dimension.value for o in observations}
    weak_areas = tuple(sorted(all_dimensions - covered))

    notes: list[str] = []
    if weak_areas:
        notes.append(
            f"Weak/partial areas with no evidence: {', '.join(weak_areas)}"
        )
    if not observations:
        notes.append("No business/technology evidence items available.")
    if missing:
        notes.append(f"{missing} observation(s) have missing source/provenance information.")

    return BusinessTechReport(
        symbol=symbol,
        as_of=as_of,
        observations=tuple(observations),
        observation_count=len(observations),
        dimension_summary=dim_summary,
        epistemic_summary=epi_summary,
        strong_count=strong,
        partial_count=partial,
        weak_count=weak,
        missing_count=missing,
        weak_areas=weak_areas,
        notes=tuple(notes),
    )


__all__ = [
    "BusinessTechObservation",
    "BusinessTechReport",
    "EpistemicState",
    "EvidenceDimension",
    "build_business_tech_evidence",
]
