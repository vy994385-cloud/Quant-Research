from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from src.data.ingestion.provenance import (
    DataProvenance,
    ReviewStatus,
    SourceType,
    create_provenance,
)


def test_high_quality_accepted_exchange_source():

    provenance = DataProvenance(
        provider_name="Example Exchange",
        source_type=SourceType.EXCHANGE,
        retrieved_at=datetime(
            2026,
            8,
            8,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 7),
        reliability_tier=1,
        review_status=ReviewStatus.ACCEPT,
    )

    assert provenance.is_high_quality
    assert provenance.retrieval_is_timezone_aware


def test_unreviewed_source_is_not_high_quality():

    provenance = DataProvenance(
        provider_name="Example Vendor",
        source_type=SourceType.VENDOR,
        retrieved_at=datetime(
            2026,
            8,
            8,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 7),
        reliability_tier=1,
    )

    assert not provenance.is_high_quality
    assert provenance.review_status == ReviewStatus.NEEDS_REVIEW


def test_low_reliability_source_is_not_high_quality():

    provenance = DataProvenance(
        provider_name="Example Source",
        source_type=SourceType.NEWS,
        retrieved_at=datetime(
            2026,
            8,
            8,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 7),
        reliability_tier=4,
        review_status=ReviewStatus.ACCEPT,
    )

    assert not provenance.is_high_quality


def test_naive_datetime_is_rejected_at_model_boundary():
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        DataProvenance(
            provider_name="Example Source",
            source_type=SourceType.VENDOR,
            retrieved_at=datetime(2026, 8, 8, 10, 0),
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 7),
            reliability_tier=2,
            review_status=ReviewStatus.ACCEPT,
        )


def test_reliability_tier_must_be_between_one_and_five():

    with pytest.raises(ValidationError):

        DataProvenance(
            provider_name="Example Source",
            source_type=SourceType.VENDOR,
            retrieved_at=datetime.now(timezone.utc),
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 7),
            reliability_tier=6,
        )


def test_create_provenance_uses_timezone_aware_utc_time():

    provenance = create_provenance(
        provider_name="Example Exchange",
        source_type=SourceType.EXCHANGE,
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 7),
        reliability_tier=1,
        review_status=ReviewStatus.ACCEPT,
    )

    assert provenance.retrieval_is_timezone_aware
    assert provenance.retrieved_at.tzinfo == timezone.utc


def test_rejected_source_is_not_high_quality():

    provenance = DataProvenance(
        provider_name="Example Exchange",
        source_type=SourceType.EXCHANGE,
        retrieved_at=datetime.now(timezone.utc),
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 7),
        reliability_tier=1,
        review_status=ReviewStatus.REJECT,
    )

    assert not provenance.is_high_quality


def test_extra_fields_are_rejected():

    with pytest.raises(ValidationError):

        DataProvenance(
            provider_name="Example",
            source_type=SourceType.VENDOR,
            retrieved_at=datetime.now(timezone.utc),
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 7),
            reliability_tier=2,
            unexpected_field="bad",
        )


def test_period_start_must_not_be_after_period_end():
    with pytest.raises(ValueError, match="period_start"):
        DataProvenance(
            provider_name="Example",
            source_type=SourceType.VENDOR,
            retrieved_at=datetime.now(timezone.utc),
            period_start=date(2026, 8, 8),
            period_end=date(2026, 8, 7),
            reliability_tier=2,
        )


def test_naive_retrieved_at_is_rejected_at_model_boundary():
    with pytest.raises(ValueError, match="timezone-aware"):
        DataProvenance(
            provider_name="Example",
            source_type=SourceType.VENDOR,
            retrieved_at=datetime(2026, 8, 8, 10),
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 7),
            reliability_tier=2,
        )
