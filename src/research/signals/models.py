from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SignalDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


class SignalSeverity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ResearchSignal(BaseModel):
    """
    Point-in-time research signal.

    Signals are derived from already-calculated research evidence.
    They do not fetch data and do not predict returns by themselves.
    """

    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(min_length=1)
    category: str = Field(min_length=1)

    direction: SignalDirection
    severity: SignalSeverity

    confidence: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)

    symbol: str = Field(min_length=1)

    observation_at: datetime

    supporting_features: tuple[str, ...] = ()
    supporting_metrics: tuple[str, ...] = ()

    @field_validator(
        "signal_id",
        "category",
        "symbol",
        mode="before",
    )
    @classmethod
    def normalize_identity(cls, value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("identity fields must be strings")

        normalized = value.strip().upper()

        if not normalized:
            raise ValueError("identity fields cannot be empty")

        return normalized

    @field_validator(
        "supporting_features",
        "supporting_metrics",
        mode="before",
    )
    @classmethod
    def normalize_supporting_values(
        cls,
        value: object,
    ) -> tuple[str, ...]:
        if value is None:
            return ()

        if isinstance(value, str):
            value = (value,)

        if not isinstance(value, (tuple, list)):
            raise TypeError(
                "supporting values must be a sequence"
            )

        normalized: list[str] = []

        for item in value:
            if not isinstance(item, str):
                raise TypeError(
                    "supporting values must contain strings"
                )

            item = item.strip().lower()

            if item and item not in normalized:
                normalized.append(item)

        return tuple(normalized)

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
