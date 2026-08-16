"""
Data models for the deep company intelligence layer.

All models are descriptive. They store evidence, provenance, and
deterministic analytical results. They do not store scores,
recommendations, or return forecasts.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from src.data.company.financials import SegmentResult

from src.research.company_intel.semantics import (
    BusinessEventType,
    ChangeType,
    ConsolidationScope,
    EvidenceRelationship,
    EvidenceStance,
    FinancialStatementType,
    IntelCategory,
    IntelDirection,
    IntelKind,
    ReportingPeriodType,
    SemanticCategory,
    VerificationStatus,
)


class SourceRef(BaseModel):
    """Reference to the source of a piece of intelligence."""

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_url: str | None = None
    reliability_tier: int = Field(ge=1, le=6)
    provenance_id: str | None = None


class CorporateIntelItem(BaseModel):
    """
    One normalized piece of company intelligence.

    The checksum makes change detection deterministic: two snapshots
    that differ only in item content produce a different checksum.
    """

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    kind: IntelKind
    semantic_category: SemanticCategory = SemanticCategory.OBSERVATION
    verification_status: VerificationStatus = VerificationStatus.REPORTED
    event_type: BusinessEventType | None = None
    topic: str | None = None
    title: str = Field(min_length=1)
    description: str = ""
    stance: EvidenceStance = EvidenceStance.NEUTRAL
    direction: IntelDirection = IntelDirection.UNKNOWN

    intel_category: IntelCategory | None = None

    # Present only for deterministic derived observations. The
    # derivation text records the exact formula / basis so the
    # observation can be reproduced and audited.
    derivation: str | None = None

    published_at: datetime | None = None
    available_at: datetime | None = None
    effective_at: datetime | None = None

    source: SourceRef
    related_entities: tuple[str, ...] = ()
    relevance: str | None = None
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    provenance_id: str | None = None

    conflicts_with: tuple[str, ...] = ()
    supports: tuple[str, ...] = ()

    checksum: str = ""

    @field_validator("published_at", "available_at", "effective_at")
    @classmethod
    def _require_aware_timestamp(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value

    @field_validator("related_entities", "conflicts_with", "supports")
    @classmethod
    def _normalize_references(
        cls,
        values: tuple[str, ...],
    ) -> tuple[str, ...]:
        normalized: list[str] = []

        for entry in values:
            value = entry.strip()

            if not value:
                raise ValueError("references cannot be empty")

            normalized.append(value)

        return tuple(normalized)

    def is_known_at(self, as_of: datetime) -> bool:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        if self.available_at is None:
            return False

        if self.available_at.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")

        return self.available_at <= as_of


class FinancialStatement(BaseModel):
    """
    A normalized financial statement for one reporting period.

    PIT integrity requires `published_at` / `available_at` to be
    present when the statement came from a dated filing.
    """

    model_config = ConfigDict(extra="forbid")

    statement_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    statement_type: FinancialStatementType
    period_type: ReportingPeriodType = ReportingPeriodType.UNKNOWN
    consolidation: ConsolidationScope = ConsolidationScope.UNKNOWN
    period_start: date | None = None
    period_end: date
    published_at: datetime | None = None
    available_at: datetime | None = None
    effective_at: datetime | None = None
    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    provenance_id: str | None = None
    currency: str | None = None
    items: dict[str, Decimal] = Field(default_factory=dict)
    segments: tuple[SegmentResult, ...] = ()
    subsidiaries: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @field_validator("published_at", "available_at", "effective_at")
    @classmethod
    def _require_aware_timestamp(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value

    def is_known_at(self, as_of: datetime) -> bool:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        if self.available_at is None:
            return False

        if self.available_at.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")

        return self.available_at <= as_of


class FinancialPeriod(BaseModel):
    """
    One reporting period with normalized metrics.

    `metrics` holds the key normalized figures; `statements` holds
    the underlying statement-level detail when available.
    """

    model_config = ConfigDict(extra="forbid")

    period_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    period_start: date | None = None
    period_end: date
    period_type: ReportingPeriodType = ReportingPeriodType.UNKNOWN
    consolidation: ConsolidationScope = ConsolidationScope.UNKNOWN
    published_at: datetime | None = None
    available_at: datetime | None = None
    effective_at: datetime | None = None
    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    provenance_id: str | None = None
    currency: str | None = None
    metrics: dict[str, Decimal] = Field(default_factory=dict)
    segments: tuple[SegmentResult, ...] = ()
    subsidiaries: tuple[str, ...] = ()
    statements: tuple[FinancialStatement, ...] = ()

    @field_validator("published_at", "available_at", "effective_at")
    @classmethod
    def _require_aware_timestamp(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value

    def is_known_at(self, as_of: datetime) -> bool:
        if as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")

        if self.available_at is None:
            return False

        if self.available_at.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")

        return self.available_at <= as_of


class FinancialIntelligence(BaseModel):
    """
    Deterministic summary of a company's reporting history.

    This is descriptive research output, not an opinion.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime

    period_count: int = Field(ge=0)
    quarterly_count: int = Field(ge=0)
    semiannual_count: int = Field(ge=0)
    annual_count: int = Field(ge=0)
    unknown_period_count: int = Field(ge=0)
    consolidated_count: int = Field(ge=0)
    standalone_count: int = Field(ge=0)
    unknown_consolidation_count: int = Field(ge=0)
    statement_count: int = Field(ge=0)
    segment_count: int = Field(ge=0)
    subsidiary_count: int = Field(ge=0)
    latest_period_end: date | None = None
    earliest_period_end: date | None = None
    coverage: dict[str, int] = Field(default_factory=dict)
    periods: tuple[FinancialPeriod, ...] = ()
    notes: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def _require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value


