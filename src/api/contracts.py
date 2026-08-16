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


__all__ = [
    "CompanyDiscoveryItem",
    "CompanyDiscoveryResponse",
    "CompanyRankingsContract",
    "CompanyResearchContract",
    "ContractAssessment",
    "ContractDataQuality",
    "ContractEvidence",
    "ContractEvidenceSummary",
    "ContractIntelligence",
    "ContractIntelligenceSection",
    "ContractNarrative",
    "ContractPointInTime",
    "ContractProvenance",
    "ContractProvenanceRecord",
    "ContractRanking",
    "ContractSignal",
    "UniverseRankingsContract",
]
