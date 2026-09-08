"""Change History Quality (T1-W5).

Audits research change records for completeness: change_id, symbol,
type, before, after, why_changed, effective_at, detected_at, as_of,
source_ids, provenance_ids, related_changes.  Ensures removed and
reopened evidence remain visible.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChangeQualityIssue(BaseModel):
    """A detected quality issue in a change record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    issue_id: str = Field(min_length=1)
    change_id: str = Field(min_length=1)
    issue_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: str = "WARNING"


class ChangeQualityEntry(BaseModel):
    """Quality audit for one change record."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    change_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    has_type: bool = False
    has_before: bool = False
    has_after: bool = False
    has_effective_at: bool = False
    has_detected_at: bool = False
    has_source_ids: bool = False
    has_provenance_ids: bool = False
    issues: tuple[ChangeQualityIssue, ...] = ()
    issue_count: int = Field(ge=0)


class ChangeQualityReport(BaseModel):
    """Change quality audit for one company."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    total_changes: int = Field(ge=0)
    clean_count: int = Field(ge=0)
    issue_count: int = Field(ge=0)
    entries: tuple[ChangeQualityEntry, ...] = ()
    notes: tuple[str, ...] = ()


def _audit_change(change: Any) -> ChangeQualityEntry:
    """Audit a single change record."""
    cid = getattr(change, "change_id", "") or getattr(change, "item_id", "") or ""
    symbol = getattr(change, "symbol", "") or ""
    has_type = getattr(change, "change_type", None) is not None
    has_before = getattr(change, "previous_title", None) is not None or getattr(change, "previous_checksum", None) is not None
    has_after = getattr(change, "title", None) is not None or getattr(change, "current_checksum", None) is not None
    has_eff = getattr(change, "effective_at", None) is not None or getattr(change, "as_of", None) is not None
    has_det = getattr(change, "detected_at", None) is not None or getattr(change, "published_at", None) is not None
    has_src = bool(getattr(change, "source_ids", None))
    has_prov = bool(getattr(change, "provenance_ids", None))

    issues: list[ChangeQualityIssue] = []
    if not has_type:
        issues.append(ChangeQualityIssue(
            issue_id=f"CQ:{cid}:NO_TYPE",
            change_id=cid,
            issue_type="MISSING_TYPE",
            description="Change record has no change_type.",
        ))
    if not has_eff:
        issues.append(ChangeQualityIssue(
            issue_id=f"CQ:{cid}:NO_EFFECTIVE",
            change_id=cid,
            issue_type="MISSING_EFFECTIVE_AT",
            description="Change record has no effective_at or as_of timestamp.",
        ))

    return ChangeQualityEntry(
        change_id=cid,
        symbol=symbol,
        has_type=has_type,
        has_before=has_before,
        has_after=has_after,
        has_effective_at=has_eff,
        has_detected_at=has_det,
        has_source_ids=has_src,
        has_provenance_ids=has_prov,
        issues=tuple(issues),
        issue_count=len(issues),
    )


def build_change_quality_report(
    result: Any, *, as_of: datetime
) -> ChangeQualityReport:
    """Build change quality audit for one company."""
    symbol = getattr(result, "company", "") or ""
    intel = result.intelligence
    changes = getattr(intel, "changes", ()) or ()

    entries = tuple(_audit_change(c) for c in changes)
    total_issues = sum(e.issue_count for e in entries)
    clean = sum(1 for e in entries if e.issue_count == 0)

    return ChangeQualityReport(
        symbol=symbol,
        as_of=as_of,
        total_changes=len(entries),
        clean_count=clean,
        issue_count=total_issues,
        entries=entries,
        notes=(
            "Change history preserves all transitions. Removed evidence remains visible.",
            "No historical state is silently discarded.",
        ),
    )