class ConflictSide(BaseModel):
    """One side of an evidence conflict."""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    semantic_category: SemanticCategory
    verification_status: VerificationStatus
    stance: EvidenceStance
    direction: IntelDirection
    source_name: str = Field(min_length=1)
    excerpt: str = Field(min_length=1)


class EvidenceConflict(BaseModel):
    """
    Two pieces of evidence that cannot both hold.

    Conflicts are surfaced as-is. The system never automatically
    concludes which side is correct.
    """

    model_config = ConfigDict(extra="forbid")

    conflict_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    description: str = Field(min_length=1)
    management_involved: bool
    first: ConflictSide
    second: ConflictSide
    as_of: datetime

    @field_validator("as_of")
    @classmethod
    def _require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value


class EvidenceLink(BaseModel):
    """An explicit support / contradiction link between items."""

    model_config = ConfigDict(extra="forbid")

    link_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    object_id: str = Field(min_length=1)
    relationship: EvidenceRelationship
    note: str | None = None


class IntelChange(BaseModel):
    """One change detected between two intelligence snapshots."""

    model_config = ConfigDict(extra="forbid")

    change_type: ChangeType
    item_id: str = Field(min_length=1)
    kind: IntelKind
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    previous_checksum: str | None = None
    current_checksum: str | None = None
    as_of: datetime

    @field_validator("as_of")
    @classmethod
    def _require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value


class SnapshotDiff(BaseModel):
    """Deterministic diff between two intelligence snapshots."""

    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1)
    as_of: datetime
    changes: tuple[IntelChange, ...] = ()
    counts: dict[str, int] = Field(default_factory=dict)

    @field_validator("as_of")
    @classmethod
    def _require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _recompute_counts(self) -> "SnapshotDiff":
        counts: dict[str, int] = {}

        for change in self.changes:
            key = change.change_type.value
            counts[key] = counts.get(key, 0) + 1

        self.counts = counts
        return self


class IntelCandidate(BaseModel):
    """
    A candidate item produced by a source provider.

    Candidates are the provider interface: providers return
    candidates, the engine validates, deduplicates, extracts, and
    archives them. A candidate is not automatically intelligence.
    """

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    company: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_url: str | None = None
    title: str = Field(min_length=1)
    body: str | None = None

    published_at: datetime | None = None
    available_at: datetime | None = None
    effective_at: datetime | None = None

    reliability_tier: int = Field(ge=1, le=6)
    kind: IntelKind = IntelKind.OTHER
    event_type: BusinessEventType | None = None
    semantic_category: SemanticCategory | None = None
    verification_status: VerificationStatus = VerificationStatus.REPORTED
    topic: str | None = None
    stance: EvidenceStance = EvidenceStance.NEUTRAL
    direction: IntelDirection = IntelDirection.UNKNOWN
    intel_category: IntelCategory | None = None
    related_entities: tuple[str, ...] = ()
    relevance: str | None = None
    confidence: Decimal | None = Field(default=None, ge=0, le=1)
    categories: tuple[str, ...] = ()
    raw: dict[str, object] | None = None

    @field_validator("published_at", "available_at", "effective_at")
    @classmethod
    def _require_aware_timestamp(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class TimelineEntry(BaseModel):
    """
    One chronological entry in a company evidence timeline.

    `timeline_at` is the canonical date used for ordering: the
    published date when known, otherwise the effective date, and
    finally the available date. Entries mirror their source item
    verbatim; no new information is added here.
    """

    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    kind: IntelKind
    intel_category: IntelCategory
    semantic_category: SemanticCategory
    verification_status: VerificationStatus
    event_type: BusinessEventType | None = None
    topic: str | None = None
    title: str = Field(min_length=1)
    description: str = ""
    direction: IntelDirection = IntelDirection.UNKNOWN
    stance: EvidenceStance = EvidenceStance.NEUTRAL

    published_at: datetime | None = None
    available_at: datetime | None = None
    effective_at: datetime | None = None
    timeline_at: datetime | None = None

    source: SourceRef
    provenance_id: str | None = None
    checksum: str = ""

    @field_validator("published_at", "available_at", "effective_at", "timeline_at")
    @classmethod
    def _require_aware_timestamp(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class CompanyTimeline(BaseModel):
    """
    A company's evidence timeline at one point in time.

    Entries are point-in-time pure: every entry was knowable at
    `as_of`. Ordering is deterministic and never editorialized.
    """

    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1)
    as_of: datetime
    entries: tuple[TimelineEntry, ...] = ()
    counts: dict[str, int] = Field(default_factory=dict)
    latest_at: datetime | None = None
    earliest_at: datetime | None = None
    notes: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def _require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value


class FreshnessStatus(BaseModel):
    """How fresh the intelligence is that is knowable at `as_of`."""

    model_config = ConfigDict(extra="forbid")

    latest_published_at: datetime | None = None
    latest_available_at: datetime | None = None
    latest_effective_at: datetime | None = None
    oldest_published_at: datetime | None = None
    oldest_available_at: datetime | None = None
    oldest_effective_at: datetime | None = None
    days_since_latest_published: int | None = None
    days_since_latest_available: int | None = None
    stale: bool = False
    notes: tuple[str, ...] = ()

    @field_validator(
        "latest_published_at",
        "latest_available_at",
        "latest_effective_at",
        "oldest_published_at",
        "oldest_available_at",
        "oldest_effective_at",
    )
    @classmethod
    def _require_aware_timestamp(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class CoverageStatus(BaseModel):
    """Coverage of the intelligence dimensions for a company."""

    model_config = ConfigDict(extra="forbid")

    item_count: int = Field(ge=0)
    by_kind: dict[str, int] = Field(default_factory=dict)
    by_category: dict[str, int] = Field(default_factory=dict)
    by_semantic: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)
    missing_categories: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class QualityStatus(BaseModel):
    """Data-quality status of an intelligence snapshot."""

    model_config = ConfigDict(extra="forbid")

    conflict_count: int = Field(ge=0)
    evidence_link_count: int = Field(ge=0)
    deduplicated_count: int = Field(ge=0)
    source_id_count: int = Field(ge=0)
    provenance_id_count: int = Field(ge=0)
    insufficient_evidence_notes: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class CompanyResearchStatus(BaseModel):
    """
    Aggregate freshness, coverage, and data-quality status of a
    company's research at one point in time.

    Descriptive only: statuses never grade the company or its
    prospects, they describe the research itself.
    """

    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1)
    as_of: datetime
    freshness: FreshnessStatus
    coverage: CoverageStatus
    quality: QualityStatus

    @field_validator("as_of")
    @classmethod
    def _require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value


