from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OwnershipSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    period_end: date

    promoter_percentage: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    institutional_percentage: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    public_percentage: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    promoter_pledged_percentage: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
    )
