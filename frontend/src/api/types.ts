/**
 * TypeScript types mirroring the L3 /api/v1 production research contract.
 *
 * These shapes are intentionally faithful to the backend Pydantic response
 * models: numeric scores arrive as decimal strings, timestamps as ISO 8601.
 */

export type SignalDirection = "POSITIVE" | "NEGATIVE" | "NEUTRAL"

export interface ContractEvidence {
  evidence_id: string
  title: string
  explanation: string
  symbol: string
  evidence_type: string
  direction: SignalDirection
  confidence: string
  reliability: string
  observation_at: string
  source_ids: string[]
  provenance_ids: string[]
}

export interface IntelligenceSection {
  status: string
  confidence: string
  observations: string[]
  unknown: string[]
  positive_count: number
  negative_count: number
  source_ids: string[]
  provenance_ids: string[]
}

export interface Intelligence {
  business_quality: IntelligenceSection | null
  financial_quality: IntelligenceSection | null
  transformation: IntelligenceSection | null
  capital_allocation: IntelligenceSection | null
  competitive_position: IntelligenceSection | null
  innovation: IntelligenceSection | null
  future_technology: IntelligenceSection | null
  customer_intelligence: IntelligenceSection | null
  management_intelligence: IntelligenceSection | null
  market_intelligence: IntelligenceSection | null
  risks_anomalies: IntelligenceSection | null
  unknown_missing: string[]
}

export interface ContractSignal {
  signal_id: string
  category: string
  direction: SignalDirection
  severity: string
  confidence: string
  title: string
  explanation: string
  symbol: string
  observation_at: string
  supporting_features: string[]
  supporting_metrics: string[]
}

export interface PointInTime {
  as_of: string
  effective_as_of: string
  market_as_of: string | null
  evidence_included: number
  acquired_evidence_included: number
  future_evidence_excluded: number
  sources_discovered: number
  sources_accepted: number
  sources_rejected: number
  pit_checks_passed: boolean
  notes: string[]
}

export interface DataQuality {
  market_validation_status: string
  market_accepted_records: number
  market_rejected_records: number
  financial_record_count: number
  financial_data_missing: boolean
  feature_statuses: Record<string, string>
  context: Record<string, number>
  provenance_completeness: Record<string, boolean | number>
  warnings: string[]
  provider_failures: string[]
}

export interface ProvenanceRecord {
  source: string
  dataset_id: string | null
  record_id: string | null
  retrieved_at: string | null
  available_at: string | null
}

export interface Provenance {
  market: ProvenanceRecord
  financials: ProvenanceRecord
  archived_sources: string[]
}

export interface Assessment {
  conclusion: string
  confidence: string
  thesis: string
  conflict_detected: boolean
  direction: string
  research_ready: boolean
}

export interface EvidenceSummary {
  positive: ContractEvidence[]
  negative: ContractEvidence[]
  neutral: ContractEvidence[]
  conflict_detected: boolean
  direction: string
  positive_count: number
  negative_count: number
  neutral_count: number
  positive_weight: string
  negative_weight: string
  average_confidence: string
  weighted_confidence: string
}

export interface Narrative {
  thesis: string
  supporting_evidence: string[]
  contradicting_evidence: string[]
  strongest_evidence: string[]
  uncertainty: string[]
  key_risks: string[]
  evidence_gaps: string[]
  what_could_change_thesis: string[]
  has_conflict: boolean
}

export interface Ranking {
  symbol: string
  company_name: string | null
  horizon: string
  score: string
  signal: string
  confidence: string
  coverage: string
  missing_components: string[]
  components: Record<string, string>
}

export interface ResearchScore {
  total: string
  signal: string
  confidence: string
  components: Record<string, string>
}

export type IntelCategory =
  | "FINANCIAL_DISCLOSURE"
  | "BUSINESS_NEWS"
  | "MANAGEMENT_STATEMENT"
  | "CORPORATE_ACTION"
  | "REGULATORY_LEGAL"
  | "EXECUTIVE_CHANGE"
  | "ORDER_CONTRACT"
  | "ACQUISITION_DIVESTMENT"
  | "CAPEX_EXPANSION"
  | "PRODUCT_BUSINESS_UPDATE"
  | "SUBSIDIARY_UPDATE"
  | "SEGMENT_UPDATE"
  | "OWNERSHIP_DISCLOSURE"
  | "INSIDER_ACTIVITY"
  | "CONFERENCE_CALL"
  | "INVESTOR_PRESENTATION"
  | "CREDIT_RATING_ACTION"
  | "LEGAL_PROCEEDING"
  | "FORECAST_GUIDANCE"
  | "OTHER"

export interface TimelineSource {
  source_name: string
  source_type: string
  source_url: string | null
  reliability_tier: number
  provenance_id: string | null
}

