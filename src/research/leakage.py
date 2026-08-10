from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from src.research.provenance import DataProvenance


@dataclass(frozen=True)
class LeakageViolation:
    """
    Describes one point-in-time data leakage violation.
    """

    record_id: str | None
    message: str
    timestamp: datetime


def find_future_data(
    provenance_records: Iterable[DataProvenance],
    *,
    timestamp: datetime,
) -> tuple[LeakageViolation, ...]:
    """
    Find records that were not yet available at timestamp.

    A record is considered leaked when:

        available_at > timestamp

    Records without available_at are also rejected because
    their point-in-time availability cannot be established.
    """

    if timestamp.tzinfo is None:
        raise ValueError(
            "timestamp must be timezone-aware"
        )

    violations: list[LeakageViolation] = []

    for provenance in provenance_records:
        if provenance.available_at is None:
            violations.append(
                LeakageViolation(
                    record_id=provenance.record_id,
                    message=(
                        "point-in-time availability is unknown"
                    ),
                    timestamp=timestamp,
                )
            )
            continue

        if provenance.available_at > timestamp:
            violations.append(
                LeakageViolation(
                    record_id=provenance.record_id,
                    message=(
                        "data was not available at research timestamp"
                    ),
                    timestamp=timestamp,
                )
            )

    return tuple(violations)


def assert_no_future_data(
    provenance_records: Iterable[DataProvenance],
    *,
    timestamp: datetime,
) -> None:
    """
    Raise ValueError if any future or unknown-availability data
    would enter the historical research calculation.
    """

    violations = find_future_data(
        provenance_records,
        timestamp=timestamp,
    )

    if violations:
        details = "; ".join(
            (
                f"{violation.record_id or '<unknown>'}: "
                f"{violation.message}"
            )
            for violation in violations
        )

        raise ValueError(
            f"research data leakage detected: {details}"
        )
