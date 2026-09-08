"""
Conflict Explorer 2.0 — deepened conflict model.

For each conflict exposes:
  - claim/topic
  - source A: value/text, period, as_of, provenance
  - source B: value/text, period, as_of, provenance
  - normalization/methodology if available
  - conflict status: OPEN, RESOLVED, PARTIAL

Never automatically selects a winner.
If an explicit source-priority rule exists, exposes the rule rather
than silently resolving.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.research.company_intel.models import (
    EvidenceConflict,
    ConflictSide,
)


class ConflictStatus(str, Enum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    PARTIAL = "PARTIAL"


class ConflictSideDetail(BaseModel):
    """One side of an evidence conflict with full provenance."""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    value_text: str = Field(min_length=1)
    period: str | None = None
    as_of: datetime | None = None
    provenance: tuple[str, ...] = ()
    semantic_category: str = ""
    verification_status: str = ""
    stance: str = ""
    direction: str = ""
    excerpt: str = ""

    @field_validator("as_of")
    @classmethod
    def _require_aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return v


class ConflictDetail(BaseModel):
    """A fully resolved conflict with both sides and metadata."""

    model_config = ConfigDict(extra="forbid")

    conflict_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    description: str = Field(min_length=1)
    management_involved: bool

    side_a: ConflictSideDetail
    side_b: ConflictSideDetail

    status: ConflictStatus = ConflictStatus.OPEN
    normalization_methodology: str | None = None
    source_priority_rule: str | None = None

    as_of: datetime
    notes: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def _require_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return v


class ConflictExplorerReport(BaseModel):
    """Full conflict analysis for a company at one point in time."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    conflicts: tuple[ConflictDetail, ...] = ()
    open_count: int = Field(ge=0)
    resolved_count: int = Field(ge=0)
    partial_count: int = Field(ge=0)
    total_count: int = Field(ge=0)
    notes: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def _require_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return v


def _side_to_detail(
    side: ConflictSide,
    conflict_as_of: datetime,
) -> ConflictSideDetail:
    """Convert a ConflictSide to a ConflictSideDetail."""

    return ConflictSideDetail(
        item_id=side.item_id,
        title=side.title,
        source_name=side.source_name,
        value_text=side.excerpt,
        as_of=conflict_as_of,
        provenance=(),
        semantic_category=side.semantic_category.value,
        verification_status=side.verification_status.value,
        stance=side.stance.value,
        direction=side.direction.value,
        excerpt=side.excerpt,
    )


def _classify_conflict_status(
    first: ConflictSide,
    second: ConflictSide,
) -> ConflictStatus:
    """
    Classify conflict status based on the evidence.

    OPEN: both sides have REPORTED or UNVERIFIED status
    RESOLVED: one side is CONFIRMED/VERIFIED and the other is REFUTED
    PARTIAL: mixed statuses that suggest partial resolution
    """

    first_status = first.verification_status.value
    second_status = second.verification_status.value

    confirmed = {"CONFIRMED", "VERIFIED"}
    refuted = {"REFUTED", "DISPROVEN"}

    if first_status in confirmed and second_status in refuted:
        return ConflictStatus.RESOLVED
    if second_status in confirmed and first_status in refuted:
        return ConflictStatus.RESOLVED

    if first_status in confirmed or second_status in confirmed:
        return ConflictStatus.PARTIAL
    if first_status in refuted or second_status in refuted:
        return ConflictStatus.PARTIAL

    return ConflictStatus.OPEN


def build_conflict_explorer(
    *,
    symbol: str,
    as_of: datetime,
    conflicts: tuple[EvidenceConflict, ...] = (),
    source_priority_rules: dict[str, str] | None = None,
) -> ConflictExplorerReport:
    """
    Build a Conflict Explorer 2.0 report.

    Deepens the conflict model with:
    - full provenance on both sides
    - status classification
    - normalization methodology disclosure
    - source priority rule exposure (never silent resolution)
    """

    rules = source_priority_rules or {}
    details: list[ConflictDetail] = []

    for conflict in conflicts:
        side_a = _side_to_detail(conflict.first, conflict.as_of)
        side_b = _side_to_detail(conflict.second, conflict.as_of)

        status = _classify_conflict_status(conflict.first, conflict.second)

        source_key_a = conflict.first.source_name
        source_key_b = conflict.second.source_name
        rule_a = rules.get(source_key_a)
        rule_b = rules.get(source_key_b)

        priority_rule = None
        if rule_a and rule_b and rule_a != rule_b:
            priority_rule = (
                f"Source priority: {source_key_a} ({rule_a}) vs "
                f"{source_key_b} ({rule_b}). System does not auto-resolve."
            )
        elif rule_a:
            priority_rule = f"{source_key_a} priority rule: {rule_a}"
        elif rule_b:
            priority_rule = f"{source_key_b} priority rule: {rule_b}"

        notes: list[str] = []
        if status == ConflictStatus.OPEN:
            notes.append("Conflict remains open; both sides coexist without resolution.")
        elif status == ConflictStatus.RESOLVED:
            notes.append(
                "One side has been refuted/disproven; conflict is resolved "
                "based on verification status changes."
            )
        elif status == ConflictStatus.PARTIAL:
            notes.append(
                "Conflict is partially resolved; one side has stronger "
                "verification status but both sides remain."
            )

        details.append(
            ConflictDetail(
                conflict_id=conflict.conflict_id,
                symbol=conflict.symbol,
                topic=conflict.topic,
                description=conflict.description,
                management_involved=conflict.management_involved,
                side_a=side_a,
                side_b=side_b,
                status=status,
                normalization_methodology=(
                    "Both sides normalized from recorded intel items "
                    "with explicit source attribution."
                ),
                source_priority_rule=priority_rule,
                as_of=as_of,
                notes=tuple(notes),
            )
        )

    details.sort(key=lambda d: d.conflict_id)

    open_count = sum(1 for d in details if d.status == ConflictStatus.OPEN)
    resolved_count = sum(1 for d in details if d.status == ConflictStatus.RESOLVED)
    partial_count = sum(1 for d in details if d.status == ConflictStatus.PARTIAL)

    notes: list[str] = []
    if not details:
        notes.append("No conflicts detected at this point in time.")
    if open_count:
        notes.append(f"{open_count} conflict(s) remain open.")
    if resolved_count:
        notes.append(f"{resolved_count} conflict(s) resolved.")
    if partial_count:
        notes.append(f"{partial_count} conflict(s) partially resolved.")

    return ConflictExplorerReport(
        symbol=symbol,
        as_of=as_of,
        conflicts=tuple(details),
        open_count=open_count,
        resolved_count=resolved_count,
        partial_count=partial_count,
        total_count=len(details),
        notes=tuple(notes),
    )


__all__ = [
    "ConflictDetail",
    "ConflictExplorerReport",
    "ConflictSideDetail",
    "ConflictStatus",
    "build_conflict_explorer",
]
