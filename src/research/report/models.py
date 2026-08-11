from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.research.signals.models import (
    ResearchSignal,
)


class ResearchConclusion(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    MIXED = "MIXED"
    NEUTRAL = "NEUTRAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ResearchEvidence(BaseModel):
    """
    A concise, point-in-time piece of evidence included in a report.
    """

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)

    symbol: str = Field(min_length=1)
    observation_at: datetime

    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()

    confidence: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    @field_validator("observation_at")
    @classmethod
    def require_timezone(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None:
            raise ValueError(
                "observation_at must be timezone-aware"
            )
        return value

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        value = value.strip().upper()

        if not value:
            raise ValueError("symbol cannot be empty")

        return value


class ResearchReport(BaseModel):
    """
    User-facing company research report.

    The report is an evidence assembly layer. It does not claim
    to predict returns and does not fabricate missing evidence.
    """

    model_config = ConfigDict(extra="forbid")

    report_version: str = "1.0"

    symbol: str = Field(min_length=1)

    as_of: datetime

    conclusion: ResearchConclusion
    confidence: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    thesis: str = Field(min_length=1)

    features: tuple[str, ...] = ()
    signals: tuple[ResearchSignal, ...] = ()

    positive_evidence: tuple[ResearchEvidence, ...] = ()
    negative_evidence: tuple[ResearchEvidence, ...] = ()

    data_quality_notes: tuple[str, ...] = ()

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        value = value.strip().upper()

        if not value:
            raise ValueError("symbol cannot be empty")

        return value

    @field_validator("as_of")
    @classmethod
    def require_timezone(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None:
            raise ValueError(
                "as_of must be timezone-aware"
            )
        return value
