from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ManagementChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    person_name: str = Field(min_length=1)

    role: str = Field(min_length=1)

    change_type: str = Field(min_length=1)

    effective_date: date

    reason: str | None = None

    evidence_ids: list[str] = Field(default_factory=list)
