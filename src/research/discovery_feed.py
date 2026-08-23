"""
Discovery / research feed foundation.

Aggregates existing recorded research into one deterministic,
evidence-first feed that can power a Discover page:

- latest financial disclosures
- company developments
- management commentary
- technology developments
- corporate actions
- industry events
- recent research observations
- research-gap changes (open gap state at as_of)
- source freshness changes (stale-source state at as_of)

Every item preserves its symbol, timestamps (published_at /
available_at / effective_at), source, provenance id, and point-in-time
eligibility. Nothing is invented here: every field mirrors an
underlying recorded research artifact.

"Trending" is explicitly defined as the highest count of feed items
published inside a trailing window ending at as_of — a measure of
research coverage activity. It is never a popularity ranking and
never expresses an opinion about a company's prospects.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.research.company_intel.semantics import (
    IntelCategory,
    IntelKind,
)
from src.research.event_identity import (
    EventCandidateRecord,
    EventDirection,
    dedupe_research_events,
)


class FeedItemType(str, Enum):
    """Type of a discovery-feed item."""

    FINANCIAL_DISCLOSURE = "FINANCIAL_DISCLOSURE"
    COMPANY_DEVELOPMENT = "COMPANY_DEVELOPMENT"
    MANAGEMENT_COMMENTARY = "MANAGEMENT_COMMENTARY"
    TECHNOLOGY_DEVELOPMENT = "TECHNOLOGY_DEVELOPMENT"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    INDUSTRY_EVENT = "INDUSTRY_EVENT"
    RESEARCH_OBSERVATION = "RESEARCH_OBSERVATION"
    RESEARCH_GAP_CHANGE = "RESEARCH_GAP_CHANGE"
    SOURCE_FRESHNESS_CHANGE = "SOURCE_FRESHNESS_CHANGE"


_ACTIONABLE_GAP_STATUSES = {
    "UNAVAILABLE",
    "STALE",
    "CONFLICTING",
    "INSUFFICIENT_EVIDENCE",
}

_DEVELOPMENT_CATEGORIES = {
    IntelCategory.PRODUCT_BUSINESS_UPDATE,
    IntelCategory.ORDER_CONTRACT,
    IntelCategory.ACQUISITION_DIVESTMENT,
    IntelCategory.CAPEX_EXPANSION,
}

_TRENDING_DEFINITION = (
    "Trending ranks companies by the number of recorded research "
    "feed items published within the trailing window ending at "
    "as_of. It reflects recent research coverage activity across "
    "the verified universe only. It is not a popularity ranking, "
    "not a score, and carries no investment opinion."
)

TRENDING_DEFINITION = _TRENDING_DEFINITION


def _require_aware(as_of: datetime) -> None:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")


class DiscoveryFeedItem(BaseModel):
    """One aggregated, provenance-preserving research feed item."""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    item_type: FeedItemType

    title: str = Field(min_length=1)
    description: str = ""

    published_at: datetime | None = None
    available_at: datetime | None = None
    effective_at: datetime | None = None

    source_name: str | None = None
    source_type: str | None = None
    provenance_id: str | None = None

    # True when an availability timestamp exists so consumers can
    # reproduce point-in-time filtering themselves.
    pit_eligible: bool = False

    # Canonical-event additions (additive, back-compatible): when one
    # underlying event is recorded by several surfaces, the feed keeps
    # ONE canonical item and unions the contributing lineage here.
    event_id: str | None = None
    direction: str | None = None
    sources: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()
    member_ids: tuple[str, ...] = ()


class DiscoveryFeed(BaseModel):
    """A deterministic, ordered research feed."""

    model_config = ConfigDict(extra="forbid")

    as_of: datetime
    items: tuple[DiscoveryFeedItem, ...] = ()
    item_count: int = 0
    type_counts: dict[str, int] = Field(default_factory=dict)
    symbols_included: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    # Additive: how many raw records were merged into canonical
    # events by identity deduplication.
    duplicates_merged: int = 0


class TrendingCompany(BaseModel):
    """One company's trailing-window feed activity."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    recent_item_count: int = Field(ge=0)
    total_item_count: int = Field(ge=0)


class TrendingResult(BaseModel):
    """
    Deterministic activity ranking over the verified universe.

    Includes the explicit definition of trending used to compute it.
    """

    model_config = ConfigDict(extra="forbid")

    as_of: datetime
    window_days: int = Field(ge=1)

    definition: str
    ranked: tuple[TrendingCompany, ...] = ()


