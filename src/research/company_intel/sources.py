"""
Provider interface and extraction for periodic intelligence feeds.

Providers return `IntelCandidate` objects. The engine validates,
deduplicates, archives, and extracts them into point-in-time
`CorporateIntelItem` objects. No provider ever touches the network
inside this package; network-backed providers belong in deployment.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Sequence

from src.research.company_intel.models import (
    CorporateIntelItem,
    IntelCandidate,
    SourceRef,
)
from src.research.company_intel.semantics import (
    SemanticCategory,
)
from src.research.raw_record import RawRecord


class IntelSourceProvider(ABC):
    """
    Contract for a source of company intelligence candidates.

    A provider returns candidates that were knowable at `as_of`.
    Providers are expected to be deterministic for a given input.
    """

    source_name: str = "unknown"

    @abstractmethod
    def fetch(
        self,
        company: str,
        *,
        since: datetime | None,
        as_of: datetime,
    ) -> list[IntelCandidate]:
        """Return candidates for the company knowable at `as_of`."""
        raise NotImplementedError


class RecordedIntelSourceProvider(IntelSourceProvider):
    """
    Recorded provider backed by a committed JSON fixture.

    Used for reproducible, network-free verification and tests.
    """

    source_name = "recorded_intel_sources"

    def __init__(
        self,
        candidates: Sequence[IntelCandidate],
        *,
        include_future: bool = False,
    ) -> None:
        self._candidates = list(candidates)
        self._include_future = include_future

    def fetch(
        self,
        company: str,
        *,
        since: datetime | None,
        as_of: datetime | None,
    ) -> list[IntelCandidate]:
        if as_of is not None and as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        results: list[IntelCandidate] = []

        for candidate in self._candidates:
            if candidate.company != company:
                continue

            if (
                not self._include_future
                and candidate.available_at is not None
                and as_of is not None
                and candidate.available_at > as_of
            ):
                continue

            if (
                since is not None
                and candidate.available_at is not None
                and candidate.available_at <= since
            ):
                continue

            results.append(candidate)

        return sorted(
            results,
            key=lambda c: (
                c.available_at.isoformat()
                if c.available_at
                else "",
                c.candidate_id,
            ),
        )

    @classmethod
    def from_json(
        cls,
        path: str | Path,
        *,
        include_future: bool = False,
    ) -> "RecordedIntelSourceProvider":
        data = json.loads(
            Path(path).read_text(encoding="utf-8")
        )

        if isinstance(data, dict):
            try:
                entries = data["candidates"]
            except KeyError:
                raise ValueError(
                    'intel fixture object must contain a "candidates" list'
                ) from None
        elif isinstance(data, list):
            entries = data
        else:
            raise ValueError(
                "intel fixture must be a candidate list or a "
                '{"candidates": [...]} object'
            )

        candidates = [
            IntelCandidate.model_validate(entry)
            for entry in entries
        ]
        return cls(
            candidates,
            include_future=include_future,
        )


class IntelSourceValidator:
    """
    Validate that a candidate is usable for a company at `as_of`.

    Returns (valid, reason). Validation covers entity matching and
    point-in-time timestamp integrity.
    """

    def validate(
        self,
        candidate: IntelCandidate,
        *,
        company: str,
        as_of: datetime,
    ) -> tuple[bool, str]:
        if candidate.company != company:
            return (
                False,
                f"candidate company '{candidate.company}' "
                f"does not match '{company}'",
            )

        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        if candidate.available_at is not None:
            if candidate.available_at.tzinfo is None:
                return (
                    False,
                    "candidate available_at must be timezone-aware",
                )

            if candidate.available_at > as_of:
                return (
                    False,
                    "candidate is not knowable at as_of "
                    "(available_at is in the future)",
                )

        for field_name in ("published_at", "effective_at"):
            value = getattr(candidate, field_name)

            if value is not None and value.tzinfo is None:
                return (
                    False,
                    f"candidate {field_name} must be timezone-aware",
                )

        if (
            candidate.published_at is not None
            and candidate.available_at is not None
            and candidate.published_at > candidate.available_at
        ):
            return (
                False,
                "candidate published_at is after available_at; "
                "publication order is broken",
            )

        return True, ""


def deduplicate_candidates(
    candidates: Sequence[IntelCandidate],
) -> tuple[list[IntelCandidate], int]:
    """
    Deduplicate candidates by content identity.

    Two candidates are duplicates when they share company, source,
    URL, normalized title, and published timestamp. Deterministic:
    the lowest candidate_id wins.
    """

    seen: set[tuple] = set()
    result: list[IntelCandidate] = []

    for candidate in sorted(
        candidates,
        key=lambda c: c.candidate_id,
    ):
        key = (
            candidate.company,
            candidate.source_name,
            candidate.source_url or "",
            candidate.title.strip().lower(),
            (
                candidate.published_at.isoformat()
                if candidate.published_at
                else ""
            ),
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(candidate)

    return result, len(candidates) - len(result)


def candidate_to_raw_record(
    candidate: IntelCandidate,
    *,
    retrieved_at: datetime,
) -> RawRecord:
    """Archive a candidate as a raw record."""
    return RawRecord(
        source_id=candidate.source_name,
        record_id=candidate.candidate_id,
        retrieved_at=retrieved_at,
        payload=candidate.model_dump(
            mode="json",
        ),
        published_at=candidate.published_at,
        available_at=candidate.available_at,
    )


class IntelExtractor:
    """
    Convert a validated candidate into a point-in-time item.
    """

    def extract(
        self,
        candidate: IntelCandidate,
        *,
        company: str,
        as_of: datetime,
    ) -> CorporateIntelItem | None:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        if candidate.company != company:
            return None

        if (
            candidate.available_at is not None
            and candidate.available_at > as_of
        ):
            return None

        source = SourceRef(
            source_name=candidate.source_name,
            source_type=candidate.source_type,
            source_url=candidate.source_url,
            reliability_tier=candidate.reliability_tier,
        )

        return CorporateIntelItem(
            item_id=f"{candidate.company}:{candidate.candidate_id}",
            symbol=candidate.company,
            kind=candidate.kind,
            semantic_category=(
                candidate.semantic_category
                or SemanticCategory.OBSERVATION
            ),
            verification_status=candidate.verification_status,
            event_type=candidate.event_type,
            topic=candidate.topic,
            title=candidate.title,
            description=candidate.body or candidate.title,
            stance=candidate.stance,
            direction=candidate.direction,
            intel_category=candidate.intel_category,
            published_at=candidate.published_at,
            available_at=candidate.available_at,
            effective_at=candidate.effective_at,
            source=source,
            related_entities=candidate.related_entities,
            relevance=candidate.relevance,
            confidence=candidate.confidence,
        )


__all__ = [
    "IntelExtractor",
    "IntelSourceProvider",
    "IntelSourceValidator",
    "RecordedIntelSourceProvider",
    "candidate_to_raw_record",
    "deduplicate_candidates",
]
