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
    CompanyResearchStatus,
    CompanyTimeline,
    ConflictSide,
    CorporateIntelItem,
    CoverageStatus,
    EvidenceConflict,
    EvidenceLink,
    FinancialIntelligence,
    FinancialPeriod,
    FinancialStatement,
    FreshnessStatus,
    IntelCandidate,
    IntelChange,
    QualityStatus,
    SegmentResult,
    SnapshotDiff,
    SourceRef,
    TimelineEntry,
    UpdateEngineStatus,
)
from src.research.company_intel.quality import (
    build_coverage_status,
    build_freshness,
    build_quality_status,
    build_research_status,
)
from src.research.company_intel.semantics import (
    BusinessEventType,
    ChangeType,
    ConclusionGateResult,
    ConsolidationScope,
    EvidenceRelationship,
    EvidenceStance,
    FinancialStatementType,
    IntelCategory,
    IntelDirection,
    IntelKind,
    ReportingPeriodType,
    SemanticCategory,
    VerificationStatus,
    default_intel_category,
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
from src.research.company_intel.timeline import (
    build_timeline,
    timeline_at,
    timeline_entry_from_item,
)
from src.research.company_intel.update import (
    PeriodicUpdateEngine,
    PeriodicUpdateResult,
)

__all__ = [
    "BusinessEventType",
    "ChangeType",
    "CompanyIntelligenceSnapshot",
    "CompanyResearchStatus",
    "CompanyTimeline",
    "ConclusionGateResult",
    "ConflictSide",
    "ConsolidationScope",
    "CorporateIntelItem",
    "CoverageStatus",
    "EvidenceConflict",
    "EvidenceLink",
    "EvidenceRelationship",
    "EvidenceStance",
    "FinancialIntelligence",
    "FinancialPeriod",
    "FinancialStatement",
    "FinancialStatementType",
    "FreshnessStatus",
    "IntelCandidate",
    "IntelCategory",
    "IntelChange",
    "IntelDirection",
    "IntelExtractor",
    "IntelKind",
    "IntelSourceProvider",
    "IntelSourceValidator",
    "PeriodicUpdateEngine",
    "PeriodicUpdateResult",
    "QualityStatus",
    "RecordedIntelSourceProvider",
    "ReportingPeriodType",
    "SegmentResult",
    "SemanticCategory",
    "SnapshotDiff",
    "SourceRef",
    "TimelineEntry",
    "UpdateEngineStatus",
    "VerificationStatus",
    "build_company_intelligence_snapshot",
    "build_coverage_status",
    "build_evidence_links",
    "build_financial_intelligence",
    "build_freshness",
    "build_quality_status",
    "build_research_status",
    "build_timeline",
    "candidate_to_raw_record",
    "change_counts",
    "classify_semantic_category",
    "conclusion_gate",
    "deduplicate_candidates",
    "default_intel_category",
    "derived_metric_items",
    "detect_changes",
    "detect_evidence_conflicts",
    "financial_periods_from_snapshots",
    "financial_periods_to_items",
    "insufficient_evidence_message",
    "intel_items_from_observations",
    "item_checksum",
    "timeline_at",
    "timeline_entry_from_item",
]
