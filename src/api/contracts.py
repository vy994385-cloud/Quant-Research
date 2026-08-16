"""
L3 production research API contract.

Explicit Pydantic response models for the deterministic company
research, ranking, and discovery endpoints.

These models describe evidence already produced by the research
engine. They never invent scores or evidence.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ContractEvidence(BaseModel):
    """One traceable evidence item in the API contract."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)

    symbol: str = Field(min_length=1)
    evidence_type: str
    direction: str

    confidence: str
    reliability: str
    observation_at: str

    source_ids: list[str] = []
    provenance_ids: list[str] = []


class ContractIntelligenceSection(BaseModel):
    """Evidence state for one research-intelligence section."""

    model_config = ConfigDict(extra="forbid")

    status: str
    confidence: str

    observations: list[str] = []
    unknown: list[str] = []

    positive_count: int = 0
    negative_count: int = 0

    source_ids: list[str] = []
    provenance_ids: list[str] = []


class ContractIntelligence(BaseModel):
    """Structured research-intelligence sections exposed by the API."""

    model_config = ConfigDict(extra="forbid")

    business_quality: ContractIntelligenceSection | None = None
    financial_quality: ContractIntelligenceSection | None = None
    transformation: ContractIntelligenceSection | None = None
    capital_allocation: ContractIntelligenceSection | None = None
    competitive_position: ContractIntelligenceSection | None = None
    innovation: ContractIntelligenceSection | None = None
    future_technology: ContractIntelligenceSection | None = None
    customer_intelligence: ContractIntelligenceSection | None = None
    management_intelligence: ContractIntelligenceSection | None = None
    market_intelligence: ContractIntelligenceSection | None = None
    risks_anomalies: ContractIntelligenceSection | None = None

    unknown_missing: list[str] = []


class ContractSignal(BaseModel):
    """One point-in-time research signal."""

    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(min_length=1)
    category: str
    direction: str
    severity: str

    confidence: str
    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)

    symbol: str = Field(min_length=1)
    observation_at: str

    supporting_features: list[str] = []
    supporting_metrics: list[str] = []


class ContractPointInTime(BaseModel):
    """Explicit point-in-time contract for a research response."""

    model_config = ConfigDict(extra="forbid")

    as_of: str
    effective_as_of: str
    market_as_of: str | None = None

    evidence_included: int = 0
    acquired_evidence_included: int = 0
    future_evidence_excluded: int = 0

    sources_discovered: int = 0
    sources_accepted: int = 0
    sources_rejected: int = 0

    pit_checks_passed: bool = False
    notes: list[str] = []


class ContractDataQuality(BaseModel):
    """Data-quality status and warnings for the research response."""

    model_config = ConfigDict(extra="forbid")

    market_validation_status: str
    market_accepted_records: int = 0
    market_rejected_records: int = 0

    financial_record_count: int = 0
    financial_data_missing: bool = False

    feature_statuses: dict[str, str] = {}
    context: dict[str, int] = {}
    provenance_completeness: dict[str, bool] = {}
    warnings: list[str] = []
    provider_failures: list[str] = []


class ContractProvenanceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    dataset_id: str | None = None
    record_id: str | None = None
    retrieved_at: str | None = None
    available_at: str | None = None


class ContractProvenance(BaseModel):
    """Provenance surviving through the API response."""

    model_config = ConfigDict(extra="forbid")

    market: ContractProvenanceRecord
    financials: ContractProvenanceRecord
    archived_sources: list[str] = []


class ContractAssessment(BaseModel):
    """Overall research assessment for one company."""

    model_config = ConfigDict(extra="forbid")

    conclusion: str
    confidence: str
    thesis: str = Field(min_length=1)

    conflict_detected: bool = False
    direction: str
    research_ready: bool = False


class ContractEvidenceSummary(BaseModel):
    """Positive, negative, and neutral evidence split."""

    model_config = ConfigDict(extra="forbid")

    positive: list[ContractEvidence] = []
    negative: list[ContractEvidence] = []
    neutral: list[ContractEvidence] = []

    conflict_detected: bool = False
    direction: str

    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0

    positive_weight: str = "0"
    negative_weight: str = "0"

    average_confidence: str = "0"
    weighted_confidence: str = "0"


