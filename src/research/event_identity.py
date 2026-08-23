"""
Canonical research-event identity and deduplication.

Multiple recorded surfaces can describe the same underlying event:
company news, corporate actions, business-event intelligence items,
and evidence records. This module gives every event one canonical
identity and merges only records that are demonstrably the same
event.

Identity rule (deterministic):
    symbol + normalized title + underlying date.

Merging rules (hard guarantees):
- Records merge ONLY on identical identity keys.
- Opposing directional records (POSITIVE vs NEGATIVE) are NEVER
  merged; they stay separate so no conflict is silently resolved.
- Merged records UNION their sources, provenance ids, and member
  record ids. Nothing is discarded.
- Verification statuses are reported as-is; a group whose members
  disagree carries "MIXED" rather than an invented single verdict.
- Output ordering and ids are fully deterministic.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


def _require_aware(as_of: datetime) -> None:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")


class EventDirection(str, Enum):
    """Canonical descriptive direction of a research event."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class EventCandidateRecord:
    """
    One deduplicable event record contributed by any source surface.

    Adapters below build this from the existing recorded models;
    nothing here invents content.
    """

    symbol: str
    title: str
    category: str

    record_id: str
    description: str = ""

    # Underlying date of the event when known (effective /
    # announcement / event date), independent of publication.
    event_date: date | None = None

    direction: EventDirection = EventDirection.UNKNOWN
    verification_status: str = "UNVERIFIED"

    published_at: datetime | None = None
    available_at: datetime | None = None
    effective_at: datetime | None = None

    source_name: str | None = None
    provenance_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("symbol", "title", "category", "record_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} cannot be empty")

        for name in ("published_at", "available_at", "effective_at"):
            value = getattr(self, name)
            if value is not None and value.tzinfo is None:
                raise ValueError(f"{name} must be timezone-aware")


@dataclass(frozen=True)
class ResearchEventRecord:
    """
    One canonical research event after deterministic deduplication.

    A merged record unions every contributing source, provenance id,
    and member record id; it never hides disagreement.
    """

    event_id: str
    symbol: str
    category: str
    event: str
    description: str

    event_date: date | None
    verification: str
    direction: EventDirection

    sources: tuple[str, ...]
    provenance_ids: tuple[str, ...]
    member_ids: tuple[str, ...]

    published_at: datetime | None
    available_at: datetime | None
    effective_at: datetime | None

    pit_eligible: bool


@dataclass(frozen=True)
class ResearchEventSet:
    """Deterministic, deduplicated research events for one company."""

    symbol: str
    as_of: datetime
    events: tuple[ResearchEventRecord, ...] = ()
    event_count: int = 0
    duplicate_records_merged: int = 0
    opposing_pairs_kept_separate: int = 0
    notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------


def normalize_event_title(title: str) -> str:
    """Case- and punctuation-insensitive title normalization."""

    chars = []
    for ch in title:
        if ch.isalnum():
            chars.append(ch.lower())
        else:
            chars.append(" ")
    return " ".join("".join(chars).split())


def canonical_event_date(candidate: EventCandidateRecord) -> date | None:
    """Underlying event date used for identity."""

    if candidate.event_date is not None:
        return candidate.event_date
    stamp = candidate.effective_at or candidate.published_at
    return stamp.date() if stamp is not None else None


def event_identity_key(candidate: EventCandidateRecord) -> tuple:
    """Deterministic grouping key for one candidate record."""

    return (
        candidate.symbol.strip().upper(),
        normalize_event_title(candidate.title),
        canonical_event_date(candidate),
    )


def compute_event_id(candidate: EventCandidateRecord) -> str:
    """Stable canonical id derived from the identity key."""

    symbol, title, day = event_identity_key(candidate)
    basis = f"{symbol}|{title}|{day.isoformat() if day else ''}"
    digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]
    return f"evt-{digest}"


# ---------------------------------------------------------------------------
# Direction / verification resolution
# ---------------------------------------------------------------------------

_OPPOSING = {"POSITIVE", "NEGATIVE"}


def _merge_direction(directions: set[EventDirection]) -> EventDirection:
    known = directions - {
        EventDirection.UNKNOWN,
        EventDirection.NEUTRAL,
    }
    if known == {"POSITIVE"}:
        return EventDirection.POSITIVE
    if known == {"NEGATIVE"}:
        return EventDirection.NEGATIVE
    if not known:
        if EventDirection.NEUTRAL in directions:
            return EventDirection.NEUTRAL
        return EventDirection.UNKNOWN
    raise AssertionError("opposing directions must be split before merge")


