"""
Evidence lineage resolution.

Builds the canonical lineage chain:
  SOURCE → SOURCE RECORD → EVIDENCE ITEM → OBSERVATION/FEATURE → CLAIM

Reuses existing DataProvenance, ResearchSource, SourceProfile,
EvidenceItem, and CorporateIntelItem models.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from src.research.company_intel.semantics import VerificationStatus
from src.research.evidence.models import (
    CanonicalEvidenceItem,
    EpistemicType,
    EvidenceClaim,
    EvidenceLineage,
    EvidenceSourceInfo,
    EvidenceSourceRecordInfo,
)
from src.research.provenance import DataProvenance, is_known_at
from src.research.source_catalog import ResearchSource, get_source
from src.research.source_reliability import (
    SourceReliabilityTier,
    get_default_source_profile,
)
from src.research.synthesis.models import EvidenceItem


def resolve_source_profile(
    source_id: str,
) -> EvidenceSourceInfo | None:
    """
    Resolve a source_id to its canonical source profile.

    Tries ResearchSource catalog first, then SourceProfile defaults.
    Returns None if the source is unknown.
    """

    try:
        research_source: ResearchSource = get_source(source_id)
        return EvidenceSourceInfo(
            source_id=research_source.source_id,
            name=research_source.name,
            source_type=research_source.domain.value,
            tier=research_source.tier.value,
            domain=research_source.domain.value,
            official=research_source.tier.value == "PRIMARY",
            requires_confirmation=False,
            reliability_tier=_reliability_tier_for_source(
                research_source
            ),
        )
    except KeyError:
        pass

    profile = get_default_source_profile(source_id)
    if profile is not None:
        return EvidenceSourceInfo(
            source_id=source_id,
            name=profile.name,
            source_type=profile.source_type,
            tier=profile.tier.value,
            domain=None,
            official=profile.official,
            requires_confirmation=profile.requires_confirmation,
            reliability_tier=profile.tier.value,
        )

    return None


def _reliability_tier_for_source(
    source: ResearchSource,
) -> str:
    """Map ResearchSource to a reliability tier string."""

    if source.tier.value == "PRIMARY":
        return SourceReliabilityTier.TIER_1.value

    if source.tier.value == "SECONDARY":
        return SourceReliabilityTier.TIER_2.value

    return SourceReliabilityTier.UNKNOWN.value


def resolve_source_records(
    provenance_ids: tuple[str, ...],
    provenance_map: dict[str, DataProvenance],
) -> tuple[EvidenceSourceRecordInfo, ...]:
    """
    Resolve provenance IDs to their canonical source records.
    """

    records: list[EvidenceSourceRecordInfo] = []

    for prov_id in provenance_ids:
        prov = provenance_map.get(prov_id)
        if prov is None:
            continue

        records.append(
            EvidenceSourceRecordInfo(
                source=prov.source,
                source_url=prov.source_url,
                retrieved_at=prov.retrieved_at,
                published_at=prov.published_at,
                available_at=prov.available_at,
                dataset_id=prov.dataset_id,
                record_id=prov.record_id,
                checksum=prov.checksum,
            )
        )

    return tuple(records)


def _classify_epistemic(
    evidence_item: EvidenceItem,
) -> EpistemicType:
    """
    Classify the epistemic type of an evidence item.

    Uses the existing evidence_type and reliability to infer
    how the evidence was produced.
    """

    from src.research.synthesis.models import EvidenceType

    # REPORTED: directly observed or disclosed facts
    if evidence_item.evidence_type in {
        EvidenceType.MARKET,
        EvidenceType.ACQUIRED,
        EvidenceType.COMPANY_INTELLIGENCE,
        EvidenceType.FUTURE_TECHNOLOGY,
    }:
        return EpistemicType.REPORTED

    # DERIVED: computed or feature-based evidence
    if evidence_item.evidence_type == EvidenceType.FEATURE:
        return EpistemicType.DERIVED

    # INFERRED: signal, trend, risk analysis
    if evidence_item.evidence_type in {
        EvidenceType.SIGNAL,
        EvidenceType.TREND,
        EvidenceType.RISK,
    }:
        return EpistemicType.INFERRED

    return EpistemicType.UNKNOWN


def _evidence_item_to_canonical(
    item: EvidenceItem,
    *,
    source_profiles: dict[str, EvidenceSourceInfo],
    provenance_map: dict[str, DataProvenance],
) -> CanonicalEvidenceItem:
    """
    Convert a synthesis EvidenceItem to a CanonicalEvidenceItem
    with resolved lineage.
    """

    primary_source_id = item.source_ids[0] if item.source_ids else ""
    source_info = source_profiles.get(primary_source_id)

    source_records = resolve_source_records(
        item.provenance_ids, provenance_map
    )

    return CanonicalEvidenceItem(
        evidence_id=item.evidence_id,
        symbol=item.symbol,
        title=item.title,
        explanation=item.explanation,
        evidence_type=item.evidence_type.value,
        direction=item.direction.value,
        confidence=str(item.confidence),
        reliability=item.reliability.value,
        epistemic_type=_classify_epistemic(item),
        verification_status=_infer_verification_status(item),
        observation_at=item.observation_at,
        source_ids=item.source_ids,
        provenance_ids=item.provenance_ids,
        source_info=source_info,
        source_records=source_records,
        category=item.evidence_type.value,
    )


def _infer_verification_status(item: EvidenceItem) -> str:
    """
    Infer verification status from evidence properties.

    Uses reliability and confidence to determine status.
    """

    from src.research.synthesis.models import EvidenceReliability

    if item.reliability in (
        EvidenceReliability.REGULATORY,
        EvidenceReliability.AUDITED,
        EvidenceReliability.PRIMARY,
    ):
        if item.confidence >= Decimal("0.8"):
            return VerificationStatus.CONFIRMED.value
        return VerificationStatus.REPORTED.value

    if item.reliability == EvidenceReliability.SECONDARY:
        return VerificationStatus.REPORTED.value

    if item.reliability == EvidenceReliability.TERTIARY:
        return VerificationStatus.UNVERIFIED.value

    return VerificationStatus.UNVERIFIED.value


def _intel_item_to_canonical(
    item: object,
    *,
    symbol: str,
    source_profiles: dict[str, EvidenceSourceInfo],
    provenance_map: dict[str, DataProvenance],
) -> CanonicalEvidenceItem | None:
    """
    Convert a CorporateIntelItem to a CanonicalEvidenceItem.

    Returns None if the item cannot be converted.
    """

    from src.research.company_intel.models import CorporateIntelItem

    if not isinstance(item, CorporateIntelItem):
        return None

    source_name = item.source.source_name if item.source else ""
    source_info = source_profiles.get(source_name)

    provenance_ids = ()
    if item.provenance_id:
        provenance_ids = (item.provenance_id,)

    source_records = resolve_source_records(
        provenance_ids, provenance_map
    )

    return CanonicalEvidenceItem(
        evidence_id=item.item_id,
        symbol=item.symbol,
        title=item.title,
        explanation=item.description or item.title,
        evidence_type=item.kind.value,
        direction=item.direction.value,
        confidence=str(item.confidence or Decimal("0")),
        reliability=_reliability_for_intel(item),
        epistemic_type=_epistemic_for_intel(item),
        verification_status=item.verification_status.value,
        published_at=item.published_at,
        available_at=item.available_at,
        source_ids=(source_name,) if source_name else (),
        provenance_ids=provenance_ids,
        source_info=source_info,
        source_records=source_records,
        category=item.intel_category.value
        if item.intel_category
        else item.kind.value,
        topic=item.topic,
        derivation=item.derivation,
    )


def _reliability_for_intel(item: object) -> str:
    """Map CorporateIntelItem to evidence reliability string."""

    from src.research.company_intel.models import CorporateIntelItem

    if not isinstance(item, CorporateIntelItem):
        return "UNKNOWN"

    tier = item.source.reliability_tier if item.source else 6

    if tier in (1, 2):
        return "PRIMARY"

    if tier == 3:
        return "SECONDARY"

    return "UNKNOWN"


def _epistemic_for_intel(item: object) -> EpistemicType:
    """Classify epistemic type for a CorporateIntelItem."""

    from src.research.company_intel.models import CorporateIntelItem
    from src.research.company_intel.semantics import (
        SemanticCategory,
    )

    if not isinstance(item, CorporateIntelItem):
        return EpistemicType.UNKNOWN

    if item.semantic_category == SemanticCategory.FACT:
        return EpistemicType.REPORTED

    if item.semantic_category == SemanticCategory.DERIVED_METRIC:
        return EpistemicType.DERIVED

    if item.semantic_category == SemanticCategory.OBSERVATION:
        return EpistemicType.INFERRED

    if item.semantic_category == SemanticCategory.MANAGEMENT_COMMENTARY:
        return EpistemicType.REPORTED

    if item.semantic_category == SemanticCategory.REPORTED_CLAIM:
        return EpistemicType.REPORTED

    if item.semantic_category == SemanticCategory.ALLEGATION:
        return EpistemicType.REPORTED

    if item.semantic_category == SemanticCategory.CONCLUSION:
        return EpistemicType.INFERRED

    return EpistemicType.UNKNOWN


def _build_claims_from_evidence(
    evidence: tuple[CanonicalEvidenceItem, ...],
    symbol: str,
    as_of: datetime,
) -> tuple[EvidenceClaim, ...]:
    """
    Build traceable claims from canonical evidence items.

    Each evidence item produces one claim that captures its
    core assertion.
    """

    claims: list[EvidenceClaim] = []

    for idx, item in enumerate(evidence, start=1):
        claim_id = f"CLAIM:{symbol}:{idx:04d}"

        claims.append(
            EvidenceClaim(
                claim_id=claim_id,
                symbol=item.symbol,
                text=item.title,
                category=item.category,
                epistemic_type=item.epistemic_type,
                confidence=item.confidence,
                verification_status=item.verification_status,
                evidence_ids=(item.evidence_id,),
                source_ids=item.source_ids,
                observation_at=item.observation_at or as_of,
            )
        )

    return tuple(claims)


def filter_evidence_by_pit(
    evidence: tuple[CanonicalEvidenceItem, ...],
    as_of: datetime,
) -> tuple[CanonicalEvidenceItem, ...]:
    """
    Filter evidence items by point-in-time availability.

    Uses the existing is_known_at pattern from DataProvenance.
    Items without available_at are excluded from PIT queries.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    filtered: list[CanonicalEvidenceItem] = []

    for item in evidence:
        if item.observation_at is not None:
            if item.observation_at > as_of:
                continue

        if item.available_at is not None:
            if item.available_at > as_of:
                continue

        filtered.append(item)

    return tuple(filtered)