# ---------------------------------------------------------------------------
# Item mapping helpers
# ---------------------------------------------------------------------------


def _direction_value(raw) -> str | None:
    value = getattr(raw, "value", raw)
    if not isinstance(value, str):
        return None
    return value.upper()


def _classify_intel_item(item) -> FeedItemType | None:
    """Deterministically classify one intelligence item."""

    category = item.intel_category

    if (
        item.kind == IntelKind.FINANCIAL_PERIOD
        or category == IntelCategory.FINANCIAL_DISCLOSURE
    ):
        return FeedItemType.FINANCIAL_DISCLOSURE

    if category == IntelCategory.CORPORATE_ACTION:
        return FeedItemType.CORPORATE_ACTION

    if (
        item.kind == IntelKind.MANAGEMENT_COMMENTARY
        or category == IntelCategory.MANAGEMENT_STATEMENT
    ):
        return FeedItemType.MANAGEMENT_COMMENTARY

    if item.kind == IntelKind.INDIRECT_INTELLIGENCE:
        return FeedItemType.INDUSTRY_EVENT

    if category in _DEVELOPMENT_CATEGORIES:
        return FeedItemType.COMPANY_DEVELOPMENT

    if item.kind == IntelKind.BUSINESS_EVENT:
        return FeedItemType.COMPANY_DEVELOPMENT

    return None


def _item_from_intel(item, as_of: datetime) -> DiscoveryFeedItem | None:
    item_type = _classify_intel_item(item)

    if item_type is None:
        return None

    return DiscoveryFeedItem(
        item_id=f"{item_type.value.lower()}:{item.symbol}:{item.item_id}",
        symbol=item.symbol,
        item_type=item_type,
        title=item.title,
        description=item.description,
        published_at=item.published_at,
        available_at=item.available_at,
        effective_at=item.effective_at,
        source_name=item.source.source_name,
        source_type=item.source.source_type,
        provenance_id=item.provenance_id,
        pit_eligible=item.available_at is not None,
        direction=(
            _direction_value(item.direction)
            if getattr(item, "direction", None) is not None
            else None
        ),
    )


def _items_from_result(result, as_of: datetime) -> list[DiscoveryFeedItem]:
    """Build all feed items contributed by one research result."""

    items: list[DiscoveryFeedItem] = []
    intel = result.intelligence
    symbol = result.company

    if intel is not None:
        for entry in intel.items:
            feed_item = _item_from_intel(entry, as_of)
            if feed_item is not None:
                items.append(feed_item)

        hidden = intel.hidden_information
        if hidden is not None:
            for observation in hidden.observations:
                items.append(
                    DiscoveryFeedItem(
                        item_id=(
                            f"{FeedItemType.RESEARCH_OBSERVATION.value.lower()}:"
                            f"{symbol}:{observation.observation_id}"
                        ),
                        symbol=symbol,
                        item_type=FeedItemType.RESEARCH_OBSERVATION,
                        title=observation.label,
                        description=observation.description,
                        published_at=None,
                        available_at=observation.as_of,
                        effective_at=observation.as_of,
                        source_name="recorded_research",
                        source_type="DERIVED",
                        provenance_id=(
                            observation.provenance_ids[0]
                            if observation.provenance_ids
                            else None
                        ),
                        pit_eligible=True,
                    )
                )

        gaps = intel.research_gaps
        if gaps is not None:
            for gap in gaps.gaps:
                if gap.status not in _ACTIONABLE_GAP_STATUSES:
                    continue

                items.append(
                    DiscoveryFeedItem(
                        item_id=(
                            f"{FeedItemType.RESEARCH_GAP_CHANGE.value.lower()}:"
                            f"{symbol}:{gap.gap_id}"
                        ),
                        symbol=symbol,
                        item_type=FeedItemType.RESEARCH_GAP_CHANGE,
                        title=(
                            f"Research gap ({gap.status.lower()}): {gap.gap}"
                        ),
                        description=gap.reason,
                        available_at=as_of,
                        source_name="research_gap_detection",
                        source_type="DERIVED",
                        pit_eligible=True,
                    )
                )

        for status in intel.source_statuses:
            if not status.stale:
                continue

            days = status.days_since_latest_published
            items.append(
                DiscoveryFeedItem(
                    item_id=(
                        f"{FeedItemType.SOURCE_FRESHNESS_CHANGE.value.lower()}:"
                        f"{symbol}:{status.source_name}"
                    ),
                    symbol=symbol,
                    item_type=FeedItemType.SOURCE_FRESHNESS_CHANGE,
                    title=(
                        f"Source freshness: {status.source_name} "
                        f"is stale at as_of"
                    ),
                    description=(
                        f"Latest published disclosure from this source was "
                        f"{days} days before as_of."
                        if days is not None
                        else "No published disclosure is recorded for "
                        f"this source."
                    ),
                    published_at=status.latest_published_at,
                    available_at=status.latest_available_at or as_of,
                    source_name=status.source_name,
                    source_type=status.source_type,
                    pit_eligible=True,
                )
            )

    for evidence_item in result.evidence_items or ():
        if evidence_item.evidence_type.value != "FUTURE_TECHNOLOGY":
            continue

        stamp = evidence_item.published_at or evidence_item.observation_at
        items.append(
            DiscoveryFeedItem(
                item_id=(
                    f"{FeedItemType.TECHNOLOGY_DEVELOPMENT.value.lower()}:"
                    f"{symbol}:{evidence_item.evidence_id}"
                ),
                symbol=symbol,
                item_type=FeedItemType.TECHNOLOGY_DEVELOPMENT,
                title=evidence_item.title,
                description=evidence_item.explanation,
                published_at=evidence_item.published_at,
                available_at=evidence_item.available_at,
                source_name=(
                    evidence_item.source_ids[0]
                    if evidence_item.source_ids
                    else None
                ),
                provenance_id=(
                    evidence_item.provenance_ids[0]
                    if evidence_item.provenance_ids
                    else None
                ),
                pit_eligible=evidence_item.available_at is not None,
            )
        )

    return items