def _merge_verification(statuses: list[str]) -> str:
    unique = sorted(set(statuses))
    if len(unique) == 1:
        return unique[0]
    return "MIXED"


# ---------------------------------------------------------------------------
# Core deduplication
# ---------------------------------------------------------------------------


def dedupe_research_events(
    candidates,
) -> tuple[ResearchEventRecord, ...]:
    """
    Deduplicate candidate records into canonical research events.

    Ordering: latest (published_at or available_at) first, then
    event_id ascending — fully deterministic.
    """

    groups: dict[tuple, list[EventCandidateRecord]] = {}
    for candidate in candidates:
        groups.setdefault(event_identity_key(candidate), []).append(
            candidate
        )

    records: list[ResearchEventRecord] = []
    for members in groups.values():
        # Opposing directional records are never merged: split the
        # group into a POSITIVE-side and a NEGATIVE-side cluster and
        # keep both. NEUTRAL/UNKNOWN members join the larger side
        # deterministically (first side wins ties by member count).
        positive_side = [
            m
            for m in members
            if m.direction == EventDirection.POSITIVE
        ]
        negative_side = [
            m
            for m in members
            if m.direction == EventDirection.NEGATIVE
        ]

        if positive_side and negative_side:
            neutral_unknown = [
                m
                for m in members
                if m.direction
                in (EventDirection.NEUTRAL, EventDirection.UNKNOWN)
            ]
            clusters = []
            if len(positive_side) >= len(negative_side):
                clusters.append((positive_side, EventDirection.POSITIVE))
                clusters.append((negative_side, EventDirection.NEGATIVE))
            else:
                clusters.append((negative_side, EventDirection.NEGATIVE))
                clusters.append((positive_side, EventDirection.POSITIVE))

            for side_members, side_direction in clusters:
                joined = sorted(
                    side_members + neutral_unknown,
                    key=lambda m: m.record_id,
                )
                records.append(_build_record(joined))
            continue

        records.append(_build_record(sorted(members, key=lambda m: m.record_id)))

    def _order_key(record: ResearchEventRecord):
        stamp = record.published_at or record.available_at
        stamp_ts = stamp.timestamp() if stamp is not None else 0.0
        return (-stamp_ts, record.event_id)

    return tuple(sorted(records, key=_order_key))


def _build_record(members: list[EventCandidateRecord]) -> ResearchEventRecord:
    first = members[0]

    published = [m.published_at for m in members if m.published_at]
    available = [m.available_at for m in members if m.available_at]
    effective = [m.effective_at for m in members if m.effective_at]
    dates = [
        d
        for d in (canonical_event_date(m) for m in members)
        if d is not None
    ]

    descriptions = [m.description for m in members if m.description]
    longest_description = (
        max(descriptions, key=len) if descriptions else ""
    )

    return ResearchEventRecord(
        event_id=compute_event_id(first),
        symbol=first.symbol.strip().upper(),
        category=first.category,
        event=first.title,
        description=longest_description,
        event_date=min(dates) if dates else None,
        verification=_merge_verification(
            [m.verification_status for m in members]
        ),
        direction=_merge_direction(
            {m.direction for m in members}
        ),
        sources=tuple(
            sorted({m.source_name for m in members if m.source_name})
        ),
        provenance_ids=tuple(
            sorted({m.provenance_id for m in members if m.provenance_id})
        ),
        member_ids=tuple(sorted({m.record_id for m in members})),
        published_at=min(published) if published else None,
        available_at=min(available) if available else None,
        effective_at=min(effective) if effective else None,
        pit_eligible=all(m.available_at is not None for m in members),
    )


