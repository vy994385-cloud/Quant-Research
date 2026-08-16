"""
Deep company research & continuous intelligence.

This package is the evidence-based "L5" foundation for company
intelligence. It models semantic categories, verification statuses,
evidence conflicts, point-in-time financial intelligence, and a
provider-driven periodic update engine.

It deliberately contains no scores, no recommendations, and no
predictions of future returns. It only organizes evidence.
"""

from src.research.company_intel.build import (
    build_company_intelligence_snapshot,
    build_financial_intelligence,
    classify_semantic_category,
    derived_metric_items,
    financial_periods_from_snapshots,
    financial_periods_to_items,
    intel_items_from_observations,
    item_checksum,
)
from src.research.company_intel.change import (
    change_counts,
    detect_changes,
)
from src.research.company_intel.evidence import (
    build_evidence_links,
    conclusion_gate,
    detect_evidence_conflicts,
)
from src.research.company_intel.models import (
    CompanyIntelligenceSnapshot,
    ConflictSide,
    CorporateIntelItem,
    EvidenceConflict,
    EvidenceLink,
    FinancialIntelligence,
    FinancialPeriod,
    FinancialStatement,
    IntelCandidate,
    IntelChange,
    SegmentResult,
    SnapshotDiff,
    SourceRef,
    UpdateEngineStatus,
)
from src.research.company_intel.semantics import (
    BusinessEventType,
    ChangeType,
    ConclusionGateResult,
    ConsolidationScope,
    EvidenceRelationship,
    EvidenceStance,
    FinancialStatementType,
    IntelDirection,
    IntelKind,
    ReportingPeriodType,
    SemanticCategory,
    VerificationStatus,
    insufficient_evidence_message,
)
from src.research.company_intel.sources import (
    IntelExtractor,
    IntelSourceProvider,
    IntelSourceValidator,
    RecordedIntelSourceProvider,
    candidate_to_raw_record,
    deduplicate_candidates,
)
from src.research.company_intel.update import (
    PeriodicUpdateEngine,
    PeriodicUpdateResult,
)

__all__ = [
    "BusinessEventType",
    "ChangeType",
    "CompanyIntelligenceSnapshot",
    "ConclusionGateResult",
    "ConflictSide",
    "ConsolidationScope",
    "CorporateIntelItem",
    "EvidenceConflict",
    "EvidenceLink",
    "EvidenceRelationship",
    "EvidenceStance",
    "FinancialIntelligence",
    "FinancialPeriod",
    "FinancialStatement",
    "FinancialStatementType",
    "IntelCandidate",
    "IntelChange",
    "IntelDirection",
    "IntelExtractor",
    "IntelKind",
    "IntelSourceProvider",
    "IntelSourceValidator",
    "PeriodicUpdateEngine",
    "PeriodicUpdateResult",
    "RecordedIntelSourceProvider",
    "ReportingPeriodType",
    "SegmentResult",
    "SemanticCategory",
    "SnapshotDiff",
    "SourceRef",
    "UpdateEngineStatus",
    "VerificationStatus",
    "build_company_intelligence_snapshot",
    "build_evidence_links",
    "build_financial_intelligence",
    "candidate_to_raw_record",
    "change_counts",
    "classify_semantic_category",
    "conclusion_gate",
    "deduplicate_candidates",
    "derived_metric_items",
    "detect_changes",
    "detect_evidence_conflicts",
    "financial_periods_from_snapshots",
    "financial_periods_to_items",
    "insufficient_evidence_message",
    "intel_items_from_observations",
    "item_checksum",
]
