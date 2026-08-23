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

    confidence: str | None = None
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

    # New research expansion fields
    cash_flow_quality: ContractCashFlowQuality | None = None
    balance_sheet_deep: ContractBalanceSheetDeep | None = None
    research_gaps: ContractResearchGaps | None = None
    cross_domain: ContractCrossDomain | None = None
    financial_anomalies: ContractFinancialAnomalies | None = None

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
    # Unknown/unavailable sector is null — never a sentinel string.
    sector: str | None = None
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

    cash_flow_quality: ContractCashFlowQuality | None = None
    balance_sheet_deep: ContractBalanceSheetDeep | None = None
    research_gaps: ContractResearchGaps | None = None
    cross_domain: ContractCrossDomain | None = None
    financial_anomalies: ContractFinancialAnomalies | None = None

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
    """One metric observation in a deep financial series.

    `unit` states the quantity contractually: "INR" for absolute
    Indian-rupee amounts (raw reported scale) and "FRACTION" for
    ratios of one (render as percentages downstream). `delta_pct` is
    always a fraction of the previous value. Division results are
    quantized to six decimals (ROUND_HALF_UP); missing values are
    null, never fabricated zeros.
    """

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    metric: str
    period_id: str
    period_end: str
    period_type: str
    consolidation: str
    observation_type: str
    unit: str = "INR"

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
    severity: str = "INFO"


class ContractHiddenInformation(BaseModel):
    """Hidden / less-obvious information for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    observations: list[ContractDerivedObservation] = []
    notes: list[str] = []


# ---- New research expansion contract models ----

class ContractCashFlowObservation(BaseModel):
    """One cash-flow quality observation."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    label: str
    semantic_category: str
    description: str
    calculation_inputs: dict[str, object] = {}
    methodology: str = ""
    confidence: str | None = None
    severity: str = "INFO"
    as_of: str


class ContractCashFlowQuality(BaseModel):
    """Cash-flow quality analysis for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    direction: str = "UNKNOWN"
    observation_count: int = 0
    observations: list[ContractCashFlowObservation] = []
    notes: list[str] = []


class ContractBalanceSheetDeepObservation(BaseModel):
    """One balance-sheet deep observation."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    label: str
    semantic_category: str
    description: str
    calculation_inputs: dict[str, object] = {}
    methodology: str = ""
    confidence: str | None = None
    severity: str = "INFO"
    as_of: str


class ContractBalanceSheetDeep(BaseModel):
    """Deep balance-sheet analysis for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    direction: str = "UNKNOWN"
    observation_count: int = 0
    observations: list[ContractBalanceSheetDeepObservation] = []
    notes: list[str] = []


class ContractResearchGap(BaseModel):
    """One research gap observation."""

    model_config = ConfigDict(extra="forbid")

    gap_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    category: str
    description: str
    status: str = "UNAVAILABLE"
    severity: str = "INFO"
    reason: str = ""
    suggested_action: str = ""
    sources_checked: list[str] = []
    evidence_refs: list[str] = []
    related_metrics: list[str] = []
    supporting_data: dict[str, str] = {}
    as_of: str


class ContractResearchGaps(BaseModel):
    """Research gaps for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    gap_count: int = 0
    gaps: list[ContractResearchGap] = []
    status_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    coverage_score: str | None = None
    coverage_explanation: str = ""
    notes: list[str] = []


class ContractCrossDomainObservation(BaseModel):
    """One cross-domain divergence observation."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    label: str
    semantic_category: str
    description: str

    domain_1_name: str = ""
    domain_1_metric: str = ""
    domain_1_value: str | None = None
    domain_1_direction: str = "UNKNOWN"

    domain_2_name: str = ""
    domain_2_metric: str = ""
    domain_2_value: str | None = None
    domain_2_direction: str = "UNKNOWN"

    relationship: str = ""
    direction: str = "NEUTRAL"
    limitations: list[str] = []

    calculation_inputs: dict[str, object] = {}
    methodology: str = ""
    confidence: str | None = None
    severity: str = "INFO"
    as_of: str

    source_name: str | None = None
    related_metrics: list[str] = []
    supporting_data: dict[str, str] = {}


class ContractCrossDomain(BaseModel):
    """Cross-domain intelligence for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    observation_count: int = 0
    observations: list[ContractCrossDomainObservation] = []
    positive_count: int = 0
    negative_count: int = 0
    mixed_count: int = 0
    neutral_count: int = 0
    notes: list[str] = []


class ContractFinancialAnomaly(BaseModel):
    """One financial divergence anomaly observation."""

    model_config = ConfigDict(extra="forbid")

    metric: str = Field(min_length=1)
    current_change: str
    comparison_change: str | None = None
    severity: str = "MEDIUM"
    explanation: str = ""