class ContractNarrative(BaseModel):
    """Structured narrative interpretation of the evidence."""

    model_config = ConfigDict(extra="forbid")

    thesis: str = Field(min_length=1)
    supporting_evidence: list[str] = []
    contradicting_evidence: list[str] = []
    strongest_evidence: list[str] = []
    uncertainty: list[str] = []
    key_risks: list[str] = []
    evidence_gaps: list[str] = []
    what_could_change_thesis: list[str] = []
    has_conflict: bool = False


class ContractRanking(BaseModel):
    """One horizon-specific research ranking."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    company_name: str | None = None
    horizon: str

    score: str
    signal: str
    confidence: str

    coverage: str = "100"
    missing_components: list[str] = []
    components: dict[str, str] = {}

    @property
    def has_degraded_evidence(self) -> bool:
        return bool(self.missing_components)


class CompanyResearchContract(BaseModel):
    """Full deterministic company research response."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    assessment: ContractAssessment
    point_in_time: ContractPointInTime

    intelligence: ContractIntelligence
    evidence: ContractEvidenceSummary
    narrative: ContractNarrative | None = None

    signals: list[ContractSignal] = []
    data_quality: ContractDataQuality
    provenance: ContractProvenance

    timeline: ContractTimeline | None = None
    research_status: ContractResearchStatus | None = None

    deep_financial_insights: ContractDeepFinancialInsights | None = None
    source_statuses: list[ContractSourceStatus] = []
    hidden_information: ContractHiddenInformation | None = None
    provider_failures: list[str] = []

    rankings: dict[str, ContractRanking] = {}
    research_score: dict[str, object] = {}


class CompanyRankingsContract(BaseModel):
    """All-horizon rankings for one company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    company_name: str | None = None
    as_of: str
    point_in_time: ContractPointInTime
    rankings: dict[str, ContractRanking]


class UniverseRankingsContract(BaseModel):
    """Horizon rankings across the supported company set."""

    model_config = ConfigDict(extra="forbid")

    as_of: str
    horizon: str
    count: int
    point_in_time: ContractPointInTime
    results: list[ContractRanking]


class CompanyDiscoveryItem(BaseModel):
    """One entry in the company discovery response."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    company_name: str | None = None
    sector: str
    research_available: bool = False


class CompanyDiscoveryResponse(BaseModel):
    """Supported-company discovery payload."""

    model_config = ConfigDict(extra="forbid")

    count: int
    results: list[CompanyDiscoveryItem]


class ContractIntelSource(BaseModel):
    """Source reference for one company-intelligence item."""

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_url: str | None = None
    reliability_tier: int = Field(ge=1, le=6)
    provenance_id: str | None = None


class ContractIntelItem(BaseModel):
    """One company-intelligence item in the API contract."""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    kind: str
    semantic_category: str
    verification_status: str
    event_type: str | None = None
    topic: str | None = None
    title: str = Field(min_length=1)
    description: str = ""
    stance: str
    direction: str

    intel_category: str | None = None
    derivation: str | None = None

    published_at: str | None = None
    available_at: str | None = None
    effective_at: str | None = None

    source: ContractIntelSource
    related_entities: list[str] = []
    relevance: str | None = None
    confidence: str | None = None
    provenance_id: str | None = None
    checksum: str = ""


class ContractSegment(BaseModel):
    """One segment result in a financial statement."""

    model_config = ConfigDict(extra="forbid")

    segment_name: str = Field(min_length=1)
    revenue: str | None = None
    profit: str | None = None
    note: str | None = None


class ContractFinancialStatement(BaseModel):
    """One normalized financial statement in the API contract."""

    model_config = ConfigDict(extra="forbid")

    statement_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    statement_type: str
    period_type: str
    consolidation: str
    period_start: str | None = None
    period_end: str
    published_at: str | None = None
    available_at: str | None = None
    effective_at: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    provenance_id: str | None = None
    currency: str | None = None
    items: dict[str, str] = {}
    segments: list[ContractSegment] = []
    subsidiaries: list[str] = []
    notes: list[str] = []


class ContractFinancialPeriod(BaseModel):
    """One reporting period with normalized metrics."""

    model_config = ConfigDict(extra="forbid")

    period_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    period_start: str | None = None
    period_end: str
    period_type: str
    consolidation: str
    published_at: str | None = None
    available_at: str | None = None
    effective_at: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    provenance_id: str | None = None
    currency: str | None = None
    metrics: dict[str, str] = {}
    segments: list[ContractSegment] = []
    subsidiaries: list[str] = []
    statements: list[ContractFinancialStatement] = []