def _build_provenance_map(
    evidence_items: tuple[EvidenceItem, ...],
) -> dict[str, DataProvenance]:
    """
    Build a mapping from provenance IDs to DataProvenance objects.

    Extracts provenance information from evidence items.
    """

    prov_map: dict[str, DataProvenance] = {}

    for item in evidence_items:
        for prov_id in item.provenance_ids:
            if prov_id not in prov_map:
                prov_map[prov_id] = DataProvenance(
                    source=prov_id,
                    source_url=None,
                    retrieved_at=item.observation_at,
                    published_at=None,
                    available_at=item.observation_at,
                )

    return prov_map


def _build_source_profiles(
    evidence: tuple[CanonicalEvidenceItem, ...],
) -> dict[str, EvidenceSourceInfo]:
    """
    Build a mapping from source IDs to source profiles.
    """

    profiles: dict[str, EvidenceSourceInfo] = {}

    for item in evidence:
        if item.source_info is not None:
            for source_id in item.source_ids:
                if source_id not in profiles:
                    profiles[source_id] = item.source_info

    return profiles


def _count_by_field(
    evidence: tuple[CanonicalEvidenceItem, ...],
    field_name: str,
) -> dict[str, int]:
    """Count evidence items by a string field."""

    counts: dict[str, int] = defaultdict(int)

    for item in evidence:
        value = getattr(item, field_name, "")
        if isinstance(value, EpistemicType):
            value = value.value
        counts[str(value)] += 1

    return dict(counts)


