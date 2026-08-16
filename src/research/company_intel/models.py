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
    FinancialObservationType,
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


class DeepMetricObservation(BaseModel):
    """
    One deep financial observation for a reporting period.

    `observation_type` states whether the value was reported by the
    company, derived deterministically from reported figures (see
    `derivation` for the exact formula), or unavailable in the
    recorded evidence. `previous_value`, `delta`, and `delta_pct`
    compare against the previous comparable period in the same
    series; quarterly and annual figures are never compared.
    """

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    period_id: str = Field(min_length=1)
    period_end: date
    period_type: ReportingPeriodType
    consolidation: ConsolidationScope
    observation_type: FinancialObservationType
    value: Decimal | None = None
    previous_value: Decimal | None = None
    delta: Decimal | None = None
    delta_pct: Decimal | None = None
    derivation: str | None = None
    notes: tuple[str, ...] = ()
    published_at: datetime | None = None
    available_at: datetime | None = None
    provenance_id: str | None = None

    @field_validator("published_at", "available_at")
    @classmethod
    def _require_aware_timestamp(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class DeepFinancialSeries(BaseModel):
    """
    One comparable series of reporting periods.

    Comparability requires the same period type and consolidation
    scope; quarterly and annual figures must never be compared
    directly, so each series is analyzed independently.
    """

    model_config = ConfigDict(extra="forbid")

    series_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    period_type: ReportingPeriodType
    consolidation: ConsolidationScope
    period_count: int = Field(ge=0)
    period_ends: tuple[date, ...] = ()
    metrics: tuple[str, ...] = ()


class DeepFinancialInsights(BaseModel):
    """
    Deep, deterministic view of a company's reporting history.

    Observations are produced only from reported figures. Derived
    values carry an explicit `derivation` so every number can be
    reproduced and audited. Nothing here is a prediction.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    series: tuple[DeepFinancialSeries, ...] = ()
    observations: tuple[DeepMetricObservation, ...] = ()
    comparability_notes: tuple[str, ...] = ()
    financial_type_counts: dict[str, int] = Field(default_factory=dict)

    @field_validator("as_of")
    @classmethod
    def _require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value


class SourceStatus(BaseModel):
    """
    Status of one source in an intelligence snapshot.

    Describes the *source*, not the company: how much evidence it
    contributes, how fresh it is, and whether provenance survives.
    """

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    item_count: int = Field(ge=0)
    categories: tuple[str, ...] = ()
    latest_published_at: datetime | None = None
    latest_available_at: datetime | None = None
    days_since_latest_published: int | None = None
    stale: bool = False
    provenance_completeness: bool = False
    notes: tuple[str, ...] = ()

    @field_validator("latest_published_at", "latest_available_at")
    @classmethod
    def _require_aware_timestamp(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class DerivedObservation(BaseModel):
    """
    One hidden / less-obvious observation derived from evidence.

    These observations never invent facts: they state what the
    evidence set deterministically implies (e.g. two claims on the
    same topic coexist without auto-resolution, or a derived metric
    diverges from a reported claim). The derivation is explicit.
    """

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    label: str = Field(min_length=1)
    semantic_category: SemanticCategory
    description: str = Field(min_length=1)
    derivation: str = Field(min_length=1)
    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()
    related_item_ids: tuple[str, ...] = ()
    as_of: datetime

    @field_validator("as_of")
    @classmethod
    def _require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return value


class HiddenInformationInsights(BaseModel):
    """
    Aggregate hidden / less-obvious information for a company.

    Every observation is derived deterministically from the recorded
    evidence; labels come from the semantic vocabulary. No inference
    is upgraded to a fact and no claim is resolved automatically.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    observations: tuple[DerivedObservation, ...] = ()
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
    """
    One change detected between two intelligence snapshots.

    The change record carries the current item's semantic category,
    category, event type, and timestamps so a "what changed" report
    can explain *what* the change is about without re-resolving the
    item. `previous_title` preserves the previous version's title
    when an item was renamed.
    """

    model_config = ConfigDict(extra="forbid")

    change_type: ChangeType
    item_id: str = Field(min_length=1)
    kind: IntelKind
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    previous_checksum: str | None = None
    current_checksum: str | None = None
    as_of: datetime

    semantic_category: SemanticCategory | None = None
    intel_category: IntelCategory | None = None
    event_type: BusinessEventType | None = None
    previous_title: str | None = None
    published_at: datetime | None = None
    available_at: datetime | None = None

    @field_validator("as_of", "published_at", "available_at")
    @classmethod
    def _require_aware_timestamp(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
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
    provider_failures: tuple[str, ...] = ()
    stale_source_count: int = Field(ge=0)
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

    deep_financial_insights: DeepFinancialInsights | None = None
    source_statuses: tuple[SourceStatus, ...] = ()
    hidden_information: HiddenInformationInsights | None = None

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

    provider_failures: tuple[str, ...] = ()

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
    "DeepFinancialInsights",
    "DeepFinancialSeries",
    "DeepMetricObservation",
    "DerivedObservation",
    "EvidenceConflict",
    "EvidenceLink",
    "FinancialIntelligence",
    "FinancialPeriod",
    "FinancialStatement",
    "FreshnessStatus",
    "HiddenInformationInsights",
    "IntelCandidate",
    "IntelChange",
    "QualityStatus",
    "SegmentResult",
    "SnapshotDiff",
    "SourceRef",
    "SourceStatus",
    "TimelineEntry",
    "UpdateEngineStatus",
]