class ContractFinancialIntelligence(BaseModel):
    """Descriptive summary of a company's reporting history."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str

    period_count: int = 0
    quarterly_count: int = 0
    semiannual_count: int = 0
    annual_count: int = 0
    unknown_period_count: int = 0
    consolidated_count: int = 0
    standalone_count: int = 0
    unknown_consolidation_count: int = 0
    statement_count: int = 0
    segment_count: int = 0
    subsidiary_count: int = 0
    latest_period_end: str | None = None
    earliest_period_end: str | None = None
    coverage: dict[str, int] = {}
    periods: list[ContractFinancialPeriod] = []
    notes: list[str] = []


class ContractConflictSide(BaseModel):
    """One side of an evidence conflict."""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    semantic_category: str
    verification_status: str
    stance: str
    direction: str
    source_name: str = Field(min_length=1)
    excerpt: str = Field(min_length=1)


class ContractEvidenceConflict(BaseModel):
    """One surfaced evidence conflict."""

    model_config = ConfigDict(extra="forbid")

    conflict_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    description: str = Field(min_length=1)
    management_involved: bool = False
    first: ContractConflictSide
    second: ContractConflictSide
    as_of: str


class ContractIntelChange(BaseModel):
    """One change detected between two intelligence snapshots."""

    model_config = ConfigDict(extra="forbid")

    change_type: str
    item_id: str = Field(min_length=1)
    kind: str
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    previous_checksum: str | None = None
    current_checksum: str | None = None
    previous_title: str | None = None
    semantic_category: str | None = None
    intel_category: str | None = None
    event_type: str | None = None
    published_at: str | None = None
    available_at: str | None = None
    as_of: str


class CompanyIntelligenceContract(BaseModel):
    """Deep company intelligence response contract."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]

    as_of: str

    financial_intelligence: ContractFinancialIntelligence | None = None

    business_events: list[ContractIntelItem] = []
    management_commentary: list[ContractIntelItem] = []
    risk_intelligence: list[ContractIntelItem] = []
    indirect_intelligence: list[ContractIntelItem] = []
    financial_intelligence_items: list[ContractIntelItem] = []
    other_intelligence: list[ContractIntelItem] = []

    conflicts: list[ContractEvidenceConflict] = []
    changes: list[ContractIntelChange] = []

    deep_financial_insights: ContractDeepFinancialInsights | None = None
    source_statuses: list[ContractSourceStatus] = []
    hidden_information: ContractHiddenInformation | None = None
    provider_failures: list[str] = []

    timeline: "ContractTimeline | None" = None
    research_status: "ContractResearchStatus | None" = None

    item_count: int = 0
    source_ids: list[str] = []
    provenance_ids: list[str] = []

    coverage: dict[str, int] = {}
    semantic_summary: dict[str, int] = {}
    status_summary: dict[str, int] = {}

    insufficient_evidence_notes: list[str] = []
    notes: list[str] = []


class ContractDeepMetricObservation(BaseModel):
    """One metric observation in a deep financial series."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    metric: str
    period_id: str
    period_end: str
    period_type: str
    consolidation: str
    observation_type: str

    value: str | None = None
    previous_value: str | None = None
    delta: str | None = None
    delta_pct: str | None = None
    derivation: str | None = None

    published_at: str | None = None
    available_at: str | None = None
    provenance_id: str | None = None


class ContractDeepFinancialSeries(BaseModel):
    """One comparable reporting-period series."""

    model_config = ConfigDict(extra="forbid")

    series_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    period_type: str
    consolidation: str
    period_count: int
    period_ends: list[str] = []
    metrics: list[str] = []


class ContractDeepFinancialInsights(BaseModel):
    """Deep financial insights for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    series: list[ContractDeepFinancialSeries] = []
    observations: list[ContractDeepMetricObservation] = []
    comparability_notes: list[str] = []
    financial_type_counts: dict[str, int] = {}


class ContractSourceStatus(BaseModel):
    """Status of one research source at as_of."""

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1)
    source_type: str
    item_count: int
    categories: list[str] = []
    latest_published_at: str | None = None
    latest_available_at: str | None = None
    days_since_latest_published: int | None = None
    stale: bool = False
    provenance_completeness: bool = False
    notes: list[str] = []


class ContractDerivedObservation(BaseModel):
    """A derived (less-obvious) observation from recorded evidence."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    label: str
    semantic_category: str
    description: str = Field(min_length=1)
    derivation: str = Field(min_length=1)
    source_ids: list[str] = []
    provenance_ids: list[str] = []
    related_item_ids: list[str] = []
    as_of: str


class ContractHiddenInformation(BaseModel):
    """Hidden / less-obvious information for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    observations: list[ContractDerivedObservation] = []
    notes: list[str] = []