# ---------------------------------------------------------------------------
# Canonical-event deduplication across feed surfaces
# ---------------------------------------------------------------------------


_FEED_TYPE_PRIORITY = {
    item_type: index
    for index, item_type in enumerate(FeedItemType)
}


def _candidate_from_feed_item(item: DiscoveryFeedItem):
    direction = EventDirection.UNKNOWN
    if item.direction in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
        direction = EventDirection(item.direction)

    return EventCandidateRecord(
        symbol=item.symbol,
        title=item.title,
        category=item.item_type.value,
        record_id=item.item_id,
        description=item.description,
        direction=direction,
        verification_status="UNVERIFIED",
        published_at=item.published_at,
        available_at=item.available_at,
        effective_at=item.effective_at,
        source_name=item.source_name,
        provenance_id=item.provenance_id,
    )


def _merge_by_event_identity(items: list[DiscoveryFeedItem]):
    """
    Collapse feed items that describe the same underlying event into
    one canonical item per identity. Opposing-direction records are
    never merged; every contributing source / provenance id survives.
    """

    if not items:
        return [], 0

    candidates = [_candidate_from_feed_item(item) for item in items]
    events = dedupe_research_events(candidates)

    by_item_id = {item.item_id: item for item in items}
    merged_items: list[DiscoveryFeedItem] = []
    merged_away = 0

    for event in events:
        members = [by_item_id[mid] for mid in event.member_ids]
        representative = min(members, key=lambda m: m.item_id)

        if len(members) == 1:
            merged_items.append(
                representative.model_copy(
                    update={
                        "event_id": event.event_id,
                        "member_ids": event.member_ids,
                    }
                )
            )
            continue

        merged_away += len(members) - 1

        descriptions = [m.description for m in members if m.description]
        known_directions = sorted(
            {
                m.direction
                for m in members
                if m.direction in ("POSITIVE", "NEGATIVE")
            }
        )
        source_types = sorted(
            {m.source_type for m in members if m.source_type}
        )

        merged_items.append(
            DiscoveryFeedItem(
                item_id=event.event_id,
                symbol=event.symbol,
                item_type=min(
                    (m.item_type for m in members),
                    key=lambda t: _FEED_TYPE_PRIORITY[t],
                ),
                title=representative.title,
                description=(
                    max(descriptions, key=len) if descriptions else ""
                ),
                published_at=event.published_at,
                available_at=event.available_at,
                effective_at=event.effective_at,
                source_name=representative.source_name,
                source_type=source_types[0] if source_types else None,
                provenance_id=representative.provenance_id,
                pit_eligible=event.pit_eligible,
                event_id=event.event_id,
                direction=(
                    known_directions[0] if len(known_directions) == 1 else None
                ),
                sources=event.sources,
                provenance_ids=event.provenance_ids,
                member_ids=event.member_ids,
            )
        )

    return merged_items, merged_away


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------


