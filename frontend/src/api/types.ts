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

// ── Cross-domain intelligence ────────────────────────────────────

export interface CrossDomainObservation {
  observation_id: string
  symbol: string
  label: string
  semantic_category: string
  description: string

  domain_1_name: string
  domain_1_metric: string
  domain_1_value: string | null
  domain_1_direction: string

  domain_2_name: string
  domain_2_metric: string
  domain_2_value: string | null
  domain_2_direction: string

  relationship: string
  direction: string
  limitations: string[]

  calculation_inputs: Record<string, object>
  methodology: string
  confidence: string | null
  severity: string
  as_of: string

  source_name: string | null
  related_metrics: string[]
  supporting_data: Record<string, string>
}

export interface CrossDomain {
  symbol: string
  as_of: string
  observation_count: number
  observations: CrossDomainObservation[]
  positive_count: number
  negative_count: number
  mixed_count: number
  neutral_count: number
  notes: string[]
}

export interface CompanyCrossDomainResponse {
  company: {
    symbol: string
    company_name: string | null
    sector: string | null
    as_of: string
  }
  cross_domain: CrossDomain | null
}

// ── F6: Company news ────────────────────────────────────────────

export interface CompanyNewsItem {
  news_id: string
  symbol: string
  headline: string
  summary: string
  category: string
  direction: string
  source_name: string
  source_url: string
  source_type: string
  published_at: string | null
  available_at: string | null
  event_date: string | null
  related_metrics: string[]
  evidence_refs: string[]
  as_of: string | null
  provenance_id: string | null
}

export interface CompanyNewsResult {
  symbol: string
  as_of: string
  items: CompanyNewsItem[]
  item_count: number
  category_counts: Record<string, number>
  source_count: number
  source_names: string[]
  notes: string[]
}

export interface CompanyNewsResponse {
  company: {
    symbol: string
    company_name: string | null
    sector: string | null
    as_of: string
  }
  news: CompanyNewsResult | null
}

// ── F6: Corporate actions ───────────────────────────────────────

export interface CorporateActionItem {
  action_id: string
  symbol: string
  action_type: string
  title: string
  description: string
  announcement_date: string | null
  effective_date: string | null
  record_date: string | null
  value: string | null
  ratio: string | null
  source_name: string
  source_url: string
  provenance_id: string | null
  published_at: string | null
  available_at: string | null
  as_of: string | null
}

export interface CorporateActionResult {
  symbol: string
  as_of: string
  items: CorporateActionItem[]
  item_count: number
  type_counts: Record<string, number>
  source_count: number
  notes: string[]
}

export interface CompanyCorporateActionsResponse {
  company: {
    symbol: string
    company_name: string | null
    sector: string | null
    as_of: string
  }
  corporate_actions: CorporateActionResult | null
}

// ── Research gaps intelligence ────────────────────────────────

export interface ResearchGap {
  gap_id: string
  symbol: string
  category: string
  description: string
  status: string
  severity: string
  reason: string
  suggested_action: string
  sources_checked: string[]
  evidence_refs: string[]
  related_metrics: string[]
  supporting_data: Record<string, string>
  as_of: string
}

export interface ResearchGaps {
  symbol: string
  as_of: string
  gap_count: number
  gaps: ResearchGap[]
  status_counts: Record<string, number>
  category_counts: Record<string, number>
  coverage_score: string | null
  coverage_explanation: string
  notes: string[]
}

export interface CompanyResearchGapsResponse {
  company: {
    symbol: string
    company_name: string | null
    sector: string | null
    as_of: string
  }
  research_gaps: ResearchGaps | null
}

// ── Deep technicals ──────────────────────────────────────────────