class CompanyIntelligenceSnapshot(BaseModel):
    """
    The deep, evidence-based intelligence view of one company
    at one point in time.

    The snapshot is point-in-time pure: every item inside was
    knowable at `as_of`. It contains no scores and no investment
    opinion.
    """

    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1)
    as_of: datetime
    captured_at: datetime

    business_events: tuple[CorporateIntelItem, ...] = ()
    management_commentary: tuple[CorporateIntelItem, ...] = ()
    risk_intelligence: tuple[CorporateIntelItem, ...] = ()
    indirect_intelligence: tuple[CorporateIntelItem, ...] = ()
    financial_intelligence_items: tuple[CorporateIntelItem, ...] = ()
    other_intelligence: tuple[CorporateIntelItem, ...] = ()

    financial_intelligence: FinancialIntelligence | None = None

    timeline: CompanyTimeline | None = None
    status: CompanyResearchStatus | None = None

    conflicts: tuple[EvidenceConflict, ...] = ()
    evidence_links: tuple[EvidenceLink, ...] = ()

    changes: tuple[IntelChange, ...] = ()

    item_count: int = Field(ge=0)
    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()

    coverage: dict[str, int] = Field(default_factory=dict)
    semantic_summary: dict[str, int] = Field(default_factory=dict)
    status_summary: dict[str, int] = Field(default_factory=dict)

    insufficient_evidence_notes: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @field_validator("as_of", "captured_at")
    @classmethod
    def _require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value

    @property
    def items(self) -> tuple[CorporateIntelItem, ...]:
        """All items held by the snapshot, deduplicated by id."""
        collected: list[CorporateIntelItem] = []
        seen: set[str] = set()

        for group in (
            self.business_events,
            self.management_commentary,
            self.risk_intelligence,
            self.indirect_intelligence,
            self.financial_intelligence_items,
            self.other_intelligence,
        ):
            for item in group:
                if item.item_id in seen:
                    continue

                seen.add(item.item_id)
                collected.append(item)

        return tuple(collected)


class UpdateEngineStatus(str, Enum):
    OK = "OK"
    DEGRADED = "DEGRADED"


__all__ = [
    "CompanyIntelligenceSnapshot",
    "CompanyResearchStatus",
    "CompanyTimeline",
    "ConflictSide",
    "CorporateIntelItem",
    "CoverageStatus",
    "EvidenceConflict",
    "EvidenceLink",
    "FinancialIntelligence",
    "FinancialPeriod",
    "FinancialStatement",
    "FreshnessStatus",
    "IntelCandidate",
    "IntelChange",
    "QualityStatus",
    "SegmentResult",
    "SnapshotDiff",
    "SourceRef",
    "TimelineEntry",
    "UpdateEngineStatus",
]