def build_discovery_feed(
    results,
    *,
    as_of: datetime,
    item_types: tuple[FeedItemType, ...] | None = None,
    limit_per_symbol: int | None = None,
) -> DiscoveryFeed:
    """
    Build the aggregated discovery feed from recorded research
    results (any iterable of RealDataVerificationResult-like objects).

    Ordering is fully deterministic: published_at descending, then
    symbol ascending, then item_id ascending.
    """

    _require_aware(as_of)

    all_items: list[DiscoveryFeedItem] = []
    symbols: list[str] = []

    for result in results:
        symbol = result.company
        symbols.append(symbol)

        result_items = _items_from_result(result, as_of)

        if item_types is not None:
            allowed = set(item_types)
            result_items = [
                item for item in result_items if item.item_type in allowed
            ]

        result_items.sort(
            key=lambda i: (
                -(i.published_at or i.available_at or as_of).timestamp(),
                i.item_id,
            )
        )

        if limit_per_symbol is not None and limit_per_symbol > 0:
            result_items = result_items[:limit_per_symbol]

        all_items.extend(result_items)

    merged_items, duplicates_merged = _merge_by_event_identity(
        all_items
    )

    def _order_key(item: DiscoveryFeedItem):
        stamp = item.published_at or item.available_at or as_of
        return (-stamp.timestamp(), item.symbol, item.item_id)

    ordered = sorted(merged_items, key=_order_key)

    type_counts: dict[str, int] = {}
    for item in ordered:
        key = item.item_type.value
        type_counts[key] = type_counts.get(key, 0) + 1

    notes: list[str] = []
    if not ordered:
        notes.append(
            "No recorded research items were knowable at as_of."
        )
    if duplicates_merged > 0:
        notes.append(
            f"{duplicates_merged} duplicate feed record(s) merged "
            "into canonical events."
        )

    unique_symbols = tuple(sorted(set(symbols)))

    return DiscoveryFeed(
        as_of=as_of,
        items=tuple(ordered),
        item_count=len(ordered),
        type_counts=type_counts,
        symbols_included=unique_symbols,
        notes=tuple(notes),
        duplicates_merged=duplicates_merged,
    )


def compute_trending(
    feed: DiscoveryFeed,
    *,
    window_days: int = 30,
) -> TrendingResult:
    """
    Compute trending activity over the feed.

    Explicit definition: companies are ordered by their count of feed
    items published strictly inside the trailing window ending at
    as_of, most active first. Ties break alphabetically by symbol.
    """

    _require_aware(feed.as_of)

    cutoff_start = feed.as_of.timestamp() - window_days * 86400

    total_by_symbol: dict[str, int] = {}
    recent_by_symbol: dict[str, int] = {}

    for item in feed.items:
        total_by_symbol[item.symbol] = (
            total_by_symbol.get(item.symbol, 0) + 1
        )

        stamp = item.published_at or item.available_at
        if stamp is None:
            continue

        if stamp.timestamp() < cutoff_start or stamp > feed.as_of:
            continue

        recent_by_symbol[item.symbol] = (
            recent_by_symbol.get(item.symbol, 0) + 1
        )

    ranked = sorted(
        (
            TrendingCompany(
                symbol=symbol,
                recent_item_count=recent_by_symbol.get(symbol, 0),
                total_item_count=count,
            )
            for symbol, count in total_by_symbol.items()
        ),
        key=lambda entry: (-entry.recent_item_count, entry.symbol),
    )

    return TrendingResult(
        as_of=feed.as_of,
        window_days=window_days,
        definition=_TRENDING_DEFINITION,
        ranked=tuple(ranked),
    )


__all__ = [
    "DiscoveryFeed",
    "DiscoveryFeedItem",
    "FeedItemType",
    "TRENDING_DEFINITION",
    "TrendingCompany",
    "TrendingResult",
    "build_discovery_feed",
    "compute_trending",
]