class ContractFinancialAnomalies(BaseModel):
    """Aggregated financial anomaly observations for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    anomaly_count: int = 0
    anomalies: list[ContractFinancialAnomaly] = []
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


class CompanyCrossDomainContract(BaseModel):
    """Cross-domain intelligence response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    cross_domain: ContractCrossDomain | None = None


class CompanyResearchGapsContract(BaseModel):
    """Research gaps response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    research_gaps: ContractResearchGaps | None = None


# =====================================================================
# Phase 4 Technical contracts
# =====================================================================


class ContractTechnicalIndicatorSet(BaseModel):
    """Complete set of technical indicators for a company."""

    model_config = ConfigDict(extra="forbid")

    # Returns
    return_1d: str | None = None
    return_5d: str | None = None
    return_10d: str | None = None
    return_20d: str | None = None
    return_50d: str | None = None
    return_100d: str | None = None
    return_200d: str | None = None

    # SMAs
    sma_5: str | None = None
    sma_10: str | None = None
    sma_20: str | None = None
    sma_50: str | None = None
    sma_100: str | None = None
    sma_200: str | None = None

    # EMAs
    ema_9: str | None = None
    ema_12: str | None = None
    ema_20: str | None = None
    ema_26: str | None = None
    ema_50: str | None = None
    ema_200: str | None = None

    # Price vs MAs
    price_vs_sma_5_pct: str | None = None
    price_vs_sma_20_pct: str | None = None
    price_vs_sma_50_pct: str | None = None
    price_vs_ema_9_pct: str | None = None
    price_vs_ema_20_pct: str | None = None
    price_vs_ema_50_pct: str | None = None

    # RSI
    rsi_14: str | None = None
    rsi_signal: str | None = None

    # MACD
    macd_line: str | None = None
    macd_signal_line: str | None = None
    macd_histogram: str | None = None
    macd_crossover: str | None = None

    # Stochastic
    stochastic_k: str | None = None
    stochastic_d: str | None = None
    stochastic_signal: str | None = None

    # Williams %R
    williams_r_14: str | None = None
    williams_r_signal: str | None = None

    # ATR
    atr_14: str | None = None
    atr_pct: str | None = None

    # Bollinger
    bollinger_upper: str | None = None
    bollinger_middle: str | None = None
    bollinger_lower: str | None = None
    bollinger_bandwidth: str | None = None
    bollinger_pct_b: str | None = None
    bollinger_signal: str | None = None

    # ADX
    adx_14: str | None = None
    adx_plus_di: str | None = None
    adx_minus_di: str | None = None
    adx_signal: str | None = None

    # CCI
    cci_20: str | None = None
    cci_signal: str | None = None

    # Volume
    obv: int | None = None
    ad_line: str | None = None
    mfi_14: str | None = None
    mfi_signal: str | None = None
    price_volume_divergence: str | None = None

    # Pivots
    pivot: str | None = None
    r1: str | None = None
    r2: str | None = None
    r3: str | None = None
    s1: str | None = None
    s2: str | None = None
    s3: str | None = None

    # Breakout
    breakout_signal: str | None = None

    # Gaps
    gap_type: str | None = None
    gap_pct: str | None = None

    # 52-week
    high_52w: str | None = None
    low_52w: str | None = None
    pct_from_52w_high: str | None = None
    pct_from_52w_low: str | None = None
    high_low_signal: str | None = None

    # Drawdowns
    current_drawdown: str | None = None
    max_drawdown_20d: str | None = None
    recovery_pct: str | None = None

    # Trend
    regime: str | None = None
    trend_strength: str | None = None
    sma_alignment: str | None = None
    ema_alignment: str | None = None


class ContractTechnicalObservation(BaseModel):
    """One technical observation with provenance."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    category: str
    observation_type: str
    indicator: str
    period: str
    value: str | None = None
    signal: str
    direction: str
    severity: str
    explanation: str
    source: str
    available_at: str | None = None
    as_of: str | None = None
    status: str
    supporting_data: dict[str, str] = {}


class ContractTechnicalObservationSet(BaseModel):
    """Complete set of technical observations."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    trading_date: str
    indicator_observations: list[ContractTechnicalObservation] = []
    signal_observations: list[ContractTechnicalObservation] = []
    total_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    available_indicators: list[str] = []
    missing_indicators: list[str] = []


class ContractDeepTechnicalResult(BaseModel):
    """Deep technical analysis result."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    trading_date: str
    bars_used: int = 0
    indicators: ContractTechnicalIndicatorSet | None = None
    observation_set: ContractTechnicalObservationSet | None = None
    available_indicators: list[str] = []
    missing_indicators: list[str] = []
    notes: list[str] = []