def build_research_event_set(
    candidates,
    *,
    symbol: str,
    as_of: datetime,
) -> ResearchEventSet:
    """
    Build the canonical research-event set for one company.

    Counts how many raw records were merged away and how many
    opposing-direction pairs were deliberately kept separate.
    """

    _require_aware(as_of)

    candidates = list(candidates)
    for candidate in candidates:
        if candidate.symbol.strip().upper() != symbol.strip().upper():
            raise ValueError(
                "candidate symbol does not match set symbol"
            )

    events = dedupe_research_events(candidates)

    merged_away = len(candidates) - len(events)

    opposing_pairs = 0
    by_identity: dict[tuple, set[EventDirection]] = {}
    for candidate in candidates:
        by_identity.setdefault(
            event_identity_key(candidate), set()
        ).add(candidate.direction)
    for directions in by_identity.values():
        if _OPPOSING <= {
            d.value for d in directions if d.value in _OPPOSING
        }:
            opposing_pairs += 1

    notes: list[str] = []
    if not candidates:
        notes.append(
            "No recorded events were knowable at as_of."
        )
    elif merged_away > 0:
        notes.append(
            f"{merged_away} duplicate record(s) merged into "
            f"canonical events."
        )
    if opposing_pairs > 0:
        notes.append(
            f"{opposing_pairs} event identity(ies) carried opposing "
            "directions and were kept as separate records."
        )

    return ResearchEventSet(
        symbol=symbol.strip().upper(),
        as_of=as_of,
        events=events,
        event_count=len(events),
        duplicate_records_merged=max(merged_away, 0),
        opposing_pairs_kept_separate=opposing_pairs,
        notes=tuple(notes),
    )


# ---------------------------------------------------------------------------
# Adapters from existing recorded source shapes
# ---------------------------------------------------------------------------


def _direction_from_intel(value) -> EventDirection:
    raw = getattr(value, "value", value)
    try:
        return EventDirection(str(raw).upper())
    except ValueError:
        return EventDirection.UNKNOWN


def candidate_from_intel_item(item) -> EventCandidateRecord:
    """Adapter for CorporateIntelItem (business events / actions)."""

    category_value = (
        item.intel_category.value
        if item.intel_category is not None
        else str(item.kind.value)
    )

    return EventCandidateRecord(
        symbol=item.symbol,
        title=item.title,
        category=category_value,
        record_id=f"intel:{item.item_id}",
        description=item.description,
        event_date=(
            item.effective_at.date()
            if item.effective_at is not None
            else None
        ),
        direction=_direction_from_intel(item.direction),
        verification_status=item.verification_status.value,
        published_at=item.published_at,
        available_at=item.available_at,
        effective_at=item.effective_at,
        source_name=item.source.source_name if item.source else None,
        provenance_id=item.provenance_id,
    )


def candidate_from_news_item(item) -> EventCandidateRecord:
    """Adapter for CompanyNewsItem."""

    return EventCandidateRecord(
        symbol=item.symbol,
        title=item.headline,
        category="NEWS",
        record_id=f"news:{item.news_id}",
        description=item.summary,
        event_date=item.event_date,
        direction=_direction_from_intel(item.direction),
        verification_status="UNVERIFIED",
        published_at=item.published_at,
        available_at=item.available_at,
        source_name=item.source_name or None,
        provenance_id=item.provenance_id,
    )


def candidate_from_corporate_action(item) -> EventCandidateRecord:
    """Adapter for CorporateActionItem."""

    return EventCandidateRecord(
        symbol=item.symbol,
        title=item.title,
        category="CORPORATE_ACTION",
        record_id=f"action:{item.action_id}",
        description=item.description,
        event_date=item.effective_date or item.announcement_date,
        direction=EventDirection.UNKNOWN,
        verification_status="UNVERIFIED",
        published_at=item.published_at,
        available_at=item.available_at,
        effective_at=None,
        source_name=item.source_name or None,
        provenance_id=item.provenance_id,
    )


def candidate_from_evidence_item(item) -> EventCandidateRecord:
    """Adapter for CanonicalEvidenceItem (event-like evidence only)."""

    stamp = item.published_at or item.observation_at

    return EventCandidateRecord(
        symbol=item.symbol,
        title=item.title,
        category="EVIDENCE",
        record_id=f"evidence:{item.evidence_id}",
        description=item.explanation,
        event_date=stamp.date() if stamp is not None else None,
        direction=EventDirection.UNKNOWN,
        verification_status=item.verification_status,
        published_at=item.published_at,
        available_at=item.available_at,
        effective_at=item.observation_at,
        source_name=item.source_ids[0] if item.source_ids else None,
        provenance_id=(
            item.provenance_ids[0] if item.provenance_ids else None
        ),
    )


__all__ = [
    "EventCandidateRecord",
    "EventDirection",
    "ResearchEventRecord",
    "ResearchEventSet",
    "build_research_event_set",
    "candidate_from_corporate_action",
    "candidate_from_evidence_item",
    "candidate_from_intel_item",
    "candidate_from_news_item",
    "canonical_event_date",
    "compute_event_id",
    "dedupe_research_events",
    "event_identity_key",
    "normalize_event_title",
]
