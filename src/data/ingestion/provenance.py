from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceType(str, Enum):
    EXCHANGE = "EXCHANGE"
    REGULATORY = "REGULATORY"
    BROKER = "BROKER"
    VENDOR = "VENDOR"
    COMPANY = "COMPANY"
    NEWS = "NEWS"
    DERIVED = "DERIVED"


class ReviewStatus(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class DataProvenance(BaseModel):
    """
    Metadata describing where a dataset came from.

    Provenance is deliberately independent from the actual
    market-data record so the same metadata structure can
    eventually be used for prices, financials, filings,
    corporate events and news.
    """

    model_config = ConfigDict(extra="forbid")

    provider_name: str = Field(min_length=1)
    source_type: SourceType

    retrieved_at: datetime

    period_start: date
    period_end: date

    reliability_tier: int = Field(ge=1, le=5)

    source_reference: str | None = None

    review_status: ReviewStatus = ReviewStatus.NEEDS_REVIEW

    notes: str | None = None

    @model_validator(mode="after")
    def validate_temporal_integrity(self):
        if self.retrieved_at.tzinfo is None:
            raise ValueError(
                "retrieved_at must be timezone-aware"
            )

        if self.period_start > self.period_end:
            raise ValueError(
                "period_start must not be after period_end"
            )

        return self

    @property
    def is_high_quality(self) -> bool:
        return (
            self.reliability_tier <= 2
            and self.review_status == ReviewStatus.ACCEPT
        )

    @property
    def retrieval_is_timezone_aware(self) -> bool:
        return self.retrieved_at.tzinfo is not None


def create_provenance(
    provider_name: str,
    source_type: SourceType,
    period_start: date,
    period_end: date,
    reliability_tier: int,
    source_reference: str | None = None,
    review_status: ReviewStatus = ReviewStatus.NEEDS_REVIEW,
    notes: str | None = None,
) -> DataProvenance:
    """
    Create provenance metadata using the current UTC time.

    UTC is used so records remain comparable across machines,
    providers and deployments.
    """

    return DataProvenance(
        provider_name=provider_name,
        source_type=source_type,
        retrieved_at=datetime.now(timezone.utc),
        period_start=period_start,
        period_end=period_end,
        reliability_tier=reliability_tier,
        source_reference=source_reference,
        review_status=review_status,
        notes=notes,
    )
