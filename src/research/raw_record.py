from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class RawRecord:
    """
    Immutable raw observation captured from an external source.

    The raw payload is preserved exactly as received so that
    research can later be reproduced and audited.
    """

    source_id: str
    record_id: str
    retrieved_at: datetime

    payload: Any

    published_at: datetime | None = None
    available_at: datetime | None = None

    dataset_id: str | None = None
    dataset_version: str | None = None

    request_metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "source_id",
            "record_id",
        ):
            value = getattr(self, field_name)

            if not value.strip():
                raise ValueError(
                    f"{field_name} cannot be empty"
                )

        if self.retrieved_at.tzinfo is None:
            raise ValueError(
                "retrieved_at must be timezone-aware"
            )

        if self.published_at is not None:
            if self.published_at.tzinfo is None:
                raise ValueError(
                    "published_at must be timezone-aware"
                )

        if self.available_at is not None:
            if self.available_at.tzinfo is None:
                raise ValueError(
                    "available_at must be timezone-aware"
                )

        if (
            self.published_at is not None
            and self.available_at is not None
            and self.available_at < self.published_at
        ):
            raise ValueError(
                "available_at cannot be earlier than published_at"
            )

        for field_name in (
            "dataset_id",
            "dataset_version",
        ):
            value = getattr(self, field_name)

            if value is not None and not value.strip():
                raise ValueError(
                    f"{field_name} cannot be blank"
                )

    def canonical_payload(self) -> str:
        """
        Return deterministic JSON representation of the payload.
        """

        return json.dumps(
            self.payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        )

    @property
    def checksum(self) -> str:
        """
        SHA-256 checksum of the canonical raw payload.
        """

        return hashlib.sha256(
            self.canonical_payload().encode("utf-8")
        ).hexdigest()

    def is_known_at(
        self,
        timestamp: datetime,
    ) -> bool:
        """
        Return whether this record was safely available
        at the supplied historical timestamp.

        Records without available_at are not considered
        point-in-time safe.
        """

        if timestamp.tzinfo is None:
            raise ValueError(
                "timestamp must be timezone-aware"
            )

        if self.available_at is None:
            return False

        return self.available_at <= timestamp