class CompanyDeepTechnicalContract(BaseModel):
    """Deep technical research response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    deep_technicals: ContractDeepTechnicalResult


# =====================================================================
# Phase 4 Attribution contracts
# =====================================================================


class ContractPriceMove(BaseModel):
    """One observed price move."""

    model_config = ConfigDict(extra="forbid")

    from_date: str
    to_date: str
    from_close: str
    to_close: str
    absolute_change: str
    percentage_change: str
    direction: str
    trading_days: int


class ContractAttributionCandidate(BaseModel):
    """One candidate explanation for a price move."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    category: str
    direction: str
    confidence: str
    title: str
    description: str
    supporting_evidence: list[str] = []
    confidence_score: str = "0"
    explanation: str = ""


class ContractPriceAttribution(BaseModel):
    """Price attribution analysis result."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    price_move: ContractPriceMove | None = None
    candidates: list[ContractAttributionCandidate] = []
    total_candidates: int = 0
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    coverage: dict[str, int] = {}
    notes: list[str] = []
    disclaimer: str = "Attribution is correlational only. Do not use for investment decisions."


class CompanyAttributionContract(BaseModel):
    """Price attribution response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    attribution: ContractPriceAttribution


# =====================================================================
# Phase 4 Business Intelligence contracts
# =====================================================================


class ContractSegmentShare(BaseModel):
    """One segment's revenue share."""

    model_config = ConfigDict(extra="forbid")

    segment_name: str = Field(min_length=1)
    revenue: str | None = None
    share_pct: str | None = None


class ContractSegmentConcentration(BaseModel):
    """Segment concentration analysis."""

    model_config = ConfigDict(extra="forbid")

    period: str
    total_revenue: str | None = None
    segment_count: int = 0
    dominant_segment: str | None = None
    dominant_segment_pct: str | None = None
    hhi: str | None = None
    concentration_level: str | None = None
    segment_shares: list[ContractSegmentShare] = []
    explanation: str = ""


class ContractSegmentTrend(BaseModel):
    """One segment trend over time."""

    model_config = ConfigDict(extra="forbid")

    segment_name: str
    direction: str
    periods_analyzed: int = 0
    first_period: str = ""
    last_period: str = ""
    share_change: str | None = None
    explanation: str = ""


class ContractBusinessQualitySignal(BaseModel):
    """One business quality signal."""

    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(min_length=1)
    signal_type: str
    direction: str
    title: str
    description: str
    metric: str
    value: str | None = None
    threshold: str | None = None


class ContractBusinessAnalysis(BaseModel):
    """Business analysis result."""

    model_config = ConfigDict(extra="forbid")

    has_profile: bool = False
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    employees: int | None = None
    segment_concentrations: list[ContractSegmentConcentration] = []
    segment_trends: list[ContractSegmentTrend] = []
    quality_signals: list[ContractBusinessQualitySignal] = []
    available_analyses: list[str] = []
    missing_analyses: list[str] = []


class ContractCompetitiveMetric(BaseModel):
    """One competitive metric comparison."""

    model_config = ConfigDict(extra="forbid")

    metric: str
    company_value: str | None = None
    peer_median: str | None = None
    percentile: str = ""
    position: str = "UNKNOWN"
    explanation: str = ""


class ContractCompetitiveSignal(BaseModel):
    """One competitive signal."""

    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(min_length=1)
    signal_type: str
    direction: str
    title: str
    description: str
    metric: str
    company_value: str | None = None
    peer_value: str | None = None
    explanation: str = ""


class ContractCompetitiveAnalysis(BaseModel):
    """Competitive analysis result."""

    model_config = ConfigDict(extra="forbid")

    has_peer_data: bool = False
    peer_count: int = 0
    metrics: list[ContractCompetitiveMetric] = []
    signals: list[ContractCompetitiveSignal] = []
    available_analyses: list[str] = []
    missing_analyses: list[str] = []


class ContractManagementPattern(BaseModel):
    """One management change pattern."""

    model_config = ConfigDict(extra="forbid")

    pattern_id: str = Field(min_length=1)
    pattern_type: str
    change_count: int = 0
    roles_affected: list[str] = []
    date_range: str = ""
    explanation: str = ""


class ContractCapitalAllocationSignal(BaseModel):
    """One capital allocation signal."""

    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(min_length=1)
    signal_type: str
    direction: str
    title: str
    description: str
    metric: str
    value: str | None = None
    explanation: str = ""


class ContractManagementAnalysis(BaseModel):
    """Management analysis result."""

    model_config = ConfigDict(extra="forbid")

    change_count: int = 0
    patterns: list[ContractManagementPattern] = []
    allocation_signals: list[ContractCapitalAllocationSignal] = []
    available_analyses: list[str] = []
    missing_analyses: list[str] = []


class ContractRiskObservation(BaseModel):
    """One risk observation."""

    model_config = ConfigDict(extra="forbid")

    risk_id: str = Field(min_length=1)
    risk_dimension: str
    severity: str
    title: str
    description: str
    explanation: str = ""