def build_evidence_lineage(
    *,
    symbol: str,
    as_of: datetime,
    evidence_items: tuple[EvidenceItem, ...] = (),
    intel_items: tuple[object, ...] = (),
    pit_filter: bool = True,
) -> EvidenceLineage:
    """
    Build the complete evidence lineage for a company.

    This is the main entry point for the F7 evidence lineage system.
    It takes evidence items and intelligence items, resolves their
    lineage to sources and provenance, and returns a unified
    EvidenceLineage object.

    Parameters
    ----------
    symbol : str
        Company symbol (e.g., "TCS").
    as_of : datetime
        Point-in-time timestamp (timezone-aware).
    evidence_items : tuple[EvidenceItem, ...]
        Evidence items from the synthesis layer.
    intel_items : tuple[object, ...]
        CorporateIntelItem objects from the intelligence layer.
    pit_filter : bool
        Whether to apply point-in-time filtering.
    """

    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")

    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise ValueError("symbol cannot be empty")

    # Build provenance map from evidence items
    provenance_map = _build_provenance_map(evidence_items)

    # Convert evidence items to canonical form
    canonical: list[CanonicalEvidenceItem] = []

    for item in evidence_items:
        if item.symbol != normalized_symbol:
            continue

        source_profiles: dict[str, EvidenceSourceInfo] = {}
        for source_id in item.source_ids:
            profile = resolve_source_profile(source_id)
            if profile is not None:
                source_profiles[source_id] = profile

        canonical.append(
            _evidence_item_to_canonical(
                item,
                source_profiles=source_profiles,
                provenance_map=provenance_map,
            )
        )

    # Convert intel items to canonical form
    for item in intel_items:
        from src.research.company_intel.models import (
            CorporateIntelItem,
        )

        if not isinstance(item, CorporateIntelItem):
            continue

        if item.symbol != normalized_symbol:
            continue

        source_profiles_intel: dict[str, EvidenceSourceInfo] = {}
        source_name = (
            item.source.source_name if item.source else ""
        )
        if source_name:
            profile = resolve_source_profile(source_name)
            if profile is not None:
                source_profiles_intel[source_name] = profile

        canonical_item = _intel_item_to_canonical(
            item,
            symbol=normalized_symbol,
            source_profiles=source_profiles_intel,
            provenance_map=provenance_map,
        )

        if canonical_item is not None:
            canonical.append(canonical_item)

    # Deduplicate by evidence_id
    seen: set[str] = set()
    deduplicated: list[CanonicalEvidenceItem] = []
    for item in canonical:
        if item.evidence_id not in seen:
            seen.add(item.evidence_id)
            deduplicated.append(item)

    canonical_tuple = tuple(deduplicated)

    # Apply PIT filtering
    pit_filtered_count = 0
    if pit_filter:
        before_count = len(canonical_tuple)
        canonical_tuple = filter_evidence_by_pit(
            canonical_tuple, as_of
        )
        pit_filtered_count = before_count - len(canonical_tuple)

    # Sort deterministically: observation_at → confidence → evidence_id
    def _sort_key(item: CanonicalEvidenceItem):
        obs = item.observation_at or datetime.min.replace(
            tzinfo=as_of.tzinfo
        )
        conf = Decimal(item.confidence) if item.confidence else Decimal("0")
        return (obs, conf, item.evidence_id)

    canonical_tuple = tuple(sorted(canonical_tuple, key=_sort_key))

    # Build claims
    claims = _build_claims_from_evidence(
        canonical_tuple, normalized_symbol, as_of
    )

    # Collect source profiles
    all_source_profiles = _build_source_profiles(canonical_tuple)

    # Collect source records
    all_source_records: list[EvidenceSourceRecordInfo] = []
    for item in canonical_tuple:
        all_source_records.extend(item.source_records)

    # Deduplicate source records
    seen_records: set[str] = set()
    unique_records: list[EvidenceSourceRecordInfo] = []
    for rec in all_source_records:
        key = (rec.source, rec.available_at.isoformat() if rec.available_at else "")
        if key not in seen_records:
            seen_records.add(key)
            unique_records.append(rec)

    # Build counts
    epistemic_counts = _count_by_field(
        canonical_tuple, "epistemic_type"
    )
    verification_counts = _count_by_field(
        canonical_tuple, "verification_status"
    )
    evidence_type_counts = _count_by_field(
        canonical_tuple, "evidence_type"
    )
    direction_counts = _count_by_field(
        canonical_tuple, "direction"
    )

    return EvidenceLineage(
        symbol=normalized_symbol,
        as_of=as_of,
        evidence=canonical_tuple,
        claims=claims,
        source_profiles=tuple(all_source_profiles.values()),
        source_records=tuple(unique_records),
        epistemic_type_counts=epistemic_counts,
        verification_status_counts=verification_counts,
        evidence_type_counts=evidence_type_counts,
        direction_counts=direction_counts,
        total_evidence=len(canonical_tuple),
        total_claims=len(claims),
        total_sources=len(all_source_profiles),
        total_provenance=len(unique_records),
        pit_filtered_count=pit_filtered_count,
    )


__all__ = [
    "build_evidence_lineage",
    "filter_evidence_by_pit",
    "resolve_source_profile",
    "resolve_source_records",
]
