"""
Research-change tracking.

Extends the existing tracking foundation (src.tracking) with
changes detected across the full research surface of a company:

- new / updated / resolved evidence (intelligence changes)
- new financial periods and disclosures
- new company events
- new corporate actions
- new technology evidence
- research-gap state
- source freshness state

Every change carries evidence traceability (source names and
provenance ids) where the underlying data provides it. This module
describes what changed in the research; it never generates alerts
with investment meaning, scores, or recommendations.
"""

from __future__ import annotations

from datetime import datetime

from src.research.company_intel.semantics import (
    IntelCategory,
    IntelKind,
    ChangeType,
)
from src.tracking.models import (
    ChangeDomain,
    CompanyTrackingResult,
    TrackedChangeType,
    TrackingChange,
    TrackingSeverity,
)

_RECENT_WINDOW_DAYS = 90

_SEVERITY_BY_CHANGE_TYPE = {
    ChangeType.NEW: TrackingSeverity.NOTABLE,
    ChangeType.UPDATED: TrackingSeverity.INFO,
    ChangeType.RESOLVED: TrackingSeverity.NOTABLE,
    ChangeType.CONFLICTING: TrackingSeverity.SIGNIFICANT,
}


def _require_aware(as_of: datetime) -> None:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")


def _change_from_intel_change(intel_change, symbol: str, as_of: datetime):
    """Map an intelligence snapshot change onto a tracked change."""

    kind = intel_change.kind
    change_type = intel_change.change_type

    if change_type == ChangeType.UNCHANGED:
        return None

    if kind == IntelKind.FINANCIAL_PERIOD:
        domain = ChangeDomain.FINANCIAL
        title = "New financial period disclosed"
        tracked_type = TrackedChangeType.NEW_FINANCIAL_DISCLOSURE
    elif (
        intel_change.intel_category is not None
        and intel_change.intel_category == IntelCategory.CORPORATE_ACTION
    ):
        domain = ChangeDomain.CORPORATE_ACTION
        title = "Corporate action recorded"
        tracked_type = TrackedChangeType.NEW_CORPORATE_ACTION
    elif kind == IntelKind.MANAGEMENT_COMMENTARY:
        domain = ChangeDomain.NEWS
        title = "Management commentary updated"
        tracked_type = TrackedChangeType.NEW_EVIDENCE
    else:
        domain = ChangeDomain.EVIDENCE
        title = "New evidence recorded"
        tracked_type = TrackedChangeType.NEW_EVIDENCE

    severity = _SEVERITY_BY_CHANGE_TYPE.get(
        change_type, TrackingSeverity.INFO
    )

    description_parts = [intel_change.description or intel_change.title]
    if intel_change.previous_title:
        description_parts.append(
            f"Previous title: {intel_change.previous_title}."
        )

    return TrackingChange(
        change_id=f"{symbol}-intel-{intel_change.item_id}",
        symbol=symbol,
        domain=domain,
        severity=severity,
        change_type=tracked_type,
        title=title,
        description=" ".join(description_parts),
        previous_value=intel_change.previous_checksum,
        current_value=intel_change.current_checksum,
        change_date=(
            intel_change.published_at.date()
            if intel_change.published_at is not None
            else None
        ),
        effective_at=(
            intel_change.available_at or intel_change.published_at
        ),
        pit_eligible=intel_change.available_at is not None,
        detected_at=as_of,
        as_of=as_of,
    )


def _recent_event_changes(items, symbol: str, as_of: datetime):
    """Surface recent business events and corporate actions."""

    changes: list[TrackingChange] = []

    for item in items:
        stamp = item.published_at or item.available_at
        if stamp is None:
            continue

        if (as_of - stamp).days > _RECENT_WINDOW_DAYS:
            continue

        if item.intel_category == IntelCategory.CORPORATE_ACTION:
            changes.append(
                TrackingChange(
                    change_id=f"{symbol}-action-{item.item_id}",
                    symbol=symbol,
                    domain=ChangeDomain.CORPORATE_ACTION,
                    severity=TrackingSeverity.INFO,
                    change_type=TrackedChangeType.NEW_CORPORATE_ACTION,
                    title=item.title,
                    description=item.description,
                    change_date=stamp.date(),
                    effective_at=item.effective_at,
                    evidence_refs=(item.provenance_id,)
                    if item.provenance_id
                    else (),
                    source_names=(item.source.source_name,),
                    provenance_ids=(item.provenance_id,)
                    if item.provenance_id
                    else (),
                    pit_eligible=item.available_at is not None,
                    detected_at=as_of,
                    as_of=as_of,
                )
            )
        elif item.kind == IntelKind.BUSINESS_EVENT:
            severity = (
                TrackingSeverity.NOTABLE
                if item.event_type is not None
                else TrackingSeverity.INFO
            )
            changes.append(
                TrackingChange(
                    change_id=f"{symbol}-event-{item.item_id}",
                    symbol=symbol,
                    domain=ChangeDomain.NEWS,
                    severity=severity,
                    change_type=TrackedChangeType.NEW_EVENT,
                    title=item.title,
                    description=item.description,
                    change_date=stamp.date(),
                    effective_at=item.effective_at,
                    evidence_refs=(item.provenance_id,)
                    if item.provenance_id
                    else (),
                    source_names=(item.source.source_name,),
                    provenance_ids=(item.provenance_id,)
                    if item.provenance_id
                    else (),
                    pit_eligible=item.available_at is not None,
                    detected_at=as_of,
                    as_of=as_of,
                )
            )

    return changes


