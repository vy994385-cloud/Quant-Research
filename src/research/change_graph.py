"""
Research Change Graph — deterministic relationship metadata between changes.

Models how evidence changes, financial changes, events, technology evidence,
gap transitions, source freshness changes, and screen entry/exit relate to
each other in time.

Relationship vocabulary is restricted to:
  - "related to"
  - "occurred alongside"
  - "recorded in same context"

No causal language ("caused by", "led to", "will cause") is ever emitted
unless the recorded evidence explicitly establishes such a relationship.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.research.change import ChangeType, ResearchChange


class RelationshipType(str, Enum):
    RELATED_TO = "related_to"
    OCCURRED_ALONGSIDE = "occurred_alongside"
    SAME_CONTEXT = "recorded_in_same_context"


class ChangeRelationship(BaseModel):
    """One deterministic relationship between two changes."""

    model_config = ConfigDict(extra="forbid")

    relationship_id: str = Field(min_length=1)
    source_change_id: str = Field(min_length=1)
    target_change_id: str = Field(min_length=1)
    relationship_type: RelationshipType
    evidence_ids: tuple[str, ...] = ()
    event_ids: tuple[str, ...] = ()
    gap_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    effective_at: datetime | None = None
    detected_at: datetime | None = None
    as_of: datetime | None = None
    note: str = ""


class ChangeGraph(BaseModel):
    """
    A deterministic graph of research changes and their relationships.

    Answers: "What changed, and how are the changes related to each other?"
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    changes: tuple[ResearchChange, ...] = ()
    relationships: tuple[ChangeRelationship, ...] = ()
    change_count: int = Field(ge=0)
    relationship_count: int = Field(ge=0)
    notes: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def _require_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return v


def _rel_hash(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:16]
    return f"rel-{digest}"


def _same_context_relationships(
    changes: tuple[ResearchChange, ...],
    as_of: datetime,
) -> list[ChangeRelationship]:
    """
    Changes detected at the same as_of with related evidence/source
    references are recorded in the same context.
    """

    if len(changes) < 2:
        return []

    # Group by source/provenance overlap
    by_source: dict[str, list[ResearchChange]] = {}
    for ch in changes:
        for prov in (ch.provenance or ()):
            by_source.setdefault(prov, []).append(ch)
        if ch.source:
            by_source.setdefault(ch.source, []).append(ch)

    seen_pairs: set[tuple[str, str]] = set()
    relationships: list[ChangeRelationship] = []

    for source_key, group in by_source.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                pair = (min(a.change_id, b.change_id), max(a.change_id, b.change_id))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                evidence_overlap = tuple(
                    sorted(
                        set(
                            (a.related_observation or "").split(",")
                        )
                        & set(
                            (b.related_observation or "").split(",")
                        )
                        - {""}
                    )
                )
                relationships.append(
                    ChangeRelationship(
                        relationship_id=_rel_hash(
                            pair[0], pair[1], "SAME_CONTEXT"
                        ),
                        source_change_id=pair[0],
                        target_change_id=pair[1],
                        relationship_type=RelationshipType.SAME_CONTEXT,
                        evidence_ids=evidence_overlap,
                        effective_at=a.effective_at or b.effective_at,
                        detected_at=a.detected_at,
                        as_of=as_of,
                        note=f"Both detected in the same context ({source_key})",
                    )
                )

    return relationships


def _occurred_alongside_relationships(
    changes: tuple[ResearchChange, ...],
    as_of: datetime,
) -> list[ChangeRelationship]:
    """
    Changes with overlapping effective_at dates are recorded as
    occurring alongside each other.
    """

    if len(changes) < 2:
        return []

    # Group by effective date (date only, not time)
    by_date: dict[str, list[ResearchChange]] = {}
    for ch in changes:
        if ch.effective_at is not None:
            key = ch.effective_at.strftime("%Y-%m-%d")
            by_date.setdefault(key, []).append(ch)

    seen_pairs: set[tuple[str, str]] = set()
    relationships: list[ChangeRelationship] = []

    for _date_key, group in by_date.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a.change_type == b.change_type:
                    continue
                pair = (min(a.change_id, b.change_id), max(a.change_id, b.change_id))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                relationships.append(
                    ChangeRelationship(
                        relationship_id=_rel_hash(
                            pair[0], pair[1], "ALONGSIDE"
                        ),
                        source_change_id=pair[0],
                        target_change_id=pair[1],
                        relationship_type=RelationshipType.OCCURRED_ALONGSIDE,
                        effective_at=a.effective_at,
                        detected_at=a.detected_at,
                        as_of=as_of,
                        note=f"Different change types with same effective date ({_date_key})",
                    )
                )

    return relationships


def _related_to_relationships(
    changes: tuple[ResearchChange, ...],
    as_of: datetime,
) -> list[ChangeRelationship]:
    """
    Changes that share related_observation or provenance links
    are related to each other.
    """

    if len(changes) < 2:
        return []

    # Index by related_observation
    by_related: dict[str, list[ResearchChange]] = {}
    for ch in changes:
        if ch.related_observation:
            by_related.setdefault(ch.related_observation, []).append(ch)

    seen_pairs: set[tuple[str, str]] = set()
    relationships: list[ChangeRelationship] = []

    for _obs_key, group in by_related.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a.change_type == b.change_type:
                    continue
                pair = (min(a.change_id, b.change_id), max(a.change_id, b.change_id))
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)

                shared_prov = tuple(
                    sorted(set(a.provenance) & set(b.provenance))
                )

                relationships.append(
                    ChangeRelationship(
                        relationship_id=_rel_hash(
                            pair[0], pair[1], "RELATED"
                        ),
                        source_change_id=pair[0],
                        target_change_id=pair[1],
                        relationship_type=RelationshipType.RELATED_TO,
                        source_ids=tuple(
                            sorted(
                                {a.source, b.source} - {None}
                            )
                        ),
                        evidence_ids=(a.related_observation,) if a.related_observation else (),
                        effective_at=a.effective_at or b.effective_at,
                        detected_at=a.detected_at,
                        as_of=as_of,
                        note=f"Changes share observation reference ({_obs_key})",
                    )
                )

    return relationships


def build_change_graph(
    changes: tuple[ResearchChange, ...],
    *,
    symbol: str,
    as_of: datetime,
) -> ChangeGraph:
    """
    Build a deterministic change graph from a set of research changes.

    Emits only safe relationship vocabulary:
    related_to, occurred_alongside, recorded_in_same_context.
    Never causal.
    """

    all_relationships: list[ChangeRelationship] = []
    all_relationships.extend(_same_context_relationships(changes, as_of))
    all_relationships.extend(_occurred_alongside_relationships(changes, as_of))
    all_relationships.extend(_related_to_relationships(changes, as_of))

    # Deduplicate by relationship_id
    seen: set[str] = set()
    unique: list[ChangeRelationship] = []
    for rel in all_relationships:
        if rel.relationship_id not in seen:
            seen.add(rel.relationship_id)
            unique.append(rel)

    unique.sort(key=lambda r: r.relationship_id)

    notes: list[str] = []
    if not changes:
        notes.append("No changes to graph.")
    if not unique and changes:
        notes.append(
            "No deterministic relationships found between the recorded changes."
        )

    return ChangeGraph(
        symbol=symbol,
        as_of=as_of,
        changes=changes,
        relationships=tuple(unique),
        change_count=len(changes),
        relationship_count=len(unique),
        notes=tuple(notes),
    )


__all__ = [
    "ChangeGraph",
    "ChangeRelationship",
    "RelationshipType",
    "build_change_graph",
]
