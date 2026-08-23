"""
Canonical evidence and lineage models.

Provides the epistemic type vocabulary and lineage resolution
functions that both the Evidence Explorer frontend and the
Professional Reports module consume.

The models here are descriptive. They never produce scores,
rankings, recommendations, or investment conclusions.
"""

from src.research.evidence.lineage import (
    build_evidence_lineage,
    filter_evidence_by_pit,
    resolve_source_profile,
    resolve_source_records,
)
from src.research.evidence.models import (
    CanonicalEvidenceItem,
    EpistemicType,
    EvidenceClaim,
    EvidenceLineage,
    EvidenceSourceInfo,
    EvidenceSourceRecordInfo,
)
from src.research.evidence.search import (
    EvidenceSearchHit,
    EvidenceSearchQuery,
    EvidenceSearchResult,
    search_evidence,
)

__all__ = [
    "CanonicalEvidenceItem",
    "EpistemicType",
    "EvidenceClaim",
    "EvidenceLineage",
    "EvidenceSearchHit",
    "EvidenceSearchQuery",
    "EvidenceSearchResult",
    "EvidenceSourceInfo",
    "EvidenceSourceRecordInfo",
    "build_evidence_lineage",
    "filter_evidence_by_pit",
    "resolve_source_profile",
    "resolve_source_records",
    "search_evidence",
]
