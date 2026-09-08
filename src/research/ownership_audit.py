"""
Ownership / Deals Final Audit.

Does not invent ownership/deals.
Inspects actual fixtures/providers and determines whether any usable
recorded data exists.

If usable: normalizes with holder, holding/value, period, as_of, source, provenance.
If not: records capability as PARTIAL / BLOCKED with exact reason.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OwnershipCapability(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    MISSING = "MISSING"


class OwnershipRecord(BaseModel):
    """One normalized ownership record from available data."""

    model_config = ConfigDict(extra="forbid")

    holder: str = Field(min_length=1)
    holding_value: str | None = None
    holding_pct: str | None = None
    period: str | None = None
    as_of: datetime | None = None
    source: str = ""
    provenance: str = ""

    @field_validator("as_of")
    @classmethod
    def _require_aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return v


class OwnershipAuditReport(BaseModel):
    """Audit of ownership data availability and capability."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    capability: OwnershipCapability
    records: tuple[OwnershipRecord, ...] = ()
    record_count: int = Field(ge=0)
    block_reason: str | None = None
    partial_reasons: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def _require_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return v


def build_ownership_audit(
    *,
    symbol: str,
    as_of: datetime,
    ownership_data: dict | None = None,
    intel_items: tuple = (),
) -> OwnershipAuditReport:
    """
    Audit actual ownership data availability.

    Does not invent ownership/deals.
    Records exact capability status with reasons.
    """

    records: list[OwnershipRecord] = []
    notes: list[str] = []
    partial_reasons: list[str] = []

    # Check if ownership data exists in the fixture
    if ownership_data is not None:
        # Promoter holdings
        promoters = ownership_data.get("promoters", [])
        for entry in promoters:
            if isinstance(entry, dict):
                records.append(
                    OwnershipRecord(
                        holder=entry.get("holder", "Unknown"),
                        holding_value=str(entry.get("value", "")) or None,
                        holding_pct=str(entry.get("percentage", "")) or None,
                        period=entry.get("period"),
                        as_of=as_of,
                        source="recorded ownership fixture",
                    )
                )

        # Institutional holdings
        institutional = ownership_data.get("institutional", [])
        for entry in institutional:
            if isinstance(entry, dict):
                records.append(
                    OwnershipRecord(
                        holder=entry.get("holder", "Unknown"),
                        holding_value=str(entry.get("value", "")) or None,
                        holding_pct=str(entry.get("percentage", "")) or None,
                        period=entry.get("period"),
                        as_of=as_of,
                        source="recorded ownership fixture",
                    )
                )

    # Check intel items for ownership-related entries
    for item in intel_items:
        title = getattr(item, "title", "").lower()
        if any(kw in title for kw in ("ownership", "promoter", "stake", "holding", "pledge")):
            source = getattr(item, "source", None)
            source_name = getattr(source, "source_name", "unknown") if source else "unknown"
            records.append(
                OwnershipRecord(
                    holder=getattr(item, "topic", "Unknown") or "Unknown",
                    holding_value=None,
                    holding_pct=None,
                    period=None,
                    as_of=getattr(item, "available_at", None) or as_of,
                    source=source_name,
                    provenance=getattr(item, "provenance_id", "") or "",
                )
            )

    if not records:
        capability = OwnershipCapability.BLOCKED
        notes.append(
            "No recorded ownership data exists in fixtures. "
            "Ownership data is fetched live from Yahoo Finance, not "
            "from recorded fixtures. Bulk/block deal recordings do not exist."
        )
        partial_reasons.append("No fixture ownership data")
        partial_reasons.append("No bulk/block deal recordings")
    elif len(records) < 3:
        capability = OwnershipCapability.PARTIAL
        notes.append(
            f"Limited ownership records ({len(records)}). "
            "Partial data from intel items only."
        )
        partial_reasons.append("Limited number of ownership records")
    else:
        capability = OwnershipCapability.PARTIAL
        notes.append(
            f"Found {len(records)} ownership-related records from intel items. "
            "No dedicated ownership fixtures available."
        )
        partial_reasons.append("Records sourced from intel items, not dedicated fixtures")

    records.sort(key=lambda r: r.holder)

    return OwnershipAuditReport(
        symbol=symbol,
        as_of=as_of,
        capability=capability,
        records=tuple(records),
        record_count=len(records),
        block_reason="No recorded ownership data in fixtures" if capability == OwnershipCapability.BLOCKED else None,
        partial_reasons=tuple(partial_reasons),
        notes=tuple(notes),
    )


__all__ = [
    "OwnershipAuditReport",
    "OwnershipCapability",
    "OwnershipRecord",
    "build_ownership_audit",
]
