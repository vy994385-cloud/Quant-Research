"""
Company tracking foundation.

Provides a structured model for tracking company research changes.
This is an information/monitoring feature, NOT an automated
trading-alert system.

Tracking records capture what changed, when it changed, and
what evidence supports the change. They never generate
buy/sell signals or investment recommendations.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ChangeDomain(str, Enum):
    """Domain in which a tracked change occurred."""

    FINANCIAL = "FINANCIAL"
    NEWS = "NEWS"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    ANOMALY = "ANOMALY"
    TIMELINE = "TIMELINE"
    TECHNOLOGY = "TECHNOLOGY"
    RESEARCH_GAP = "RESEARCH_GAP"
    EVIDENCE = "EVIDENCE"
    SCREEN = "SCREEN"
    OTHER = "OTHER"


class TrackedChangeType(str, Enum):
    """
    Canonical change vocabulary for tracking output.

    Every value describes a recorded research fact (new evidence,
    a new disclosure, a state transition). No value expresses an
    investment opinion or a prediction.
    """

    NEW_EVIDENCE = "NEW_EVIDENCE"
    NEW_FINANCIAL_DISCLOSURE = "NEW_FINANCIAL_DISCLOSURE"
    NEW_EVENT = "NEW_EVENT"
    NEW_CORPORATE_ACTION = "NEW_CORPORATE_ACTION"
    NEW_TECHNOLOGY_EVIDENCE = "NEW_TECHNOLOGY_EVIDENCE"
    RESEARCH_GAP_CHANGED = "RESEARCH_GAP_CHANGED"
    SOURCE_BECAME_STALE = "SOURCE_BECAME_STALE"
    SCREEN_ENTRY = "SCREEN_ENTRY"
    SCREEN_EXIT = "SCREEN_EXIT"


class TrackingSeverity(str, Enum):
    """Severity of a tracked change."""

    INFO = "INFO"
    NOTABLE = "NOTABLE"
    SIGNIFICANT = "SIGNIFICANT"


class TrackingChange(BaseModel):
    """
    A single tracked change for a company.

    Describes what changed, in which domain, and provides
    evidence traceability.
    """

    model_config = ConfigDict(extra="forbid")

    change_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)

    domain: ChangeDomain
    severity: TrackingSeverity = TrackingSeverity.INFO

    # Canonical change vocabulary (see TrackedChangeType).
    change_type: TrackedChangeType | None = None

    title: str = Field(min_length=1)
    description: str = ""

    previous_value: str | None = None
    current_value: str | None = None

    change_date: date | None = None
    evidence_refs: tuple[str, ...] = ()
    source_names: tuple[str, ...] = ()

    # When the change was detected (defaults to as_of) and, when the
    # underlying record states it, when it took effect.
    detected_at: datetime | None = None
    effective_at: datetime | None = None

    # True when the change is reproducible at as_of from recorded
    # availability timestamps.
    pit_eligible: bool = False
    provenance_ids: tuple[str, ...] = ()

    # Deterministic content hash identifying the change itself (not
    # the detection run). Same logical change detected twice yields
    # the same fingerprint.
    fingerprint: str = ""

    as_of: datetime | None = None

    @model_validator(mode="after")
    def _finalize(self) -> "TrackingChange":
        if self.detected_at is None and self.as_of is not None:
            self.detected_at = self.as_of

        if not self.fingerprint:
            basis = "|".join(
                (
                    self.change_type.value if self.change_type else "",
                    self.domain.value,
                    self.symbol.strip().upper(),
                    self.title,
                    str(self.previous_value or ""),
                    str(self.current_value or ""),
                    str(self.change_date or ""),
                    ",".join(sorted(self.evidence_refs)),
                    ",".join(sorted(set(self.source_names))),
                )
            )
            digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()
            self.fingerprint = digest[:16]

        return self


class CompanyTrackingResult(BaseModel):
    """
    Tracking result for a company.

    Lists recent changes across domains with counts.
    Does NOT generate alerts or recommendations.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime

    changes: tuple[TrackingChange, ...] = ()
    change_count: int = 0

    domain_counts: dict[str, int] = Field(
        default_factory=dict,
    )

    significant_count: int = 0
    notable_count: int = 0

    notes: tuple[str, ...] = ()

    @classmethod
    def from_changes(
        cls,
        symbol: str,
        as_of: datetime,
        changes: tuple[TrackingChange, ...],
    ) -> CompanyTrackingResult:
        """Build a tracking result from a collection of changes."""

        domain_counts: dict[str, int] = {}
        significant = 0
        notable = 0

        for change in changes:
            d = change.domain.value
            domain_counts[d] = domain_counts.get(d, 0) + 1
            if change.severity == TrackingSeverity.SIGNIFICANT:
                significant += 1
            elif change.severity == TrackingSeverity.NOTABLE:
                notable += 1

        notes: list[str] = []
        if not changes:
            notes.append(
                "No recent tracked changes for this company."
            )

        return cls(
            symbol=symbol,
            as_of=as_of,
            changes=changes,
            change_count=len(changes),
            domain_counts=domain_counts,
            significant_count=significant,
            notable_count=notable,
            notes=tuple(notes),
        )
