"""
F8 — Professional Research Report API contracts.

Pydantic response models for the professional report endpoint.
These models describe evidence already produced by the research
engine. They never invent scores, evidence, or timing.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ContractF8ReportItem(BaseModel):
    """One item within a report section."""

    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    epistemic_type: str = "UNKNOWN"
    evidence_ids: list[str] = []
    source_ids: list[str] = []
    confidence: str = "0"
    observation_at: str | None = None
    metadata: dict[str, str] = {}


class ContractF8ReportSection(BaseModel):
    """One section of a professional research report."""

    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    status: str = "MISSING"
    epistemic_type: str = "UNKNOWN"
    items: list[ContractF8ReportItem] = []
    evidence_ids: list[str] = []
    source_ids: list[str] = []
    total_items: int = 0
    notes: list[str] = []
    metadata: dict[str, str] = {}


class ContractF7EvidenceItemSimple(BaseModel):
    """Simplified evidence item for evidence sections."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    evidence_type: str = ""
    direction: str = ""
    confidence: str = "0"
    reliability: str = ""
    epistemic_type: str = "UNKNOWN"
    verification_status: str = "UNVERIFIED"
    observation_at: str | None = None
    source_ids: list[str] = []


class ContractF8EvidenceSection(BaseModel):
    """Evidence classification section."""

    model_config = ConfigDict(extra="forbid")

    section_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    items: list[ContractF7EvidenceItemSimple] = []
    total_items: int = 0
    notes: list[str] = []


class ContractF8ConflictDetail(BaseModel):
    """Detailed evidence conflict with both sides."""

    model_config = ConfigDict(extra="forbid")

    conflict_id: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    description: str = Field(min_length=1)
    management_involved: bool = False
    first_item_id: str = ""
    first_title: str = ""
    first_direction: str = ""
    first_source: str = ""
    first_excerpt: str = ""
    second_item_id: str = ""
    second_title: str = ""
    second_direction: str = ""
    second_source: str = ""
    second_excerpt: str = ""


class ContractF8ExecutiveOverview(BaseModel):
    """Executive overview of the research evidence."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    company_name: str | None = None
    as_of: str | None = None

    evidence_direction: str = "UNKNOWN"
    evidence_direction_confidence: str = "0"

    total_evidence: int = 0
    positive_count: int = 0
    negative_count: int = 0
    conflicting_count: int = 0

    key_findings: list[ContractF8ReportItem] = []
    key_risks: list[ContractF8ReportItem] = []
    uncertainties: list[str] = []
    cannot_assess: list[str] = []
    what_changed: list[ContractF8ReportItem] = []
    hidden_insights: list[ContractF8ReportItem] = []


class ContractF8QualityIndicator(BaseModel):
    """One quality indicator."""

    model_config = ConfigDict(extra="forbid")

    indicator_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: str = "UNKNOWN"
    value: str = ""
    explanation: str = ""


class ContractF8QualityLayer(BaseModel):
    """Quality assessment of the report."""

    model_config = ConfigDict(extra="forbid")

    evidence_coverage_pct: str = "0"
    provenance_coverage_pct: str = "0"
    source_freshness_pct: str = "0"
    unresolved_conflict_count: int = 0
    critical_gap_count: int = 0
    stale_input_count: int = 0
    unsupported_dimension_count: int = 0
    pit_status: str = "UNKNOWN"
    indicators: list[ContractF8QualityIndicator] = []
    notes: list[str] = []


class ContractF8SourceHealthEntry(BaseModel):
    """Source health for one data source."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    source_type: str = ""
    tier: str = ""
    reliability_tier: str = "UNKNOWN"
    evidence_count: int = 0
    latest_observation: str | None = None
    freshness_status: str = "UNKNOWN"
    coverage_status: str = "UNKNOWN"
    stale: bool = False
    provenance_complete: bool = False
    categories: list[str] = []


class ContractF8SourceHealth(BaseModel):
    """Aggregate source health."""

    model_config = ConfigDict(extra="forbid")

    total_sources: int = 0
    healthy_sources: int = 0
    degraded_sources: int = 0
    missing_sources: int = 0
    stale_sources: int = 0
    entries: list[ContractF8SourceHealthEntry] = []
    provider_failures: list[str] = []
    notes: list[str] = []


class ContractF8ProvenanceChain(BaseModel):
    """Provenance chain."""

    model_config = ConfigDict(extra="forbid")

    total_provenance: int = 0
    with_available_at: int = 0
    with_published_at: int = 0
    records: list[dict] = []
    notes: list[str] = []


class ContractF8PITIntegrity(BaseModel):
    """PIT integrity check."""

    model_config = ConfigDict(extra="forbid")

    as_of: str
    effective_as_of: str | None = None
    market_as_of: str | None = None
    evidence_included: int = 0
    future_evidence_excluded: int = 0
    sources_discovered: int = 0
    sources_accepted: int = 0
    pit_checks_passed: bool = True
    notes: list[str] = []


class ContractF8Methodology(BaseModel):
    """Methodology and limitations."""

    model_config = ConfigDict(extra="forbid")

    methodology_summary: str = ""
    known_limitations: list[str] = []
    data_freshness_note: str = ""
    PIT_policy: str = ""
    epistemic_disclosure: str = ""
    notes: list[str] = []


class ContractF8ProfessionalReport(BaseModel):
    """
    Complete professional research report response.

    22 sections assembled from F7 evidence lineage.
    Every item carries epistemic type labeling.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str
    company_name: str | None = None
    report_version: str = "2.0"

    executive_overview: ContractF8ExecutiveOverview | None = None
    research_snapshot: ContractF8ReportSection | None = None
    business_context: ContractF8ReportSection | None = None
    financial_performance: ContractF8ReportSection | None = None
    financial_quality: ContractF8ReportSection | None = None
    market_context: ContractF8ReportSection | None = None
    business_developments: ContractF8ReportSection | None = None
    management_strategy: ContractF8ReportSection | None = None
    competitive_position: ContractF8ReportSection | None = None
    innovation: ContractF8ReportSection | None = None
    future_technology: ContractF8ReportSection | None = None
    industry_context: ContractF8ReportSection | None = None
    capital_allocation: ContractF8ReportSection | None = None
    corporate_actions: ContractF8ReportSection | None = None
    timeline: ContractF8ReportSection | None = None

    positive_evidence: ContractF8EvidenceSection | None = None
    negative_evidence: ContractF8EvidenceSection | None = None
    conflicting_evidence: ContractF8EvidenceSection | None = None
    conflict_details: list[ContractF8ConflictDetail] = []

    research_gaps: ContractF8ReportSection | None = None
    source_health: ContractF8SourceHealth | None = None
    provenance_chain: ContractF8ProvenanceChain | None = None
    pit_integrity: ContractF8PITIntegrity | None = None
    methodology: ContractF8Methodology | None = None

    quality_layer: ContractF8QualityLayer | None = None

    notes: list[str] = []


class CompanyProfessionalReportResponse(BaseModel):
    """Professional research report response wrapper."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    report: ContractF8ProfessionalReport


__all__ = [
    "CompanyProfessionalReportResponse",
    "ContractF8ConflictDetail",
    "ContractF8ExecutiveOverview",
    "ContractF8EvidenceSection",
    "ContractF8Methodology",
    "ContractF8PITIntegrity",
    "ContractF8ProvenanceChain",
    "ContractF8ProfessionalReport",
    "ContractF8QualityIndicator",
    "ContractF8QualityLayer",
    "ContractF8ReportItem",
    "ContractF8ReportSection",
    "ContractF8SourceHealth",
    "ContractF8SourceHealthEntry",
]
