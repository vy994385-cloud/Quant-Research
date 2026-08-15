from __future__ import annotations

from datetime import datetime

from src.research.acquisition.models import (
    ResearchCategory,
    ResearchQuestion,
)


_DEFAULT_RESEARCH_QUESTIONS: tuple[ResearchQuestion, ...] = (
    ResearchQuestion(
        question_id="business-model",
        category=ResearchCategory.BUSINESS_MODEL,
        question="What are the company's major businesses, products, services, and revenue drivers?",
        priority=1,
    ),
    ResearchQuestion(
        question_id="products",
        category=ResearchCategory.PRODUCTS,
        question="What important products, platforms, or services has the company launched, expanded, or materially changed?",
        priority=2,
    ),
    ResearchQuestion(
        question_id="customers",
        category=ResearchCategory.CUSTOMERS,
        question="Who are the company's important disclosed customers, customer groups, and strategic accounts?",
        priority=2,
    ),
    ResearchQuestion(
        question_id="management",
        category=ResearchCategory.MANAGEMENT,
        question="What material management, leadership, governance, or strategic changes have occurred?",
        priority=2,
    ),
    ResearchQuestion(
        question_id="capital-allocation",
        category=ResearchCategory.CAPITAL_ALLOCATION,
        question="How is management allocating capital through investment, acquisitions, dividends, buybacks, debt, or other major uses?",
        priority=2,
    ),
    ResearchQuestion(
        question_id="innovation",
        category=ResearchCategory.INNOVATION,
        question="What evidence exists of meaningful R&D, patents, engineering capability, innovation, or new technology development?",
        priority=1,
    ),
    ResearchQuestion(
        question_id="ai-technology",
        category=ResearchCategory.AI_TECHNOLOGY,
        question="What concrete evidence exists of AI, automation, cloud, semiconductor, software, or other strategically important technology exposure?",
        priority=1,
    ),
    ResearchQuestion(
        question_id="transformation",
        category=ResearchCategory.TRANSFORMATION,
        question="What evidence shows that the company is transforming its business, products, operations, or competitive model?",
        priority=1,
    ),
    ResearchQuestion(
        question_id="competitive-position",
        category=ResearchCategory.COMPETITIVE_POSITION,
        question="What evidence supports or challenges the company's competitive position, differentiation, market share, pricing power, or barriers to entry?",
        priority=1,
    ),
    ResearchQuestion(
        question_id="partnerships",
        category=ResearchCategory.PARTNERSHIPS,
        question="What material partnerships, alliances, joint ventures, or ecosystem relationships could affect the business?",
        priority=2,
    ),
    ResearchQuestion(
        question_id="regulatory",
        category=ResearchCategory.REGULATORY,
        question="What material regulatory, legal, policy, compliance, or government developments could affect the company?",
        priority=2,
    ),
    ResearchQuestion(
        question_id="risks",
        category=ResearchCategory.RISKS,
        question="What material operational, financial, technological, regulatory, competitive, or strategic risks are supported by evidence?",
        priority=1,
    ),
    ResearchQuestion(
        question_id="material-events",
        category=ResearchCategory.MATERIAL_EVENTS,
        question="What recent material events could reasonably affect the company's business, financial position, or future outlook?",
        priority=1,
    ),
    ResearchQuestion(
        question_id="industry",
        category=ResearchCategory.INDUSTRY,
        question="What important industry developments could materially change the company's future opportunity or risk?",
        priority=2,
    ),
)


class ResearchPlanner:
    """
    Creates a deterministic research workload.

    The planner decides what needs to be researched.
    It does not retrieve sources, interpret evidence, or produce
    investment conclusions.
    """

    def plan(
        self,
        company: str,
        as_of: datetime,
    ) -> list[ResearchQuestion]:
        if not company.strip():
            raise ValueError("company must not be empty")

        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

        return list(_DEFAULT_RESEARCH_QUESTIONS)
