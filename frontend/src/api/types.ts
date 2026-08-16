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
  rankings: Record<string, Ranking>
  research_score: ResearchScore
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
