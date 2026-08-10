from datetime import datetime, timezone

import pytest

from src.research.provenance import (
    DataProvenance,
    is_known_at,
)


def test_valid_provenance_is_created() -> None:
    published = datetime(
        2026,
        1,
        1,
        10,
        0,
        tzinfo=timezone.utc,
    )

    available = datetime(
        2026,
        1,
        1,
        10,
        1,
        tzinfo=timezone.utc,
    )

    retrieved = datetime(
        2026,
        1,
        1,
        10,
        2,
        tzinfo=timezone.utc,
    )

    provenance = DataProvenance(
        source="Reuters",
        source_url="https://example.com/article",
        published_at=published,
        available_at=available,
        retrieved_at=retrieved,
        dataset_id="news",
        dataset_version="1",
        record_id="article-1",
        checksum="abc123",
    )

    assert provenance.source == "Reuters"
    assert provenance.record_id == "article-1"


def test_source_cannot_be_empty() -> None:
    with pytest.raises(
        ValueError,
        match="source cannot be empty",
    ):
        DataProvenance(
            source=" ",
            source_url=None,
            published_at=None,
            available_at=None,
            retrieved_at=datetime.now(timezone.utc),
        )


def test_retrieved_at_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="retrieved_at must be timezone-aware",
    ):
        DataProvenance(
            source="Reuters",
            source_url=None,
            published_at=None,
            available_at=None,
            retrieved_at=datetime(2026, 1, 1),
        )


def test_published_at_must_be_timezone_aware() -> None:
    with pytest.raises(
        ValueError,
        match="published_at must be timezone-aware",
    ):
        DataProvenance(
            source="Reuters",
            source_url=None,
            published_at=datetime(2026, 1, 1),
            available_at=None,
            retrieved_at=datetime.now(timezone.utc),
        )


def test_available_at_cannot_precede_published_at() -> None:
    published = datetime(
        2026,
        1,
        1,
        10,
        0,
        tzinfo=timezone.utc,
    )

    available = datetime(
        2026,
        1,
        1,
        9,
        59,
        tzinfo=timezone.utc,
    )

    with pytest.raises(
        ValueError,
        match="available_at cannot be earlier than published_at",
    ):
        DataProvenance(
            source="Reuters",
            source_url=None,
            published_at=published,
            available_at=available,
            retrieved_at=datetime.now(timezone.utc),
        )


def test_is_known_at_rejects_naive_timestamp() -> None:
    provenance = DataProvenance(
        source="Reuters",
        source_url=None,
        published_at=None,
        available_at=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        retrieved_at=datetime.now(timezone.utc),
    )

    with pytest.raises(
        ValueError,
        match="timestamp must be timezone-aware",
    ):
        is_known_at(
            provenance,
            datetime(2026, 1, 2),
        )


def test_is_known_at_returns_false_without_available_timestamp() -> None:
    provenance = DataProvenance(
        source="Reuters",
        source_url=None,
        published_at=None,
        available_at=None,
        retrieved_at=datetime.now(timezone.utc),
    )

    timestamp = datetime(
        2026,
        1,
        2,
        tzinfo=timezone.utc,
    )

    assert is_known_at(
        provenance,
        timestamp,
    ) is False


def test_is_known_at_respects_boundary() -> None:
    available = datetime(
        2026,
        1,
        1,
        10,
        0,
        tzinfo=timezone.utc,
    )

    provenance = DataProvenance(
        source="Reuters",
        source_url=None,
        published_at=None,
        available_at=available,
        retrieved_at=datetime.now(timezone.utc),
    )

    before = datetime(
        2026,
        1,
        1,
        9,
        59,
        tzinfo=timezone.utc,
    )

    exactly = datetime(
        2026,
        1,
        1,
        10,
        0,
        tzinfo=timezone.utc,
    )

    after = datetime(
        2026,
        1,
        1,
        10,
        1,
        tzinfo=timezone.utc,
    )

    assert is_known_at(provenance, before) is False
    assert is_known_at(provenance, exactly) is True
    assert is_known_at(provenance, after) is True
