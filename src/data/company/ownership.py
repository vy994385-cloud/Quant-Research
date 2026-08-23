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


class TopHolder(BaseModel):
    """One top institutional or significant holder."""

    model_config = ConfigDict(extra="forbid")

    holder_name: str = Field(min_length=1)
    holder_type: str = "INSTITUTIONAL"
    shares_held: int | None = None
    share_percentage: float | None = Field(default=None, ge=0, le=100)
    date_reported: date | None = None
    source_name: str | None = None
    source_type: str | None = None


class OwnershipSummary(BaseModel):
    """Complete ownership breakdown with top holders."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    period_end: date

    promoter_percentage: float | None = Field(default=None, ge=0, le=100)
    institutional_percentage: float | None = Field(default=None, ge=0, le=100)
    public_percentage: float | None = Field(default=None, ge=0, le=100)
    insider_percentage: float | None = Field(default=None, ge=0, le=100)

    top_holders: tuple[TopHolder, ...] = ()

    source_name: str | None = None
    source_type: str | None = None

    @property
    def has_top_holders(self) -> bool:
        return len(self.top_holders) > 0

    @property
    def holder_count(self) -> int:
        return len(self.top_holders)