class ContractRiskAnalysis(BaseModel):
    """Risk analysis result."""

    model_config = ConfigDict(extra="forbid")

    observations: list[ContractRiskObservation] = []
    dimension_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    available_analyses: list[str] = []
    missing_analyses: list[str] = []


class ContractBusinessDerivedObservation(BaseModel):
    """A cross-domain derived observation."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    evidence_classification: str
    domain: str
    title: str
    description: str
    source_domains: list[str] = []
    explanation: str = ""


class ContractDerivedObservations(BaseModel):
    """Set of cross-domain derived observations."""

    model_config = ConfigDict(extra="forbid")

    observations: list[ContractBusinessDerivedObservation] = []
    fact_count: int = 0
    observation_count: int = 0
    interpretation_count: int = 0
    available_analyses: list[str] = []
    missing_analyses: list[str] = []


class ContractBusinessIntelligence(BaseModel):
    """Complete business intelligence result."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    has_profile: bool = False
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    employees: int | None = None
    business_analysis: ContractBusinessAnalysis | None = None
    competitive_analysis: ContractCompetitiveAnalysis | None = None
    management_analysis: ContractManagementAnalysis | None = None
    risk_analysis: ContractRiskAnalysis | None = None
    derived_observations: ContractDerivedObservations | None = None
    total_observations: int = 0
    risk_count: int = 0
    derived_count: int = 0
    available_analyses: list[str] = []
    missing_analyses: list[str] = []
    notes: list[str] = []


class CompanyBusinessIntelligenceContract(BaseModel):
    """Business intelligence response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    business_intelligence: ContractBusinessIntelligence


# =====================================================================
# Phase 4 Fundamentals contracts
# =====================================================================


class ContractFinancialMetric(BaseModel):
    """One raw financial metric observation."""

    model_config = ConfigDict(extra="forbid")

    metric: str
    value: str | None = None
    available: bool = False
    source: str | None = None
    as_of: str | None = None


class ContractFinancialRatio(BaseModel):
    """One calculated financial ratio."""

    model_config = ConfigDict(extra="forbid")

    ratio: str
    value: str | None = None
    available: bool = False
    numerator_metric: str | None = None
    denominator_metric: str | None = None
    explanation: str = ""


class ContractFinancialPeriodDetail(BaseModel):
    """One reporting period with all metrics and ratios."""

    model_config = ConfigDict(extra="forbid")

    period_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    period_end: str
    period_type: str | None = None
    consolidation: str | None = None
    published_at: str | None = None
    available_at: str | None = None
    effective_at: str | None = None
    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    currency: str | None = None
    metrics: list[ContractFinancialMetric] = []
    ratios: list[ContractFinancialRatio] = []


class ContractFinancialHistory(BaseModel):
    """Complete financial history with metrics and ratios."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    period_count: int = 0
    periods: list[ContractFinancialPeriodDetail] = []
    available_metrics: list[str] = []
    missing_metrics: list[str] = []
    available_ratios: list[str] = []
    missing_ratios: list[str] = []
    coverage: dict[str, int] = {}
    notes: list[str] = []