class ContractTimelineEntry(BaseModel):
    """One chronological entry in a company evidence timeline."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    kind: str
    intel_category: str
    semantic_category: str
    verification_status: str
    event_type: str | None = None
    topic: str | None = None
    title: str = Field(min_length=1)
    description: str = ""
    stance: str
    direction: str

    published_at: str | None = None
    available_at: str | None = None
    effective_at: str | None = None
    timeline_at: str | None = None

    source: ContractIntelSource
    provenance_id: str | None = None
    checksum: str = ""


class ContractTimeline(BaseModel):
    """A company's evidence timeline at one point in time."""

    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1)
    as_of: str
    entries: list[ContractTimelineEntry] = []
    counts: dict[str, int] = {}
    latest_at: str | None = None
    earliest_at: str | None = None
    notes: list[str] = []


class ContractFreshness(BaseModel):
    """Freshness of the intelligence knowable at as_of."""

    model_config = ConfigDict(extra="forbid")

    latest_published_at: str | None = None
    latest_available_at: str | None = None
    latest_effective_at: str | None = None
    oldest_published_at: str | None = None
    oldest_available_at: str | None = None
    oldest_effective_at: str | None = None
    days_since_latest_published: int | None = None
    days_since_latest_available: int | None = None
    stale: bool = False
    notes: list[str] = []


class ContractCoverage(BaseModel):
    """Coverage of the intelligence dimensions for a company."""

    model_config = ConfigDict(extra="forbid")

    item_count: int = 0
    by_kind: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_semantic: dict[str, int] = {}
    by_status: dict[str, int] = {}
    missing_categories: list[str] = []
    notes: list[str] = []


class ContractQuality(BaseModel):
    """Data-quality status of an intelligence snapshot."""

    model_config = ConfigDict(extra="forbid")

    conflict_count: int = 0
    evidence_link_count: int = 0
    deduplicated_count: int = 0
    source_id_count: int = 0
    provenance_id_count: int = 0
    insufficient_evidence_notes: list[str] = []
    notes: list[str] = []


class ContractResearchStatus(BaseModel):
    """Aggregate research status for a company at as_of."""

    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1)
    as_of: str
    freshness: ContractFreshness
    coverage: ContractCoverage
    quality: ContractQuality


class CompanyTimelineContract(BaseModel):
    """Timeline response for one company at one point in time."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    timeline: ContractTimeline


class CompanyDeepFinancialInsightsContract(BaseModel):
    """Deep financial insights response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    deep_financial_insights: ContractDeepFinancialInsights | None = None


class CompanySourceStatusesContract(BaseModel):
    """Source statuses response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    source_statuses: list[ContractSourceStatus] = []


class CompanyHiddenInformationContract(BaseModel):
    """Hidden / less-obvious information response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    hidden_information: ContractHiddenInformation | None = None


__all__ = [
    "CompanyDiscoveryItem",
    "CompanyDiscoveryResponse",
    "CompanyIntelligenceContract",
    "CompanyRankingsContract",
    "CompanyResearchContract",
    "CompanyTimelineContract",
    "CompanyDeepFinancialInsightsContract",
    "CompanySourceStatusesContract",
    "CompanyHiddenInformationContract",
    "ContractAssessment",
    "ContractConflictSide",
    "ContractCoverage",
    "ContractDataQuality",
    "ContractDeepFinancialInsights",
    "ContractDeepFinancialSeries",
    "ContractDeepMetricObservation",
    "ContractDerivedObservation",
    "ContractEvidence",
    "ContractEvidenceConflict",
    "ContractEvidenceSummary",
    "ContractFinancialIntelligence",
    "ContractFinancialPeriod",
    "ContractFinancialStatement",
    "ContractFreshness",
    "ContractHiddenInformation",
    "ContractIntelChange",
    "ContractIntelItem",
    "ContractIntelSource",
    "ContractIntelligence",
    "ContractIntelligenceSection",
    "ContractNarrative",
    "ContractPointInTime",
    "ContractProvenance",
    "ContractProvenanceRecord",
    "ContractQuality",
    "ContractRanking",
    "ContractResearchStatus",
    "ContractSegment",
    "ContractSignal",
    "ContractSourceStatus",
    "ContractTimeline",
    "ContractTimelineEntry",
    "UniverseRankingsContract",
]
