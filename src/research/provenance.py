from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class DataProvenance:
    """
    Immutable provenance record for a research data object.

    Historical research must be able to answer:

    - Where did this data come from?
    - When was it published?
    - When was our system allowed to know it?
    - Which dataset/version produced it?
    """

    source: str
    source_url: str | None
    retrieved_at: datetime
    published_at: datetime | None
    available_at: datetime | None

    dataset_id: str | None = None
    dataset_version: str | None = None
    record_id: str | None = None
    checksum: str | None = None
    raw_payload: Any = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source cannot be empty")

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
            "source_url",
            "dataset_id",
            "dataset_version",
            "record_id",
            "checksum",
        ):
            value = getattr(self, field_name)

            if value is not None and not value.strip():
                raise ValueError(
                    f"{field_name} cannot be blank"
                )


def is_known_at(
    provenance: DataProvenance,
    timestamp: datetime,
) -> bool:
    """
    Return whether the data was available to the research
    system at the supplied historical timestamp.

    Missing available_at means the data cannot safely be
    treated as point-in-time known.
    """

    if timestamp.tzinfo is None:
        raise ValueError(
            "timestamp must be timezone-aware"
        )

    if provenance.available_at is None:
        return False

    return provenance.available_at <= timestamp
