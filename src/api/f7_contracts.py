"""
F7 — Canonical Evidence Lineage API contracts.

Pydantic response models for the evidence lineage endpoints.
These models describe evidence already produced by the research
engine. They never invent scores, evidence, or timing.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ContractF7EvidenceSource(BaseModel):
    """Source profile for one piece of evidence."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    tier: str
    domain: str | None = None
    official: bool = False
    requires_confirmation: bool = False
    reliability_tier: str = "UNKNOWN"


class ContractF7SourceRecord(BaseModel):
    """Provenance record for one piece of evidence."""

    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    source_url: str | None = None
    retrieved_at: str | None = None
    published_at: str | None = None
    available_at: str | None = None
    dataset_id: str | None = None
    record_id: str | None = None
    checksum: str | None = None


class ContractF7EvidenceItem(BaseModel):
    """Canonical evidence item with full lineage."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)

    evidence_type: str
    direction: str
    confidence: str
    reliability: str

    epistemic_type: str = "UNKNOWN"
    verification_status: str = "UNVERIFIED"

    observation_at: str | None = None
    published_at: str | None = None
    available_at: str | None = None

    source_ids: list[str] = []
    provenance_ids: list[str] = []

    source: ContractF7EvidenceSource | None = None
    source_records: list[ContractF7SourceRecord] = []

    category: str = ""
    topic: str | None = None
    derivation: str | None = None


class ContractF7Claim(BaseModel):
    """A traceable claim linked to evidence items."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    text: str = Field(min_length=1)
    category: str = Field(min_length=1)

    epistemic_type: str = "UNKNOWN"
    confidence: str = "0"
    verification_status: str = "UNVERIFIED"

    evidence_ids: list[str] = []
    source_ids: list[str] = []
    observation_at: str | None = None


class ContractF7EvidenceLineage(BaseModel):
    """Complete evidence lineage for one company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: str

    evidence: list[ContractF7EvidenceItem] = []
    claims: list[ContractF7Claim] = []

    source_profiles: list[ContractF7EvidenceSource] = []
    source_records: list[ContractF7SourceRecord] = []

    epistemic_type_counts: dict[str, int] = {}
    verification_status_counts: dict[str, int] = {}
    evidence_type_counts: dict[str, int] = {}
    direction_counts: dict[str, int] = {}

    total_evidence: int = 0
    total_claims: int = 0
    total_sources: int = 0
    total_provenance: int = 0

    pit_filtered_count: int = 0
    notes: list[str] = []


class CompanyEvidenceContract(BaseModel):
    """Evidence lineage response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    evidence_lineage: ContractF7EvidenceLineage | None = None


class CompanyEvidenceDetailContract(BaseModel):
    """Single evidence item with related claims and lineage detail."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    evidence_item: ContractF7EvidenceItem
    related_claims: list[ContractF7Claim] = []
    related_evidence: list[ContractF7EvidenceItem] = []


__all__ = [
    "CompanyEvidenceContract",
    "CompanyEvidenceDetailContract",
    "ContractF7Claim",
    "ContractF7EvidenceItem",
    "ContractF7EvidenceLineage",
    "ContractF7EvidenceSource",
    "ContractF7SourceRecord",
]