class CompanyFinancialHistoryContract(BaseModel):
    """Financial history response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    financial_history: ContractFinancialHistory


class ContractPeriodGrowthRate(BaseModel):
    """Growth rate between two consecutive periods."""

    model_config = ConfigDict(extra="forbid")

    from_period: str
    to_period: str
    previous_value: str | None = None
    current_value: str | None = None
    growth_rate: str | None = None
    metric: str = ""


class ContractTrajectoryAnalysis(BaseModel):
    """Multi-period trajectory for one financial metric."""

    model_config = ConfigDict(extra="forbid")

    metric: str
    symbol: str = Field(min_length=1)
    period_count: int = 0
    first_period: str = ""
    last_period: str = ""
    first_value: str | None = None
    last_value: str | None = None
    cagr: str | None = None
    total_change: str | None = None
    total_change_pct: str | None = None
    growth_rates: list[ContractPeriodGrowthRate] = []
    direction: str | None = None
    acceleration: str | None = None
    persistence_pct: str | None = None
    average_growth_rate: str | None = None
    min_growth_rate: str | None = None
    max_growth_rate: str | None = None
    explanation: str = ""


class ContractMarginTrajectory(BaseModel):
    """Margin trajectory over multiple periods."""

    model_config = ConfigDict(extra="forbid")

    margin_name: str
    symbol: str = Field(min_length=1)
    period_count: int = 0
    first_period: str = ""
    last_period: str = ""
    first_value: str | None = None
    last_value: str | None = None
    total_change_pp: str | None = None
    direction: str | None = None
    persistent: bool = False
    values: list[list[str | None]] = []
    explanation: str = ""


class ContractLeverageTrajectory(BaseModel):
    """Leverage trajectory over multiple periods."""

    model_config = ConfigDict(extra="forbid")

    metric: str
    symbol: str = Field(min_length=1)
    period_count: int = 0
    first_period: str = ""
    last_period: str = ""
    first_value: str | None = None
    last_value: str | None = None
    direction: str | None = None
    elevated: bool = False
    peak_value: str | None = None
    trough_value: str | None = None
    values: list[list[str | None]] = []
    explanation: str = ""


class ContractCashProfitComparison(BaseModel):
    """Cash vs profit comparison for one period."""

    model_config = ConfigDict(extra="forbid")

    period: str
    net_profit: str | None = None
    operating_cash_flow: str | None = None
    free_cash_flow: str | None = None
    ocf_to_profit_ratio: str | None = None
    fcf_to_profit_ratio: str | None = None
    ocf_exceeds_profit: bool | None = None
    fcf_exceeds_profit: bool | None = None
    explanation: str = ""


class ContractGrowthDivergence(BaseModel):
    """One growth divergence observation."""

    model_config = ConfigDict(extra="forbid")

    period: str
    metric: str
    metric_growth_rate: str | None = None
    revenue_growth_rate: str | None = None
    divergence_pp: str | None = None
    flagged: bool = False
    explanation: str = ""


class ContractEarningsQualityObservation(BaseModel):
    """Earnings quality observation."""

    model_config = ConfigDict(extra="forbid")

    observation_type: str
    symbol: str = Field(min_length=1)
    severity: str
    periods_covered: int = 0
    first_period: str = ""
    last_period: str = ""
    value: str | None = None
    metric: str = ""
    cash_profit_comparisons: list[ContractCashProfitComparison] = []
    growth_divergences: list[ContractGrowthDivergence] = []
    persistent: bool = False
    explanation: str = ""


class ContractDebtGrowthComparison(BaseModel):
    """Debt vs revenue growth comparison."""

    model_config = ConfigDict(extra="forbid")

    period: str
    debt_growth_rate: str | None = None
    revenue_growth_rate: str | None = None
    divergence_pp: str | None = None
    flagged: bool = False
    explanation: str = ""


class ContractLiquidityChange(BaseModel):
    """Liquidity ratio change between periods."""

    model_config = ConfigDict(extra="forbid")

    from_period: str
    to_period: str
    previous_ratio: str | None = None
    current_ratio: str | None = None
    change: str | None = None
    deteriorated: bool = False
    explanation: str = ""


class ContractWorkingCapitalChange(BaseModel):
    """Working capital change between periods."""

    model_config = ConfigDict(extra="forbid")

    from_period: str
    to_period: str
    previous_value: str | None = None
    current_value: str | None = None
    change: str | None = None
    explanation: str = ""


class ContractCashDebtChange(BaseModel):
    """Cash-to-debt ratio change between periods."""

    model_config = ConfigDict(extra="forbid")

    from_period: str
    to_period: str
    previous_ratio: str | None = None
    current_ratio: str | None = None
    change_pct: str | None = None
    weakened: bool = False
    explanation: str = ""


class ContractEquityChange(BaseModel):
    """Equity change between periods."""

    model_config = ConfigDict(extra="forbid")

    from_period: str
    to_period: str
    previous_value: str | None = None
    current_value: str | None = None
    change_pct: str | None = None
    eroded: bool = False
    explanation: str = ""


class ContractBalanceSheetQualityObservation(BaseModel):
    """Balance sheet quality observation."""

    model_config = ConfigDict(extra="forbid")

    observation_type: str
    symbol: str = Field(min_length=1)
    severity: str
    periods_covered: int = 0
    first_period: str = ""
    last_period: str = ""
    debt_comparisons: list[ContractDebtGrowthComparison] = []
    liquidity_changes: list[ContractLiquidityChange] = []
    working_capital_changes: list[ContractWorkingCapitalChange] = []
    cash_debt_changes: list[ContractCashDebtChange] = []
    equity_changes: list[ContractEquityChange] = []
    persistent: bool = False
    explanation: str = ""


class ContractFundamentalObservation(BaseModel):
    """One fundamental observation with provenance."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    category: str
    observation_type: str
    period: str
    metric: str
    value: str | None = None
    previous_value: str | None = None
    change: str | None = None
    change_pct: str | None = None
    calculation_method: str = ""
    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None
    available_at: str | None = None
    as_of: str | None = None
    status: str = "AVAILABLE"
    direction: str = "NEUTRAL"
    severity: str = "LOW"
    explanation: str = ""
    related_metrics: list[str] = []
    supporting_data: dict[str, str] = {}