export interface TimelineEntry {
  entry_id: string
  symbol: string
  kind: string
  intel_category: IntelCategory
  semantic_category: string
  verification_status: string
  event_type: string | null
  topic: string | null
  title: string
  description: string
  stance: string
  direction: string
  published_at: string | null
  available_at: string | null
  effective_at: string | null
  timeline_at: string | null
  source: TimelineSource
  provenance_id: string | null
  checksum: string
}

export interface CompanyTimeline {
  company: string
  as_of: string
  entries: TimelineEntry[]
  counts: Record<string, number>
  latest_at: string | null
  earliest_at: string | null
  notes: string[]
}

export interface ResearchFreshness {
  latest_published_at: string | null
  latest_available_at: string | null
  latest_effective_at: string | null
  oldest_published_at: string | null
  oldest_available_at: string | null
  oldest_effective_at: string | null
  days_since_latest_published: number | null
  days_since_latest_available: number | null
  stale: boolean
  notes: string[]
}

export interface ResearchCoverage {
  item_count: number
  by_kind: Record<string, number>
  by_category: Record<string, number>
  by_semantic: Record<string, number>
  by_status: Record<string, number>
  missing_categories: string[]
  notes: string[]
}

export interface ResearchQuality {
  conflict_count: number
  evidence_link_count: number
  deduplicated_count: number
  source_id_count: number
  provenance_id_count: number
  insufficient_evidence_notes: string[]
  notes: string[]
}

export interface ResearchStatus {
  company: string
  as_of: string
  freshness: ResearchFreshness
  coverage: ResearchCoverage
  quality: ResearchQuality
}

export interface CompanyResearch {
  company: {
    symbol: string
    company_name: string | null
    sector: string | null
    as_of: string
  }
  assessment: Assessment
  point_in_time: PointInTime
  intelligence: Intelligence
  evidence: EvidenceSummary
  narrative: Narrative | null
  signals: ContractSignal[]
  data_quality: DataQuality
  provenance: Provenance
  timeline: CompanyTimeline | null
  research_status: ResearchStatus | null
  deep_financial_insights: DeepFinancialInsights | null
  source_statuses: SourceStatus[]
  hidden_information: HiddenInformation | null
  provider_failures: string[]
  rankings: Record<string, Ranking>
  research_score: ResearchScore
}

export interface CompanyTimelineResponse {
  company: {
    symbol: string
    company_name: string | null
    sector: string | null
    as_of: string
  }
  timeline: CompanyTimeline
}

export interface CompanyRankings {
  symbol: string
  company_name: string | null
  as_of: string
  point_in_time: PointInTime
  rankings: Record<string, Ranking>
}

export interface UniverseRankings {
  as_of: string
  horizon: string
  count: number
  point_in_time: PointInTime
  results: Ranking[]
}

export interface DiscoveryItem {
  symbol: string
  company_name: string | null
  sector: string
  research_available: boolean
}

export interface DiscoveryResponse {
  count: number
  results: DiscoveryItem[]
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details: Record<string, unknown>
  }
}

// ── Deep continuous research layer ──────────────────────────────

export interface DeepMetricObservation {
  observation_id: string
  symbol: string
  metric: string
  period_id: string
  period_end: string
  period_type: string
  consolidation: string
  observation_type: string
  value: string | null
  previous_value: string | null
  delta: string | null
  delta_pct: string | null
  derivation: string | null
  published_at: string | null
  available_at: string | null
  provenance_id: string | null
}

export interface DeepFinancialSeries {
  series_id: string
  symbol: string
  period_type: string
  consolidation: string
  period_count: number
  period_ends: string[]
  metrics: string[]
}

export interface DeepFinancialInsights {
  symbol: string
  as_of: string
  series: DeepFinancialSeries[]
  observations: DeepMetricObservation[]
  comparability_notes: string[]
  financial_type_counts: Record<string, number>
}

export interface SourceStatus {
  source_name: string
  source_type: string
  item_count: number
  categories: string[]
  latest_published_at: string | null
  latest_available_at: string | null
  days_since_latest_published: number | null
  stale: boolean
  provenance_completeness: boolean
  notes: string[]
}

export interface DerivedObservation {
  observation_id: string
  symbol: string
  label: string
  semantic_category: string
  description: string
  derivation: string
  source_ids: string[]
  provenance_ids: string[]
  related_item_ids: string[]
  as_of: string
}

export interface HiddenInformation {
  symbol: string
  as_of: string
  observations: DerivedObservation[]
  notes: string[]
}

export interface CompanyDeepFinancialResponse {
  company: {
    symbol: string
    company_name: string | null
    sector: string | null
    as_of: string
  }
  deep_financial_insights: DeepFinancialInsights | null
}

export interface CompanySourceStatusesResponse {
  company: {
    symbol: string
    company_name: string | null
    sector: string | null
    as_of: string
  }
  source_statuses: SourceStatus[]
}

export interface CompanyHiddenInformationResponse {
  company: {
    symbol: string
    company_name: string | null
    sector: string | null
    as_of: string
  }
  hidden_information: HiddenInformation | null
}
