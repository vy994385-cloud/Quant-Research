"""
Source Quality / Freshness Intelligence.

Deterministic source states:
  CURRENT
  STALE
  MISSING
  DEGRADED
  UNKNOWN

Where data supports, exposes:
  - latest_available_at
  - latest_effective_date
  - observation_count
  - evidence_count
  - freshness_state
  - provenance_completeness
  - PIT_eligibility

No source scores. No "best source" ranking.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FreshnessState(str, Enum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    MISSING = "MISSING"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


class SourceIntelligence(BaseModel):
    """Deterministic intelligence about one source."""

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1)
    source_type: str = Field(min_length=1)

    freshness_state: FreshnessState

    latest_available_at: datetime | None = None
    latest_effective_date: datetime | None = None
    observation_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    provenance_completeness: bool = False
    pit_eligible: bool = True

    days_since_latest: int | None = None
    stale_threshold_days: int | None = None

    categories: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @field_validator("latest_available_at", "latest_effective_date")
    @classmethod
    def _require_aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return v


class SourceIntelligenceReport(BaseModel):
    """Full source intelligence for a company at one point in time."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    sources: tuple[SourceIntelligence, ...] = ()
    current_count: int = Field(ge=0)
    stale_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    degraded_count: int = Field(ge=0)
    unknown_count: int = Field(ge=0)
    total_sources: int = Field(ge=0)
    notes: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def _require_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return v


def _determine_freshness_state(
    *,
    stale: bool,
    has_data: bool,
    provenance_complete: bool,
) -> FreshnessState:
    if not has_data:
        return FreshnessState.MISSING
    if stale and not provenance_complete:
        return FreshnessState.DEGRADED
    if stale:
        return FreshnessState.STALE
    return FreshnessState.CURRENT


def build_source_intelligence(
    *,
    symbol: str,
    as_of: datetime,
    source_statuses: tuple = (),
    evidence_items: tuple = (),
    provenance_ids: set[str] | None = None,
) -> SourceIntelligenceReport:
    """
    Build deterministic source intelligence from source statuses
    and evidence items.

    No scores. No rankings. Only factual source-state observations.
    """

    prov_ids = provenance_ids or set()
    sources: list[SourceIntelligence] = []

    # Index evidence by source
    ev_by_source: dict[str, list[str]] = {}
    for item in evidence_items:
        src_ids = getattr(item, "source_ids", ())
        ev_id = getattr(item, "evidence_id", "")
        for sid in src_ids:
            ev_by_source.setdefault(str(sid), []).append(ev_id)

    for status in source_statuses:
        src_name = status.source_name
        src_type = status.source_type

        has_data = status.item_count > 0
        provenance_complete = status.provenance_completeness

        freshness_state = _determine_freshness_state(
            stale=status.stale,
            has_data=has_data,
            provenance_complete=provenance_complete,
        )

        evidence_in_source = ev_by_source.get(src_name, [])
        pit_eligible = (
            status.latest_available_at is not None
            and status.latest_available_at <= as_of
        )

        notes: list[str] = []
        if freshness_state == FreshnessState.MISSING:
            notes.append(f"No data recorded for source {src_name}.")
        elif freshness_state == FreshnessState.DEGRADED:
            notes.append(
                f"Source {src_name} is stale with incomplete provenance."
            )
        elif freshness_state == FreshnessState.STALE:
            notes.append(f"Source {src_name} latest data exceeds freshness threshold.")

        sources.append(
            SourceIntelligence(
                source_name=src_name,
                source_type=src_type,
                freshness_state=freshness_state,
                latest_available_at=status.latest_available_at,
                latest_effective_date=status.latest_published_at,
                observation_count=status.item_count,
                evidence_count=len(evidence_in_source),
                provenance_completeness=provenance_complete,
                pit_eligible=pit_eligible,
                days_since_latest=status.days_since_latest_published,
                categories=tuple(status.categories),
                notes=tuple(notes),
            )
        )

    sources.sort(key=lambda s: s.source_name)

    current_count = sum(1 for s in sources if s.freshness_state == FreshnessState.CURRENT)
    stale_count = sum(1 for s in sources if s.freshness_state == FreshnessState.STALE)
    missing_count = sum(1 for s in sources if s.freshness_state == FreshnessState.MISSING)
    degraded_count = sum(1 for s in sources if s.freshness_state == FreshnessState.DEGRADED)
    unknown_count = sum(1 for s in sources if s.freshness_state == FreshnessState.UNKNOWN)

    notes: list[str] = []
    if not sources:
        notes.append("No source status records available.")
    if missing_count:
        notes.append(f"{missing_count} source(s) have no recorded data.")
    if degraded_count:
        notes.append(f"{degraded_count} source(s) are degraded.")

    return SourceIntelligenceReport(
        symbol=symbol,
        as_of=as_of,
        sources=tuple(sources),
        current_count=current_count,
        stale_count=stale_count,
        missing_count=missing_count,
        degraded_count=degraded_count,
        unknown_count=unknown_count,
        total_sources=len(sources),
        notes=tuple(notes),
    )


__all__ = [
    "FreshnessState",
    "SourceIntelligence",
    "SourceIntelligenceReport",
    "build_source_intelligence",
]