class ContractFundamentalObservationSet(BaseModel):
    """Complete set of fundamental observations."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    trajectory_observations: list[ContractFundamentalObservation] = []
    earnings_quality_observations: list[ContractFundamentalObservation] = []
    balance_sheet_observations: list[ContractFundamentalObservation] = []
    anomaly_observations: list[ContractFundamentalObservation] = []
    total_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    coverage: dict[str, int] = {}
    notes: list[str] = []


class ContractDeepFundamentalResult(BaseModel):
    """Deep fundamental analysis result."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    period_count: int = 0
    first_period: str = ""
    last_period: str = ""
    trajectories: list[ContractTrajectoryAnalysis] = []
    margin_trajectories: list[ContractMarginTrajectory] = []
    leverage_trajectories: list[ContractLeverageTrajectory] = []
    earnings_quality_observations: list[ContractEarningsQualityObservation] = []
    balance_sheet_observations: list[ContractBalanceSheetQualityObservation] = []
    anomalies: list[ContractSignal] = []
    financial_trends: list[dict] = []
    observation_set: ContractFundamentalObservationSet | None = None
    available_analyses: list[str] = []
    missing_analyses: list[str] = []
    notes: list[str] = []
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0


class CompanyDeepFundamentalContract(BaseModel):
    """Deep fundamental research response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    deep_fundamentals: ContractDeepFundamentalResult


# =====================================================================
# Phase 4 Events contracts
# =====================================================================


class ContractEventClassification(BaseModel):
    """One classified event."""

    model_config = ConfigDict(extra="forbid")

    event_date: str
    category: str
    title: str
    description: str
    direction: str
    materiality: int = 0
    impact: str = "UNKNOWN"
    evidence_count: int = 0
    evidence_ids: list[str] = []


class ContractEventCluster(BaseModel):
    """A cluster of related events."""

    model_config = ConfigDict(extra="forbid")

    cluster_id: str = Field(min_length=1)
    category: str
    event_count: int = 0
    date_range: str = ""
    titles: list[str] = []
    overall_direction: str = "UNKNOWN"
    overall_materiality: int = 0
    explanation: str = ""


class ContractEventAnalysis(BaseModel):
    """Event analysis result."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    event_count: int = 0
    classifications: list[ContractEventClassification] = []
    clusters: list[ContractEventCluster] = []
    category_counts: dict[str, int] = {}
    direction_counts: dict[str, int] = {}
    coverage: dict[str, int] = {}
    notes: list[str] = []


class CompanyEventsContract(BaseModel):
    """Event analysis response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    events: ContractEventAnalysis


# =====================================================================
# Phase 4 Research Timeline contracts
# =====================================================================


class ContractResearchTimelineEntry(BaseModel):
    """One timeline entry."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(min_length=1)
    entry_type: str
    date: str
    title: str
    description: str
    direction: str
    materiality: int = 0
    category: str
    supporting_data: dict[str, str] = {}
    evidence_count: int = 0


class ContractResearchTimelineSummary(BaseModel):
    """Timeline summary statistics."""

    model_config = ConfigDict(extra="forbid")

    total_entries: int = 0
    event_count: int = 0
    price_count: int = 0
    ownership_count: int = 0
    management_count: int = 0
    volume_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    high_materiality_count: int = 0
    date_range: str = ""
    earliest_date: str = ""
    latest_date: str = ""


class ContractResearchTimeline(BaseModel):
    """Research timeline result."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    entries: list[ContractResearchTimelineEntry] = []
    summary: ContractResearchTimelineSummary
    notes: list[str] = []


class CompanyResearchTimelineContract(BaseModel):
    """Research timeline response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    timeline: ContractResearchTimeline


# =====================================================================
# Phase 4 Analyst Intelligence contracts
# =====================================================================


class ContractAnalystRecommendation(BaseModel):
    """One period of analyst recommendations."""

    model_config = ConfigDict(extra="forbid")

    period: str = Field(min_length=1)
    strong_buy: int = 0
    buy: int = 0
    hold: int = 0
    sell: int = 0
    strong_sell: int = 0
    total_analysts: int = 0
    consensus_score: str | None = None


class ContractAnalystRatingChange(BaseModel):
    """One analyst rating change event."""

    model_config = ConfigDict(extra="forbid")

    firm: str = Field(min_length=1)
    analyst_name: str | None = None
    action: str = Field(min_length=1)
    from_grade: str | None = None
    to_grade: str | None = None
    date: str | None = None


class ContractEarningsSurprise(BaseModel):
    """One historical earnings surprise."""

    model_config = ConfigDict(extra="forbid")

    period_ending: str | None = None
    reported_eps: str | None = None
    estimated_eps: str | None = None
    surprise_amount: str | None = None
    surprise_percentage: str | None = None
    beat_estimate: bool | None = None


class ContractCalendarEvent(BaseModel):
    """One upcoming or recent calendar event."""

    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1)
    event_date: str | None = None
    description: str | None = None


