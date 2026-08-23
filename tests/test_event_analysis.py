"""Tests for event analysis engine."""

from datetime import date, datetime, timezone

import pytest

from src.analysis.event_analysis import (
    EventAnalysisResult,
    EventCategory,
    EventClassification,
    EventCluster,
    EventImpact,
    analyze_events,
)
from src.data.company.events import CompanyEvent


_AS_OF = datetime(2024, 6, 15, tzinfo=timezone.utc)


def _event(
    event_date: date,
    category: str = "EARNINGS",
    title: str = "Q4 Results",
    description: str = "Quarterly results announced",
    direction: str = "POSITIVE",
    materiality: int = 3,
) -> CompanyEvent:
    return CompanyEvent(
        symbol="TEST",
        event_date=event_date,
        category=category,
        title=title,
        description=description,
        direction=direction,
        materiality=materiality,
    )


# ---------------------------------------------------------------------------
# Empty / insufficient data
# ---------------------------------------------------------------------------


class TestInsufficientData:
    def test_empty_events(self):
        result = analyze_events([], "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert result.event_count == 0
        assert len(result.notes) > 0

    def test_pit_filter(self):
        event = _event(date(2025, 1, 1))
        result = analyze_events([event], "TEST", _AS_OF)
        assert result.event_count == 0


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class TestClassification:
    def test_explicit_category(self):
        event = _event(
            date(2024, 1, 1),
            category="CUSTOM_TYPE",
            title="Board meeting",
            description="Annual board meeting held",
        )
        result = analyze_events([event], "TEST", _AS_OF)
        cls = result.classifications[0]
        # Keywords take priority; "board" matches MANAGEMENT
        assert cls.category == EventCategory.MANAGEMENT.value

    def test_inferred_category_earnings(self):
        event = _event(
            date(2024, 1, 1),
            category="OTHER",
            title="Annual profit announcement",
            description="Company reported profit",
        )
        result = analyze_events([event], "TEST", _AS_OF)
        cls = result.classifications[0]
        assert cls.category == EventCategory.EARNINGS.value

    def test_inferred_category_management(self):
        event = _event(
            date(2024, 1, 1),
            category="OTHER",
            title="CEO resignation",
            description="Chief executive officer resigned",
        )
        result = analyze_events([event], "TEST", _AS_OF)
        cls = result.classifications[0]
        assert cls.category == EventCategory.MANAGEMENT.value

    def test_inferred_category_corporate_action(self):
        event = _event(
            date(2024, 1, 1),
            category="OTHER",
            title="Stock split 2:1",
            description="Board approved stock split",
        )
        result = analyze_events([event], "TEST", _AS_OF)
        cls = result.classifications[0]
        assert cls.category == EventCategory.CORPORATE_ACTION.value

    def test_inferred_category_regulatory(self):
        event = _event(
            date(2024, 1, 1),
            category="OTHER",
            title="SEBI investigation",
            description="Regulatory investigation initiated",
        )
        result = analyze_events([event], "TEST", _AS_OF)
        cls = result.classifications[0]
        assert cls.category == EventCategory.REGULATORY.value

    def test_inferred_category_business_dev(self):
        event = _event(
            date(2024, 1, 1),
            category="OTHER",
            title="New contract won",
            description="Major customer contract",
        )
        result = analyze_events([event], "TEST", _AS_OF)
        cls = result.classifications[0]
        assert cls.category == EventCategory.BUSINESS_DEVELOPMENT.value

    def test_inferred_category_capital_markets(self):
        event = _event(
            date(2024, 1, 1),
            category="OTHER",
            title="QIP placement",
            description="Qualified institutional placement",
        )
        result = analyze_events([event], "TEST", _AS_OF)
        cls = result.classifications[0]
        assert cls.category == EventCategory.CAPITAL_MARKETS.value


# ---------------------------------------------------------------------------
# Impact assessment
# ---------------------------------------------------------------------------


class TestImpact:
    def test_high_impact(self):
        event = _event(
            date(2024, 1, 1), materiality=5
        )
        result = analyze_events([event], "TEST", _AS_OF)
        cls = result.classifications[0]
        assert cls.impact == EventImpact.HIGH.value

    def test_medium_impact(self):
        event = _event(
            date(2024, 1, 1), materiality=3
        )
        result = analyze_events([event], "TEST", _AS_OF)
        cls = result.classifications[0]
        assert cls.impact == EventImpact.MEDIUM.value

    def test_low_impact(self):
        event = _event(
            date(2024, 1, 1), materiality=1
        )
        result = analyze_events([event], "TEST", _AS_OF)
        cls = result.classifications[0]
        assert cls.impact == EventImpact.LOW.value


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------


class TestClustering:
    def test_cluster_close_events(self):
        events = [
            _event(date(2024, 1, 1), title="Earnings Q1"),
            _event(date(2024, 1, 3), title="Earnings guidance"),
            _event(date(2024, 3, 1), title="Earnings Q2"),
        ]
        result = analyze_events(events, "TEST", _AS_OF)
        # First two should cluster, third separate
        assert len(result.clusters) >= 1
        assert result.clusters[0].event_count == 2

    def test_separate_category_clusters(self):
        events = [
            _event(
                date(2024, 1, 1),
                category="EARNINGS",
                title="Q1 Results",
                description="Quarterly results announced",
            ),
            _event(
                date(2024, 1, 1),
                category="MANAGEMENT",
                title="New CFO appointed",
                description="Chief financial officer appointed to the board",
            ),
        ]
        result = analyze_events(events, "TEST", _AS_OF)
        categories = [c.category for c in result.clusters]
        assert EventCategory.EARNINGS.value in categories
        assert EventCategory.MANAGEMENT.value in categories


# ---------------------------------------------------------------------------
# Counts
# ---------------------------------------------------------------------------


class TestCounts:
    def test_category_counts(self):
        events = [
            _event(
                date(2024, 1, 1),
                category="EARNINGS",
                title="Q1 Results",
                description="Quarterly results announced",
            ),
            _event(
                date(2024, 2, 1),
                category="EARNINGS",
                title="Q2 Results",
                description="Quarterly results announced",
            ),
            _event(
                date(2024, 3, 1),
                category="MANAGEMENT",
                title="New CFO",
                description="Chief financial officer appointed",
            ),
        ]
        result = analyze_events(events, "TEST", _AS_OF)
        assert result.category_counts["EARNINGS"] == 2
        assert result.category_counts["MANAGEMENT"] == 1

    def test_direction_counts(self):
        events = [
            _event(
                date(2024, 1, 1),
                direction="POSITIVE",
            ),
            _event(
                date(2024, 2, 1),
                direction="NEGATIVE",
            ),
            _event(
                date(2024, 3, 1),
                direction="NEUTRAL",
            ),
        ]
        result = analyze_events(events, "TEST", _AS_OF)
        assert result.direction_counts["POSITIVE"] == 1
        assert result.direction_counts["NEGATIVE"] == 1
        assert result.direction_counts["NEUTRAL"] == 1
