"""Tests for research timeline engine."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.analysis.research_timeline import (
    ResearchTimelineResult,
    TimelineDirection,
    TimelineEntry,
    TimelineEntryType,
    TimelineSummary,
    build_research_timeline,
)
from src.data.company.events import CompanyEvent
from src.data.company.management import ManagementChange
from src.data.company.ownership import OwnershipSnapshot
from src.data.models import PriceBar


_AS_OF = datetime(2024, 6, 15, tzinfo=timezone.utc)


def _event(
    event_date: date,
    title: str = "Test Event",
    category: str = "EARNINGS",
    direction: str = "POSITIVE",
    materiality: int = 3,
) -> CompanyEvent:
    return CompanyEvent(
        symbol="TEST",
        event_date=event_date,
        category=category,
        title=title,
        description=f"Description for {title}",
        direction=direction,
        materiality=materiality,
    )


def _mgmt(
    effective_date: date,
    person: str = "John Doe",
    role: str = "CEO",
    change_type: str = "Appointment",
) -> ManagementChange:
    return ManagementChange(
        symbol="TEST",
        person_name=person,
        role=role,
        change_type=change_type,
        effective_date=effective_date,
    )


def _snap(
    period_end: date,
    promoter: Decimal | None = None,
    pledge: Decimal | None = None,
) -> OwnershipSnapshot:
    return OwnershipSnapshot(
        symbol="TEST",
        period_end=period_end,
        promoter_percentage=promoter,
        promoter_pledged_percentage=pledge,
    )


def _rising_bars(
    n: int,
    start: str = "2024-01-01",
    daily_change: Decimal = Decimal("1"),
) -> list[PriceBar]:
    bars = []
    base = date.fromisoformat(start)
    for i in range(n):
        d = base + timedelta(days=i)
        o = Decimal("100") + daily_change * Decimal(i)
        bars.append(
            PriceBar(
                symbol="TEST",
                trading_date=d,
                open=o,
                high=o + Decimal("2"),
                low=o - Decimal("2"),
                close=o + Decimal("1"),
                volume=1000,
            )
        )
    return bars


# ---------------------------------------------------------------------------
# Empty data
# ---------------------------------------------------------------------------


class TestEmptyTimeline:
    def test_no_data(self):
        result = build_research_timeline("TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert len(result.entries) == 0
        assert result.summary.total_entries == 0

    def test_events_only(self):
        events = [
            _event(date(2024, 1, 1), title="Q1 Results"),
            _event(date(2024, 3, 1), title="Q2 Results"),
        ]
        result = build_research_timeline(
            "TEST", _AS_OF, events=events
        )
        assert result.summary.event_count == 2
        assert result.summary.total_entries == 2


# ---------------------------------------------------------------------------
# Entry types
# ---------------------------------------------------------------------------


class TestEntryTypes:
    def test_management_entry(self):
        mgmt = [_mgmt(date(2024, 2, 1))]
        result = build_research_timeline(
            "TEST", _AS_OF, management_changes=mgmt
        )
        assert result.summary.management_count == 1
        entry = result.entries[0]
        assert entry.entry_type == TimelineEntryType.MANAGEMENT.value

    def test_ownership_entry(self):
        snaps = [
            _snap(date(2024, 1, 1), promoter=Decimal("40")),
            _snap(date(2024, 6, 1), promoter=Decimal("50")),
        ]
        result = build_research_timeline(
            "TEST", _AS_OF, ownership_snapshots=snaps
        )
        assert result.summary.ownership_count >= 1

    def test_price_entry(self):
        bars = _rising_bars(10, daily_change=Decimal("5"))
        result = build_research_timeline(
            "TEST", _AS_OF, price_bars=bars
        )
        assert result.summary.price_count >= 1


# ---------------------------------------------------------------------------
# Chronological ordering
# ---------------------------------------------------------------------------


class TestOrdering:
    def test_entries_are_chronological(self):
        events = [
            _event(date(2024, 6, 1), title="Later"),
            _event(date(2024, 1, 1), title="Earlier"),
        ]
        mgmt = [_mgmt(date(2024, 3, 1))]
        result = build_research_timeline(
            "TEST", _AS_OF, events=events, management_changes=mgmt
        )
        dates = [e.date for e in result.entries]
        assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


class TestSummary:
    def test_summary_counts(self):
        events = [
            _event(
                date(2024, 1, 1),
                direction="POSITIVE",
                materiality=5,
            ),
            _event(
                date(2024, 2, 1),
                direction="NEGATIVE",
                materiality=2,
            ),
        ]
        result = build_research_timeline(
            "TEST", _AS_OF, events=events
        )
        s = result.summary
        assert s.positive_count == 1
        assert s.negative_count == 1
        assert s.high_materiality_count == 1

    def test_date_range(self):
        events = [
            _event(date(2024, 1, 1)),
            _event(date(2024, 6, 1)),
        ]
        result = build_research_timeline(
            "TEST", _AS_OF, events=events
        )
        assert "2024-01-01" in result.summary.date_range
        assert "2024-06-01" in result.summary.date_range


# ---------------------------------------------------------------------------
# PIT filter
# ---------------------------------------------------------------------------


class TestPITFilter:
    def test_future_events_excluded(self):
        events = [
            _event(date(2024, 1, 1)),
            _event(date(2025, 6, 1)),
        ]
        result = build_research_timeline(
            "TEST", _AS_OF, events=events
        )
        assert result.summary.event_count == 1
