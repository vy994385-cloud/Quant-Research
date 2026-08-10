from datetime import datetime, timezone

import pytest

from src.research.leakage import (
    assert_no_future_data,
    find_future_data,
)
from src.research.provenance import DataProvenance


def make_provenance(
    *,
    available_at: datetime | None,
    record_id: str = "record-1",
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
        record_id=record_id,
    )


def test_future_data_is_detected() -> None:
    provenance = make_provenance(
        available_at=datetime(
            2026,
            1,
            1,
            11,
            0,
            tzinfo=timezone.utc,
        )
    )

    violations = find_future_data(
        [provenance],
        timestamp=datetime(
            2026,
            1,
            1,
            10,
            30,
            tzinfo=timezone.utc,
        ),
    )

    assert len(violations) == 1
    assert violations[0].record_id == "record-1"


def test_available_data_is_not_flagged() -> None:
    provenance = make_provenance(
        available_at=datetime(
            2026,
            1,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        )
    )

    violations = find_future_data(
        [provenance],
        timestamp=datetime(
            2026,
            1,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert violations == ()


def test_missing_available_at_is_flagged() -> None:
    provenance = make_provenance(
        available_at=None,
    )

    violations = find_future_data(
        [provenance],
        timestamp=datetime(
            2026,
            1,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        ),
    )

    assert len(violations) == 1


def test_naive_research_timestamp_is_rejected() -> None:
    provenance = make_provenance(
        available_at=datetime(
            2026,
            1,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        )
    )

    with pytest.raises(
        ValueError,
        match="timestamp must be timezone-aware",
    ):
        find_future_data(
            [provenance],
            timestamp=datetime(2026, 1, 1, 10, 0),
        )


def test_assert_no_future_data_raises() -> None:
    provenance = make_provenance(
        available_at=datetime(
            2026,
            1,
            1,
            11,
            0,
            tzinfo=timezone.utc,
        )
    )

    with pytest.raises(
        ValueError,
        match="research data leakage detected",
    ):
        assert_no_future_data(
            [provenance],
            timestamp=datetime(
                2026,
                1,
                1,
                10,
                0,
                tzinfo=timezone.utc,
            ),
        )