export interface TechnicalIndicatorSet {
  // Returns
  return_1d: string | null
  return_5d: string | null
  return_10d: string | null
  return_20d: string | null
  return_50d: string | null
  return_100d: string | null
  return_200d: string | null
  // SMAs
  sma_5: string | null
  sma_10: string | null
  sma_20: string | null
  sma_50: string | null
  sma_100: string | null
  sma_200: string | null
  // EMAs
  ema_9: string | null
  ema_12: string | null
  ema_20: string | null
  ema_26: string | null
  ema_50: string | null
  ema_200: string | null
  // Price vs MAs
  price_vs_sma_5_pct: string | null
  price_vs_sma_20_pct: string | null
  price_vs_sma_50_pct: string | null
  price_vs_ema_9_pct: string | null
  price_vs_ema_20_pct: string | null
  price_vs_ema_50_pct: string | null
  // RSI
  rsi_14: string | null
  rsi_signal: string | null
  // MACD
  macd_line: string | null
  macd_signal_line: string | null
  macd_histogram: string | null
  macd_crossover: string | null
  // Stochastic
  stochastic_k: string | null
  stochastic_d: string | null
  stochastic_signal: string | null
  // Williams %R
  williams_r_14: string | null
  williams_r_signal: string | null
  // ATR
  atr_14: string | null
  atr_pct: string | null
  // Bollinger Bands
  bollinger_upper: string | null
  bollinger_middle: string | null
  bollinger_lower: string | null
  bollinger_bandwidth: string | null
  bollinger_pct_b: string | null
  bollinger_signal: string | null
  // ADX
  adx_14: string | null
  adx_plus_di: string | null
  adx_minus_di: string | null
  adx_signal: string | null
  // CCI
  cci_20: string | null
  cci_signal: string | null
  // Volume
  obv: number | null
  ad_line: number | null
  mfi_14: string | null
  mfi_signal: string | null
  price_volume_divergence: string | null
  // Pivots
  pivot: string | null
  r1: string | null
  r2: string | null
  r3: string | null
  s1: string | null
  s2: string | null
  s3: string | null
  // Breakout
  breakout_signal: string | null
  // Gaps
  gap_type: string | null
  gap_pct: string | null
  // 52-week
  high_52w: string | null
  low_52w: string | null
  pct_from_52w_high: string | null
  pct_from_52w_low: string | null
  high_low_signal: string | null
  // Drawdowns
  current_drawdown: string | null
  max_drawdown_20d: string | null
  recovery_pct: string | null
  // Trend
  regime: string | null
  trend_strength: string | null
  sma_alignment: string | null
  ema_alignment: string | null
}

export interface TechnicalObservation {
  observation_id: string
  symbol: string
  category: string
  observation_type: string
  indicator: string
  period: string
  value: string
  signal: string
  direction: string
  severity: string
  explanation: string
  source: string
  available_at: string | null
  as_of: string | null
  status: string
  supporting_data: Record<string, string>
}

export interface TechnicalObservationSet {
  symbol: string
  as_of: string
  trading_date: string
  indicator_observations: TechnicalObservation[]
  signal_observations: TechnicalObservation[]
  total_count: number
  positive_count: number
  negative_count: number
  neutral_count: number
  available_indicators: string[]
  missing_indicators: string[]
}

export interface DeepTechnicalResult {
  symbol: string
  as_of: string
  trading_date: string
  bars_used: number
  indicators: TechnicalIndicatorSet | null
  observation_set: TechnicalObservationSet | null
  available_indicators: string[]
  missing_indicators: string[]
  notes: string[]
}

export interface CompanyDeepTechnicalResponse {
  company: {
    symbol: string
    name: string
  }
  deep_technicals: DeepTechnicalResult
}

// ── F7 — Evidence Lineage ─────────────────────────────────────

export interface F7EvidenceSource {
  source_id: string
  name: string
  source_type: string
  tier: string
  domain: string | null
  official: boolean
  requires_confirmation: boolean
  reliability_tier: string
}

export interface F7SourceRecord {
  source: string
  source_url: string | null
  retrieved_at: string | null
  published_at: string | null
  available_at: string | null
  dataset_id: string | null
  record_id: string | null
  checksum: string | null
}

export interface F7EvidenceItem {
  evidence_id: string
  symbol: string
  title: string
  explanation: string
  evidence_type: string
  direction: string
  confidence: string
  reliability: string
  epistemic_type: string
  verification_status: string
  observation_at: string | null
  published_at: string | null
  available_at: string | null
  source_ids: string[]
  provenance_ids: string[]
  source: F7EvidenceSource | null
  source_records: F7SourceRecord[]
  category: string
  topic: string | null
  derivation: string | null
}

export interface F7Claim {
  claim_id: string
  symbol: string
  text: string
  category: string
  epistemic_type: string
  confidence: string
  verification_status: string
  evidence_ids: string[]
  source_ids: string[]
  observation_at: string | null
}

export interface F7EvidenceLineage {
  symbol: string
  as_of: string
  evidence: F7EvidenceItem[]
  claims: F7Claim[]
  source_profiles: F7EvidenceSource[]
  source_records: F7SourceRecord[]
  epistemic_type_counts: Record<string, number>
  verification_status_counts: Record<string, number>
  evidence_type_counts: Record<string, number>
  direction_counts: Record<string, number>
  total_evidence: number
  total_claims: number
  total_sources: number
  total_provenance: number
  pit_filtered_count: number
  notes: string[]
}

export interface CompanyEvidenceResponse {
  company: {
    symbol: string
    company_name: string | null
    sector: string | null
    as_of: string
  }
  evidence_lineage: F7EvidenceLineage | null
}

export interface PriceHistoryBar {
  trading_date: string
  open: string
  high: string
  low: string
  close: string
  volume: number
  adjusted_close: string | null
}

export interface PriceHistoryResponse {
  symbol: string
  as_of: string
  bars: PriceHistoryBar[]
  bars_returned: number
  history_start: string | null
  history_end: string | null
  price_basis: string
}

