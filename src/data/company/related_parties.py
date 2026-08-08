from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RelatedPartyTransaction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    period_end: date

    related_party_name: str = Field(min_length=1)

    transaction_type: str = Field(min_length=1)

    amount: Decimal = Field(ge=0)

    description: str | None = None

    evidence_ids: list[str] = Field(default_factory=list)