class ContractMarketValuation(BaseModel):
    """Market valuation data from Yahoo Finance."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    market_cap: str | None = None
    enterprise_value: str | None = None
    trailing_pe: str | None = None
    forward_pe: str | None = None
    peg_ratio: str | None = None
    price_to_book: str | None = None
    price_to_sales: str | None = None
    enterprise_to_revenue: str | None = None
    enterprise_to_ebitda: str | None = None
    dividend_yield: str | None = None
    trailing_annual_dividend_yield: str | None = None
    beta: str | None = None
    fifty_two_week_high: str | None = None
    fifty_two_week_low: str | None = None
    fifty_day_average: str | None = None
    two_hundred_day_average: str | None = None
    avg_volume_10d: str | None = None
    shares_outstanding: str | None = None
    float_shares: str | None = None


class ContractAnalystIntelligence(BaseModel):
    """Complete analyst intelligence result."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    has_recommendations: bool = False
    has_rating_changes: bool = False
    has_earnings_history: bool = False
    recommendations: list[ContractAnalystRecommendation] = []
    rating_changes: list[ContractAnalystRatingChange] = []
    earnings_surprises: list[ContractEarningsSurprise] = []
    calendar_events: list[ContractCalendarEvent] = []
    valuation: ContractMarketValuation | None = None
    recommendation_count: int = 0
    rating_change_count: int = 0
    earnings_surprise_count: int = 0
    calendar_event_count: int = 0


class CompanyAnalystIntelligenceContract(BaseModel):
    """Analyst intelligence response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    analyst_intelligence: ContractAnalystIntelligence


# =====================================================================
# Phase 4 Ownership contracts
# =====================================================================


class ContractOwnershipPeriod(BaseModel):
    """One ownership period breakdown."""

    model_config = ConfigDict(extra="forbid")

    period_end: str
    promoter_pct: str | None = None
    institutional_pct: str | None = None
    public_pct: str | None = None
    pledge_pct: str | None = None
    concentration_ratio: str | None = None
    coverage_pct: str | None = None
    evidence_count: int = 0


class ContractOwnershipTrend(BaseModel):
    """One ownership trend."""

    model_config = ConfigDict(extra="forbid")

    metric: str
    direction: str
    periods_analyzed: int = 0
    first_period: str = ""
    last_period: str = ""
    first_value: str | None = None
    last_value: str | None = None
    change: str | None = None
    change_pct: str | None = None
    min_value: str | None = None
    max_value: str | None = None
    explanation: str = ""


class ContractOwnershipSignal(BaseModel):
    """One ownership signal."""

    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(min_length=1)
    signal_type: str
    direction: str
    severity: str
    title: str
    description: str
    current_value: str | None = None
    previous_value: str | None = None
    change: str | None = None
    evidence_ids: list[str] = []
    explanation: str = ""


class ContractOwnershipAnalysis(BaseModel):
    """Ownership analysis result."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    snapshot_count: int = 0
    periods: list[ContractOwnershipPeriod] = []
    trends: list[ContractOwnershipTrend] = []
    signals: list[ContractOwnershipSignal] = []
    coverage: dict[str, int] = {}
    notes: list[str] = []


class CompanyOwnershipContract(BaseModel):
    """Ownership analysis response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    ownership: ContractOwnershipAnalysis


# =====================================================================
# Phase 4 Ownership Summary contracts
# =====================================================================


class ContractTopHolder(BaseModel):
    """One top shareholder."""

    model_config = ConfigDict(extra="forbid")

    holder_name: str = Field(min_length=1)
    holder_type: str = "INSTITUTIONAL"
    shares_held: str | None = None
    share_percentage: str | None = None
    date_reported: str | None = None


class ContractOwnershipSummary(BaseModel):
    """Ownership breakdown summary with top holders."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    period_end: str
    promoter_percentage: str | None = None
    institutional_percentage: str | None = None
    public_percentage: str | None = None
    insider_percentage: str | None = None
    top_holders: list[ContractTopHolder] = []
    has_top_holders: bool = False
    holder_count: int = 0


