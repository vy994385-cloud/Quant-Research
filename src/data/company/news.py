"""
Company news data model.

Structured representation of company-specific news items with
source, category, and temporal metadata.

News items are sourced from recorded evidence and never invented.
Every news item carries provenance and as_of metadata.

This module does NOT create AI-generated importance scores
or investment recommendations.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class NewsCategory(str, Enum):
    """Categorical classification of company news."""

    EARNINGS = "EARNINGS"
    PRODUCT = "PRODUCT"
    TECHNOLOGY = "TECHNOLOGY"
    MANAGEMENT = "MANAGEMENT"
    REGULATION = "REGULATION"
    ACQUISITION = "ACQUISITION"
    PARTNERSHIP = "PARTNERSHIP"
    LITIGATION = "LITIGATION"
    CAPITAL_ALLOCATION = "CAPITAL_ALLOCATION"
    INDUSTRY = "INDUSTRY"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    OWNERSHIP = "OWNERSHIP"
    OTHER = "OTHER"


class NewsDirection(str, Enum):
    """Descriptive direction of a news item."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class CompanyNewsItem(BaseModel):
    """
    A single news item for a company.

    All fields are preserved from the source evidence.
    No importance scores or investment relevance ratings are assigned.
    """

    model_config = ConfigDict(extra="forbid")

    news_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    headline: str = Field(min_length=1)
    summary: str = ""

    category: NewsCategory = NewsCategory.OTHER
    direction: NewsDirection = NewsDirection.UNKNOWN

    source_name: str = ""
    source_url: str = ""
    source_type: str = ""

    published_at: datetime | None = None
    available_at: datetime | None = None

    event_date: date | None = None

    related_metrics: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    as_of: datetime | None = None

    provenance_id: str | None = None


class CompanyNewsResult(BaseModel):
    """
    Aggregated news results for a company.

    Describes available news items with category counts.
    Does not rank or score news items.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime

    items: tuple[CompanyNewsItem, ...] = ()
    item_count: int = 0

    category_counts: dict[str, int] = Field(
        default_factory=dict,
    )

    source_count: int = 0
    source_names: tuple[str, ...] = ()

    notes: tuple[str, ...] = ()

    @classmethod
    def from_items(
        cls,
        symbol: str,
        as_of: datetime,
        items: tuple[CompanyNewsItem, ...],
    ) -> CompanyNewsResult:
        """Build a news result from a collection of items."""

        category_counts: dict[str, int] = {}
        source_names: set[str] = set()

        for item in items:
            cat = item.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
            if item.source_name:
                source_names.add(item.source_name)

        notes: list[str] = []
        if not items:
            notes.append("No news items available for this company.")

        return cls(
            symbol=symbol,
            as_of=as_of,
            items=items,
            item_count=len(items),
            category_counts=category_counts,
            source_count=len(source_names),
            source_names=tuple(sorted(source_names)),
            notes=tuple(notes),
        )
