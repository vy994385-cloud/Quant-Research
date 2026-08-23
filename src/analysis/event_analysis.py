"""
Event analysis engine.

Analyzes company events to derive:
  - Event categorization and taxonomy
  - Event impact assessment (materiality, direction)
  - Corporate actions (dividends, splits) extraction
  - Event clustering and deduplication
  - Timeline construction
  - Subsequent observation linking

All analysis is deterministic and PIT-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Sequence

from src.data.company.events import CompanyEvent
from src.data.company.evidence import Evidence


class EventCategory(str, Enum):
    EARNINGS = "EARNINGS"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    MANAGEMENT = "MANAGEMENT"
    REGULATORY = "REGULATORY"
    BUSINESS_DEVELOPMENT = "BUSINESS_DEVELOPMENT"
    CAPITAL_MARKETS = "CAPITAL_MARKETS"
    OTHER = "OTHER"


class EventImpact(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class EventClassification:
    """Enriched event with category and impact classification."""

    event_date: str
    category: str
    title: str
    description: str
    direction: str
    materiality: int
    impact: str
    evidence_count: int = 0
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class EventCluster:
    """A cluster of related events."""

    cluster_id: str
    category: str
    event_count: int
    date_range: str
    titles: tuple[str, ...] = ()
    overall_direction: str = "UNKNOWN"
    overall_materiality: int = 0
    explanation: str = ""


@dataclass(frozen=True)
class EventAnalysisResult:
    """Complete event analysis for one company."""

    symbol: str
    as_of: str
    event_count: int = 0
    classifications: tuple[EventClassification, ...] = ()
    clusters: tuple[EventCluster, ...] = ()
    category_counts: dict[str, int] = field(default_factory=dict)
    direction_counts: dict[str, int] = field(default_factory=dict)
    coverage: dict[str, int] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    evidence: tuple[Evidence, ...] = ()


# Category inference rules
_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    EventCategory.EARNINGS.value: [
        "earnings", "quarterly results", "annual results",
        "revenue", "profit", "loss", "dividend",
        "financial results", "q1", "q2", "q3", "q4",
    ],
    EventCategory.CORPORATE_ACTION.value: [
        "stock split", "bonus", "rights issue",
        "buyback", "merger", "acquisition",
        "demerger", "delisting", "listing",
    ],
    EventCategory.MANAGEMENT.value: [
        "ceo", "cfo", "chairman", "director",
        "resignation", "appointment", "removal",
        "management change", "board",
    ],
    EventCategory.REGULATORY.value: [
        "sebi", "rbi", "regulatory", "compliance",
        "investigation", "penalty", "order",
        "license", "approval",
    ],
    EventCategory.BUSINESS_DEVELOPMENT.value: [
        "contract", "order", "partnership", "joint venture",
        "new product", "expansion", "capacity",
        "customer", "client",
    ],
    EventCategory.CAPITAL_MARKETS.value: [
        "fpo", "ipo", "preferential allotment",
        "qip", "placement", "debenture",
        "bond", "ncd", "qualified institutional",
    ],
}


def _infer_category(event: CompanyEvent) -> str:
    """Infer event category from title and description."""
    text = f"{event.title} {event.description}".lower()
    explicit = event.category.strip().upper()

    # Keyword-based inference takes priority for richer classification
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return category

    # Fall back to explicit category if it maps to a known category
    for cat in EventCategory:
        if explicit == cat.value:
            return cat.value

    return EventCategory.OTHER.value


def _assess_impact(
    materiality: int, direction: str
) -> str:
    """Assess overall event impact."""
    if materiality >= 4:
        return EventImpact.HIGH.value
    elif materiality >= 2:
        return EventImpact.MEDIUM.value
    elif materiality >= 1:
        return EventImpact.LOW.value
    return EventImpact.UNKNOWN.value


def _classify_event(event: CompanyEvent) -> EventClassification:
    """Build enriched classification for one event."""
    category = _infer_category(event)
    impact = _assess_impact(event.materiality, event.direction)

    return EventClassification(
        event_date=event.event_date.isoformat(),
        category=category,
        title=event.title,
        description=event.description,
        direction=event.direction,
        materiality=event.materiality,
        impact=impact,
        evidence_count=len(event.evidence_ids),
        evidence_ids=tuple(event.evidence_ids),
    )


def _cluster_events(
    events: list[CompanyEvent],
) -> list[EventCluster]:
    """
    Cluster events by category and time proximity.

    Events within 7 days of each other in the same category
    are grouped into a single cluster.
    """
    if not events:
        return []

    classified = [_classify_event(e) for e in events]

    # Group by category
    by_category: dict[str, list[tuple[CompanyEvent, EventClassification]]] = {}
    for event, cls in zip(events, classified):
        by_category.setdefault(cls.category, []).append((event, cls))

    clusters: list[EventCluster] = []
    cluster_idx = 0

    for category, items in by_category.items():
        # Sort by date
        items.sort(key=lambda x: x[0].event_date)

        current_cluster_events: list[CompanyEvent] = [items[0][0]]
        current_cluster_cls: list[EventClassification] = [items[0][1]]

        for i in range(1, len(items)):
            event, cls = items[i]
            prev_date = current_cluster_events[-1].event_date

            # Cluster if within 7 days
            if (event.event_date - prev_date).days <= 7:
                current_cluster_events.append(event)
                current_cluster_cls.append(cls)
            else:
                # Emit current cluster
                titles = tuple(c.title for c in current_cluster_cls)
                directions = [c.direction for c in current_cluster_cls]
                avg_materiality = round(
                    sum(c.materiality for c in current_cluster_cls)
                    / len(current_cluster_cls)
                )

                clusters.append(
                    EventCluster(
                        cluster_id=f"CLUSTER-{cluster_idx:03d}",
                        category=category,
                        event_count=len(current_cluster_events),
                        date_range=(
                            f"{current_cluster_events[0].event_date.isoformat()}"
                            f" to "
                            f"{current_cluster_events[-1].event_date.isoformat()}"
                        ),
                        titles=titles,
                        overall_direction=_majority_direction(directions),
                        overall_materiality=avg_materiality,
                        explanation=(
                            f"{len(current_cluster_events)} {category.lower()} "
                            f"events clustered."
                        ),
                    )
                )
                cluster_idx += 1
                current_cluster_events = [event]
                current_cluster_cls = [cls]

        # Emit final cluster
        if current_cluster_events:
            titles = tuple(c.title for c in current_cluster_cls)
            directions = [c.direction for c in current_cluster_cls]
            avg_materiality = round(
                sum(c.materiality for c in current_cluster_cls)
                / len(current_cluster_cls)
            )
            clusters.append(
                EventCluster(
                    cluster_id=f"CLUSTER-{cluster_idx:03d}",
                    category=category,
                    event_count=len(current_cluster_events),
                    date_range=(
                        f"{current_cluster_events[0].event_date.isoformat()}"
                        f" to "
                        f"{current_cluster_events[-1].event_date.isoformat()}"
                    ),
                    titles=titles,
                    overall_direction=_majority_direction(directions),
                    overall_materiality=avg_materiality,
                    explanation=(
                        f"{len(current_cluster_events)} {category.lower()} "
                        f"events clustered."
                    ),
                )
            )
            cluster_idx += 1

    return clusters


def _majority_direction(directions: list[str]) -> str:
    """Return the majority direction, or NEUTRAL."""
    if not directions:
        return "UNKNOWN"
    counts: dict[str, int] = {}
    for d in directions:
        counts[d] = counts.get(d, 0) + 1
    return max(counts, key=counts.get)  # type: ignore


def analyze_events(
    events: Sequence[CompanyEvent],
    symbol: str,
    as_of: datetime,
) -> EventAnalysisResult:
    """
    Run the full event analysis pipeline.

    Deterministic: no external calls, no network, no randomness.
    """
    notes: list[str] = []

    if not events:
        notes.append("No events available.")
        return EventAnalysisResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            notes=tuple(notes),
        )

    # PIT filter
    if as_of.tzinfo:
        filtered = [
            e for e in events
            if datetime.combine(
                e.event_date, datetime.min.time()
            ).replace(tzinfo=as_of.tzinfo) <= as_of
        ]
    else:
        filtered = [
            e for e in events
            if e.event_date <= as_of.date()
        ]

    if not filtered:
        notes.append("No events available at as_of date.")
        return EventAnalysisResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            notes=tuple(notes),
        )

    # Classify
    classifications = [_classify_event(e) for e in filtered]

    # Count by category
    category_counts: dict[str, int] = {}
    for cls in classifications:
        category_counts[cls.category] = (
            category_counts.get(cls.category, 0) + 1
        )

    # Count by direction
    direction_counts: dict[str, int] = {}
    for cls in classifications:
        direction_counts[cls.direction] = (
            direction_counts.get(cls.direction, 0) + 1
        )

    # Cluster
    clusters = _cluster_events(list(filtered))

    # Coverage
    coverage: dict[str, int] = {
        "event_count": len(filtered),
        "classified_count": len(classifications),
        "cluster_count": len(clusters),
    }

    return EventAnalysisResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        event_count=len(filtered),
        classifications=tuple(classifications),
        clusters=tuple(clusters),
        category_counts=category_counts,
        direction_counts=direction_counts,
        coverage=coverage,
        notes=tuple(notes),
    )


# ---------------------------------------------------------------------------
# Event Timeline with Subsequent Observations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubsequentObservation:
    """
    A measurable observation that occurred after an event.

    Links an event to subsequent financial or market changes
    where measurable. Does NOT imply causality.
    """

    observation_type: str  # FINANCIAL, MARKET, VOLUME
    metric: str
    period: str
    value: str | None = None
    change: str | None = None
    change_pct: str | None = None
    direction: str = "UNKNOWN"
    days_after_event: int | None = None
    explanation: str = ""


@dataclass(frozen=True)
class EventTimelineEntry:
    """
    A single event in the timeline with linked subsequent observations.
    """

    event_date: str
    category: str
    title: str
    description: str
    direction: str
    materiality: int
    impact: str

    evidence_count: int = 0
    evidence_ids: tuple[str, ...] = ()

    subsequent_observations: tuple[SubsequentObservation, ...] = ()
    subsequent_observations_count: int = 0


@dataclass(frozen=True)
class EventTimeline:
    """
    Complete event timeline for one company.

    Events are ordered chronologically with linked
    subsequent observations where available.
    """

    symbol: str
    as_of: str

    entries: tuple[EventTimelineEntry, ...] = ()
    entry_count: int = 0

    category_counts: dict[str, int] = field(default_factory=dict)
    direction_counts: dict[str, int] = field(default_factory=dict)

    with_subsequent_observations: int = 0
    notes: tuple[str, ...] = ()


def build_event_timeline(
    *,
    events: Sequence[CompanyEvent],
    symbol: str,
    as_of: datetime,
    subsequent_financial_observations: dict[str, list] | None = None,
    subsequent_market_observations: dict[str, list] | None = None,
) -> EventTimeline:
    """
    Build an event timeline with linked subsequent observations.

    Args:
        events: Company events to include in timeline
        symbol: Company symbol
        as_of: Point-in-time cutoff
        subsequent_financial_observations: Dict mapping event_date
            (ISO string) to list of financial observations after
            that date. Each observation is a dict with keys:
            metric, period, value, change, change_pct, direction
        subsequent_market_observations: Dict mapping event_date
            (ISO string) to list of market observations after
            that date. Each observation is a dict with keys:
            metric, period, value, change, change_pct, direction

    Returns:
        EventTimeline with entries ordered chronologically

    Note:
        This function does NOT establish causality between events
        and subsequent observations. It only links them by
        temporal proximity for research purposes.
    """
    notes: list[str] = []

    if not events:
        notes.append("No events available for timeline.")
        return EventTimeline(
            symbol=symbol,
            as_of=as_of.isoformat(),
            notes=tuple(notes),
        )

    # PIT filter
    if as_of.tzinfo:
        filtered = [
            e for e in events
            if datetime.combine(
                e.event_date, datetime.min.time()
            ).replace(tzinfo=as_of.tzinfo) <= as_of
        ]
    else:
        filtered = [
            e for e in events
            if e.event_date <= as_of.date()
        ]

    if not filtered:
        notes.append("No events available at as_of date.")
        return EventTimeline(
            symbol=symbol,
            as_of=as_of.isoformat(),
            notes=tuple(notes),
        )

    # Sort by date
    sorted_events = sorted(filtered, key=lambda e: e.event_date)

    # Build entries
    entries: list[EventTimelineEntry] = []
    category_counts: dict[str, int] = {}
    direction_counts: dict[str, int] = {}
    with_subsequent = 0

    for event in sorted_events:
        classification = _classify_event(event)
        event_date_str = event.event_date.isoformat()

        # Link subsequent financial observations
        subsequent_obs: list[SubsequentObservation] = []

        if subsequent_financial_observations:
            fin_obs = subsequent_financial_observations.get(
                event_date_str, []
            )
            for obs in fin_obs:
                days_after = None
                if obs.get("period"):
                    try:
                        event_dt = datetime.combine(
                            event.event_date,
                            datetime.min.time(),
                        )
                        period_dt = date.fromisoformat(
                            obs["period"]
                        )
                        period_dt_with_tz = datetime.combine(
                            period_dt, datetime.min.time()
                        )
                        if event_dt.tzinfo:
                            period_dt_with_tz = (
                                period_dt_with_tz.replace(
                                    tzinfo=event_dt.tzinfo
                                )
                            )
                        days_after = (
                            period_dt_with_tz - event_dt
                        ).days
                    except (ValueError, TypeError):
                        pass

                subsequent_obs.append(
                    SubsequentObservation(
                        observation_type="FINANCIAL",
                        metric=obs.get("metric", "unknown"),
                        period=obs.get("period", ""),
                        value=obs.get("value"),
                        change=obs.get("change"),
                        change_pct=obs.get("change_pct"),
                        direction=obs.get("direction", "UNKNOWN"),
                        days_after_event=days_after,
                        explanation=(
                            f"Financial observation "
                            f"{obs.get('metric', 'unknown')} "
                            f"after {event.title}"
                        ),
                    )
                )

        # Link subsequent market observations
        if subsequent_market_observations:
            mkt_obs = subsequent_market_observations.get(
                event_date_str, []
            )
            for obs in mkt_obs:
                days_after = None
                if obs.get("period"):
                    try:
                        event_dt = datetime.combine(
                            event.event_date,
                            datetime.min.time(),
                        )
                        period_dt = date.fromisoformat(
                            obs["period"]
                        )
                        period_dt_with_tz = datetime.combine(
                            period_dt, datetime.min.time()
                        )
                        if event_dt.tzinfo:
                            period_dt_with_tz = (
                                period_dt_with_tz.replace(
                                    tzinfo=event_dt.tzinfo
                                )
                            )
                        days_after = (
                            period_dt_with_tz - event_dt
                        ).days
                    except (ValueError, TypeError):
                        pass

                subsequent_obs.append(
                    SubsequentObservation(
                        observation_type="MARKET",
                        metric=obs.get("metric", "unknown"),
                        period=obs.get("period", ""),
                        value=obs.get("value"),
                        change=obs.get("change"),
                        change_pct=obs.get("change_pct"),
                        direction=obs.get("direction", "UNKNOWN"),
                        days_after_event=days_after,
                        explanation=(
                            f"Market observation "
                            f"{obs.get('metric', 'unknown')} "
                            f"after {event.title}"
                        ),
                    )
                )

        if subsequent_obs:
            with_subsequent += 1

        entries.append(
            EventTimelineEntry(
                event_date=event_date_str,
                category=classification.category,
                title=classification.title,
                description=classification.description,
                direction=classification.direction,
                materiality=classification.materiality,
                impact=classification.impact,
                evidence_count=classification.evidence_count,
                evidence_ids=classification.evidence_ids,
                subsequent_observations=tuple(subsequent_obs),
                subsequent_observations_count=len(subsequent_obs),
            )
        )

        # Update counts
        category_counts[classification.category] = (
            category_counts.get(classification.category, 0) + 1
        )
        direction_counts[classification.direction] = (
            direction_counts.get(classification.direction, 0) + 1
        )

    return EventTimeline(
        symbol=symbol,
        as_of=as_of.isoformat(),
        entries=tuple(entries),
        entry_count=len(entries),
        category_counts=category_counts,
        direction_counts=direction_counts,
        with_subsequent_observations=with_subsequent,
        notes=tuple(notes),
    )
