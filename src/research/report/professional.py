"""
Professional Research Report models and assembly engine.

Canonical 22-section professional research report that integrates:
  - F7 canonical evidence lineage (source of truth)
  - Company intelligence snapshot (all analysis modules)
  - Research gaps from F6
  - Cross-domain observations
  - Evidence conflicts
  - Intel changes (what-changed layer)
  - Timeline events
  - Hidden/derived observations
  - Source health with provider failures
  - PIT integrity with market_as_of
  - Quality layer with stale/unsupported tracking

Every substantive item carries epistemic type labeling.
Unknown is never converted to negative evidence.
Inference is never presented as reported fact.

This module produces structured data for frontend rendering.
It does NOT produce scores, rankings, recommendations,
buy/sell calls, or trade signals.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.research.evidence.models import (
    CanonicalEvidenceItem,
    EpistemicType,
    EvidenceClaim,
    EvidenceLineage,
    EvidenceSourceInfo,
    EvidenceSourceRecordInfo,
)


# ── Epistemic labels ────────────────────────────────────────────


class SectionEpistemic(str, Enum):
    """Epistemic status for a report section or item."""

    REPORTED = "REPORTED"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


# ── Section models ──────────────────────────────────────────────


@dataclass(frozen=True)
class ReportItem:
    """One traceable item within a report section."""

    item_id: str
    text: str
    epistemic_type: str = SectionEpistemic.UNKNOWN.value
    evidence_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    confidence: str = "0"
    observation_at: datetime | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ReportSection:
    """One section of a professional research report."""

    section_id: str
    title: str
    status: str = "MISSING"
    epistemic_type: str = SectionEpistemic.UNKNOWN.value
    items: tuple[ReportItem, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    total_items: int = 0
    notes: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ReportEvidenceSection:
    """Evidence classification section (positive/negative/conflicting)."""

    section_id: str
    title: str
    items: tuple[CanonicalEvidenceItem, ...] = ()
    total_items: int = 0
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReportConflictDetail:
    """Detailed evidence conflict with both sides."""

    conflict_id: str
    topic: str
    description: str
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


# ── Quality layer ───────────────────────────────────────────────


@dataclass(frozen=True)
class ReportQualityIndicator:
    """One quality indicator for the report."""

    indicator_id: str
    name: str
    status: str = "UNKNOWN"
    value: str = ""
    explanation: str = ""


@dataclass(frozen=True)
class ReportQualityLayer:
    """Quality assessment of the assembled report."""

    evidence_coverage_pct: str = "0"
    provenance_coverage_pct: str = "0"
    source_freshness_pct: str = "0"
    unresolved_conflict_count: int = 0
    critical_gap_count: int = 0
    stale_input_count: int = 0
    unsupported_dimension_count: int = 0
    pit_status: str = "UNKNOWN"

    indicators: tuple[ReportQualityIndicator, ...] = ()
    notes: tuple[str, ...] = ()


# ── Executive overview ──────────────────────────────────────────


@dataclass(frozen=True)
class ReportExecutiveOverview:
    """Executive-level synthesis of the research evidence."""

    symbol: str
    company_name: str | None = None
    as_of: datetime | None = None

    evidence_direction: str = "UNKNOWN"
    evidence_direction_confidence: str = "0"

    total_evidence: int = 0
    positive_count: int = 0
    negative_count: int = 0
    conflicting_count: int = 0

    key_findings: tuple[ReportItem, ...] = ()
    key_risks: tuple[ReportItem, ...] = ()
    uncertainties: tuple[str, ...] = ()
    cannot_assess: tuple[str, ...] = ()

    what_changed: tuple[ReportItem, ...] = ()
    hidden_insights: tuple[ReportItem, ...] = ()


# ── Source health ───────────────────────────────────────────────


@dataclass(frozen=True)
class ReportSourceHealthEntry:
    """Source health for one data source."""

    source_id: str
    name: str
    source_type: str = ""
    tier: str = ""
    reliability_tier: str = "UNKNOWN"
    evidence_count: int = 0
    latest_observation: datetime | None = None
    freshness_status: str = "UNKNOWN"
    coverage_status: str = "UNKNOWN"
    stale: bool = False
    provenance_complete: bool = False
    categories: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReportSourceHealth:
    """Aggregate source health for the report."""

    total_sources: int = 0
    healthy_sources: int = 0
    degraded_sources: int = 0
    missing_sources: int = 0
    stale_sources: int = 0
    entries: tuple[ReportSourceHealthEntry, ...] = ()
    provider_failures: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


# ── Provenance chain ────────────────────────────────────────────


@dataclass(frozen=True)
class ReportProvenanceChain:
    """Provenance chain for the report."""

    total_provenance: int = 0
    with_available_at: int = 0
    with_published_at: int = 0
    records: tuple[EvidenceSourceRecordInfo, ...] = ()
    notes: tuple[str, ...] = ()


# ── PIT integrity ──────────────────────────────────────────────


@dataclass(frozen=True)
class ReportPITIntegrity:
    """Point-in-time integrity check for the report."""

    as_of: datetime
    effective_as_of: datetime | None = None
    market_as_of: str | None = None
    evidence_included: int = 0
    future_evidence_excluded: int = 0
    sources_discovered: int = 0
    sources_accepted: int = 0
    pit_checks_passed: bool = True
    notes: tuple[str, ...] = ()


# ── Methodology ─────────────────────────────────────────────────


@dataclass(frozen=True)
class ReportMethodology:
    """Methodology and limitations disclosure."""

    methodology_summary: str = ""
    known_limitations: tuple[str, ...] = ()
    data_freshness_note: str = ""
    PIT_policy: str = ""
    epistemic_disclosure: str = ""
    notes: tuple[str, ...] = ()


# ── Professional Report (top-level) ────────────────────────────


@dataclass(frozen=True)
class ProfessionalResearchReport:
    """
    Canonical professional research report.

    22 sections assembled from F7 evidence lineage and all
    research modules. Every substantive item carries epistemic
    type labeling. UNKNOWN is never treated as negative.

    This is structured data for frontend rendering.
    It does NOT contain scores, rankings, recommendations,
    buy/sell calls, or trade signals.
    """

    symbol: str
    as_of: datetime
    company_name: str | None = None
    report_version: str = "2.0"

    # ── 22 sections ──
    executive_overview: ReportExecutiveOverview | None = None
    research_snapshot: ReportSection | None = None
    business_context: ReportSection | None = None
    financial_performance: ReportSection | None = None
    financial_quality: ReportSection | None = None
    market_context: ReportSection | None = None
    business_developments: ReportSection | None = None
    management_strategy: ReportSection | None = None
    competitive_position: ReportSection | None = None
    innovation: ReportSection | None = None
    future_technology: ReportSection | None = None
    industry_context: ReportSection | None = None
    capital_allocation: ReportSection | None = None
    corporate_actions: ReportSection | None = None
    timeline: ReportSection | None = None

    # Evidence classification sections
    positive_evidence: ReportEvidenceSection | None = None
    negative_evidence: ReportEvidenceSection | None = None
    conflicting_evidence: ReportEvidenceSection | None = None
    conflict_details: tuple[ReportConflictDetail, ...] = ()

    # Research intelligence sections
    research_gaps: ReportSection | None = None
    source_health: ReportSourceHealth | None = None
    provenance_chain: ReportProvenanceChain | None = None
    pit_integrity: ReportPITIntegrity | None = None
    methodology: ReportMethodology | None = None

    # Quality layer
    quality_layer: ReportQualityLayer | None = None

    # Evidence lineage reference (not serialized to API)
    evidence_lineage: EvidenceLineage | None = None

    # Notes
    notes: tuple[str, ...] = ()


# =================================================================
# ASSEMBLY ENGINE
# =================================================================

# ── Section ID constants ────────────────────────────────────────

SEC_RESEARCH_SNAPSHOT = "research_snapshot"
SEC_BUSINESS_CONTEXT = "business_context"
SEC_FINANCIAL_PERFORMANCE = "financial_performance"
SEC_FINANCIAL_QUALITY = "financial_quality"
SEC_MARKET_CONTEXT = "market_context"
SEC_BUSINESS_DEVELOPMENTS = "business_developments"
SEC_MANAGEMENT_STRATEGY = "management_strategy"
SEC_COMPETITIVE_POSITION = "competitive_position"
SEC_INNOVATION = "innovation"
SEC_FUTURE_TECHNOLOGY = "future_technology"
SEC_INDUSTRY_CONTEXT = "industry_context"
SEC_CAPITAL_ALLOCATION = "capital_allocation"
SEC_CORPORATE_ACTIONS = "corporate_actions"
SEC_TIMELINE = "timeline"
SEC_RESEARCH_GAPS = "research_gaps"


# ── Category mapping ────────────────────────────────────────────

_SECTION_CATEGORIES: dict[str, str] = {
    SEC_BUSINESS_CONTEXT: "BUSINESS",
    SEC_FINANCIAL_PERFORMANCE: "FINANCIAL",
    SEC_FINANCIAL_QUALITY: "FINANCIAL",
    SEC_MARKET_CONTEXT: "MARKET",
    SEC_BUSINESS_DEVELOPMENTS: "EVENT",
    SEC_MANAGEMENT_STRATEGY: "MANAGEMENT",
    SEC_COMPETITIVE_POSITION: "COMPETITIVE",
    SEC_INNOVATION: "INNOVATION",
    SEC_FUTURE_TECHNOLOGY: "FUTURE_TECHNOLOGY",
    SEC_INDUSTRY_CONTEXT: "INDUSTRY",
    SEC_CAPITAL_ALLOCATION: "CAPITAL_ALLOCATION",
    SEC_CORPORATE_ACTIONS: "CORPORATE_ACTION",
    SEC_TIMELINE: "TIMELINE",
    SEC_RESEARCH_GAPS: "RESEARCH_GAP",
}


# ── Deduplication ───────────────────────────────────────────────


def _normalize_text(value: str) -> str:
    """Normalize text for duplicate detection."""
    return " ".join(value.split()).strip().lower()


def _confidence_value(item: CanonicalEvidenceItem) -> float:
    try:
        return float(item.confidence)
    except (TypeError, ValueError):
        return 0.0


def _deduplicate_evidence(
    evidence: tuple[CanonicalEvidenceItem, ...],
) -> tuple[CanonicalEvidenceItem, ...]:
    """
    Deduplicate evidence items deterministically.

    Two passes:
      1. by evidence_id — first occurrence wins;
      2. by normalized content — items describing the same fact
         (identical title + explanation) collapse into one record
         whose source/provenance ids are the union of the merged
         records. The representative keeps the lowest evidence_id so
         output stays deterministic.
    """
    seen: set[str] = set()
    unique: list[CanonicalEvidenceItem] = []
    for item in sorted(evidence, key=lambda x: x.evidence_id):
        if item.evidence_id not in seen:
            seen.add(item.evidence_id)
            unique.append(item)

    by_content: dict[tuple[str, str, str], CanonicalEvidenceItem] = {}
    order: list[tuple[str, str, str]] = []
    for item in unique:
        key = (
            _normalize_text(item.title),
            _normalize_text(item.explanation),
            item.direction.upper(),
        )
        existing = by_content.get(key)
        if existing is None:
            by_content[key] = item
            order.append(key)
            continue

        representative = (
            existing
            if item.evidence_id > existing.evidence_id
            else item
        )
        merged = replace(
            representative,
            source_ids=tuple(
                sorted(
                    set(existing.source_ids) | set(item.source_ids)
                )
            ),
            provenance_ids=tuple(
                sorted(
                    set(existing.provenance_ids)
                    | set(item.provenance_ids)
                )
            ),
            reliability=(
                existing.reliability
                if _confidence_value(existing) >= _confidence_value(item)
                else item.reliability
            ),
        )
        by_content[key] = merged

    return tuple(by_content[key] for key in order)


def _sorted_items(items: tuple) -> tuple:
    """Sort items deterministically by item_id."""
    return tuple(sorted(items, key=lambda x: getattr(x, "item_id", getattr(x, "evidence_id", ""))))


# ── Evidence helpers ────────────────────────────────────────────


def _classify_epistemic(item: CanonicalEvidenceItem) -> str:
    """Classify the epistemic type of an evidence item."""
    return (
        item.epistemic_type.value
        if hasattr(item.epistemic_type, "value")
        else str(item.epistemic_type)
    )


def _evidence_to_report_item(
    item: CanonicalEvidenceItem,
) -> ReportItem:
    """Convert a CanonicalEvidenceItem to a ReportItem."""
    return ReportItem(
        item_id=item.evidence_id,
        text=f"{item.title}: {item.explanation}",
        epistemic_type=_classify_epistemic(item),
        evidence_ids=(item.evidence_id,),
        source_ids=list(item.source_ids),
        confidence=item.confidence,
        observation_at=item.observation_at,
        metadata={
            "evidence_type": item.evidence_type,
            "direction": item.direction,
            "reliability": item.reliability,
            "verification_status": item.verification_status,
        },
    )


def _evidence_by_direction(
    evidence: tuple[CanonicalEvidenceItem, ...],
) -> dict[str, list[CanonicalEvidenceItem]]:
    """Group evidence by direction."""
    result: dict[str, list[CanonicalEvidenceItem]] = defaultdict(list)
    for item in evidence:
        result[item.direction.upper()].append(item)
    return dict(result)


def _evidence_by_category(
    evidence: tuple[CanonicalEvidenceItem, ...],
) -> dict[str, list[CanonicalEvidenceItem]]:
    """Group evidence by category."""
    result: dict[str, list[CanonicalEvidenceItem]] = defaultdict(list)
    for item in evidence:
        key = item.category.upper() if item.category else "UNCATEGORIZED"
        result[key].append(item)
    return dict(result)


def _category_for_section(section_id: str) -> str:
    """Get the evidence category that maps to a section."""
    return _SECTION_CATEGORIES.get(section_id, "")


# ── Intel category → section mapping ────────────────────────────

_INTEL_CATEGORY_TO_SECTIONS: dict[str, list[str]] = {
    "FINANCIAL_DISCLOSURE": [SEC_FINANCIAL_PERFORMANCE, SEC_FINANCIAL_QUALITY],
    "BUSINESS_NEWS": [SEC_BUSINESS_DEVELOPMENTS, SEC_BUSINESS_CONTEXT],
    "MANAGEMENT_STATEMENT": [SEC_MANAGEMENT_STRATEGY],
    "CORPORATE_ACTION": [SEC_CORPORATE_ACTIONS],
    "EXECUTIVE_CHANGE": [SEC_MANAGEMENT_STRATEGY],
    "ORDER_CONTRACT": [SEC_BUSINESS_DEVELOPMENTS],
    "ACQUISITION_DIVESTMENT": [SEC_BUSINESS_DEVELOPMENTS, SEC_COMPETITIVE_POSITION],
    "CAPEX_EXPANSION": [SEC_CAPITAL_ALLOCATION],
    "PRODUCT_BUSINESS_UPDATE": [SEC_BUSINESS_DEVELOPMENTS, SEC_INNOVATION],
    "SUBSIDIARY_UPDATE": [SEC_BUSINESS_CONTEXT],
    "SEGMENT_UPDATE": [SEC_FINANCIAL_PERFORMANCE],
    "OWNERSHIP_DISCLOSURE": [SEC_BUSINESS_CONTEXT],
    "CONFERENCE_CALL": [SEC_MANAGEMENT_STRATEGY],
    "INVESTOR_PRESENTATION": [SEC_MANAGEMENT_STRATEGY],
    "CREDIT_RATING_ACTION": [SEC_FINANCIAL_QUALITY],
    "LEGAL_PROCEEDING": [SEC_BUSINESS_DEVELOPMENTS],
    "FORECAST_GUIDANCE": [SEC_MANAGEMENT_STRATEGY],
}


def _primary_section_for_intel_category(
    intel_category: str,
) -> str | None:
    """Return the primary (first-listed) section for an intel category."""
    sections = _INTEL_CATEGORY_TO_SECTIONS.get(intel_category)
    if not sections:
        return None
    return sections[0]


def _intel_items_for_section(
    section_id: str,
    intel_items: tuple,
) -> list:
    """
    Filter intel items whose PRIMARY section is the given section.

    Intel categories that map to several sections are presented once,
    in their primary section, so the readable narrative never repeats
    the same intelligence item across topic sections.
    """
    matching: list = []
    if not intel_items:
        return matching

    for item in intel_items:
        cat_val = (
            item.intel_category.value
            if item.intel_category and hasattr(item.intel_category, "value")
            else str(item.intel_category) if item.intel_category else ""
        )
        if not cat_val:
            continue
        if _primary_section_for_intel_category(cat_val) == section_id:
            matching.append(item)
    return matching


def _build_section_from_evidence(
    section_id: str,
    title: str,
    evidence: tuple[CanonicalEvidenceItem, ...],
    intel_items: tuple = (),
    claimed_texts: dict[str, str] | None = None,
) -> ReportSection | None:
    """
    Build a report section from evidence matching a category,
    enriched with intel items.

    `claimed_texts` is a shared registry mapping normalized item text
    to the section that first presented it. Items already presented
    in another topic section are omitted here (with a note), so the
    readable narrative does not repeat the same content.
    """
    category = _category_for_section(section_id)
    if not category:
        return None

    matching_ev = [
        item for item in evidence
        if item.category.upper() == category
    ]

    matching_intel = _intel_items_for_section(section_id, intel_items)

    if not matching_ev and not matching_intel:
        return None

    # Sort deterministically
    matching_ev.sort(key=lambda x: x.evidence_id)
    matching_intel.sort(key=lambda x: x.item_id)

    # Section-level attribution unions every matching item, including
    # any later suppressed as duplicates, so no source is lost.
    section_source_ids: set[str] = set()
    for item in matching_ev:
        section_source_ids.update(item.source_ids)
    for item in matching_intel:
        if item.source:
            section_source_ids.add(item.source.source_name)

    suppressed = 0

    def _claim(key: str) -> bool:
        nonlocal suppressed
        if claimed_texts is None:
            return True
        if key in claimed_texts:
            suppressed += 1
            return False
        claimed_texts[key] = section_id
        return True

    def _evidence_key(item: CanonicalEvidenceItem) -> str:
        return "|".join((
            _normalize_text(item.title),
            _normalize_text(item.explanation),
            item.direction.upper(),
            (item.category or "").upper(),
            item.evidence_type.upper(),
        ))

    def _intel_key(item) -> str:
        return "|".join((
            "INTEL",
            _normalize_text(item.title),
            _normalize_text(item.description or ""),
        ))

    matching_ev = [
        item for item in matching_ev
        if _claim(_evidence_key(item))
    ]
    matching_intel = [
        item for item in matching_intel
        if _claim(_intel_key(item))
    ]

    if not matching_ev and not matching_intel:
        return None

    ev_items = tuple(_evidence_to_report_item(item) for item in matching_ev)
    intel_report_items = tuple(_intel_to_report_item(item) for item in matching_intel)
    all_items = ev_items + intel_report_items

    all_evidence_ids: list[str] = []
    epistemic_counts: dict[str, int] = defaultdict(int)

    for item in matching_ev:
        all_evidence_ids.append(item.evidence_id)
        epistemic_counts[item.epistemic_type.value] += 1

    for item in matching_intel:
        vs = (
            item.verification_status.value
            if hasattr(item.verification_status, "value")
            else str(item.verification_status)
        )
        epistemic_counts[vs] += 1

    dominant_epistemic = max(
        epistemic_counts.items(),
        key=lambda x: x[1],
    )[0] if epistemic_counts else SectionEpistemic.UNKNOWN.value

    total = len(matching_ev) + len(matching_intel)

    notes: list[str] = []
    if matching_intel and not matching_ev:
        notes.append(
            f"Section populated from {len(matching_intel)} intelligence items "
            f"(no evidence lineage items in this category)."
        )
    if matching_ev and matching_intel:
        notes.append(
            f"Section combines {len(matching_ev)} evidence items with "
            f"{len(matching_intel)} intelligence items."
        )
    if suppressed:
        notes.append(
            f"{suppressed} duplicate item(s) already presented in this "
            "report were omitted here."
        )

    return ReportSection(
        section_id=section_id,
        title=title,
        status="COMPLETE" if total >= 3 else "PARTIAL",
        epistemic_type=dominant_epistemic,
        items=all_items,
        evidence_ids=tuple(all_evidence_ids),
        source_ids=tuple(sorted(section_source_ids)),
        total_items=total,
        notes=tuple(notes),
    )


def _build_evidence_section(
    section_id: str,
    title: str,
    evidence: tuple[CanonicalEvidenceItem, ...],
    direction_filter: str,
) -> ReportEvidenceSection | None:
    """Build an evidence classification section."""
    matching = [
        item for item in evidence
        if item.direction.upper() == direction_filter.upper()
    ]

    if not matching:
        return None

    matching.sort(key=lambda x: x.evidence_id)

    return ReportEvidenceSection(
        section_id=section_id,
        title=title,
        items=tuple(matching),
        total_items=len(matching),
    )


# ── Intel item to report item ───────────────────────────────────


def _intel_item_text(item) -> str:
    """Readable text for an intel item (mirrors _intel_to_report_item)."""
    if item.description:
        return f"{item.title}: {item.description}"
    return item.title


def _intel_to_report_item(item) -> ReportItem:
    """Convert a CorporateIntelItem to a ReportItem."""
    epistemic = SectionEpistemic.UNKNOWN.value
    vs = (
        item.verification_status.value
        if hasattr(item.verification_status, "value")
        else str(item.verification_status)
    )
    if vs == "REPORTED":
        epistemic = SectionEpistemic.REPORTED.value
    elif vs == "DERIVED":
        epistemic = SectionEpistemic.DERIVED.value
    elif vs == "INFERRED":
        epistemic = SectionEpistemic.INFERRED.value

    confidence_str = (
        str(item.confidence)
        if item.confidence is not None
        else "0"
    )

    return ReportItem(
        item_id=item.item_id,
        text=_intel_item_text(item),
        epistemic_type=epistemic,
        evidence_ids=(),
        source_ids=(item.source.source_name,) if item.source else (),
        confidence=confidence_str,
        observation_at=item.published_at or item.available_at,
        metadata={
            "kind": item.kind.value if hasattr(item.kind, "value") else str(item.kind),
            "direction": item.direction.value if hasattr(item.direction, "value") else str(item.direction),
            "stance": item.stance.value if hasattr(item.stance, "value") else str(item.stance),
            "semantic_category": item.semantic_category.value if hasattr(item.semantic_category, "value") else str(item.semantic_category),
        },
    )


# ── Section builders using intel items ──────────────────────────


def _build_section_from_intel(
    section_id: str,
    title: str,
    intel_items: tuple,
    kind_filter: str | None = None,
    category_filter: str | None = None,
) -> ReportSection | None:
    """Build a section from CorporateIntelItem tuples."""
    matching = []
    for item in intel_items:
        kind_val = item.kind.value if hasattr(item.kind, "value") else str(item.kind)
        if kind_filter and kind_val != kind_filter:
            continue
        cat_val = (
            item.intel_category.value
            if item.intel_category and hasattr(item.intel_category, "value")
            else str(item.intel_category) if item.intel_category else ""
        )
        if category_filter and cat_val != category_filter:
            continue
        matching.append(item)

    if not matching:
        return None

    matching.sort(key=lambda x: x.item_id)
    items = tuple(_intel_to_report_item(item) for item in matching)

    all_source_ids: set[str] = set()
    all_evidence_ids: list[str] = []

    for item in matching:
        if item.source:
            all_source_ids.add(item.source.source_name)

    return ReportSection(
        section_id=section_id,
        title=title,
        status="COMPLETE" if len(matching) >= 3 else "PARTIAL",
        epistemic_type=SectionEpistemic.REPORTED.value,
        items=items,
        source_ids=tuple(sorted(all_source_ids)),
        total_items=len(matching),
    )


# ── Executive overview ──────────────────────────────────────────


def _build_executive_overview(
    lineage: EvidenceLineage,
    company_name: str | None,
    intel_items: tuple = (),
    intelligence=None,
) -> ReportExecutiveOverview:
    """Build a synthesized executive overview from all available data."""
    evidence = _deduplicate_evidence(lineage.evidence)
    by_direction = _evidence_by_direction(evidence)

    positive = by_direction.get("POSITIVE", [])
    negative = by_direction.get("NEGATIVE", [])
    mixed = by_direction.get("MIXED", [])

    total = len(evidence)
    pos_count = len(positive)
    neg_count = len(negative)
    conflict_count = len(mixed)

    if pos_count > neg_count and pos_count > conflict_count:
        direction = "POSITIVE"
    elif neg_count > pos_count and neg_count > conflict_count:
        direction = "NEGATIVE"
    elif conflict_count > 0:
        direction = "MIXED"
    elif total > 0:
        direction = "NEUTRAL"
    else:
        direction = "UNKNOWN"

    # Key findings: highest confidence evidence across positive+negative
    key_findings = tuple(
        _evidence_to_report_item(item)
        for item in sorted(
            positive + negative,
            key=lambda x: float(x.confidence),
            reverse=True,
        )[:5]
    )

    # Key risks: negative evidence
    key_risks = tuple(
        _evidence_to_report_item(item)
        for item in sorted(
            negative,
            key=lambda x: float(x.confidence),
            reverse=True,
        )[:3]
    )

    # Uncertainties: UNKNOWN claims, deduplicated deterministically
    uncertainties: list[str] = []
    seen_uncertain: set[str] = set()
    for claim in sorted(lineage.claims, key=lambda c: c.claim_id):
        if claim.epistemic_type != EpistemicType.UNKNOWN:
            continue
        key = _normalize_text(claim.text)
        if key in seen_uncertain:
            continue
        seen_uncertain.add(key)
        uncertainties.append(claim.text)

    # Cannot assess: from intelligence insufficient_evidence_notes
    cannot_assess: list[str] = []
    if intelligence is not None and hasattr(intelligence, "insufficient_evidence_notes"):
        cannot_assess = list(intelligence.insufficient_evidence_notes)

    # What changed: from intelligence changes
    what_changed: list[ReportItem] = []
    if intelligence is not None and hasattr(intelligence, "changes"):
        for change in sorted(intelligence.changes, key=lambda c: c.item_id)[:5]:
            what_changed.append(ReportItem(
                item_id=f"change-{change.item_id}",
                text=f"{change.change_type.value}: {change.title} — {change.description}",
                epistemic_type=SectionEpistemic.REPORTED.value,
                metadata={
                    "change_type": change.change_type.value if hasattr(change.change_type, "value") else str(change.change_type),
                    "kind": change.kind.value if hasattr(change.kind, "value") else str(change.kind),
                },
            ))

    # Hidden insights: from intelligence hidden_information
    hidden_insights: list[ReportItem] = []
    if intelligence is not None and hasattr(intelligence, "hidden_information"):
        hi = intelligence.hidden_information
        if hi is not None and hasattr(hi, "observations"):
            for obs in sorted(hi.observations, key=lambda o: o.observation_id)[:5]:
                hidden_insights.append(ReportItem(
                    item_id=obs.observation_id,
                    text=f"{obs.label}: {obs.description}",
                    epistemic_type=SectionEpistemic.DERIVED.value,
                    evidence_ids=list(obs.related_item_ids),
                    source_ids=list(obs.source_ids),
                    metadata={
                        "derivation": obs.derivation,
                        "severity": obs.severity,
                        "semantic_category": obs.semantic_category.value if hasattr(obs.semantic_category, "value") else str(obs.semantic_category),
                    },
                ))

    return ReportExecutiveOverview(
        symbol=lineage.symbol,
        company_name=company_name,
        as_of=lineage.as_of,
        evidence_direction=direction,
        evidence_direction_confidence=str(
            max(
                (float(item.confidence) for item in evidence),
                default=0,
            )
        ),
        total_evidence=total,
        positive_count=pos_count,
        negative_count=neg_count,
        conflicting_count=conflict_count,
        key_findings=key_findings,
        key_risks=key_risks,
        uncertainties=tuple(uncertainties[:5]),
        cannot_assess=tuple(cannot_assess[:5]),
        what_changed=tuple(what_changed),
        hidden_insights=tuple(hidden_insights),
    )


# ── Research snapshot ───────────────────────────────────────────


def _build_research_snapshot(
    lineage: EvidenceLineage,
    intelligence=None,
    *,
    total_sources: int | None = None,
) -> ReportSection:
    """Build the research snapshot section with counts and summaries."""
    items: list[ReportItem] = []

    items.append(ReportItem(
        item_id="snapshot-evidence-count",
        text=f"Total evidence items: {lineage.total_evidence}",
        epistemic_type=SectionEpistemic.REPORTED.value,
    ))

    items.append(ReportItem(
        item_id="snapshot-claim-count",
        text=f"Total claims: {lineage.total_claims}",
        epistemic_type=SectionEpistemic.REPORTED.value,
    ))

    snapshot_sources = (
        total_sources
        if total_sources is not None
        else lineage.total_sources
    )
    items.append(ReportItem(
        item_id="snapshot-source-count",
        text=f"Total sources: {snapshot_sources}",
        epistemic_type=SectionEpistemic.REPORTED.value,
    ))

    for ep_type, count in sorted(lineage.epistemic_type_counts.items()):
        items.append(ReportItem(
            item_id=f"snapshot-epistemic-{ep_type}",
            text=f"Epistemic type '{ep_type}': {count} items",
            epistemic_type=SectionEpistemic.REPORTED.value,
        ))

    for direction, count in sorted(lineage.direction_counts.items()):
        items.append(ReportItem(
            item_id=f"snapshot-direction-{direction}",
            text=f"Direction '{direction}': {count} items",
            epistemic_type=SectionEpistemic.REPORTED.value,
        ))

    # Intel-level summaries
    if intelligence is not None:
        if hasattr(intelligence, "item_count"):
            items.append(ReportItem(
                item_id="snapshot-intel-items",
                text=f"Intelligence items: {intelligence.item_count}",
                epistemic_type=SectionEpistemic.REPORTED.value,
            ))

        if hasattr(intelligence, "conflicts") and intelligence.conflicts:
            items.append(ReportItem(
                item_id="snapshot-conflicts",
                text=f"Evidence conflicts detected: {len(intelligence.conflicts)}",
                epistemic_type=SectionEpistemic.REPORTED.value,
            ))

        if hasattr(intelligence, "changes") and intelligence.changes:
            items.append(ReportItem(
                item_id="snapshot-changes",
                text=f"Changes detected: {len(intelligence.changes)}",
                epistemic_type=SectionEpistemic.REPORTED.value,
            ))

        if intelligence.status is not None:
            freshness = intelligence.status.freshness
            if freshness.stale:
                items.append(ReportItem(
                    item_id="snapshot-stale",
                    text="Research data is stale — sources have not updated recently.",
                    epistemic_type=SectionEpistemic.REPORTED.value,
                    metadata={"severity": "WARNING"},
                ))

    return ReportSection(
        section_id=SEC_RESEARCH_SNAPSHOT,
        title="Research Snapshot",
        status="COMPLETE",
        epistemic_type=SectionEpistemic.REPORTED.value,
        items=tuple(items),
        total_items=len(items),
    )


# ── Research gaps ───────────────────────────────────────────────


def _build_research_gaps_section(
    research_gaps: Any,
) -> ReportSection | None:
    """Build the research gaps section from ResearchGapResult."""
    if research_gaps is None:
        return None

    if not hasattr(research_gaps, "gaps"):
        return None

    gaps = research_gaps.gaps
    if not gaps:
        return None

    items: list[ReportItem] = []
    for gap in sorted(gaps, key=lambda g: g.gap_id):
        items.append(ReportItem(
            item_id=gap.gap_id,
            text=f"[{gap.status}] {gap.category}: {gap.gap}",
            epistemic_type=SectionEpistemic.REPORTED.value,
            metadata={
                "status": gap.status,
                "category": gap.category,
                "priority": gap.priority,
                "reason": gap.reason,
                "what_would_resolve": gap.what_would_resolve,
            },
        ))

    return ReportSection(
        section_id=SEC_RESEARCH_GAPS,
        title="Research Gaps & Unknowns",
        status="PARTIAL" if items else "MISSING",
        epistemic_type=SectionEpistemic.REPORTED.value,
        items=tuple(items),
        total_items=len(items),
    )


# ── Source health ───────────────────────────────────────────────


def _build_source_health(
    lineage: EvidenceLineage,
    intelligence=None,
) -> ReportSourceHealth:
    """Build source health from lineage + intelligence source statuses."""
    entries: list[ReportSourceHealthEntry] = []

    # Start from lineage source profiles
    evidence_by_source: dict[str, list[CanonicalEvidenceItem]] = defaultdict(list)
    for item in lineage.evidence:
        for sid in item.source_ids:
            evidence_by_source[sid].append(item)

    for profile in lineage.source_profiles:
        items = evidence_by_source.get(profile.source_id, [])

        latest_obs = None
        for item in items:
            if item.observation_at is not None:
                if latest_obs is None or item.observation_at > latest_obs:
                    latest_obs = item.observation_at

        entries.append(ReportSourceHealthEntry(
            source_id=profile.source_id,
            name=profile.name,
            source_type=profile.source_type,
            tier=profile.tier,
            reliability_tier=profile.reliability_tier,
            evidence_count=len(items),
            latest_observation=latest_obs,
            freshness_status="CURRENT" if items else "NO_EVIDENCE",
            coverage_status="ACTIVE" if items else "INACTIVE",
        ))

    # Enrich with intelligence source statuses
    provider_failures: list[str] = []
    if intelligence is not None:
        if hasattr(intelligence, "source_statuses"):
            for ss in intelligence.source_statuses:
                # Check if already in entries
                existing = any(
                    e.name == ss.source_name for e in entries
                )
                if not existing:
                    entries.append(ReportSourceHealthEntry(
                        source_id=ss.source_name,
                        name=ss.source_name,
                        source_type=ss.source_type,
                        evidence_count=ss.item_count,
                        latest_observation=ss.latest_available_at,
                        freshness_status="STALE" if ss.stale else "CURRENT",
                        coverage_status="ACTIVE" if ss.item_count > 0 else "INACTIVE",
                        stale=ss.stale,
                        provenance_complete=ss.provenance_completeness,
                        categories=ss.categories,
                    ))
                else:
                    # Update existing entry with intel data
                    for e in entries:
                        if e.name == ss.source_name:
                            entries[entries.index(e)] = ReportSourceHealthEntry(
                                source_id=e.source_id,
                                name=e.name,
                                source_type=e.source_type or ss.source_type,
                                tier=e.tier,
                                reliability_tier=e.reliability_tier,
                                evidence_count=max(e.evidence_count, ss.item_count),
                                latest_observation=e.latest_observation or ss.latest_available_at,
                                freshness_status="STALE" if ss.stale else e.freshness_status,
                                coverage_status=e.coverage_status,
                                stale=ss.stale,
                                provenance_complete=ss.provenance_completeness,
                                categories=ss.categories or e.categories,
                            )

        if hasattr(intelligence, "provider_failures"):
            provider_failures = list(intelligence.provider_failures)

    healthy = sum(1 for e in entries if e.coverage_status == "ACTIVE" and not e.stale)
    degraded = sum(1 for e in entries if e.coverage_status == "INACTIVE" or e.stale)
    stale = sum(1 for e in entries if e.stale)
    missing = max(0, len(entries) - healthy - degraded)

    return ReportSourceHealth(
        total_sources=len(entries),
        healthy_sources=healthy,
        degraded_sources=degraded,
        missing_sources=missing,
        stale_sources=stale,
        entries=tuple(sorted(entries, key=lambda e: e.source_id)),
        provider_failures=tuple(provider_failures),
    )


# ── Provenance chain ────────────────────────────────────────────


def _build_provenance_chain(
    lineage: EvidenceLineage,
) -> ReportProvenanceChain:
    """Build provenance chain from evidence lineage."""
    with_available = sum(
        1 for rec in lineage.source_records
        if rec.available_at is not None
    )
    with_published = sum(
        1 for rec in lineage.source_records
        if rec.published_at is not None
    )

    return ReportProvenanceChain(
        total_provenance=lineage.total_provenance,
        with_available_at=with_available,
        with_published_at=with_published,
        records=lineage.source_records,
    )


# ── PIT integrity ──────────────────────────────────────────────


def _build_pit_integrity(
    lineage: EvidenceLineage,
    as_of: datetime,
    intelligence=None,
    acquisition=None,
) -> ReportPITIntegrity:
    """Build PIT integrity check with full metadata."""
    future_count = 0
    for item in lineage.evidence:
        if (
            item.observation_at is not None
            and item.observation_at > as_of
        ):
            future_count += 1

    # Extract acquisition metadata
    sources_discovered = 0
    sources_accepted = 0
    market_as_of = None

    if acquisition is not None:
        if hasattr(acquisition, "sources_discovered"):
            sources_discovered = acquisition.sources_discovered
        if hasattr(acquisition, "sources_accepted"):
            sources_accepted = acquisition.sources_accepted

    # Market as_of from intelligence — reported as a calendar date to
    # match the market-data as-of semantics used across the API layer.
    if intelligence is not None:
        if hasattr(intelligence, "as_of"):
            market_as_of = intelligence.as_of.date().isoformat()

    return ReportPITIntegrity(
        as_of=as_of,
        effective_as_of=as_of,
        market_as_of=market_as_of,
        evidence_included=lineage.total_evidence,
        future_evidence_excluded=future_count,
        sources_discovered=sources_discovered,
        sources_accepted=sources_accepted,
        pit_checks_passed=future_count == 0,
        notes=(
            f"Report covers evidence available at or before {as_of.isoformat()}.",
        ),
    )


# ── Quality layer ───────────────────────────────────────────────


def _build_quality_layer(
    lineage: EvidenceLineage,
    research_gaps: Any = None,
    intelligence=None,
) -> ReportQualityLayer:
    """Build quality layer with comprehensive indicators."""
    evidence = _deduplicate_evidence(lineage.evidence)
    total_evidence = len(evidence)
    with_source = sum(
        1 for item in evidence if item.source_ids
    )
    with_provenance = sum(
        1 for item in evidence if item.provenance_ids
    )

    evidence_cov = (
        str(round(with_source / total_evidence * 100, 1))
        if total_evidence > 0
        else "0"
    )
    provenance_cov = (
        str(round(with_provenance / total_evidence * 100, 1))
        if total_evidence > 0
        else "0"
    )

    unresolved = sum(
        1 for c in lineage.claims
        if c.verification_status == "UNVERIFIED"
    )

    gap_count = 0
    if research_gaps is not None and hasattr(research_gaps, "gap_count"):
        gap_count = research_gaps.gap_count

    # Stale inputs from intelligence
    stale_count = 0
    unsupported_count = 0
    if intelligence is not None:
        if intelligence.status is not None:
            stale_count = intelligence.status.quality.stale_source_count
            if intelligence.status.coverage.missing_categories:
                unsupported_count = len(intelligence.status.coverage.missing_categories)

    # Source freshness
    source_freshness_pct = "0"
    if intelligence is not None and hasattr(intelligence, "source_statuses"):
        total_src = len(intelligence.source_statuses)
        fresh_src = sum(
            1 for ss in intelligence.source_statuses if not ss.stale
        )
        if total_src > 0:
            source_freshness_pct = str(round(fresh_src / total_src * 100, 1))

    pit_status = "PASSED" if lineage.pit_filtered_count == 0 else "FILTERED"

    indicators = [
        ReportQualityIndicator(
            indicator_id="evidence-coverage",
            name="Evidence Coverage",
            status="GOOD" if float(evidence_cov) >= 80 else "PARTIAL",
            value=f"{evidence_cov}%",
            explanation="Percentage of evidence items with source attribution.",
        ),
        ReportQualityIndicator(
            indicator_id="provenance-coverage",
            name="Provenance Coverage",
            status="GOOD" if float(provenance_cov) >= 80 else "PARTIAL",
            value=f"{provenance_cov}%",
            explanation="Percentage of evidence items with provenance records.",
        ),
        ReportQualityIndicator(
            indicator_id="source-freshness",
            name="Source Freshness",
            status="GOOD" if float(source_freshness_pct) >= 80 else "WARNING",
            value=f"{source_freshness_pct}%",
            explanation="Percentage of sources with recent data.",
        ),
        ReportQualityIndicator(
            indicator_id="unresolved-claims",
            name="Unresolved Claims",
            status="GOOD" if unresolved == 0 else "WARNING",
            value=str(unresolved),
            explanation="Claims without verification status.",
        ),
        ReportQualityIndicator(
            indicator_id="research-gaps",
            name="Research Gaps",
            status="GOOD" if gap_count == 0 else "WARNING",
            value=str(gap_count),
            explanation="Known research gaps identified.",
        ),
        ReportQualityIndicator(
            indicator_id="stale-inputs",
            name="Stale Inputs",
            status="GOOD" if stale_count == 0 else "WARNING",
            value=str(stale_count),
            explanation="Sources identified as stale.",
        ),
        ReportQualityIndicator(
            indicator_id="unsupported-dimensions",
            name="Unsupported Dimensions",
            status="GOOD" if unsupported_count == 0 else "WARNING",
            value=str(unsupported_count),
            explanation="Research dimensions with missing category coverage.",
        ),
    ]

    return ReportQualityLayer(
        evidence_coverage_pct=evidence_cov,
        provenance_coverage_pct=provenance_cov,
        source_freshness_pct=source_freshness_pct,
        unresolved_conflict_count=unresolved,
        critical_gap_count=gap_count,
        stale_input_count=stale_count,
        unsupported_dimension_count=unsupported_count,
        pit_status=pit_status,
        indicators=tuple(indicators),
    )


# ── Methodology ─────────────────────────────────────────────────


def _build_methodology() -> ReportMethodology:
    """Build methodology disclosure."""
    return ReportMethodology(
        methodology_summary=(
            "This report is assembled from canonical evidence lineage. "
            "Every substantive item carries epistemic type labeling. "
            "No scores, rankings, recommendations, buy/sell calls, "
            "or trade signals are produced."
        ),
        known_limitations=(
            "Evidence completeness depends on source availability.",
            "Some evidence may be stale if sources have not updated.",
            "Cross-domain inferences are descriptive, not causal.",
            "Unknown epistemic types indicate classification is pending.",
        ),
        data_freshness_note=(
            "Evidence freshness depends on the underlying data sources. "
            "Check source_health for individual source freshness."
        ),
        PIT_policy=(
            "All evidence is filtered to be point-in-time safe. "
            "Evidence with available_at after the report as_of "
            "is excluded."
        ),
        epistemic_disclosure=(
            "Every item in this report is labeled with its epistemic "
            "type: REPORTED (directly stated in source), DERIVED "
            "(computed from reported values), INFERRED (inferred from "
            "multiple sources), or UNKNOWN (classification pending). "
            "UNKNOWN never indicates negative evidence."
        ),
    )


# ── Conflicting evidence details ────────────────────────────────


def _build_conflict_details(intelligence=None) -> tuple[ReportConflictDetail, ...]:
    """Build detailed conflict information from intelligence."""
    if intelligence is None:
        return ()

    if not hasattr(intelligence, "conflicts"):
        return ()

    details: list[ReportConflictDetail] = []
    for conflict in sorted(intelligence.conflicts, key=lambda c: c.conflict_id):
        details.append(ReportConflictDetail(
            conflict_id=conflict.conflict_id,
            topic=conflict.topic,
            description=conflict.description,
            management_involved=conflict.management_involved,
            first_item_id=conflict.first.item_id,
            first_title=conflict.first.title,
            first_direction=(
                conflict.first.direction.value
                if hasattr(conflict.first.direction, "value")
                else str(conflict.first.direction)
            ),
            first_source=conflict.first.source_name,
            first_excerpt=conflict.first.excerpt,
            second_item_id=conflict.second.item_id,
            second_title=conflict.second.title,
            second_direction=(
                conflict.second.direction.value
                if hasattr(conflict.second.direction, "value")
                else str(conflict.second.direction)
            ),
            second_source=conflict.second.source_name,
            second_excerpt=conflict.second.excerpt,
        ))

    return tuple(details)


# ── Main assembly function ──────────────────────────────────────


def build_professional_report(
    *,
    lineage: EvidenceLineage,
    company_name: str | None = None,
    intel_items: tuple = (),
    intelligence=None,
    research_gaps: Any = None,
    acquisition: Any = None,
) -> ProfessionalResearchReport:
    """
    Build a ProfessionalResearchReport from F7 evidence lineage
    and the full company intelligence snapshot.

    Consumes:
      - F7 EvidenceLineage (source of truth for evidence)
      - CompanyIntelligenceSnapshot (all analysis modules)
      - ResearchGapResult (research gaps)
      - AcquisitionResult (source counts)
    """
    # Deduplicate evidence (by id, then by normalized content)
    evidence = _deduplicate_evidence(lineage.evidence)

    # Intel items that were converted into the canonical evidence pool
    # are presented once, through the intel enrichment path below.
    # Their evidence-pool twins would duplicate the same narrative.
    intel_item_ids = {item.item_id for item in intel_items}
    section_evidence = tuple(
        item for item in evidence
        if item.evidence_id not in intel_item_ids
    )

    # Shared registry ensuring each item text is presented in exactly
    # one topic section of the readable report.
    claimed_texts: dict[str, str] = {}

    # Source health is built first so the research snapshot can quote
    # a source count consistent with the source health layer.
    source_health = _build_source_health(lineage, intelligence)

    # Build sections from evidence categories, enriched with intel items
    research_snapshot = _build_research_snapshot(
        lineage,
        intelligence,
        total_sources=source_health.total_sources,
    )

    business_context = _build_section_from_evidence(
        SEC_BUSINESS_CONTEXT, "Business Context", section_evidence, intel_items,
        claimed_texts=claimed_texts,
    )
    financial_performance = _build_section_from_evidence(
        SEC_FINANCIAL_PERFORMANCE, "Financial Performance", section_evidence, intel_items,
        claimed_texts=claimed_texts,
    )
    financial_quality = _build_section_from_evidence(
        SEC_FINANCIAL_QUALITY, "Financial Quality", section_evidence, intel_items,
        claimed_texts=claimed_texts,
    )
    market_context = _build_section_from_evidence(
        SEC_MARKET_CONTEXT, "Market Context", section_evidence, intel_items,
        claimed_texts=claimed_texts,
    )
    business_developments = _build_section_from_evidence(
        SEC_BUSINESS_DEVELOPMENTS, "Business Developments", section_evidence, intel_items,
        claimed_texts=claimed_texts,
    )
    management_strategy = _build_section_from_evidence(
        SEC_MANAGEMENT_STRATEGY, "Management & Strategy", section_evidence, intel_items,
        claimed_texts=claimed_texts,
    )
    competitive_position = _build_section_from_evidence(
        SEC_COMPETITIVE_POSITION, "Competitive Position", section_evidence, intel_items,
        claimed_texts=claimed_texts,
    )
    innovation = _build_section_from_evidence(
        SEC_INNOVATION, "Innovation", section_evidence, intel_items,
        claimed_texts=claimed_texts,
    )
    future_technology = _build_section_from_evidence(
        SEC_FUTURE_TECHNOLOGY, "Future Technology", section_evidence, intel_items,
        claimed_texts=claimed_texts,
    )
    industry_context_section = _build_section_from_evidence(
        SEC_INDUSTRY_CONTEXT, "Industry Context", section_evidence, intel_items,
        claimed_texts=claimed_texts,
    )
    capital_allocation = _build_section_from_evidence(
        SEC_CAPITAL_ALLOCATION, "Capital Allocation", section_evidence, intel_items,
        claimed_texts=claimed_texts,
    )
    corporate_actions = _build_section_from_evidence(
        SEC_CORPORATE_ACTIONS, "Corporate Actions", section_evidence, intel_items,
        claimed_texts=claimed_texts,
    )
    timeline_section = _build_section_from_evidence(
        SEC_TIMELINE, "Timeline", section_evidence, intel_items,
        claimed_texts=claimed_texts,
    )

    # Research gaps section from ResearchGapResult
    research_gaps_section = _build_research_gaps_section(research_gaps)

    # Evidence classification sections
    positive_ev = _build_evidence_section(
        "positive_evidence", "Positive Evidence", evidence, "POSITIVE"
    )
    negative_ev = _build_evidence_section(
        "negative_evidence", "Negative Evidence", evidence, "NEGATIVE"
    )
    conflicting_ev = _build_evidence_section(
        "conflicting_evidence", "Conflicting Evidence", evidence, "MIXED"
    )

    # Conflict details from intelligence
    conflict_details = _build_conflict_details(intelligence)

    # Executive overview
    exec_overview = _build_executive_overview(
        lineage, company_name, intel_items, intelligence
    )

    # Provenance chain
    provenance_chain = _build_provenance_chain(lineage)

    # PIT integrity
    pit_integrity = _build_pit_integrity(
        lineage, lineage.as_of, intelligence, acquisition
    )

    # Methodology
    methodology = _build_methodology()

    # Quality layer
    quality_layer = _build_quality_layer(lineage, research_gaps, intelligence)

    return ProfessionalResearchReport(
        symbol=lineage.symbol,
        as_of=lineage.as_of,
        company_name=company_name,
        executive_overview=exec_overview,
        research_snapshot=research_snapshot,
        business_context=business_context,
        financial_performance=financial_performance,
        financial_quality=financial_quality,
        market_context=market_context,
        business_developments=business_developments,
        management_strategy=management_strategy,
        competitive_position=competitive_position,
        innovation=innovation,
        future_technology=future_technology,
        industry_context=industry_context_section,
        capital_allocation=capital_allocation,
        corporate_actions=corporate_actions,
        timeline=timeline_section,
        positive_evidence=positive_ev,
        negative_evidence=negative_ev,
        conflicting_evidence=conflicting_ev,
        conflict_details=conflict_details,
        research_gaps=research_gaps_section,
        source_health=source_health,
        provenance_chain=provenance_chain,
        pit_integrity=pit_integrity,
        methodology=methodology,
        quality_layer=quality_layer,
        evidence_lineage=lineage,
    )


__all__ = [
    "ProfessionalResearchReport",
    "ReportConflictDetail",
    "ReportEvidenceSection",
    "ReportExecutiveOverview",
    "ReportItem",
    "ReportMethodology",
    "ReportPITIntegrity",
    "ReportProvenanceChain",
    "ReportQualityIndicator",
    "ReportQualityLayer",
    "ReportSection",
    "ReportSourceHealth",
    "SectionEpistemic",
    "build_professional_report",
]
