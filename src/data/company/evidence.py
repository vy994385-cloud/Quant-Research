from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class Evidence(BaseModel):
    """
    Source supporting a company-intelligence observation.

    Evidence is factual provenance metadata. It must not be
    interpreted as a company score or investment conclusion.

    Point-in-time research must use available_at to determine
    whether the evidence was actually knowable at an as-of time.
    """

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)

    source_name: str = Field(min_length=1)

    source_type: str = Field(min_length=1)

    title: str = Field(min_length=1)

    published_date: date | None = None

    published_at: datetime | None = None

    available_at: datetime | None = None

    retrieved_at: datetime | None = None

    url: str | None = None

    reliability_tier: int = Field(ge=1, le=6)

    excerpt: str | None = None

    @property
    def is_high_quality(self) -> bool:
        return self.reliability_tier <= 3

    @property
    def is_point_in_time_eligible(self) -> bool:
        """
        Evidence without an availability timestamp cannot be safely
        used in point-in-time research.
        """
        return self.available_at is not None

    def is_known_at(self, as_of: datetime) -> bool:
        """
        Return whether this evidence was available by the supplied
        point-in-time timestamp.

        A missing available_at is deliberately treated as unknown,
        never as available.
        """
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

        if self.available_at is None:
            return False

        if self.available_at.tzinfo is None or self.available_at.utcoffset() is None:
            raise ValueError("available_at must be timezone-aware")

        return self.available_at <= as_of
