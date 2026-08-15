from datetime import datetime, timezone

import pytest

from src.research.acquisition.models import ResearchCategory
from src.research.acquisition.planner import ResearchPlanner


def test_planner_creates_broad_research_workload():
    planner = ResearchPlanner()

    questions = planner.plan(
        "TCS",
        datetime(2026, 8, 15, 12, tzinfo=timezone.utc),
    )

    assert len(questions) == 14

    categories = {question.category for question in questions}

    assert ResearchCategory.BUSINESS_MODEL in categories
    assert ResearchCategory.AI_TECHNOLOGY in categories
    assert ResearchCategory.INNOVATION in categories
    assert ResearchCategory.TRANSFORMATION in categories
    assert ResearchCategory.CUSTOMERS in categories
    assert ResearchCategory.MANAGEMENT in categories
    assert ResearchCategory.COMPETITIVE_POSITION in categories
    assert ResearchCategory.RISKS in categories


def test_planner_is_deterministic():
    planner = ResearchPlanner()

    as_of = datetime(
        2026,
        8,
        15,
        12,
        tzinfo=timezone.utc,
    )

    first = planner.plan("TCS", as_of)
    second = planner.plan("TCS", as_of)

    assert first == second


def test_planner_rejects_empty_company():
    planner = ResearchPlanner()

    with pytest.raises(ValueError, match="company must not be empty"):
        planner.plan(
            "   ",
            datetime(
                2026,
                8,
                15,
                12,
                tzinfo=timezone.utc,
            ),
        )


def test_planner_rejects_naive_as_of():
    planner = ResearchPlanner()

    with pytest.raises(
        ValueError,
        match="as_of must be timezone-aware",
    ):
        planner.plan("TCS", datetime(2026, 8, 15, 12))
