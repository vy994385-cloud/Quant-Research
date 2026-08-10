from datetime import datetime, timezone
from decimal import Decimal

from src.research.data_quality import MarketBarLike
from src.research.integrity import validate_research_integrity
from src.research.provenance import DataProvenance


def make_bar() -> MarketBarLike:
    return MarketBarLike(
        timestamp=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("1000"),
    )


def make_provenance(
    available_at: datetime | None,
) -> DataProvenance:
    return DataProvenance(
        source="Reuters",
        source_url="https://example.com",
        retrieved_at=datetime(
            2026,
            1,
            1,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        published_at=datetime(
            2026,
            1,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        available_at=available_at,
        record_id="record-1",
    )


def test_valid_research_passes_integrity_gate() -> None:
    report = validate_research_integrity(
        [make_bar()],
        [
            make_provenance(
                datetime(
                    2026,
                    1,
                    1,
                    10,
                    0,
                    tzinfo=timezone.utc,
                )
            )
        ],
        research_timestamp=datetime(
            2026,
            1,
            1,
            11,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert report.is_valid is True
    assert report.requires_review is False
    assert report.issue_count == 0


def test_future_data_requires_review() -> None:
    report = validate_research_integrity(
        [make_bar()],
        [
            make_provenance(
                datetime(
                    2026,
                    1,
                    1,
                    12,
                    0,
                    tzinfo=timezone.utc,
                )
            )
        ],
        research_timestamp=datetime(
            2026,
            1,
            1,
            11,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert report.is_valid is False
    assert report.requires_review is True
    assert len(report.leakage_violations) == 1


def test_bad_market_data_requires_review() -> None:
    bad_bar = MarketBarLike(
        timestamp=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        open=Decimal("100"),
        high=Decimal("90"),
        low=Decimal("80"),
        close=Decimal("85"),
        volume=Decimal("1000"),
    )

    report = validate_research_integrity(
        [bad_bar],
        [
            make_provenance(
                datetime(
                    2026,
                    1,
                    1,
                    10,
                    0,
                    tzinfo=timezone.utc,
                )
            )
        ],
        research_timestamp=datetime(
            2026,
            1,
            1,
            11,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert report.is_valid is False
    assert report.requires_review is True
    assert report.data_quality.issue_count > 0
