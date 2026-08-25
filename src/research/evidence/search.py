"""
Deterministic lexical search over canonical evidence records.

Searches the recorded evidence lineage (titles, explanations,
categories, topics, linked claims) with plain term matching:

- every term must appear (AND semantics), case-insensitive;
- an optional exact phrase must appear as a contiguous substring;
- no similarity scores, no embeddings, no ranking heuristics —
  ordering is fully determined by timestamps and ids;
- each hit carries a categorical match_tier (title / text /
  metadata-only) and the explicit list of fields that matched —
  these are labels for transparency, never relevance scores;
- optional company / category / source / date-range / observation-
  window filters;
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
    exact_phrase: str | None = None
    symbol: str | None = None
    category: str | None = None
    source_id: str | None = None
    published_from: date | None = None
    published_to: date | None = None
    observation_from: date | None = None
    observation_to: date | None = None
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

    # Transparency labels (never scores): where the terms matched.
    match_tier: str = Field(default="text")
    matched_fields: tuple[str, ...] = ()
    snippet: str | None = None


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


_SNIPPET_RADIUS = 90


def _snippet_for(text: str, terms: tuple[str, ...]) -> str | None:
    """Deterministic excerpt around the first term occurrence."""

    positions = [
        text.find(term)
        for term in terms
        if text.find(term) >= 0
    ]
    if not positions:
        return None
    start = max(0, min(positions) - _SNIPPET_RADIUS)
    end = min(len(text), min(positions) + _SNIPPET_RADIUS)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def _match_fields_and_tier(
    item,
    claims_by_evidence,
    terms: tuple[str, ...],
) -> tuple[str, tuple[str, ...]]:
    """
    Categorical match labeling (never a score).

    Returns (tier, matched_fields):
    - tier 'title': every term matches within the title;
    - tier 'text': every term matches across title + explanation +
      linked claim texts;
    - tier 'metadata': some term only matches category/topic/type/
      source identifiers.
    """

    title = item.title.lower()
    body_parts = [item.explanation.lower()]
    for claim in claims_by_evidence.get(item.evidence_id, ()):
        body_parts.append(str(claim.text).lower())
    body = " ".join(body_parts)
    metadata = " ".join(
        [
            (item.category or "").lower(),
            (item.topic or "").lower(),
            item.evidence_type.value
            if hasattr(item.evidence_type, "value")
            else str(item.evidence_type),
            " ".join(item.source_ids).lower(),
        ]
    )

    matched: list[str] = []
    in_title_all = True
    in_text_all = True

    for term in terms:
        in_title = term in title
        in_body = term in body
        in_meta = term in metadata
        if in_title and "title" not in matched:
            matched.append("title")
        if in_body and "text" not in matched:
            matched.append("text")
        if in_meta and "metadata" not in matched:
            matched.append("metadata")
        if not in_title:
            in_title_all = False
        if not (in_title or in_body or in_meta):
            in_title_all = False
            in_text_all = False
        elif not in_body and not in_title:
            in_text_all = False

    if in_title_all:
        tier = "title"
    elif in_text_all:
        tier = "text"
    else:
        tier = "metadata"

    field_order = {"title": 0, "text": 1, "metadata": 2}
    ordered = tuple(
        sorted(matched, key=lambda name: field_order.get(name, 9))
    )
    return tier, ordered


def search_evidence(
    lineage,
    *,
    text: str = "",
    exact_phrase: str | None = None,
    symbol: str | None = None,
    category: str | None = None,
    source_id: str | None = None,
    published_from: date | None = None,
    published_to: date | None = None,
    observation_from: date | None = None,
    observation_to: date | None = None,
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
    phrase = (
        exact_phrase.strip().lower()
        if exact_phrase and exact_phrase.strip()
        else None
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

        if observation_from is not None or observation_to is not None:
            observed = item.observation_at
            if observed is None:
                continue
            day = observed.date()
            if observation_from is not None and day < observation_from:
                continue
            if observation_to is not None and day > observation_to:
                continue

        haystack = _haystack_for(item, claims_by_evidence)

        missing = [t for t in terms if t not in haystack]
        if missing:
            continue

        if phrase is not None and phrase not in haystack:
            continue

        match_tier, matched_fields = _match_fields_and_tier(
            item,
            claims_by_evidence,
            terms,
        )

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
                match_tier=match_tier,
                matched_fields=matched_fields,
                snippet=_snippet_for(
                    item.explanation, terms
                )
                if terms
                else None,
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
            exact_phrase=exact_phrase if phrase else None,
            symbol=symbol.strip().upper() if symbol else None,
            category=category,
            source_id=source_id,
            published_from=published_from,
            published_to=published_to,
            observation_from=observation_from,
            observation_to=observation_to,
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
