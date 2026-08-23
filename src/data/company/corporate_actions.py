"""
Corporate actions data model.

Structured representation of corporate actions such as dividends,
splits, buybacks, mergers, and capital changes.

All fields are sourced from recorded evidence and never invented.
Each action carries provenance and as_of metadata.

This module does NOT create investment recommendations or
automated trading signals.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class CorporateActionType(str, Enum):
    """Types of corporate actions tracked."""

    DIVIDEND = "DIVIDEND"
    STOCK_SPLIT = "STOCK_SPLIT"
    BONUS_ISSUE = "BONUS_ISSUE"
    RIGHTS_ISSUE = "RIGHTS_ISSUE"
    BUYBACK = "BUYBACK"
    MERGER = "MERGER"
    ACQUISITION = "ACQUISITION"
    DEMERGER = "DEMERGER"
    DELISTING = "DELISTING"
    LISTING = "LISTING"
    SHARE_CAPITAL_CHANGE = "SHARE_CAPITAL_CHANGE"
    OTHER = "OTHER"


class CorporateActionItem(BaseModel):
    """
    A single corporate action for a company.

    All fields are preserved from the source evidence.
    """

    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    action_type: CorporateActionType

    title: str = Field(min_length=1)
    description: str = ""

    announcement_date: date | None = None
    effective_date: date | None = None
    record_date: date | None = None

    value: str | None = None
    ratio: str | None = None

    source_name: str = ""
    source_url: str = ""
    provenance_id: str | None = None

    published_at: datetime | None = None
    available_at: datetime | None = None
    as_of: datetime | None = None


class CorporateActionResult(BaseModel):
    """
    Aggregated corporate actions for a company.

    Describes available actions with type counts.
    Does not score or rank actions.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime

    items: tuple[CorporateActionItem, ...] = ()
    item_count: int = 0

    type_counts: dict[str, int] = Field(
        default_factory=dict,
    )

    source_count: int = 0
    notes: tuple[str, ...] = ()

    @classmethod
    def from_items(
        cls,
        symbol: str,
        as_of: datetime,
        items: tuple[CorporateActionItem, ...],
    ) -> CorporateActionResult:
        """Build a result from a collection of items."""

        type_counts: dict[str, int] = {}
        source_names: set[str] = set()

        for item in items:
            t = item.action_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
            if item.source_name:
                source_names.add(item.source_name)

        notes: list[str] = []
        if not items:
            notes.append(
                "No corporate actions available for this company."
            )

        return cls(
            symbol=symbol,
            as_of=as_of,
            items=items,
            item_count=len(items),
            type_counts=type_counts,
            source_count=len(source_names),
            notes=tuple(notes),
        )
