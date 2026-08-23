"""
Canonical evidence models and epistemic vocabulary.

EpistemicType classifies how a piece of evidence was produced.
It describes the epistemological status, not the investment meaning.

CanonicalEvidenceItem is the unified view that links an EvidenceItem
or CorporateIntelItem back to its source, provenance, and claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EpistemicType(str, Enum):
    """
    How a piece of evidence was produced.

    - REPORTED:   value explicitly stated in source material.
    - DERIVED:    value computed from reported values via a
                  clear, documented formula.
    - INFERRED:   value inferred from multiple evidence items
                  or contextual reasoning.
    - UNKNOWN:    epistemic type not determined.

    UNKNOWN must never be treated as negative evidence; it
    indicates the system has not classified the epistemic status.
    """

    REPORTED = "REPORTED"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class EvidenceSourceInfo:
    """
    Lightweight source description for the evidence lineage.

    Maps to an existing ResearchSource or SourceProfile. This is
    a read-only projection, not a new source model.
    """

    source_id: str
    name: str
    source_type: str
    tier: str
    domain: str | None = None
    official: bool = False
    requires_confirmation: bool = False
    reliability_tier: str = "UNKNOWN"

    def __post_init__(self) -> None:
        for field_name in ("source_id", "name", "source_type"):
            value = getattr(self, field_name)
            if not value.strip():
                raise ValueError(
                    f"{field_name} cannot be empty"
                )


@dataclass(frozen=True)
class EvidenceSourceRecordInfo:
    """
    Provenance record for one piece of evidence.

    Maps to an existing DataProvenance instance. This is a
    read-only projection, not a new provenance model.
    """

    source: str
    source_url: str | None = None
    retrieved_at: datetime | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None
    dataset_id: str | None = None
    record_id: str | None = None
    checksum: str | None = None

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source cannot be empty")

        for field_name in ("retrieved_at", "published_at", "available_at"):
            value = getattr(self, field_name)
            if value is not None and value.tzinfo is None:
                raise ValueError(
                    f"{field_name} must be timezone-aware"
                )


@dataclass(frozen=True)
class EvidenceClaim:
    """
    A traceable claim linked to one or more evidence items.

    Claims represent the textual assertions that evidence supports
    or contradicts. They are descriptive, not evaluative.
    """

    claim_id: str
    symbol: str
    text: str
    category: str
    epistemic_type: EpistemicType = EpistemicType.UNKNOWN
    confidence: str = "0"
    verification_status: str = "UNVERIFIED"
    evidence_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    observation_at: datetime | None = None

    def __post_init__(self) -> None:
        for field_name in ("claim_id", "symbol", "text", "category"):
            value = getattr(self, field_name)
            if not value.strip():
                raise ValueError(
                    f"{field_name} cannot be empty"
                )

        if self.observation_at is not None:
            if self.observation_at.tzinfo is None:
                raise ValueError(
                    "observation_at must be timezone-aware"
                )


@dataclass(frozen=True)
class CanonicalEvidenceItem:
    """
    Unified evidence item with full lineage.

    This is the canonical representation that both the Evidence
    Explorer frontend and the Professional Reports module consume.
    It links an evidence item back to its source, provenance, and
    epistemic classification.
    """

    evidence_id: str
    symbol: str
    title: str
    explanation: str

    evidence_type: str
    direction: str
    confidence: str
    reliability: str

    epistemic_type: EpistemicType = EpistemicType.UNKNOWN
    verification_status: str = "UNVERIFIED"

    observation_at: datetime | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None

    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()

    source_info: EvidenceSourceInfo | None = None
    source_records: tuple[EvidenceSourceRecordInfo, ...] = ()

    category: str = ""
    topic: str | None = None
    derivation: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("evidence_id", "symbol", "title", "explanation"):
            value = getattr(self, field_name)
            if not value.strip():
                raise ValueError(
                    f"{field_name} cannot be empty"
                )

        for field_name in ("observation_at", "published_at", "available_at"):
            value = getattr(self, field_name)
            if value is not None and value.tzinfo is None:
                raise ValueError(
                    f"{field_name} must be timezone-aware"
                )


@dataclass(frozen=True)
class EvidenceLineage:
    """
    Complete lineage for one company's evidence at a point in time.

    Contains canonical evidence items, claims, source information,
    and provenance records. This is the top-level object the
    Evidence Explorer and Professional Reports consume.
    """

    symbol: str
    as_of: datetime

    evidence: tuple[CanonicalEvidenceItem, ...] = ()
    claims: tuple[EvidenceClaim, ...] = ()

    source_profiles: tuple[EvidenceSourceInfo, ...] = ()
    source_records: tuple[EvidenceSourceRecordInfo, ...] = ()

    epistemic_type_counts: dict[str, int] = None  # type: ignore[assignment]
    verification_status_counts: dict[str, int] = None  # type: ignore[assignment]
    evidence_type_counts: dict[str, int] = None  # type: ignore[assignment]
    direction_counts: dict[str, int] = None  # type: ignore[assignment]

    total_evidence: int = 0
    total_claims: int = 0
    total_sources: int = 0
    total_provenance: int = 0

    pit_filtered_count: int = 0
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.symbol.strip():
            raise ValueError("symbol cannot be empty")

        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        if self.epistemic_type_counts is None:
            object.__setattr__(
                self, "epistemic_type_counts", {}
            )
        if self.verification_status_counts is None:
            object.__setattr__(
                self, "verification_status_counts", {}
            )
        if self.evidence_type_counts is None:
            object.__setattr__(
                self, "evidence_type_counts", {}
            )
        if self.direction_counts is None:
            object.__setattr__(
                self, "direction_counts", {}
            )


__all__ = [
    "CanonicalEvidenceItem",
    "EpistemicType",
    "EvidenceClaim",
    "EvidenceLineage",
    "EvidenceSourceInfo",
    "EvidenceSourceRecordInfo",
]
