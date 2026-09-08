"""
Research Product Builders (T1-W4).

Builds deterministic ResearchSnapshot and ResearchSectionRegistry
from existing verification results. These are the canonical
consolidation points that the frontend can call.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.research.section_registry import (
    CANONICAL_SECTIONS,
    ResearchSectionRegistry,
    SectionEntry,
)
from src.research.snapshot import (
    ResearchSnapshot,
    SnapshotChange,
    SnapshotConflict,
    SnapshotCoverage,
    SnapshotCoverageArea,
    SnapshotEvidence,
    SnapshotFreshness,
    SnapshotGap,
    SnapshotIdentity,
    SnapshotObservation,
    SnapshotProvenance,
    SnapshotSource,
)
from src.research.vocabulary import (
    ConflictResolution,
    ResearchAvailability,
    ResearchDirection,
    ResearchGapStatus,
    SourceFreshness,
)


def _extract_identity(result, *, as_of: datetime) -> SnapshotIdentity:
    """Extract company identity and PIT accounting from a verification result."""
    intel = result.intelligence
    pit = getattr(result, "pit_checks", None) or {}

    symbol = getattr(result, "symbol", None) or getattr(result, "company", "") or ""
    company_name = getattr(result, "company", None)
    sector = getattr(result, "sector", None)

    # Compute PIT accounting from pit_checks dict
    pit_passed = all(v for v in pit.values()) if isinstance(pit, dict) and pit else False
    evidence_included = getattr(result, "financial_record_count", 0) or 0

    return SnapshotIdentity(
        symbol=symbol,
        company_name=company_name,
        sector=sector,
        as_of=as_of,
        effective_as_of=as_of,
        market_as_of=as_of,
        requested_as_of=as_of,
        pit_checks_passed=pit_passed,
        future_evidence_excluded=0,
        evidence_included=evidence_included,
    )


def _extract_evidence(result) -> SnapshotEvidence:
    """Extract evidence summary from a verification result."""
    intel = result.intelligence
    evidence_items = getattr(result, "evidence_items", None) or []

    positive = 0
    negative = 0
    neutral = 0
    conflicting = 0
    epistemic_counts: dict[str, int] = {}
    evidence_ids: list[str] = []
    source_ids_set: set[str] = set()
    provenance_ids_set: set[str] = set()

    for item in evidence_items:
        eid = getattr(item, "evidence_id", None)
        if eid:
            evidence_ids.append(eid)
        direction = str(getattr(item, "direction", "NEUTRAL")).upper()
        if direction == "POSITIVE":
            positive += 1
        elif direction == "NEGATIVE":
            negative += 1
        elif direction in ("NEUTRAL", "UNKNOWN"):
            neutral += 1
        else:
            conflicting += 1

        ep_type = str(getattr(item, "epistemic_type", "UNKNOWN"))
        epistemic_counts[ep_type] = epistemic_counts.get(ep_type, 0) + 1

        for sid in getattr(item, "source_ids", ()) or ():
            source_ids_set.add(sid)
        for pid in getattr(item, "provenance_ids", ()) or ():
            provenance_ids_set.add(pid)

    total = positive + negative + neutral + conflicting
    direction = ResearchDirection.UNKNOWN
    if total > 0:
        if positive > negative and positive > neutral:
            direction = ResearchDirection.POSITIVE
        elif negative > positive and negative > neutral:
            direction = ResearchDirection.NEGATIVE
        elif positive == 0 and negative == 0:
            direction = ResearchDirection.NEUTRAL

    return SnapshotEvidence(
        total_count=total,
        positive_count=positive,
        negative_count=negative,
        neutral_count=neutral,
        conflicting_count=conflicting,
        direction=direction,
        epistemic_counts=epistemic_counts,
        evidence_ids=tuple(evidence_ids),
        source_ids=tuple(sorted(source_ids_set)),
        provenance_ids=tuple(sorted(provenance_ids_set)),
    )


def _extract_freshness(result) -> SnapshotFreshness:
    """Extract source freshness summary."""
    intel = result.intelligence
    source_statuses = getattr(intel, "source_statuses", None) or [] if intel else []

    current = 0
    stale = 0
    missing = 0
    degraded = 0
    unknown = 0

    for src in source_statuses:
        state = str(getattr(src, "freshness_state", "UNKNOWN")).upper()
        if state == "CURRENT":
            current += 1
        elif state == "STALE":
            stale += 1
        elif state == "MISSING":
            missing += 1
        elif state == "DEGRADED":
            degraded += 1
        else:
            unknown += 1

    return SnapshotFreshness(
        current_count=current,
        stale_count=stale,
        missing_count=missing,
        degraded_count=degraded,
        unknown_count=unknown,
        total_sources=current + stale + missing + degraded + unknown,
    )


def _extract_sources(result) -> tuple[SnapshotSource, ...]:
    """Extract source records."""
    intel = result.intelligence
    source_statuses = getattr(intel, "source_statuses", None) or [] if intel else []

    sources = []
    for src in source_statuses:
        name = getattr(src, "source_name", "unknown")
        state_str = str(getattr(src, "freshness_state", "UNKNOWN")).upper()
        try:
            freshness = SourceFreshness(state_str)
        except ValueError:
            freshness = SourceFreshness.UNKNOWN

        evidence_count = getattr(src, "item_count", 0) or 0
        categories = tuple(getattr(src, "categories", None) or [])
        pit_eligible = getattr(src, "pit_eligible", False)

        sources.append(SnapshotSource(
            source_name=name,
            freshness=freshness,
            evidence_count=evidence_count,
            categories=categories,
            pit_eligible=pit_eligible,
        ))

    return tuple(sources)


def _extract_conflicts(result) -> tuple[SnapshotConflict, ...]:
    """Extract conflict summary records."""
    intel = result.intelligence
    conflicts = getattr(intel, "conflicts", None) or [] if intel else []

    records = []
    for c in conflicts:
        cid = getattr(c, "conflict_id", "")
        topic = getattr(c, "topic", "")
        status_str = str(getattr(c, "status", "OPEN")).upper()
        try:
            status = ConflictResolution(status_str)
        except ValueError:
            status = ConflictResolution.OPEN

        side_a = ""
        side_b = ""
        sides = getattr(c, "sides", None) or []
        if len(sides) >= 2:
            side_a = getattr(sides[0], "title", "") or str(sides[0])
            side_b = getattr(sides[1], "title", "") or str(sides[1])
        elif len(sides) == 1:
            side_a = getattr(sides[0], "title", "") or str(sides[0])

        records.append(SnapshotConflict(
            conflict_id=cid,
            topic=topic,
            status=status,
            side_a_summary=side_a,
            side_b_summary=side_b,
        ))

    return tuple(records)


def _extract_gaps(result) -> tuple[SnapshotGap, ...]:
    """Extract research gap records."""
    intel = result.intelligence
    gaps_data = None
    if intel:
        rg = getattr(intel, "research_gaps", None)
        if rg:
            gaps_data = getattr(rg, "gaps", None) or []

    if not gaps_data:
        return ()

    records = []
    for g in gaps_data:
        gid = getattr(g, "gap_id", "")
        category = getattr(g, "category", "")
        description = getattr(g, "gap", "") or getattr(g, "description", "")
        status_str = str(getattr(g, "status", "UNAVAILABLE")).upper()
        try:
            status = ResearchGapStatus(status_str)
        except ValueError:
            status = ResearchGapStatus.UNAVAILABLE
        severity = getattr(g, "severity", "LOW") or "LOW"

        records.append(SnapshotGap(
            gap_id=gid,
            category=category,
            description=description,
            status=status,
            severity=severity,
        ))

    return tuple(records)


def _extract_observations(result) -> tuple[SnapshotObservation, ...]:
    """Extract key observations from financial quality and business/tech."""
    observations: list[SnapshotObservation] = []
    intel = result.intelligence

    # Financial quality observations
    if intel and hasattr(intel, "deep_financial_insights") and intel.deep_financial_insights:
        dfi = intel.deep_financial_insights
        for obs in getattr(dfi, "observations", None) or []:
            observations.append(SnapshotObservation(
                observation_id=getattr(obs, "observation_id", ""),
                metric=getattr(obs, "metric", "") or getattr(obs, "label", ""),
                domain="financial",
                value=str(obs.get("value")) if isinstance(obs, dict) else str(getattr(obs, "value", None)),
                unit=getattr(obs, "unit", ""),
                direction=ResearchDirection.NEUTRAL,
                epistemic_type="DERIVED",
                available=True,
            ))

    # Source status count
    return tuple(observations)


def build_research_snapshot(
    result,
    *,
    as_of: datetime | None = None,
    changes=(),
) -> ResearchSnapshot:
    """
    Build a deterministic ResearchSnapshot from a verification result.

    Consolidates all research outputs for a company at a given as_of.
    """
    if as_of is None:
        as_of = getattr(result, "as_of", datetime.now(timezone.utc))

    identity = _extract_identity(result, as_of=as_of)
    evidence = _extract_evidence(result)
    freshness = _extract_freshness(result)
    sources = _extract_sources(result)
    conflicts = _extract_conflicts(result)
    gaps = _extract_gaps(result)
    observations = _extract_observations(result)

    # Changes
    change_records = []
    for ch in changes or ():
        change_records.append(SnapshotChange(
            change_id=getattr(ch, "change_id", ""),
            change_type=str(getattr(ch, "change_type", "")),
            title=getattr(ch, "title", ""),
            description=getattr(ch, "description", ""),
            source=getattr(ch, "source", ""),
            before=getattr(ch, "before", None),
            after=getattr(ch, "after", None),
            why_changed=getattr(ch, "why_changed", None),
            pit_eligible=getattr(ch, "pit_eligible", True),
        ))

    # Coverage
    intel = result.intelligence
    coverage_by_kind = {}
    if intel:
        cov = getattr(intel, "coverage", None) or {}
        if isinstance(cov, dict):
            coverage_by_kind = cov

    coverage_areas = []
    for kind, count in sorted(coverage_by_kind.items()):
        status = ResearchAvailability.AVAILABLE if count > 0 else ResearchAvailability.MISSING
        coverage_areas.append(SnapshotCoverageArea(
            area=kind,
            status=status,
            item_count=count if isinstance(count, int) else 0,
        ))

    available_c = sum(1 for a in coverage_areas if a.status == ResearchAvailability.AVAILABLE)
    coverage = SnapshotCoverage(
        area_count=len(coverage_areas),
        available_count=available_c,
        limited_count=0,
        missing_count=len(coverage_areas) - available_c,
        stale_count=0,
        conflicting_count=0,
        areas=tuple(coverage_areas),
    )

    # Provenance
    prov_ids: set[str] = set()
    src_ids: set[str] = set()
    for item in getattr(result, "evidence_items", None) or ():
        for pid in getattr(item, "provenance_ids", ()) or ():
            prov_ids.add(pid)
        for sid in getattr(item, "source_ids", ()) or ():
            src_ids.add(sid)

    provenance = SnapshotProvenance(
        total_provenance=len(prov_ids),
        total_sources=len(src_ids),
        provenance_ids=tuple(sorted(prov_ids)),
        source_ids=tuple(sorted(src_ids)),
    )

    # Financial counts
    fin_obs_count = 0
    fin_derived_count = 0
    if intel and hasattr(intel, "deep_financial_insights") and intel.deep_financial_insights:
        dfi = intel.deep_financial_insights
        fin_obs_count = len(getattr(dfi, "observations", None) or [])

    return ResearchSnapshot(
        symbol=identity.symbol,
        as_of=as_of,
        identity=identity,
        changes=tuple(change_records),
        change_count=len(change_records),
        observations=observations,
        observation_count=len(observations),
        evidence=evidence,
        financial_observation_count=fin_obs_count,
        financial_derived_count=fin_derived_count,
        coverage=coverage,
        conflicts=conflicts,
        conflict_count=len(conflicts),
        gaps=gaps,
        gap_count=len(gaps),
        freshness=freshness,
        sources=sources,
        source_count=len(sources),
        provenance=provenance,
    )


def build_section_registry(
    result,
    *,
    as_of: datetime | None = None,
) -> ResearchSectionRegistry:
    """
    Build a deterministic ResearchSectionRegistry from a verification result.

    Describes which research sections are available and their metadata.
    """
    if as_of is None:
        as_of = getattr(result, "as_of", datetime.now(timezone.utc))

    symbol = getattr(result, "symbol", None) or getattr(result, "company", "") or ""
    intel = result.intelligence

    sections: list[SectionEntry] = []

    for section_id, title, domain in CANONICAL_SECTIONS:
        available = False
        item_count = 0
        source_count = 0
        limitations: str | None = None

        if section_id == "overview":
            available = True
            item_count = 1
        elif section_id == "financials":
            if intel and hasattr(intel, "deep_financial_insights") and intel.deep_financial_insights:
                dfi = intel.deep_financial_insights
                observations = getattr(dfi, "observations", None) or []
                item_count = len(observations)
                available = item_count > 0
        elif section_id == "business":
            if intel:
                biz = getattr(intel, "business_events", None) or []
                item_count = len(biz)
                available = item_count > 0
        elif section_id == "market":
            available = True
            item_count = 1
        elif section_id == "technology":
            if intel:
                tech = getattr(intel, "indirect_intelligence", None) or []
                item_count = len(tech)
                available = item_count > 0
            limitations = "Technology evidence from indirect intelligence only"
        elif section_id == "events":
            if intel and getattr(intel, "timeline", None):
                entries = getattr(intel.timeline, "entries", None) or []
                item_count = len(entries)
                available = item_count > 0
        elif section_id == "evidence":
            evidence_items = getattr(result, "evidence_items", None) or []
            item_count = len(evidence_items)
            available = item_count > 0
        elif section_id == "coverage":
            if intel:
                cov = getattr(intel, "coverage", None) or {}
                if isinstance(cov, dict):
                    item_count = len(cov)
                    available = item_count > 0
        elif section_id == "provenance":
            prov_ids: set[str] = set()
            for item in getattr(result, "evidence_items", None) or ():
                for pid in getattr(item, "provenance_ids", ()) or ():
                    prov_ids.add(pid)
            item_count = len(prov_ids)
            available = item_count > 0

        # Source count from source statuses
        if intel:
            source_statuses = getattr(intel, "source_statuses", None) or []
            source_count = len(source_statuses)

        coverage_state = ResearchAvailability.AVAILABLE if available else ResearchAvailability.MISSING
        if item_count > 0 and not available:
            coverage_state = ResearchAvailability.LIMITED

        sections.append(SectionEntry(
            section_id=section_id,
            title=title,
            domain=domain,
            available=available,
            item_count=item_count,
            coverage_state=coverage_state,
            as_of=as_of,
            source_count=source_count,
            limitations=limitations,
        ))

    available_count = sum(1 for s in sections if s.available)

    return ResearchSectionRegistry(
        symbol=symbol,
        as_of=as_of,
        sections=tuple(sections),
        total_sections=len(sections),
        available_sections=available_count,
        unavailable_sections=len(sections) - available_count,
    )
