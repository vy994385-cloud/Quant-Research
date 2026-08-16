"""
Deterministic change detection between intelligence snapshots.

Change classification:

- NEW:         item only exists in the new snapshot.
- UPDATED:     item exists in both, content checksum differs.
- UNCHANGED:   item exists in both, content identical.
- RESOLVED:    item moved to RESOLVED status.
- CONFLICTING: item moved to CONTRADICTED status.
"""

from __future__ import annotations

from datetime import datetime
from typing import Mapping, Sequence

from src.research.company_intel.models import (
    CorporateIntelItem,
    IntelChange,
    SnapshotDiff,
)
from src.research.company_intel.semantics import (
    ChangeType,
    VerificationStatus,
)


def _as_map(
    items: Sequence[CorporateIntelItem],
) -> dict[str, CorporateIntelItem]:
    return {item.item_id: item for item in items}


def _item_order(
    items: Sequence[CorporateIntelItem],
) -> list[str]:
    return sorted(
        {item.item_id for item in items}
    )


def _change(
    change_type: ChangeType,
    item: CorporateIntelItem,
    *,
    as_of: datetime,
    description: str,
    previous_checksum: str | None,
) -> IntelChange:
    return IntelChange(
        change_type=change_type,
        item_id=item.item_id,
        kind=item.kind,
        title=item.title,
        description=description,
        previous_checksum=previous_checksum,
        current_checksum=item.checksum,
        as_of=as_of,
    )


def detect_changes(
    *,
    company: str,
    as_of: datetime,
    before: Sequence[CorporateIntelItem],
    after: Sequence[CorporateIntelItem],
) -> SnapshotDiff:
    """
    Detect changes between two point-in-time item sets.

    Items that exist only in `before` are ignored: snapshots are
    cumulative point-in-time views, so items should never disappear.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    before_map = _as_map(before)
    after_map = _as_map(after)

    changes: list[IntelChange] = []

    for item_id in _item_order(after):
        previous = before_map.get(item_id)
        current = after_map.get(item_id)

        if current is None:
            continue

        if previous is None:
            changes.append(
                _change(
                    ChangeType.NEW,
                    current,
                    as_of=as_of,
                    description=(
                        f"New {current.kind.value} item '{current.title}' "
                        "appears in this snapshot."
                    ),
                    previous_checksum=None,
                )
            )
            continue

        if (
            previous.verification_status
            != VerificationStatus.RESOLVED
            and current.verification_status
            == VerificationStatus.RESOLVED
        ):
            changes.append(
                _change(
                    ChangeType.RESOLVED,
                    current,
                    as_of=as_of,
                    description=(
                        f"Item '{current.title}' is now resolved "
                        f"(was {previous.verification_status.value})."
                    ),
                    previous_checksum=previous.checksum,
                )
            )
            continue

        if (
            previous.verification_status
            != VerificationStatus.CONTRADICTED
            and current.verification_status
            == VerificationStatus.CONTRADICTED
        ):
            changes.append(
                _change(
                    ChangeType.CONFLICTING,
                    current,
                    as_of=as_of,
                    description=(
                        f"Item '{current.title}' is now contradicted "
                        f"(was {previous.verification_status.value})."
                    ),
                    previous_checksum=previous.checksum,
                )
            )
            continue

        if current.checksum != previous.checksum:
            changes.append(
                _change(
                    ChangeType.UPDATED,
                    current,
                    as_of=as_of,
                    description=(
                        f"Item '{current.title}' changed since the "
                        "previous snapshot."
                    ),
                    previous_checksum=previous.checksum,
                )
            )
            continue

        changes.append(
            _change(
                ChangeType.UNCHANGED,
                current,
                as_of=as_of,
                description=(
                    f"Item '{current.title}' is unchanged since the "
                    "previous snapshot."
                ),
                previous_checksum=previous.checksum,
            )
        )

    return SnapshotDiff(
        company=company,
        as_of=as_of,
        changes=tuple(changes),
    )


def change_counts(
    changes: Sequence[IntelChange],
) -> dict[str, int]:
    """Count changes by change type."""
    counts: dict[str, int] = {}

    for change in changes:
        key = change.change_type.value
        counts[key] = counts.get(key, 0) + 1

    return counts


__all__ = [
    "change_counts",
    "detect_changes",
]
