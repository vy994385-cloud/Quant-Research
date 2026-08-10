from datetime import datetime, timezone

import pytest

from src.research.raw_archive import RawArchive
from src.research.raw_record import RawRecord


def make_record(
    record_id: str = "record_001",
    payload: dict | None = None,
) -> RawRecord:
    return RawRecord(
        source_id="test_source",
        record_id=record_id,
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
        payload=(
            payload
            if payload is not None
            else {"value": 100}
        ),
    )


def test_save_and_load_round_trip(tmp_path):
    archive = RawArchive(tmp_path)

    original = make_record()

    path = archive.save(original)

    assert path.exists()

    loaded = archive.load(
        "test_source",
        "record_001",
    )

    assert loaded == original
    assert loaded.checksum == original.checksum


def test_exists(tmp_path):
    archive = RawArchive(tmp_path)

    record = make_record()

    assert not archive.exists(record)

    archive.save(record)

    assert archive.exists(record)


def test_same_record_can_be_saved_again(tmp_path):
    archive = RawArchive(tmp_path)

    record = make_record()

    first_path = archive.save(record)
    second_path = archive.save(record)

    assert first_path == second_path


def test_different_payload_cannot_overwrite_record(
    tmp_path,
):
    archive = RawArchive(tmp_path)

    archive.save(
        make_record(
            payload={"value": 100}
        )
    )

    with pytest.raises(ValueError):
        archive.save(
            make_record(
                payload={"value": 200}
            )
        )


def test_missing_record_raises(tmp_path):
    archive = RawArchive(tmp_path)

    with pytest.raises(FileNotFoundError):
        archive.load(
            "test_source",
            "missing",
        )


def test_checksum_tampering_is_detected(tmp_path):
    archive = RawArchive(tmp_path)

    record = make_record()

    path = archive.save(record)

    content = path.read_text(
        encoding="utf-8"
    )

    content = content.replace(
        '"value": 100',
        '"value": 999',
    )

    path.write_text(
        content,
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        archive.load(
            "test_source",
            "record_001",
        )