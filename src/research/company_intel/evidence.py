"""
Evidence conflict and link detection.

Conflicts are surfaced with both sides and their provenance. The
system never decides which side is correct; that is a research
judgement the user makes from the evidence.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Sequence

from src.research.company_intel.models import (
    ConflictSide,
    CorporateIntelItem,
    EvidenceConflict,
    EvidenceLink,
)
from src.research.company_intel.semantics import (
    ConclusionGateResult,
    EvidenceRelationship,
    EvidenceStance,
    IntelKind,
    VerificationStatus,
)


def _excerpt(item: CorporateIntelItem) -> str:
    return item.description or item.title


def _conflict_side(
    item: CorporateIntelItem,
) -> ConflictSide:
    return ConflictSide(
        item_id=item.item_id,
        title=item.title,
        semantic_category=item.semantic_category,
        verification_status=item.verification_status,
        stance=item.stance,
        direction=item.direction,
        source_name=item.source.source_name,
        excerpt=_excerpt(item),
    )


def _build_conflict(
    first: CorporateIntelItem,
    second: CorporateIntelItem,
    as_of: datetime,
) -> EvidenceConflict:
    topic = first.topic or second.topic or "evidence"

    ordered = sorted(
        [first, second],
        key=lambda i: i.item_id,
    )

    conflict_id = (
        f"conflict:{first.symbol}:"
        f"{ordered[0].item_id}:{ordered[1].item_id}"
    )

    description = (
        f"Evidence conflict on topic '{topic}' between "
        f"'{first.title}' and '{second.title}'. "
        "Both sides are surfaced; no side is auto-concluded."
    )

    management_involved = (
        first.kind == IntelKind.MANAGEMENT_COMMENTARY
        or second.kind == IntelKind.MANAGEMENT_COMMENTARY
    )

    return EvidenceConflict(
        conflict_id=conflict_id,
        symbol=first.symbol,
        topic=topic,
        description=description,
        management_involved=management_involved,
        first=_conflict_side(first),
        second=_conflict_side(second),
        as_of=as_of,
    )


def detect_evidence_conflicts(
    items: Sequence[CorporateIntelItem],
    *,
    as_of: datetime,
) -> tuple[EvidenceConflict, ...]:
    """
    Detect evidence conflicts deterministically.

    Two sources of conflicts are considered:

    1. explicit `conflicts_with` declarations; and
    2. opposite stances on the same topic.

    Each unordered pair yields exactly one conflict.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    known = [
        item
        for item in items
        if item.is_known_at(as_of)
    ]

    by_id = {item.item_id: item for item in known}

    conflicts: list[EvidenceConflict] = []
    seen_pairs: set[frozenset[str]] = set()

    def _pair_add(
        first: CorporateIntelItem,
        second: CorporateIntelItem,
    ) -> None:
        pair = frozenset((first.item_id, second.item_id))

        if pair in seen_pairs:
            return

        seen_pairs.add(pair)
        conflicts.append(
            _build_conflict(first, second, as_of)
        )

    # Explicit declarations.
    for item in sorted(
        known,
        key=lambda i: i.item_id,
    ):
        for target_id in item.conflicts_with:
            target = by_id.get(target_id)

            if target is None:
                continue

            if target.stance == item.stance:
                continue

            _pair_add(item, target)

    # Stance-based conflicts within a topic.
    by_topic: dict[str, list[CorporateIntelItem]] = defaultdict(list)

    for item in known:
        if item.topic:
            by_topic[item.topic].append(item)

    for topic in sorted(by_topic):
        group = sorted(
            by_topic[topic],
            key=lambda i: i.item_id,
        )

        supportive = [
            item
            for item in group
            if item.stance == EvidenceStance.SUPPORTIVE
        ]
        contrary = [
            item
            for item in group
            if item.stance == EvidenceStance.CONTRARY
        ]

        for support_item in supportive:
            for contrary_item in contrary:
                if support_item.source.source_name == contrary_item.source.source_name:
                    continue

                _pair_add(support_item, contrary_item)

    return tuple(conflicts)


def build_evidence_links(
    items: Sequence[CorporateIntelItem],
    *,
    as_of: datetime,
) -> tuple[EvidenceLink, ...]:
    """
    Build explicit support / contradiction links.

    Only links whose targets exist in the same point-in-time set are
    emitted.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    known = [
        item
        for item in items
        if item.is_known_at(as_of)
    ]

    by_id = {item.item_id: item for item in known}

    links: list[EvidenceLink] = []

    for item in sorted(
        known,
        key=lambda i: i.item_id,
    ):
        for target_id in item.supports:
            if target_id not in by_id:
                continue

            links.append(
                EvidenceLink(
                    link_id=(
                        f"link:{item.item_id}:"
                        f"supports:{target_id}"
                    ),
                    symbol=item.symbol,
                    subject_id=item.item_id,
                    object_id=target_id,
                    relationship=EvidenceRelationship.SUPPORTS,
                )
            )

        for target_id in item.conflicts_with:
            if target_id not in by_id:
                continue

            links.append(
                EvidenceLink(
                    link_id=(
                        f"link:{item.item_id}:"
                        f"contradicts:{target_id}"
                    ),
                    symbol=item.symbol,
                    subject_id=item.item_id,
                    object_id=target_id,
                    relationship=EvidenceRelationship.CONTRADICTS,
                )
            )

    return tuple(links)


def conclusion_gate(
    items: Sequence[CorporateIntelItem],
    *,
    require_distinct_sources: bool = True,
) -> ConclusionGateResult:
    """
    Decide whether a conclusion is supported.

    A conclusion requires at least two pieces of confirmed evidence
    from sufficiently reliable sources. When unsupported, the result
    carries the canonical insufficient-evidence message.
    """

    confirmed = [
        item
        for item in items
        if item.verification_status == VerificationStatus.CONFIRMED
        and item.source.reliability_tier <= 2
    ]

    distinct_sources = {
        item.source.source_name
        for item in confirmed
    }

    if len(confirmed) >= 2 and (
        not require_distinct_sources
        or len(distinct_sources) >= 2
    ):
        return ConclusionGateResult.supported_result()

    return ConclusionGateResult.insufficient_result()


__all__ = [
    "build_evidence_links",
    "conclusion_gate",
    "detect_evidence_conflicts",
]
