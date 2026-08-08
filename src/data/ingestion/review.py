from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from src.data.ingestion.anomalies import MarketAnomaly
from src.data.ingestion.provenance import (
    DataProvenance,
    ReviewStatus,
)
from src.data.models import PriceBar


class ReviewDecision(str, Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ReviewReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: str = Field(min_length=1)


class IngestionReview(BaseModel):
    """
    Unified, explainable review result for an ingestion batch.

    This object describes data quality. It is NOT a trading signal.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    decision: ReviewDecision

    reasons: list[ReviewReason] = Field(default_factory=list)

    anomaly_count: int = Field(ge=0)

    provenance_quality: bool

    records_received: int = Field(ge=0)

    records_accepted: int = Field(ge=0)

    records_rejected: int = Field(ge=0)

    @property
    def is_trade_signal(self) -> bool:
        """
        Explicitly prevents this object from being interpreted
        as a trading recommendation.
        """

        return False


def review_ingestion(
    symbol: str,
    bars: list[PriceBar],
    provenance: DataProvenance,
    anomalies: list[MarketAnomaly],
    validation_errors: list[str] | None = None,
) -> IngestionReview:
    """
    Produce one explainable ingestion-quality decision.

    Rules:

    - structural validation errors => REJECT
    - rejected provenance => REJECT
    - suspicious anomalies => NEEDS_REVIEW
    - unreviewed provenance => NEEDS_REVIEW
    - otherwise => ACCEPT
    """

    errors = validation_errors or []

    reasons: list[ReviewReason] = []

    for error in errors:
        reasons.append(
            ReviewReason(
                code="VALIDATION_ERROR",
                message=error,
                severity="CRITICAL",
            )
        )

    if provenance.review_status == ReviewStatus.REJECT:

        reasons.append(
            ReviewReason(
                code="PROVENANCE_REJECTED",
                message=(
                    "The source has been explicitly rejected "
                    "for research use."
                ),
                severity="CRITICAL",
            )
        )

    elif provenance.review_status == ReviewStatus.NEEDS_REVIEW:

        reasons.append(
            ReviewReason(
                code="PROVENANCE_UNREVIEWED",
                message=(
                    "The source has not yet been approved "
                    "for research use."
                ),
                severity="WARNING",
            )
        )

    for anomaly in anomalies:

        reasons.append(
            ReviewReason(
                code=anomaly.code,
                message=anomaly.message,
                severity=anomaly.severity.value,
            )
        )

    if errors or provenance.review_status == ReviewStatus.REJECT:

        decision = ReviewDecision.REJECT

    elif (
        provenance.review_status == ReviewStatus.NEEDS_REVIEW
        or anomalies
    ):

        decision = ReviewDecision.NEEDS_REVIEW

    else:

        decision = ReviewDecision.ACCEPT

    records_received = len(bars)

    records_rejected = 1 if errors else 0

    records_accepted = (
        records_received
        if not errors
        else max(0, records_received - records_rejected)
    )

    return IngestionReview(
        symbol=symbol,
        decision=decision,
        reasons=reasons,
        anomaly_count=len(anomalies),
        provenance_quality=provenance.is_high_quality,
        records_received=records_received,
        records_accepted=records_accepted,
        records_rejected=records_rejected,
    )
