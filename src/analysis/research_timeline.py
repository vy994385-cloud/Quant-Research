"""
Research timeline engine.

Constructs a chronological timeline combining:
  - Company events (earnings, corporate actions, etc.)
  - Price movements (daily bars as context)
  - Ownership changes
  - Management changes
  - Volume patterns

All timeline entries are descriptive, not predictive.
All analysis is deterministic and PIT-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Sequence

from src.data.company.events import CompanyEvent
from src.data.company.management import ManagementChange
from src.data.company.ownership import OwnershipSnapshot
from src.data.models import PriceBar


class TimelineEntryType(str, Enum):
    EVENT = "EVENT"
    PRICE = "PRICE"
    OWNERSHIP = "OWNERSHIP"
    MANAGEMENT = "MANAGEMENT"
    VOLUME = "VOLUME"


class TimelineDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True)
class TimelineEntry:
    """One chronological timeline entry."""

    entry_id: str
    entry_type: str
    date: str
    title: str
    description: str
    direction: str
    materiality: int
    category: str
    supporting_data: dict[str, str] = field(default_factory=dict)
    evidence_count: int = 0


@dataclass(frozen=True)
class TimelineSummary:
    """Summary statistics for a timeline."""

    total_entries: int = 0
    event_count: int = 0
    price_count: int = 0
    ownership_count: int = 0
    management_count: int = 0
    volume_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    high_materiality_count: int = 0
    date_range: str = ""
    earliest_date: str = ""
    latest_date: str = ""


@dataclass(frozen=True)
class ResearchTimelineResult:
    """Complete research timeline for one company."""

    symbol: str
    as_of: str
    entries: tuple[TimelineEntry, ...] = ()
    summary: TimelineSummary = field(default_factory=TimelineSummary)
    notes: tuple[str, ...] = ()


def _event_to_entry(
    event: CompanyEvent, idx: int
) -> TimelineEntry:
    """Convert a CompanyEvent to a TimelineEntry."""
    return TimelineEntry(
        entry_id=f"EVT-{idx:05d}",
        entry_type=TimelineEntryType.EVENT.value,
        date=event.event_date.isoformat(),
        title=event.title,
        description=event.description,
        direction=event.direction,
        materiality=event.materiality,
        category=event.category,
        supporting_data={},
        evidence_count=len(event.evidence_ids),
    )


def _management_to_entry(
    change: ManagementChange, idx: int
) -> TimelineEntry:
    """Convert a ManagementChange to a TimelineEntry."""
    direction = TimelineDirection.NEUTRAL.value
    if change.change_type.upper() in {"RESIGNATION", "REMOVAL"}:
        direction = TimelineDirection.NEGATIVE.value
    elif change.change_type.upper() in {"APPOINTMENT", "PROMOTION"}:
        direction = TimelineDirection.POSITIVE.value

    return TimelineEntry(
        entry_id=f"MGT-{idx:05d}",
        entry_type=TimelineEntryType.MANAGEMENT.value,
        date=change.effective_date.isoformat(),
        title=(
            f"{change.change_type}: {change.person_name} ({change.role})"
        ),
        description=(
            f"{change.person_name} - {change.role}: "
            f"{change.change_type}"
            + (f" ({change.reason})" if change.reason else "")
        ),
        direction=direction,
        materiality=3,
        category="MANAGEMENT",
        supporting_data={
            "person_name": change.person_name,
            "role": change.role,
            "change_type": change.change_type,
        },
        evidence_count=len(change.evidence_ids),
    )


def _ownership_to_entries(
    snapshots: Sequence[OwnershipSnapshot],
    symbol: str,
    start_idx: int,
) -> list[TimelineEntry]:
    """Convert ownership snapshots to timeline entries."""
    entries: list[TimelineEntry] = []
    idx = start_idx

    sorted_snaps = sorted(snapshots, key=lambda s: s.period_end)

    for i in range(1, len(sorted_snaps)):
        prev = sorted_snaps[i - 1]
        curr = sorted_snaps[i]

        # Detect significant changes
        changes: list[str] = []
        direction = TimelineDirection.NEUTRAL.value
        materiality = 1

        if (
            prev.promoter_percentage is not None
            and curr.promoter_percentage is not None
        ):
            move = curr.promoter_percentage - prev.promoter_percentage
            if abs(move) > Decimal("2"):
                changes.append(
                    f"Promoter: {prev.promoter_percentage}% -> "
                    f"{curr.promoter_percentage}%"
                )
                if move > 0:
                    direction = TimelineDirection.POSITIVE.value
                else:
                    direction = TimelineDirection.NEGATIVE.value
                materiality = max(materiality, 2)

        if (
            prev.promoter_pledged_percentage is not None
            and curr.promoter_pledged_percentage is not None
        ):
            pledge_move = (
                curr.promoter_pledged_percentage
                - prev.promoter_pledged_percentage
            )
            if abs(pledge_move) > Decimal("2"):
                changes.append(
                    f"Pledge: {prev.promoter_pledged_percentage}% -> "
                    f"{curr.promoter_pledged_percentage}%"
                )
                if pledge_move > 0:
                    direction = TimelineDirection.NEGATIVE.value
                materiality = max(materiality, 3)

        if changes:
            entries.append(
                TimelineEntry(
                    entry_id=f"OWN-{idx:05d}",
                    entry_type=TimelineEntryType.OWNERSHIP.value,
                    date=curr.period_end.isoformat(),
                    title="Ownership change detected",
                    description="; ".join(changes),
                    direction=direction,
                    materiality=materiality,
                    category="OWNERSHIP",
                    supporting_data={
                        "promoter": str(curr.promoter_percentage or ""),
                        "institutional": str(
                            curr.institutional_percentage or ""
                        ),
                    },
                )
            )
            idx += 1

    return entries


def _price_to_entries(
    bars: Sequence[PriceBar],
    symbol: str,
    start_idx: int,
    window_days: int = 5,
) -> list[TimelineEntry]:
    """Convert significant price moves to timeline entries."""
    entries: list[TimelineEntry] = []
    idx = start_idx

    if len(bars) < window_days + 1:
        return entries

    sorted_bars = sorted(bars, key=lambda b: b.trading_date)

    # Compute rolling window moves
    for i in range(window_days, len(sorted_bars)):
        window = sorted_bars[i - window_days : i + 1]
        first = window[0]
        last = window[-1]

        pct = ((last.close - first.close) / first.close * Decimal("100")).quantize(
            Decimal("0.01")
        )

        if abs(pct) > Decimal("5"):
            direction = (
                TimelineDirection.POSITIVE.value
                if pct > 0
                else TimelineDirection.NEGATIVE.value
            )

            entries.append(
                TimelineEntry(
                    entry_id=f"PRC-{idx:05d}",
                    entry_type=TimelineEntryType.PRICE.value,
                    date=last.trading_date.isoformat(),
                    title=f"Price move: {pct}%",
                    description=(
                        f"Price moved {pct}% over "
                        f"{window_days} trading days "
                        f"({first.close} -> {last.close})."
                    ),
                    direction=direction,
                    materiality=3 if abs(pct) > Decimal("10") else 2,
                    category="PRICE",
                    supporting_data={
                        "from_close": str(first.close),
                        "to_close": str(last.close),
                        "pct_change": str(pct),
                    },
                )
            )
            idx += 1

    return entries


def _volume_to_entries(
    bars: Sequence[PriceBar],
    symbol: str,
    start_idx: int,
) -> list[TimelineEntry]:
    """Convert unusual volume events to timeline entries."""
    entries: list[TimelineEntry] = []
    idx = start_idx

    if len(bars) < 20:
        return entries

    sorted_bars = sorted(bars, key=lambda b: b.trading_date)

    for i in range(20, len(sorted_bars)):
        window = sorted_bars[i - 20 : i]
        avg_vol = sum(b.volume for b in window) / 20

        if avg_vol == 0:
            continue

        current = sorted_bars[i]
        ratio = Decimal(str(current.volume)) / Decimal(str(avg_vol))

        if ratio > Decimal("3"):
            entries.append(
                TimelineEntry(
                    entry_id=f"VOL-{idx:05d}",
                    entry_type=TimelineEntryType.VOLUME.value,
                    date=current.trading_date.isoformat(),
                    title=f"Unusual volume: {ratio.quantize(Decimal('0.1'))}x avg",
                    description=(
                        f"Volume ({current.volume}) is "
                        f"{ratio.quantize(Decimal('0.1'))}x "
                        f"the 20-day average."
                    ),
                    direction=TimelineDirection.NEUTRAL.value,
                    materiality=2,
                    category="VOLUME",
                    supporting_data={
                        "volume": str(current.volume),
                        "avg_volume": str(int(avg_vol)),
                        "ratio": str(ratio.quantize(Decimal("0.1"))),
                    },
                )
            )
            idx += 1

    return entries


def build_research_timeline(
    symbol: str,
    as_of: datetime,
    events: Sequence[CompanyEvent] = (),
    management_changes: Sequence[ManagementChange] = (),
    ownership_snapshots: Sequence[OwnershipSnapshot] = (),
    price_bars: Sequence[PriceBar] = (),
) -> ResearchTimelineResult:
    """
    Build a chronological research timeline.

    Deterministic: no external calls, no network, no randomness.
    """
    notes: list[str] = []
    all_entries: list[TimelineEntry] = []
    idx = 0

    # Events
    filtered_events = [
        e for e in events
        if (
            e.event_date <= as_of.date()
            if as_of.tzinfo is None
            else datetime.combine(
                e.event_date, datetime.min.time()
            ).replace(tzinfo=as_of.tzinfo) <= as_of
        )
    ]
    for event in filtered_events:
        all_entries.append(_event_to_entry(event, idx))
        idx += 1

    # Management changes
    filtered_mgmt = [
        m for m in management_changes
        if (
            m.effective_date <= as_of.date()
            if as_of.tzinfo is None
            else datetime.combine(
                m.effective_date, datetime.min.time()
            ).replace(tzinfo=as_of.tzinfo) <= as_of
        )
    ]
    for change in filtered_mgmt:
        all_entries.append(_management_to_entry(change, idx))
        idx += 1

    # Ownership changes - filter by period_end <= as_of
    filtered_ownership = [
        o for o in ownership_snapshots
        if (
            o.period_end <= as_of.date()
            if as_of.tzinfo is None
            else datetime.combine(
                o.period_end, datetime.min.time()
            ).replace(tzinfo=as_of.tzinfo) <= as_of
        )
    ]
    ownership_entries = _ownership_to_entries(
        filtered_ownership, symbol, idx
    )
    all_entries.extend(ownership_entries)
    idx += len(ownership_entries)

    # Price moves - filter by trading_date <= as_of
    filtered_price = [
        p for p in price_bars
        if (
            p.trading_date <= as_of.date()
            if as_of.tzinfo is None
            else datetime.combine(
                p.trading_date, datetime.min.time()
            ).replace(tzinfo=as_of.tzinfo) <= as_of
        )
    ]
    price_entries = _price_to_entries(filtered_price, symbol, idx)
    all_entries.extend(price_entries)
    idx += len(price_entries)

    # Volume events - use same filtered price bars
    volume_entries = _volume_to_entries(filtered_price, symbol, idx)
    all_entries.extend(volume_entries)
    idx += len(volume_entries)

    # Sort chronologically
    all_entries.sort(key=lambda e: e.date)

    # Summary
    if all_entries:
        positive = sum(
            1 for e in all_entries
            if e.direction == TimelineDirection.POSITIVE.value
        )
        negative = sum(
            1 for e in all_entries
            if e.direction == TimelineDirection.NEGATIVE.value
        )
        neutral = len(all_entries) - positive - negative

        high_mat = sum(
            1 for e in all_entries if e.materiality >= 4
        )

        summary = TimelineSummary(
            total_entries=len(all_entries),
            event_count=sum(
                1 for e in all_entries
                if e.entry_type == TimelineEntryType.EVENT.value
            ),
            price_count=sum(
                1 for e in all_entries
                if e.entry_type == TimelineEntryType.PRICE.value
            ),
            ownership_count=sum(
                1 for e in all_entries
                if e.entry_type == TimelineEntryType.OWNERSHIP.value
            ),
            management_count=sum(
                1 for e in all_entries
                if e.entry_type == TimelineEntryType.MANAGEMENT.value
            ),
            volume_count=sum(
                1 for e in all_entries
                if e.entry_type == TimelineEntryType.VOLUME.value
            ),
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            high_materiality_count=high_mat,
            date_range=(
                f"{all_entries[0].date} to {all_entries[-1].date}"
            ),
            earliest_date=all_entries[0].date,
            latest_date=all_entries[-1].date,
        )
    else:
        summary = TimelineSummary()
        notes.append("No timeline entries available.")

    return ResearchTimelineResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        entries=tuple(all_entries),
        summary=summary,
        notes=tuple(notes),
    )
