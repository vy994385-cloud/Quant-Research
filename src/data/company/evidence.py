from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class Evidence(BaseModel):
    """
    Source supporting a company-intelligence observation.

    The system should never treat an unsupported claim
    as verified intelligence.
    """

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1)
    source_type: str = Field(min_length=1)

    title: str = Field(min_length=1)

    published_date: date | None = None

    url: str | None = None

    reliability_tier: int = Field(ge=1, le=6)

    excerpt: str | None = None

    @property
    def is_high_quality(self) -> bool:
        return self.reliability_tier <= 3