def _technology_evidence_changes(evidence_items, symbol: str, as_of: datetime):
    """Surface recent technology evidence."""

    changes: list[TrackingChange] = []

    for item in evidence_items:
        if item.evidence_type.value != "FUTURE_TECHNOLOGY":
            continue

        stamp = item.published_at or item.observation_at
        if stamp is None:
            continue

        if (as_of - stamp).days > _RECENT_WINDOW_DAYS:
            continue

        changes.append(
            TrackingChange(
                change_id=f"{symbol}-tech-{item.evidence_id}",
                symbol=symbol,
                domain=ChangeDomain.TECHNOLOGY,
                severity=TrackingSeverity.INFO,
                change_type=TrackedChangeType.NEW_TECHNOLOGY_EVIDENCE,
                title=item.title,
                description=item.explanation,
                change_date=stamp.date(),
                evidence_refs=tuple(item.provenance_ids),
                source_names=tuple(item.source_ids),
                provenance_ids=tuple(item.provenance_ids),
                pit_eligible=item.available_at is not None,
                detected_at=as_of,
                as_of=as_of,
            )
        )

    return changes


def _research_gap_changes(research_gaps, symbol: str, as_of: datetime):
    """Surface the current open research-gap state at as_of."""

    if research_gaps is None:
        return []

    actionable_statuses = {
        "UNAVAILABLE",
        "STALE",
        "CONFLICTING",
        "INSUFFICIENT_EVIDENCE",
    }

    changes: list[TrackingChange] = []

    for gap in research_gaps.gaps:
        if gap.status not in actionable_statuses:
            continue

        severity_map = {
            "HIGH": TrackingSeverity.SIGNIFICANT,
            "MEDIUM": TrackingSeverity.NOTABLE,
            "LOW": TrackingSeverity.INFO,
        }
        severity = severity_map.get(gap.priority, TrackingSeverity.INFO)

        changes.append(
            TrackingChange(
                change_id=f"{symbol}-gap-{gap.gap_id}",
                symbol=symbol,
                domain=ChangeDomain.RESEARCH_GAP,
                severity=severity,
                change_type=TrackedChangeType.RESEARCH_GAP_CHANGED,
                title=f"Research gap ({gap.status.lower()}): {gap.gap}",
                description=gap.reason,
                current_value=gap.status,
                evidence_refs=tuple(gap.evidence_refs),
                source_names=tuple(gap.sources_checked),
                detected_at=as_of,
                as_of=as_of,
            )
        )

    return changes


def _source_freshness_changes(source_statuses, symbol: str, as_of: datetime):
    """Surface stale-source freshness state at as_of."""

    changes: list[TrackingChange] = []

    for status in source_statuses:
        if not status.stale:
            continue

        days = status.days_since_latest_published
        description = (
            f"Latest published disclosure from this source was "
            f"{days} days before as_of."
            if days is not None
            else "No published disclosure is recorded for this source."
        )

        changes.append(
            TrackingChange(
                change_id=f"{symbol}-fresh-{status.source_name}",
                symbol=symbol,
                domain=ChangeDomain.EVIDENCE,
                severity=TrackingSeverity.NOTABLE,
                change_type=TrackedChangeType.SOURCE_BECAME_STALE,
                title=f"Source freshness: {status.source_name} is stale",
                description=description,
                previous_value=None,
                current_value=str(days)
                if days is not None
                else None,
                change_date=(
                    status.latest_published_at.date()
                    if status.latest_published_at is not None
                    else None
                ),
                source_names=(status.source_name,),
                detected_at=as_of,
                as_of=as_of,
            )
        )

    return changes


def build_research_change_result(result, as_of: datetime) -> CompanyTrackingResult:
    """
    Build a cross-domain research-change result for one recorded
    research result. Deterministic and PIT-safe: every input was
    already knowable at result.as_of.
    """

    _require_aware(as_of)
    symbol = result.company

    intel = result.intelligence
    changes: list[TrackingChange] = []

    if intel is not None:
        for intel_change in intel.changes:
            change = _change_from_intel_change(intel_change, symbol, as_of)
            if change is not None:
                changes.append(change)

        changes.extend(
            _recent_event_changes(intel.items, symbol, as_of)
        )
        changes.extend(
            _source_freshness_changes(
                intel.source_statuses, symbol, as_of
            )
        )
        changes.extend(
            _research_gap_changes(intel.research_gaps, symbol, as_of)
        )

    changes.extend(
        _technology_evidence_changes(
            result.evidence_items or (), symbol, as_of
        )
    )

    # Deduplicate by change id (an intel item may appear both via the
    # snapshot diff and the recent-event window).
    unique: dict[str, TrackingChange] = {}
    for change in changes:
        existing = unique.get(change.change_id)
        if existing is None or change.severity != TrackingSeverity.INFO:
            unique[change.change_id] = change

    ordered = sorted(
        unique.values(),
        key=lambda c: (c.change_date or as_of.date(), c.change_id),
        reverse=True,
    )

    return CompanyTrackingResult.from_changes(
        symbol=symbol,
        as_of=as_of,
        changes=tuple(ordered),
    )


__all__ = [
    "build_research_change_result",
]
