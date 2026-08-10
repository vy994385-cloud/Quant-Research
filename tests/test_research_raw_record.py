from datetime import datetime, timezone

import pytest

from src.research.raw_record import RawRecord


def make_record(
    payload: dict,
) -> RawRecord:
    return RawRecord(
        source_id="test_source",
        record_id="record_001",
        retrieved_at=datetime(
            2026,
            1,
            2,
            tzinfo=timezone.utc,
        ),
        published_at=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        available_at=datetime(
            2026,
            1,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        payload=payload,
    )


def test_checksum_is_deterministic():
    first = make_record(
        {"b": 2, "a": 1}
    )

    second = make_record(
        {"a": 1, "b": 2}
    )

    assert first.checksum == second.checksum


def test_different_payload_has_different_checksum():
    first = make_record(
        {"value": 1}
    )

    second = make_record(
        {"value": 2}
    )

    assert first.checksum != second.checksum


def test_record_is_known_at_timestamp():
    record = make_record(
        {"value": 1}
    )

    assert record.is_known_at(
        datetime(
            2026,
            1,
            1,
            1,
            tzinfo=timezone.utc,
        )
    )

    assert not record.is_known_at(
        datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        )
    )


def test_missing_available_at_is_not_point_in_time_safe():
    record = RawRecord(
        source_id="test",
        record_id="record",
        retrieved_at=datetime(
            2026,
            1,
            2,
            tzinfo=timezone.utc,
        ),
        payload={"value": 1},
    )

    assert not record.is_known_at(
        datetime(
            2026,
            1,
            3,
            tzinfo=timezone.utc,
        )
    )


def test_rejects_naive_retrieval_time():
    with pytest.raises(ValueError):
        RawRecord(
            source_id="test",
            record_id="record",
            retrieved_at=datetime(2026, 1, 1),
            payload={},
        )


def test_rejects_invalid_availability_order():
    with pytest.raises(ValueError):
        RawRecord(
            source_id="test",
            record_id="record",
            retrieved_at=datetime(
                2026,
                1,
                2,
                tzinfo=timezone.utc,
            ),
            published_at=datetime(
                2026,
                1,
                2,
                tzinfo=timezone.utc,
            ),
            available_at=datetime(
                2026,
                1,
                1,
                tzinfo=timezone.utc,
            ),
            payload={},
        )