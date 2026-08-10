from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.research.raw_record import RawRecord


class RawArchive:
    """
    Simple immutable filesystem archive for raw research records.

    Records are stored as JSON files:

        archive/
            source_id/
                record_id.json

    Existing records cannot be silently overwritten.
    """

    def __init__(
        self,
        root: str | Path,
    ) -> None:
        self.root = Path(root)

    def _record_path(
        self,
        record: RawRecord,
    ) -> Path:
        return (
            self.root
            / record.source_id
            / f"{record.record_id}.json"
        )

    def exists(
        self,
        record: RawRecord,
    ) -> bool:
        return self._record_path(record).exists()

    def save(
        self,
        record: RawRecord,
    ) -> Path:
        """
        Persist a raw record.

        If the record already exists, its checksum must match.
        """

        path = self._record_path(record)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if path.exists():
            existing = self.load(
                record.source_id,
                record.record_id,
            )

            if existing.checksum != record.checksum:
                raise ValueError(
                    "cannot overwrite raw record with "
                    "different checksum: "
                    f"{record.source_id}/{record.record_id}"
                )

            return path

        data = {
            "source_id": record.source_id,
            "record_id": record.record_id,
            "retrieved_at": record.retrieved_at.isoformat(),
            "published_at": (
                record.published_at.isoformat()
                if record.published_at is not None
                else None
            ),
            "available_at": (
                record.available_at.isoformat()
                if record.available_at is not None
                else None
            ),
            "dataset_id": record.dataset_id,
            "dataset_version": record.dataset_version,
            "request_metadata": record.request_metadata,
            "payload": record.payload,
            "checksum": record.checksum,
        }

        path.write_text(
            json.dumps(
                data,
                sort_keys=True,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        return path

    def load(
        self,
        source_id: str,
        record_id: str,
    ) -> RawRecord:
        """
        Load one archived raw record.
        """

        path = (
            self.root
            / source_id.strip()
            / f"{record_id.strip()}.json"
        )

        if not path.exists():
            raise FileNotFoundError(
                f"raw record not found: "
                f"{source_id}/{record_id}"
            )

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

        record = RawRecord(
    source_id=data["source_id"],
    record_id=data["record_id"],
    retrieved_at=datetime.fromisoformat(
        data["retrieved_at"]
    ),
    published_at=(
        datetime.fromisoformat(
            data["published_at"]
        )
        if data["published_at"] is not None
        else None
    ),
    available_at=(
        datetime.fromisoformat(
            data["available_at"]
        )
        if data["available_at"] is not None
        else None
    ),
    dataset_id=data["dataset_id"],
    dataset_version=data["dataset_version"],
    request_metadata=data["request_metadata"],
    payload=data["payload"],
)

        if record.checksum != data["checksum"]:
            raise ValueError(
                "raw record checksum mismatch: "
                f"{source_id}/{record_id}"
            )

        return record