class CompanyOwnershipSummaryContract(BaseModel):
    """Ownership summary response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    ownership_summary: ContractOwnershipSummary


# ── F6 contracts (delegated to f6_contracts module) ──────────────
from src.api.f6_contracts import (  # noqa: E402, F401
    CompanyChartDataContract,
    CompanyCorporateActionsContract,
    CompanyIndustryContextContract,
    CompanyNewsContract,
    CompanyTrackingContract,
    ContractChartDataPoint,
    ContractChartDataSet,
    ContractChartSeries,
    ContractCompanyNewsItem,
    ContractCompanyNewsResult,
    ContractCorporateActionItem,
    ContractCorporateActionResult,
    ContractIndustryCharacteristic,
    ContractIndustryContextResult,
    ContractIndustryResearchQuestion,
    ContractTrackingChange,
    ContractTrackingResult,
)


__all__ = [
    # Existing L3 contracts
    "CompanyDiscoveryItem",
    "CompanyDiscoveryResponse",
    "CompanyIntelligenceContract",
    "CompanyRankingsContract",
    "CompanyResearchContract",
    "CompanyTimelineContract",
    "CompanyDeepFinancialInsightsContract",
    "CompanySourceStatusesContract",
    "CompanyHiddenInformationContract",
    "CompanyResearchGapsContract",
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
    "ContractResearchGap",
    "ContractResearchGaps",
    "ContractResearchStatus",
    "ContractSegment",
    "ContractSignal",
    "ContractSourceStatus",
    "ContractTimeline",
    "ContractTimelineEntry",
    "UniverseRankingsContract",
    # Phase 4 Technical
    "CompanyDeepTechnicalContract",
    "ContractDeepTechnicalResult",
    "ContractTechnicalIndicatorSet",
    "ContractTechnicalObservation",
    "ContractTechnicalObservationSet",
    # Phase 4 Attribution
    "CompanyAttributionContract",
    "ContractAttributionCandidate",
    "ContractPriceAttribution",
    "ContractPriceMove",
    # Phase 4 Business Intelligence
    "CompanyBusinessIntelligenceContract",
    "ContractBusinessAnalysis",
    "ContractBusinessDerivedObservation",
    "ContractBusinessIntelligence",
    "ContractBusinessQualitySignal",
    "ContractCapitalAllocationSignal",
    "ContractCompetitiveAnalysis",
    "ContractCompetitiveMetric",
    "ContractCompetitiveSignal",
    "ContractDerivedObservations",
    "ContractManagementAnalysis",
    "ContractManagementPattern",
    "ContractRiskAnalysis",
    "ContractRiskObservation",
    "ContractSegmentConcentration",
    "ContractSegmentShare",
    "ContractSegmentTrend",
    # Phase 4 Fundamentals
    "CompanyDeepFundamentalContract",
    "CompanyFinancialHistoryContract",
    "ContractBalanceSheetDeepObservation",
    "ContractBalanceSheetQualityObservation",
    "ContractCashDebtChange",
    "ContractCashProfitComparison",
    "ContractDebtGrowthComparison",
    "ContractDeepFundamentalResult",
    "ContractEarningsQualityObservation",
    "ContractEquityChange",
    "ContractFinancialHistory",
    "ContractFinancialMetric",
    "ContractFinancialPeriodDetail",
    "ContractFinancialRatio",
    "ContractFundamentalObservation",
    "ContractFundamentalObservationSet",
    "ContractGrowthDivergence",
    "ContractLeverageTrajectory",
    "ContractLiquidityChange",
    "ContractMarginTrajectory",
    "ContractPeriodGrowthRate",
    "ContractTrajectoryAnalysis",
    "ContractWorkingCapitalChange",
    # Phase 4 Events
    "CompanyEventsContract",
    "ContractEventAnalysis",
    "ContractEventClassification",
    "ContractEventCluster",
    # Phase 4 Timeline
    "CompanyResearchTimelineContract",
    "ContractResearchTimeline",
    "ContractResearchTimelineEntry",
    "ContractResearchTimelineSummary",
    # Phase 4 Analyst
    "CompanyAnalystIntelligenceContract",
    "ContractAnalystIntelligence",
    "ContractAnalystRatingChange",
    "ContractAnalystRecommendation",
    "ContractCalendarEvent",
    "ContractEarningsSurprise",
    "ContractMarketValuation",
    # Phase 4 Ownership
    "CompanyOwnershipContract",
    "CompanyOwnershipSummaryContract",
    "ContractOwnershipAnalysis",
    "ContractOwnershipPeriod",
    "ContractOwnershipSignal",
    "ContractOwnershipSummary",
    "ContractOwnershipTrend",
    "ContractTopHolder",
    # F6 — Chart Data
    "ContractChartDataPoint",
    "ContractChartSeries",
    "ContractChartDataSet",
    "CompanyChartDataContract",
    # F6 — Company News
    "ContractCompanyNewsItem",
    "ContractCompanyNewsResult",
    "CompanyNewsContract",
    # F6 — Corporate Actions
    "ContractCorporateActionItem",
    "ContractCorporateActionResult",
    "CompanyCorporateActionsContract",
    # F6 — Industry Context
    "ContractIndustryCharacteristic",
    "ContractIndustryResearchQuestion",
    "ContractIndustryContextResult",
    "CompanyIndustryContextContract",
    # F6 — Tracking
    "ContractTrackingChange",
    "ContractTrackingResult",
    "CompanyTrackingContract",
]
