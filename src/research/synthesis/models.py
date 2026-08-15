from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


class EvidenceType(str, Enum):
    FEATURE = "FEATURE"
    SIGNAL = "SIGNAL"
    COMPANY_INTELLIGENCE = "COMPANY_INTELLIGENCE"
    TREND = "TREND"
    MARKET = "MARKET"
    RISK = "RISK"
    FUTURE_TECHNOLOGY = "FUTURE_TECHNOLOGY"


class EvidenceReliability(str, Enum):
    """
    Reliability class of the underlying evidence.

    This describes evidence quality, not expected investment return.
    """

    PRIMARY = "PRIMARY"
    REGULATORY = "REGULATORY"
    AUDITED = "AUDITED"
    SECONDARY = "SECONDARY"
    TERTIARY = "TERTIARY"
    UNKNOWN = "UNKNOWN"


_RELIABILITY_WEIGHT = {
    EvidenceReliability.REGULATORY: Decimal("1.00"),
    EvidenceReliability.AUDITED: Decimal("1.00"),
    EvidenceReliability.PRIMARY: Decimal("0.90"),
    EvidenceReliability.SECONDARY: Decimal("0.65"),
    EvidenceReliability.TERTIARY: Decimal("0.35"),
    EvidenceReliability.UNKNOWN: Decimal("0.20"),
}


class EvidenceItem(BaseModel):
    """
    One traceable piece of research evidence.

    This model describes evidence already produced by lower
    research layers. It does not invent new evidence.
    """

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)

    evidence_type: EvidenceType

    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)

    direction: EvidenceDirection

    confidence: Decimal = Field(ge=0, le=1)

    reliability: EvidenceReliability = (
        EvidenceReliability.UNKNOWN
    )

    observation_at: datetime

    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()

        if not normalized:
            raise ValueError("symbol cannot be empty")

        return normalized

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

    @field_validator("source_ids", "provenance_ids")
    @classmethod
    def normalize_references(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        normalized: list[str] = []

        for item in values:
            value = item.strip()

            if not value:
                raise ValueError(
                    "evidence references cannot be empty"
                )

            normalized.append(value)

        return tuple(normalized)

    @property
    def reliability_weight(self) -> Decimal:
        return _RELIABILITY_WEIGHT[self.reliability]

    @property
    def weighted_confidence(self) -> Decimal:
        """
        Confidence adjusted by evidence reliability.

        This is an evidence-quality measure, not a return forecast.
        """

        return self.confidence * self.reliability_weight


class EvidenceSynthesis(BaseModel):
    """
    Deterministic synthesis of validated research evidence.

    This is an evidence aggregation object, not a trading signal.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime

    evidence: tuple[EvidenceItem, ...] = ()

    positive_count: int = Field(ge=0)
    negative_count: int = Field(ge=0)
    neutral_count: int = Field(ge=0)

    positive_weight: Decimal = Field(ge=0)
    negative_weight: Decimal = Field(ge=0)

    average_confidence: Decimal = Field(
        ge=0,
        le=1,
    )

    weighted_confidence: Decimal = Field(
        ge=0,
        le=1,
    )

    conflict_detected: bool = False

    direction: EvidenceDirection

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized = value.strip().upper()

        if not normalized:
            raise ValueError("symbol cannot be empty")

        return normalized

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


__all__ = [
    "EvidenceDirection",
    "EvidenceItem",
    "EvidenceReliability",
    "EvidenceSynthesis",
    "EvidenceType",
]
