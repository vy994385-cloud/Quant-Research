from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EventDirection = Literal[
    "POSITIVE",
    "NEGATIVE",
    "NEUTRAL",
    "UNKNOWN",
]


class CompanyEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    event_date: date

    category: str = Field(min_length=1)

    title: str = Field(min_length=1)

    description: str = Field(min_length=1)

    direction: EventDirection = "UNKNOWN"

    materiality: int = Field(
        default=1,
        ge=1,
        le=5,
    )

    evidence_ids: list[str] = Field(default_factory=list)
