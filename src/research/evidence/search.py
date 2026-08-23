"""
Deterministic lexical search over canonical evidence records.

Searches the recorded evidence lineage (titles, explanations,
categories, topics, linked claims) with plain term matching:

- every term must appear (AND semantics), case-insensitive;
- no similarity scores, no embeddings, no ranking heuristics —
  ordering is fully determined by timestamps and ids;
- optional company / category / source / date-range filters;
- optional point-in-time cutoff: only evidence that is provably
  knowable at as_of is returned.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


def _require_aware(as_of: datetime) -> None:
    if as_of.tzinfo is not None:
        return
    raise ValueError("as_of must be timezone-aware")


class EvidenceSearchQuery(BaseModel):
    """Echo of the executed query (stable field names)."""

    model_config = ConfigDict(extra="forbid")

    text_terms: tuple[str, ...] = ()
    symbol: str | None = None
    category: str | None = None
    source_id: str | None = None
    published_from: date | None = None
    published_to: date | None = None
    as_of: datetime | None = None


class EvidenceSearchHit(BaseModel):
    """One matching evidence record with full lineage."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    title: str
    explanation: str
    category: str
    evidence_type: str
    direction: str

    verification_status: str
    epistemic_type: str

    # PIT status: True when an availability timestamp exists (and,
    # when searching historically, is on or before as_of).
    pit_eligible: bool

    observation_at: datetime | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None

    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()
    matched_claim_ids: tuple[str, ...] = ()


class EvidenceSearchResult(BaseModel):
    """Deterministic search result over one evidence lineage."""

    model_config = ConfigDict(extra="forbid")

    query: EvidenceSearchQuery
    hits: tuple[EvidenceSearchHit, ...] = ()
    hit_count: int = Field(ge=0)
    searched_count: int = Field(ge=0)
    notes: tuple[str, ...] = ()


def _haystack_for(item, claims_by_evidence) -> str:
    parts = [
        item.title,
        item.explanation,
        item.category,
        item.topic or "",
        item.evidence_type.value
        if hasattr(item.evidence_type, "value")
        else str(item.evidence_type),
        " ".join(item.source_ids),
    ]

    for claim in claims_by_evidence.get(item.evidence_id, ()):
        parts.append(claim.text)

    return " ".join(parts).lower()


def _claim_index(claims) -> dict[str, list]:
    index: dict[str, list] = {}
    for claim in claims or ():
        for evidence_id in claim.evidence_ids:
            index.setdefault(evidence_id, []).append(claim)
    return index


def _item_stamp(item) -> datetime | None:
    return item.published_at or item.observation_at or item.available_at


def search_evidence(
    lineage,
    *,
    text: str = "",
    symbol: str | None = None,
    category: str | None = None,
    source_id: str | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
    as_of: datetime | None = None,
) -> EvidenceSearchResult:
    """
    Execute a deterministic lexical search over one evidence lineage.

    lineage: an EvidenceLineage-like object (evidence + claims).
    """

    if as_of is not None:
        _require_aware(as_of)

    terms = tuple(
        t for t in (part.lower() for part in text.split()) if t
    )

    claims_by_evidence = _claim_index(getattr(lineage, "claims", ()))

    searched = 0
    hits: list[EvidenceSearchHit] = []

    for item in lineage.evidence:
        searched += 1

        if symbol is not None:
            normalized = symbol.strip().upper()
            if normalized and item.symbol.strip().upper() != normalized:
                continue

        if category is not None:
            wanted = category.strip().lower()
            if wanted and (item.category or "").strip().lower() != wanted:
                continue

        if source_id is not None:
            wanted_source = source_id.strip().lower()
            if wanted_source and wanted_source not in {
                s.lower() for s in item.source_ids
            }:
                continue

        if as_of is not None:
            # Historical search keeps only provably-knowable items.
            if item.available_at is None:
                continue
            if item.available_at > as_of:
                continue

        if published_from is not None or published_to is not None:
            stamp = item.published_at or item.observation_at
            if stamp is None:
                continue
            day = stamp.date()
            if published_from is not None and day < published_from:
                continue
            if published_to is not None and day > published_to:
                continue

        haystack = _haystack_for(item, claims_by_evidence)

        missing = [t for t in terms if t not in haystack]
        if missing:
            continue

        matched_claims = tuple(
            sorted(
                claim.claim_id
                for claim in claims_by_evidence.get(
                    item.evidence_id, ()
                )
            )
        )

        hits.append(
            EvidenceSearchHit(
                evidence_id=item.evidence_id,
                symbol=item.symbol,
                title=item.title,
                explanation=item.explanation,
                category=item.category,
                evidence_type=(
                    item.evidence_type.value
                    if hasattr(item.evidence_type, "value")
                    else str(item.evidence_type)
                ),
                direction=(
                    item.direction.value
                    if hasattr(item.direction, "value")
                    else str(item.direction)
                ),
                verification_status=item.verification_status,
                epistemic_type=(
                    item.epistemic_type.value
                    if hasattr(item.epistemic_type, "value")
                    else str(item.epistemic_type)
                ),
                pit_eligible=item.available_at is not None,
                observation_at=item.observation_at,
                published_at=item.published_at,
                available_at=item.available_at,
                source_ids=tuple(sorted(item.source_ids)),
                provenance_ids=tuple(sorted(item.provenance_ids)),
                matched_claim_ids=matched_claims,
            )
        )

    def _order_key(hit: EvidenceSearchHit):
        stamp = (
            hit.published_at
            or hit.observation_at
            or hit.available_at
        )
        stamp_ts = stamp.timestamp() if stamp is not None else 0.0
        return (-stamp_ts, hit.evidence_id)

    hits.sort(key=_order_key)

    notes: list[str] = []
    if searched and not hits:
        notes.append("No recorded evidence matched this search.")
    if as_of is not None and not hits and searched:
        notes.append(
            "Historical mode: only evidence provably knowable at "
            "as_of was considered."
        )

    return EvidenceSearchResult(
        query=EvidenceSearchQuery(
            text_terms=terms,
            symbol=symbol.strip().upper() if symbol else None,
            category=category,
            source_id=source_id,
            published_from=published_from,
            published_to=published_to,
            as_of=as_of,
        ),
        hits=tuple(hits),
        hit_count=len(hits),
        searched_count=searched,
        notes=tuple(notes),
    )


__all__ = [
    "EvidenceSearchHit",
    "EvidenceSearchQuery",
    "EvidenceSearchResult",
    "search_evidence",
]
