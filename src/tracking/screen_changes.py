"""
Screen-membership transition tracking.

When a deterministic screen is re-run over time, companies enter or
leave its result set. These transitions are recorded research facts
("this company now satisfies / no longer satisfies these explicit
filters"). They carry no investment advice, no score, and no
prediction.
"""

from __future__ import annotations

from datetime import datetime

from src.tracking.models import (
    ChangeDomain,
    TrackedChangeType,
    TrackingChange,
    TrackingSeverity,
)


def _require_aware(as_of: datetime) -> None:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")


def build_screen_transition_changes(
    *,
    screen_hash: str,
    screen_name: str,
    previous_symbols,
    current_symbols,
    as_of: datetime,
) -> tuple[TrackingChange, ...]:
    """
    Diff two executions of one screen definition.

    previous_symbols / current_symbols: iterables of matched symbols.
    Returns deterministically ordered SCREEN_ENTRY / SCREEN_EXIT
    changes. Identical inputs always yield identical changes.
    """

    _require_aware(as_of)

    if not screen_hash.strip():
        raise ValueError("screen_hash cannot be empty")
    if not screen_name.strip():
        raise ValueError("screen_name cannot be empty")

    previous = {s.strip().upper() for s in previous_symbols}
    current = {s.strip().upper() for s in current_symbols}

    entered = sorted(current - previous)
    exited = sorted(previous - current)

    changes: list[TrackingChange] = []

    for symbol in entered:
        changes.append(
            TrackingChange(
                change_id=(
                    f"screen-{screen_hash[:8]}-{symbol}-ENTRY"
                ),
                symbol=symbol,
                domain=ChangeDomain.SCREEN,
                severity=TrackingSeverity.INFO,
                change_type=TrackedChangeType.SCREEN_ENTRY,
                title=f"Now satisfies screen '{screen_name}'",
                description=(
                    f"The company's recorded data satisfies every "
                    f"filter of screen '{screen_name}' "
                    f"(definition {screen_hash[:8]}) as of the "
                    f"detection time."
                ),
                current_value=screen_hash,
                detected_at=as_of,
                pit_eligible=True,
                as_of=as_of,
            )
        )

    for symbol in exited:
        changes.append(
            TrackingChange(
                change_id=(
                    f"screen-{screen_hash[:8]}-{symbol}-EXIT"
                ),
                symbol=symbol,
                domain=ChangeDomain.SCREEN,
                severity=TrackingSeverity.INFO,
                change_type=TrackedChangeType.SCREEN_EXIT,
                title=f"No longer satisfies screen '{screen_name}'",
                description=(
                    f"The company's recorded data no longer "
                    f"satisfies every filter of screen "
                    f"'{screen_name}' (definition "
                    f"{screen_hash[:8]}) as of the detection time."
                ),
                previous_value=screen_hash,
                detected_at=as_of,
                pit_eligible=True,
                as_of=as_of,
            )
        )

    changes.sort(key=lambda c: (c.change_type.value, c.symbol))

    return tuple(changes)


__all__ = [
    "build_screen_transition_changes",
]
