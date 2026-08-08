from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class Security(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    company_name: str = Field(min_length=1)

    exchange: str = Field(min_length=1)
    isin: str = Field(min_length=1)

    security_type: str = Field(min_length=1)

    sector: str | None = None
    industry: str | None = None

    currency: str = "INR"

    active_from: date | None = None
    active_to: date | None = None

    @property
    def is_active(self) -> bool:
        return self.active_to is None
