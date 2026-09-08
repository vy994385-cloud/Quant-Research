"""
Alert Engine Design Preparation — backend-neutral deterministic alert-event contract.

Defines the event contract around existing change types.
No delivery system, no auth, no database, no email, no webhook infrastructure.

Event types:
  NEW_EVIDENCE
  NEW_FINANCIAL_DISCLOSURE
  NEW_EVENT
  NEW_CORPORATE_ACTION
  NEW_TECHNOLOGY_EVIDENCE
  RESEARCH_GAP_CHANGED
  SOURCE_BECAME_STALE
  SCREEN_ENTRY
  SCREEN_EXIT

Each event provides:
  alert_type, symbol, change_id, context_id, as_of,
  effective_at, source_ids, provenance_ids, human-readable summary
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AlertType(str, Enum):
    NEW_EVIDENCE = "NEW_EVIDENCE"
    NEW_FINANCIAL_DISCLOSURE = "NEW_FINANCIAL_DISCLOSURE"
    NEW_EVENT = "NEW_EVENT"
    NEW_CORPORATE_ACTION = "NEW_CORPORATE_ACTION"
    NEW_TECHNOLOGY_EVIDENCE = "NEW_TECHNOLOGY_EVIDENCE"
    RESEARCH_GAP_CHANGED = "RESEARCH_GAP_CHANGED"
    SOURCE_BECAME_STALE = "SOURCE_BECAME_STALE"
    SCREEN_ENTRY = "SCREEN_ENTRY"
    SCREEN_EXIT = "SCREEN_EXIT"


class AlertEvent(BaseModel):
    """One deterministic alert event contract."""

    model_config = ConfigDict(extra="forbid")

    alert_id: str = Field(min_length=1)
    alert_type: AlertType
    symbol: str = Field(min_length=1)
    change_id: str | None = None
    context_id: str | None = None
    as_of: datetime
    effective_at: datetime | None = None
    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()
    summary: str = Field(min_length=1)
    description: str = ""
    previous_state: str | None = None
    current_state: str | None = None

    @field_validator("as_of", "effective_at")
    @classmethod
    def _require_aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return v


class AlertEventContract(BaseModel):
    """Complete alert event contract for a symbol."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    events: tuple[AlertEvent, ...] = ()
    event_count: int = Field(ge=0)
    alert_type_counts: dict[str, int] = Field(default_factory=dict)
    notes: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def _require_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return v


def build_alert_events(
    *,
    symbol: str,
    as_of: datetime,
    changes: tuple = (),
    context_id: str | None = None,
) -> AlertEventContract:
    """
    Build deterministic alert events from research changes.

    This is an event contract only. No delivery system.
    """

    events: list[AlertEvent] = []

    _change_type_to_alert = {
        "NEW_EVIDENCE": AlertType.NEW_EVIDENCE,
        "CHANGED_EVIDENCE": AlertType.NEW_EVIDENCE,
        "NEW_FINANCIAL_DISCLOSURE": AlertType.NEW_FINANCIAL_DISCLOSURE,
        "CHANGED_FINANCIAL_DISCLOSURE": AlertType.NEW_FINANCIAL_DISCLOSURE,
        "NEW_EVENT": AlertType.NEW_EVENT,
        "CHANGED_EVENT": AlertType.NEW_EVENT,
        "NEW_CORPORATE_ACTION": AlertType.NEW_CORPORATE_ACTION,
        "NEW_TECHNOLOGY_EVIDENCE": AlertType.NEW_TECHNOLOGY_EVIDENCE,
        "RESEARCH_GAP_CHANGED": AlertType.RESEARCH_GAP_CHANGED,
        "RESEARCH_GAP_OPENED": AlertType.RESEARCH_GAP_CHANGED,
        "RESEARCH_GAP_RESOLVED": AlertType.RESEARCH_GAP_CHANGED,
        "RESEARCH_GAP_REOPENED": AlertType.RESEARCH_GAP_CHANGED,
        "SOURCE_BECAME_STALE": AlertType.SOURCE_BECAME_STALE,
        "SOURCE_BECAME_FRESH": AlertType.SOURCE_BECAME_STALE,
        "SCREEN_ENTRY": AlertType.SCREEN_ENTRY,
        "SCREEN_EXIT": AlertType.SCREEN_EXIT,
    }

    for change in changes:
        change_type_val = (
            change.change_type.value
            if hasattr(change.change_type, "value")
            else str(change.change_type)
        )
        alert_type = _change_type_to_alert.get(change_type_val)
        if alert_type is None:
            continue

        summary = (
            f"{change_type_val}: {change.title}"
            if hasattr(change, "title")
            else change_type_val
        )

        events.append(
            AlertEvent(
                alert_id=f"alert-{change.change_id}",
                alert_type=alert_type,
                symbol=symbol,
                change_id=getattr(change, "change_id", None),
                context_id=context_id,
                as_of=as_of,
                effective_at=getattr(change, "effective_at", None),
                source_ids=(getattr(change, "source", None),) if getattr(change, "source", None) else (),
                provenance_ids=getattr(change, "provenance", ()) or (),
                summary=summary,
                description=getattr(change, "description", "") or "",
                previous_state=getattr(change, "previous_state", None),
                current_state=getattr(change, "current_state", None),
            )
        )

    events.sort(key=lambda e: (e.alert_type.value, e.alert_id))

    type_counts: dict[str, int] = {}
    for ev in events:
        type_counts[ev.alert_type.value] = type_counts.get(ev.alert_type.value, 0) + 1

    notes: list[str] = []
    if not events:
        notes.append("No alert events generated from the available changes.")
    notes.append("Alert event contract only. No delivery system is active.")

    return AlertEventContract(
        symbol=symbol,
        as_of=as_of,
        events=tuple(events),
        event_count=len(events),
        alert_type_counts=type_counts,
        notes=tuple(notes),
    )


__all__ = [
    "AlertEvent",
    "AlertEventContract",
    "AlertType",
    "build_alert_events",
]
