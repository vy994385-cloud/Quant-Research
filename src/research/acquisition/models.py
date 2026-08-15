from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ResearchCategory(StrEnum):
    BUSINESS_MODEL = "business_model"
    PRODUCTS = "products"
    CUSTOMERS = "customers"
    MANAGEMENT = "management"
    CAPITAL_ALLOCATION = "capital_allocation"
    INNOVATION = "innovation"
    AI_TECHNOLOGY = "ai_technology"
    TRANSFORMATION = "transformation"
    COMPETITIVE_POSITION = "competitive_position"
    PARTNERSHIPS = "partnerships"
    REGULATORY = "regulatory"
    RISKS = "risks"
    MATERIAL_EVENTS = "material_events"
    INDUSTRY = "industry"


class ResearchQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str = Field(min_length=1)
    category: ResearchCategory
    question: str = Field(min_length=1)
    priority: int = Field(ge=1, le=5)


class SourceCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    url: str = Field(min_length=1)
    title: str = Field(min_length=1)

    published_at: datetime | None = None
    available_at: datetime | None = None

    reliability_tier: int = Field(ge=1, le=6)


class ResearchObservation(BaseModel):
    """
    A factual observation extracted from a source.

    This model deliberately contains no score, recommendation,
    bullish/bearish label, or investment conclusion.
    """

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    company: str = Field(min_length=1)
    category: ResearchCategory

    claim: str = Field(min_length=1)
    evidence_excerpt: str = Field(min_length=1)

    source_id: str = Field(min_length=1)

    reliability_tier: int | None = Field(
        default=None,
        ge=1,
        le=6,
    )

    published_at: datetime | None = None
    available_at: datetime | None = None
    extracted_at: datetime

    confidence: float = Field(ge=0.0, le=1.0)

    def is_known_at(self, as_of: datetime) -> bool:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

        if self.available_at is None:
            return False

        if self.available_at.tzinfo is None or self.available_at.utcoffset() is None:
            raise ValueError("available_at must be timezone-aware")

        return self.available_at <= as_of