// ── F8 — Professional Research Report ─────────────────────────

export interface F8ReportItem {
  item_id: string
  text: string
  epistemic_type: string
  evidence_ids: string[]
  source_ids: string[]
  confidence: string
  observation_at: string | null
  metadata: Record<string, string>
}

export interface F8ReportSection {
  section_id: string
  title: string
  status: string
  epistemic_type: string
  items: F8ReportItem[]
  evidence_ids: string[]
  source_ids: string[]
  total_items: number
  notes: string[]
  metadata: Record<string, string>
}

export interface F8EvidenceItemSimple {
  evidence_id: string
  symbol: string
  title: string
  explanation: string
  evidence_type: string
  direction: string
  confidence: string
  reliability: string
  epistemic_type: string
  verification_status: string
  observation_at: string | null
  source_ids: string[]
}

export interface F8EvidenceSection {
  section_id: string
  title: string
  items: F8EvidenceItemSimple[]
  total_items: number
  notes: string[]
}

export interface F8ConflictDetail {
  conflict_id: string
  topic: string
  description: string
  management_involved: boolean
  first_item_id: string
  first_title: string
  first_direction: string
  first_source: string
  first_excerpt: string
  second_item_id: string
  second_title: string
  second_direction: string
  second_source: string
  second_excerpt: string
}

export interface F8ExecutiveOverview {
  symbol: string
  company_name: string | null
  as_of: string | null
  evidence_direction: string
  evidence_direction_confidence: string
  total_evidence: number
  positive_count: number
  negative_count: number
  conflicting_count: number
  key_findings: F8ReportItem[]
  key_risks: F8ReportItem[]
  uncertainties: string[]
  cannot_assess: string[]
  what_changed: F8ReportItem[]
  hidden_insights: F8ReportItem[]
}

export interface F8QualityIndicator {
  indicator_id: string
  name: string
  status: string
  value: string
  explanation: string
}

export interface F8QualityLayer {
  evidence_coverage_pct: string
  provenance_coverage_pct: string
  source_freshness_pct: string
  unresolved_conflict_count: number
  critical_gap_count: number
  stale_input_count: number
  unsupported_dimension_count: number
  pit_status: string
  indicators: F8QualityIndicator[]
  notes: string[]
}

export interface F8SourceHealthEntry {
  source_id: string
  name: string
  source_type: string
  tier: string
  reliability_tier: string
  evidence_count: number
  latest_observation: string | null
  freshness_status: string
  coverage_status: string
  stale: boolean
  provenance_complete: boolean
  categories: string[]
}

export interface F8SourceHealth {
  total_sources: number
  healthy_sources: number
  degraded_sources: number
  missing_sources: number
  stale_sources: number
  entries: F8SourceHealthEntry[]
  provider_failures: string[]
  notes: string[]
}

export interface F8PITIntegrity {
  as_of: string
  effective_as_of: string | null
  market_as_of: string | null
  evidence_included: number
  future_evidence_excluded: number
  sources_discovered: number
  sources_accepted: number
  pit_checks_passed: boolean
  notes: string[]
}

export interface F8Methodology {
  methodology_summary: string
  known_limitations: string[]
  data_freshness_note: string
  PIT_policy: string
  epistemic_disclosure: string
  notes: string[]
}

export interface F8ProfessionalReport {
  symbol: string
  as_of: string
  company_name: string | null
  report_version: string
  executive_overview: F8ExecutiveOverview | null
  research_snapshot: F8ReportSection | null
  business_context: F8ReportSection | null
  financial_performance: F8ReportSection | null
  financial_quality: F8ReportSection | null
  market_context: F8ReportSection | null
  business_developments: F8ReportSection | null
  management_strategy: F8ReportSection | null
  competitive_position: F8ReportSection | null
  innovation: F8ReportSection | null
  future_technology: F8ReportSection | null
  industry_context: F8ReportSection | null
  capital_allocation: F8ReportSection | null
  corporate_actions: F8ReportSection | null
  timeline: F8ReportSection | null
  positive_evidence: F8EvidenceSection | null
  negative_evidence: F8EvidenceSection | null
  conflicting_evidence: F8EvidenceSection | null
  conflict_details: F8ConflictDetail[]
  research_gaps: F8ReportSection | null
  source_health: F8SourceHealth | null
  provenance_chain: { total_provenance: number; notes: string[] } | null
  pit_integrity: F8PITIntegrity | null
  methodology: F8Methodology | null
  quality_layer: F8QualityLayer | null
  notes: string[]
}

export interface CompanyProfessionalReportResponse {
  company: {
    symbol: string
    company_name: string | null
    sector: string | null
    as_of: string
  }
  report: F8ProfessionalReport
}
