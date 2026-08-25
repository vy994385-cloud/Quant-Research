"""
Deterministic research-change detection and context snapshots.

Everything in this module answers one class of question without any
prediction or opinion:

- "What does the record look like at a given as_of?"  (snapshot)
- "What changed between two recorded points in time?" (changes/delta)
- "Which conflicts exist right now?"                  (conflicts)
- "What is coming, as announced?"                     (calendar)

Design rules locked by the product contract:

- Deterministic: identical inputs produce identical outputs; every
  collection is sorted before serialization.
- PIT-safe: both sides of any comparison are produced through the
  recorded research service at their own explicit as_of, so later
  evidence can never leak into an earlier snapshot.
- Provenance-backed: every change carries its source and provenance
  identifiers where the underlying record has them.
- No scores, no rankings, no recommendations: changes describe state
  transitions of the *record*, never quality or direction opinions.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.analysis.research_gaps import ResearchGap
from src.api.recorded_research import COMPANY_NAMES
from src.research.evidence.lineage import build_evidence_lineage
from src.screener.engine import execute_screen
from src.screener.fields import extract_company_fields
from src.verification.real_data import RealDataVerificationResult


def _require_aware(label: str, value: datetime) -> None:
    if value.tzinfo is None:
        raise ValueError(f"{label} must be timezone-aware")


def _as_datetime(value) -> datetime | None:
    """Coerce date-or-datetime to a timezone-aware datetime."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    return None


# ---------------------------------------------------------------------------
# Research-context snapshot contract
# ---------------------------------------------------------------------------


CONTEXT_SCHEMA_VERSION = "2.0.0"


class ResearchContextSnapshot(BaseModel):
    """
    Immutable, replayable description of what the system knew for one
    company at one point in time.

    `context_id` is derived deterministically from symbol + as_of, so
    the same id always replays to the same snapshot content.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: str = CONTEXT_SCHEMA_VERSION
    context_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    company_name: str | None = None
    sector: str | None = None

    universe: tuple[str, ...] = ()
    requested_as_of: datetime | None = None
    effective_as_of: datetime
    market_as_of: datetime | None = None

    as_of: datetime
    evidence_included: int = Field(ge=0)
    acquired_evidence_included: int = Field(ge=0)
    future_evidence_excluded: int = Field(ge=0)

    sources_accepted: int = Field(ge=0)
    sources_discovered: int = Field(ge=0)

    coverage_item_count: int = Field(ge=0)
    coverage_by_kind: dict[str, int] = Field(default_factory=dict)
    missing_categories: tuple[str, ...] = ()

    conflict_count: int = Field(ge=0)
    gap_count: int = Field(ge=0)

    pit_checks_passed: bool
    financial_record_count: int = Field(ge=0)

    provenance_summary: tuple[str, ...] = ()
    research_observations: int = Field(ge=0)
    gap_states: tuple[str, ...] = ()
    conflict_topics: tuple[str, ...] = ()
    freshness_summary: tuple[str, ...] = ()
    source_included: tuple[str, ...] = ()
    source_excluded: tuple[str, ...] = ()

    notes: tuple[str, ...] = ()


def context_id_for(symbol: str, as_of: datetime) -> str:
    """Deterministic, parseable research-context identifier."""

    _require_aware("as_of", as_of)
    stamp = as_of.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    digest = hashlib.sha256(
        f"{symbol.strip().upper()}|{stamp}".encode("utf-8")
    ).hexdigest()[:12]
    return f"rc-{symbol.strip().upper()}-{stamp}-{digest}"


def parse_context_id(context_id: str) -> tuple[str, datetime]:
    """
    Split a well-formed context id back into (symbol, as_of).

    Raises ValueError when the id is malformed or its integrity
    digest does not match — a tampered id never resolves.
    """

    parts = context_id.split("-")
    if len(parts) != 4 or parts[0] != "rc":
        raise ValueError("malformed research-context id")
    _, symbol, stamp, digest = parts
    if len(digest) != 12 or not stamp.endswith("Z") or len(stamp) != 16:
        raise ValueError("malformed research-context id")
    expected = hashlib.sha256(
        f"{symbol}|{stamp}".encode("utf-8")
    ).hexdigest()[:12]
    if digest != expected:
        raise ValueError("research-context id failed integrity check")
    as_of = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(
        tzinfo=timezone.utc
    )
    return symbol, as_of


def build_context_snapshot(
    result: RealDataVerificationResult,
    *,
    universe: tuple[str, ...] = (),
    requested_as_of: datetime | None = None,
) -> ResearchContextSnapshot:
    """Contract-ize one recorded research result."""

    intel = result.intelligence
    status = intel.status if intel is not None else None

    # Reuse the exact PIT accounting already shipped in the research
    # contract so snapshot numbers can never drift from /research.
    from src.api.serializers import _point_in_time

    pit = _point_in_time(result)

    # Provenance summary: unique source ids referenced.
    provenance_ids: set[str] = set()
    for item in (result.evidence_items or ()):
        provenance_ids.update(item.provenance_ids)
    if intel is not None:
        for item in intel.items:
            if item.provenance_id:
                provenance_ids.add(item.provenance_id)

    # Research observations count.
    obs_count = 0
    if intel is not None and intel.deep_financial_insights is not None:
        obs_count = len(intel.deep_financial_insights.observations)

    # Gap states.
    gap_states: tuple[str, ...] = ()
    if intel is not None and intel.research_gaps is not None:
        gap_states = tuple(
            sorted(
                f"{gap.category}:{gap.status}"
                for gap in intel.research_gaps.gaps
            )
        )

    # Conflict topics.
    conflict_topics: tuple[str, ...] = ()
    if intel is not None and intel.conflicts:
        conflict_topics = tuple(
            sorted(c.topic for c in intel.conflicts)
        )

    # Freshness summary.
    freshness_summary: tuple[str, ...] = ()
    if intel is not None:
        freshness_summary = tuple(
            sorted(
                f"{s.source_name}:{'stale' if s.stale else 'fresh'}"
                for s in intel.source_statuses
            )
        )

    # Source included/excluded.
    source_included = tuple(
        sorted(s.source_name for s in (intel.source_statuses if intel else ()) if not s.stale)
    )
    source_excluded = tuple(
        sorted(s.source_name for s in (intel.source_statuses if intel else ()) if s.stale)
    )

    return ResearchContextSnapshot(
        context_id=context_id_for(result.company, result.as_of),
        symbol=result.company,
        company_name=COMPANY_NAMES.get(result.company),
        sector=result.sector,
        universe=universe,
        requested_as_of=requested_as_of,
        effective_as_of=result.as_of,
        as_of=result.as_of,
        evidence_included=int(pit["evidence_included"]),
        acquired_evidence_included=int(pit["acquired_evidence_included"]),
        future_evidence_excluded=int(pit["future_evidence_excluded"]),
        sources_accepted=int(pit["sources_accepted"]),
        sources_discovered=int(pit["sources_discovered"]),
        coverage_item_count=status.coverage.item_count if status else 0,
        coverage_by_kind=dict(sorted((status.coverage.by_kind.items())) if status else {}),
        missing_categories=tuple(status.coverage.missing_categories) if status else (),
        conflict_count=(
            status.quality.conflict_count if status else 0
        ),
        gap_count=(
            len(intel.research_gaps.gaps)
            if intel is not None and intel.research_gaps is not None
            else 0
        ),
        pit_checks_passed=bool(pit["pit_checks_passed"]),
        financial_record_count=result.financial_record_count,
        provenance_summary=tuple(sorted(provenance_ids)),
        research_observations=obs_count,
        gap_states=gap_states,
        conflict_topics=conflict_topics,
        freshness_summary=freshness_summary,
        source_included=source_included,
        source_excluded=source_excluded,
    )


# ---------------------------------------------------------------------------
# Change records
# ---------------------------------------------------------------------------


class ChangeType(str, Enum):
    NEW_EVIDENCE = "NEW_EVIDENCE"
    CHANGED_EVIDENCE = "CHANGED_EVIDENCE"
    RESOLVED_EVIDENCE = "RESOLVED_EVIDENCE"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    REMOVED_EVIDENCE = "REMOVED_EVIDENCE"
    REOPENED_EVIDENCE = "REOPENED_EVIDENCE"
    NEW_FINANCIAL_DISCLOSURE = "NEW_FINANCIAL_DISCLOSURE"
    CHANGED_FINANCIAL_DISCLOSURE = "CHANGED_FINANCIAL_DISCLOSURE"
    NEW_EVENT = "NEW_EVENT"
    CHANGED_EVENT = "CHANGED_EVENT"
    NEW_CORPORATE_ACTION = "NEW_CORPORATE_ACTION"
    NEW_TECHNOLOGY_EVIDENCE = "NEW_TECHNOLOGY_EVIDENCE"
    RESEARCH_GAP_CHANGED = "RESEARCH_GAP_CHANGED"
    RESEARCH_GAP_OPENED = "RESEARCH_GAP_OPENED"
    RESEARCH_GAP_RESOLVED = "RESEARCH_GAP_RESOLVED"
    RESEARCH_GAP_REOPENED = "RESEARCH_GAP_REOPENED"
    SOURCE_BECAME_STALE = "SOURCE_BECAME_STALE"
    SOURCE_BECAME_FRESH = "SOURCE_BECAME_FRESH"
    SCREEN_ENTRY = "SCREEN_ENTRY"
    SCREEN_EXIT = "SCREEN_EXIT"


class ResearchChange(BaseModel):
    """One deterministic state transition of the research record."""

    model_config = ConfigDict(extra="forbid")

    change_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    change_type: ChangeType
    detected_at: datetime
    effective_at: datetime | None = None
    as_of: datetime

    title: str = Field(min_length=1)
    description: str = ""
    source: str | None = None
    provenance: tuple[str, ...] = ()
    related_observation: str | None = None

    before: str | None = None
    after: str | None = None
    why_changed: str | None = None

    previous_state: str | None = None
    current_state: str | None = None
    pit_eligible: bool = True


def _all_items(result: RealDataVerificationResult):
    intel = result.intelligence
    if intel is None:
        return ()
    return (
        tuple(intel.business_events)
        + tuple(intel.management_commentary)
        + tuple(intel.risk_intelligence)
        + tuple(intel.indirect_intelligence)
        + tuple(intel.financial_intelligence_items)
        + tuple(intel.other_intelligence)
    )


def _items_by_id(result):
    return {item.item_id: item for item in _all_items(result)}


def _lineage(result):
    intel = result.intelligence
    return build_evidence_lineage(
        symbol=result.company,
        as_of=result.as_of,
        evidence_items=result.evidence_items,
        intel_items=intel.items if intel is not None else (),
        pit_filter=True,
    )


def _gap_key(gap: ResearchGap) -> str:
    raw = f"{gap.category}|{gap.gap}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _observation_key(obs) -> str:
    period = obs.period_end if hasattr(obs, "period_end") else ""
    kind = getattr(obs, "observation_type", "")
    return f"{obs.metric}|{period}|{kind}"


def _change(
    *,
    change_type: ChangeType,
    symbol: str,
    detected_at: datetime,
    title: str,
    description: str = "",
    effective_at: datetime | None = None,
    source: str | None = None,
    provenance: tuple[str, ...] = (),
    related: str | None = None,
    before: str | None = None,
    after: str | None = None,
    why_changed: str | None = None,
    previous_state: str | None = None,
    current_state: str | None = None,
    pit_eligible: bool = True,
) -> ResearchChange:
    digest = hashlib.sha256(
        "|".join(
            [
                symbol,
                change_type.value,
                related or title,
                previous_state or "",
                current_state or "",
            ]
        ).encode("utf-8")
    ).hexdigest()[:16]
    return ResearchChange(
        change_id=f"chg-{digest}",
        symbol=symbol,
        change_type=change_type,
        detected_at=detected_at,
        effective_at=effective_at,
        as_of=detected_at,
        title=title,
        description=description,
        source=source,
        provenance=tuple(sorted(provenance)),
        related_observation=related,
        before=before,
        after=after,
        why_changed=why_changed,
        previous_state=previous_state,
        current_state=current_state,
        pit_eligible=pit_eligible,
    )


def _item_changes(
    prev_result: RealDataVerificationResult,
    curr_result: RealDataVerificationResult,
) -> list[ResearchChange]:
    """Item-level additions and changes classified into typed change records."""

    prev_items = _items_by_id(prev_result)
    curr_items = _items_by_id(curr_result)
    changes: list[ResearchChange] = []

    for item_id, item in curr_items.items():
        if item_id not in prev_items:
            category_value = (
                item.intel_category.value
                if item.intel_category is not None
                else ""
            )

            if category_value == "CORPORATE_ACTION":
                change_type = ChangeType.NEW_CORPORATE_ACTION
            elif category_value == "PRODUCT_BUSINESS_UPDATE":
                change_type = ChangeType.NEW_TECHNOLOGY_EVIDENCE
            elif item.kind.value == "FINANCIAL_PERIOD":
                change_type = ChangeType.NEW_EVENT
            else:
                change_type = ChangeType.NEW_EVENT

            effective = item.effective_at or item.published_at or item.available_at
            changes.append(
                _change(
                    change_type=change_type,
                    symbol=item.symbol,
                    detected_at=curr_result.as_of,
                    effective_at=effective,
                    title=item.title,
                    description=item.description,
                    source=item.source.source_name,
                    provenance=(item.provenance_id,) if item.provenance_id else (),
                    related=item.item_id,
                    before=None,
                    after=item.description or item.title,
                    why_changed="New item recorded",
                    previous_state="ABSENT",
                    current_state=str(item.verification_status.value),
                    pit_eligible=(
                        item.available_at is not None
                        and item.available_at <= curr_result.as_of
                    ),
                )
            )
        else:
            prev_item = prev_items[item_id]
            changed_fields = []
            for field_name in ("title", "description", "verification_status"):
                old_val = str(getattr(prev_item, field_name, ""))
                new_val = str(getattr(item, field_name, ""))
                if old_val != new_val:
                    changed_fields.append(field_name)
            if changed_fields:
                category_value = (
                    item.intel_category.value
                    if item.intel_category is not None
                    else ""
                )
                if category_value == "CORPORATE_ACTION":
                    change_type = ChangeType.NEW_CORPORATE_ACTION
                else:
                    change_type = ChangeType.CHANGED_EVENT
                changes.append(
                    _change(
                        change_type=change_type,
                        symbol=item.symbol,
                        detected_at=curr_result.as_of,
                        effective_at=item.effective_at or item.published_at,
                        title=f"Changed: {item.title}",
                        description=f"Fields changed: {', '.join(changed_fields)}",
                        source=item.source.source_name,
                        provenance=(item.provenance_id,) if item.provenance_id else (),
                        related=item.item_id,
                        before=str(getattr(prev_item, changed_fields[0], "")),
                        after=str(getattr(item, changed_fields[0], "")),
                        why_changed=f"Field(s) changed: {', '.join(changed_fields)}",
                        previous_state=str(prev_item.verification_status.value),
                        current_state=str(item.verification_status.value),
                        pit_eligible=True,
                    )
                )

    for item_id, item in prev_items.items():
        if item_id not in curr_items:
            changes.append(
                _change(
                    change_type=ChangeType.REMOVED_EVIDENCE,
                    symbol=item.symbol,
                    detected_at=curr_result.as_of,
                    title=f"Removed: {item.title}",
                    description=item.description,
                    source=item.source.source_name,
                    provenance=(item.provenance_id,) if item.provenance_id else (),
                    related=item.item_id,
                    before=item.title,
                    after=None,
                    why_changed="Item no longer present in current record",
                    previous_state=str(item.verification_status.value),
                    current_state="REMOVED",
                    pit_eligible=True,
                )
            )

    return changes


def _evidence_changes(
    prev_result: RealDataVerificationResult,
    curr_result: RealDataVerificationResult,
) -> list[ResearchChange]:
    prev_lineage = _lineage(prev_result)
    curr_lineage = _lineage(curr_result)
    prev_ids = {item.evidence_id for item in prev_lineage.evidence}
    prev_by_id = {item.evidence_id: item for item in prev_lineage.evidence}

    changes: list[ResearchChange] = []
    for item in curr_lineage.evidence:
        if item.evidence_id in prev_ids:
            prev_item = prev_by_id[item.evidence_id]
            # Detect changed evidence
            changed = False
            for field in ("title", "explanation", "verification_status"):
                if getattr(prev_item, field, "") != getattr(item, field, ""):
                    changed = True
                    break
            if changed:
                changes.append(
                    _change(
                        change_type=ChangeType.CHANGED_EVIDENCE,
                        symbol=item.symbol,
                        detected_at=curr_result.as_of,
                        effective_at=item.published_at
                        or item.observation_at
                        or item.available_at,
                        title=f"Changed: {item.title}",
                        description=item.explanation,
                        source=", ".join(item.source_ids),
                        provenance=item.provenance_ids,
                        related=item.evidence_id,
                        before=prev_item.title,
                        after=item.title,
                        why_changed="Evidence record content changed",
                        previous_state=prev_item.verification_status,
                        current_state=item.verification_status,
                        pit_eligible=(
                            item.available_at is not None
                            and item.available_at <= curr_result.as_of
                        ),
                    )
                )
        else:
            changes.append(
                _change(
                    change_type=ChangeType.NEW_EVIDENCE,
                    symbol=item.symbol,
                    detected_at=curr_result.as_of,
                    effective_at=item.published_at
                    or item.observation_at
                    or item.available_at,
                    title=item.title,
                    description=item.explanation,
                    source=", ".join(item.source_ids),
                    provenance=item.provenance_ids,
                    related=item.evidence_id,
                    before=None,
                    after=item.title,
                    why_changed="New evidence recorded",
                    previous_state="ABSENT",
                    current_state=item.verification_status,
                    pit_eligible=(
                        item.available_at is not None
                        and item.available_at <= curr_result.as_of
                    ),
                )
            )

    # Detect removed evidence
    curr_ids = {item.evidence_id for item in curr_lineage.evidence}
    for item in prev_lineage.evidence:
        if item.evidence_id not in curr_ids:
            changes.append(
                _change(
                    change_type=ChangeType.REMOVED_EVIDENCE,
                    symbol=item.symbol,
                    detected_at=curr_result.as_of,
                    effective_at=item.published_at
                    or item.observation_at
                    or item.available_at,
                    title=f"Removed: {item.title}",
                    description=item.explanation,
                    source=", ".join(item.source_ids),
                    provenance=item.provenance_ids,
                    related=item.evidence_id,
                    before=item.title,
                    after=None,
                    why_changed="Evidence no longer present",
                    previous_state=item.verification_status,
                    current_state="REMOVED",
                    pit_eligible=True,
                )
            )

    return changes


def _financial_changes(
    prev_result: RealDataVerificationResult,
    curr_result: RealDataVerificationResult,
) -> list[ResearchChange]:
    prev_insights = (
        prev_result.intelligence.deep_financial_insights
        if prev_result.intelligence
        else None
    )
    curr_insights = (
        curr_result.intelligence.deep_financial_insights
        if curr_result.intelligence
        else None
    )
    if curr_insights is None:
        return []

    prev_keys = {
        _observation_key(obs)
        for obs in (prev_insights.observations if prev_insights else ())
    }

    changes: list[ResearchChange] = []
    for obs in curr_insights.observations:
        key = _observation_key(obs)
        if key in prev_keys:
            continue
        changes.append(
            _change(
                change_type=ChangeType.NEW_FINANCIAL_DISCLOSURE,
                symbol=curr_result.company,
                detected_at=curr_result.as_of,
                effective_at=_as_datetime(getattr(obs, "period_end", None)),
                title=f"{obs.metric} observation recorded",
                description=getattr(obs, "explanation", "") or "",
                source="recorded financial disclosures",
                related=key,
                before=None,
                after=str(getattr(obs, "value", "")),
                why_changed="New financial observation recorded",
                previous_state="ABSENT",
                current_state=str(getattr(obs, "value", "")),
                pit_eligible=True,
            )
        )
    return changes


def _gap_changes(
    prev_result: RealDataVerificationResult,
    curr_result: RealDataVerificationResult,
) -> list[ResearchChange]:
    def gaps(result):
        intel = result.intelligence
        if intel is None or intel.research_gaps is None:
            return {}
        return {_gap_key(gap): gap for gap in intel.research_gaps.gaps}

    prev_gaps = gaps(prev_result)
    curr_gaps = gaps(curr_result)

    changes: list[ResearchChange] = []
    for key, gap in curr_gaps.items():
        prev_gap = prev_gaps.get(key)
        if prev_gap is None:
            changes.append(
                _change(
                    change_type=ChangeType.RESEARCH_GAP_OPENED,
                    symbol=gap.symbol,
                    detected_at=curr_result.as_of,
                    title=f"New research gap: {gap.category}",
                    description=gap.gap,
                    related=key,
                    before=None,
                    after=gap.status,
                    why_changed="New gap detected in current record",
                    previous_state="NOT_PRESENT",
                    current_state=gap.status,
                    pit_eligible=True,
                )
            )
        elif prev_gap.status != gap.status:
            prev_status = prev_gap.status
            curr_status = gap.status
            if prev_status not in ("UNAVAILABLE", "CONFLICTING") and curr_status in ("UNAVAILABLE",):
                change_type = ChangeType.RESEARCH_GAP_RESOLVED
            elif prev_status in ("UNAVAILABLE",) and curr_status not in ("UNAVAILABLE",):
                change_type = ChangeType.RESEARCH_GAP_REOPENED
            else:
                change_type = ChangeType.RESEARCH_GAP_CHANGED
            changes.append(
                _change(
                    change_type=change_type,
                    symbol=gap.symbol,
                    detected_at=curr_result.as_of,
                    title=f"Gap status changed: {gap.category}",
                    description=gap.gap,
                    related=key,
                    before=prev_status,
                    after=curr_status,
                    why_changed=f"Status changed from {prev_status} to {curr_status}",
                    previous_state=prev_status,
                    current_state=curr_status,
                    pit_eligible=True,
                )
            )

    for key, gap in prev_gaps.items():
        if key not in curr_gaps:
            changes.append(
                _change(
                    change_type=ChangeType.RESEARCH_GAP_RESOLVED,
                    symbol=gap.symbol,
                    detected_at=curr_result.as_of,
                    title=f"Gap resolved: {gap.category}",
                    description=gap.gap,
                    related=key,
                    before=gap.status,
                    after=None,
                    why_changed="Gap no longer present in current record",
                    previous_state=gap.status,
                    current_state="RESOLVED",
                    pit_eligible=True,
                )
            )

    return changes


def _stale_source_changes(
    prev_result: RealDataVerificationResult,
    curr_result: RealDataVerificationResult,
) -> list[ResearchChange]:
    intel_prev = prev_result.intelligence
    intel_curr = curr_result.intelligence
    prev_stale = {
        s.source_name: s for s in (intel_prev.source_statuses if intel_prev else ())
    }

    changes: list[ResearchChange] = []
    for source in intel_curr.source_statuses if intel_curr else ():
        prev_source = prev_stale.get(source.source_name)
        was_stale = prev_source.stale if prev_source else False
        if source.stale and not was_stale:
            changes.append(
                _change(
                    change_type=ChangeType.SOURCE_BECAME_STALE,
                    symbol=curr_result.company,
                    detected_at=curr_result.as_of,
                    title=f"Source became stale: {source.source_name}",
                    description=(
                        "The most recent publication from this source is "
                        "older than the freshness threshold."
                    ),
                    source=source.source_name,
                    related=source.source_name,
                    before="FRESH",
                    after="STALE",
                    why_changed="Latest publication exceeded freshness threshold",
                    previous_state="FRESH",
                    current_state="STALE",
                    pit_eligible=True,
                )
            )
        elif prev_source is not None and was_stale and not source.stale:
            changes.append(
                _change(
                    change_type=ChangeType.SOURCE_BECAME_FRESH,
                    symbol=curr_result.company,
                    detected_at=curr_result.as_of,
                    title=f"Source became fresh: {source.source_name}",
                    description=(
                        "A new publication from this source restored "
                        "freshness."
                    ),
                    source=source.source_name,
                    related=source.source_name,
                    before="STALE",
                    after="FRESH",
                    why_changed="New publication restored source freshness",
                    previous_state="STALE",
                    current_state="FRESH",
                    pit_eligible=True,
                )
            )
    return changes


_SYMBOL_CHANGERS = (
    _item_changes,
    _evidence_changes,
    _financial_changes,
    _gap_changes,
    _stale_source_changes,
)


def build_symbol_changes(
    prev_result: RealDataVerificationResult,
    curr_result: RealDataVerificationResult,
) -> tuple[ResearchChange, ...]:
    """Every typed record change for one symbol between two as_ofs."""

    changes: list[ResearchChange] = []
    for fn in _SYMBOL_CHANGERS:
        changes.extend(fn(prev_result, curr_result))

    changes.sort(key=lambda c: (c.change_type.value, c.change_id))
    return tuple(changes)


def build_screen_entry_exit(
    service: RecordedCompanyResearchService,
    definition,
    previous_as_of: datetime,
    current_as_of: datetime,
) -> tuple[ResearchChange, ...]:
    """
    Symbols entering/leaving a screen between two universe snapshots.

    Both sides run the same deterministic engine over the recorded
    field rows at their own as_of, so entry/exit is reproducible.
    """

    def matched(as_of: datetime) -> set[str]:
        field_rows = {
            symbol: extract_company_fields(service.run(symbol, as_of=as_of))
            for symbol in service.companies
            if service.research_available(symbol)
        }
        execution = execute_screen(definition, field_rows)
        return set(execution.matched_symbols)

    prev_matched = matched(previous_as_of)
    curr_matched = matched(current_as_of)

    changes: list[ResearchChange] = []
    for symbol in sorted(curr_matched - prev_matched):
        changes.append(
            _change(
                change_type=ChangeType.SCREEN_ENTRY,
                symbol=symbol,
                detected_at=current_as_of,
                title=f"Entered screen: {definition.name}",
                related=definition.definition_hash(),
                previous_state="OUTSIDE",
                current_state="INSIDE",
            )
        )
    for symbol in sorted(prev_matched - curr_matched):
        changes.append(
            _change(
                change_type=ChangeType.SCREEN_EXIT,
                symbol=symbol,
                detected_at=current_as_of,
                title=f"Left screen: {definition.name}",
                related=definition.definition_hash(),
                previous_state="INSIDE",
                current_state="OUTSIDE",
            )
        )
    changes.sort(key=lambda c: (c.change_type.value, c.change_id))
    return tuple(changes)


# ---------------------------------------------------------------------------
# Evidence delta (before-vs-after research comparison)
# ---------------------------------------------------------------------------


class StatePair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    previous: str | None = None
    current: str | None = None


class EvidenceDeltaEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    title: str
    direction: str
    verification_status: str
    published_at: datetime | None = None
    available_at: datetime | None = None
    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()
    changed_fields: tuple[str, ...] = ()
    states: StatePair | None = None


class ConflictDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conflict_id: str = Field(min_length=1)
    topic: str
    management_involved: bool
    first_title: str
    second_title: str


class GapDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gap_key: str = Field(min_length=1)
    category: str
    gap: str
    previous_status: str | None = None
    current_status: str | None = None


class SourceFreshnessChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1)
    stale: StatePair
    days_since_latest: StatePair | None = None


class FinancialObservationChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(min_length=1)
    period_end: str | None = None
    previous_value: str | None = None
    current_value: str | None = None
    unit: str | None = None
    observation_type: str | None = None


class ItemSetDelta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str = Field(min_length=1)
    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()


class EvidenceDeltaReport(BaseModel):
    """Deterministic before-vs-after comparison for one symbol."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    baseline_as_of: datetime
    current_as_of: datetime

    new_evidence: tuple[EvidenceDeltaEntry, ...] = ()
    removed_evidence: tuple[EvidenceDeltaEntry, ...] = ()
    changed_evidence: tuple[EvidenceDeltaEntry, ...] = ()

    new_conflicts: tuple[ConflictDelta, ...] = ()
    resolved_conflicts: tuple[ConflictDelta, ...] = ()

    new_gaps: tuple[GapDelta, ...] = ()
    resolved_gaps: tuple[GapDelta, ...] = ()

    source_freshness_changes: tuple[SourceFreshnessChange, ...] = ()
    financial_observation_changes: tuple[FinancialObservationChange, ...] = ()
    removed_observations: tuple[FinancialObservationChange, ...] = ()
    item_set_deltas: tuple[ItemSetDelta, ...] = ()

    notes: tuple[str, ...] = ()


def _delta_entry(item, changed: tuple[str, ...] = (), states=None):
    return EvidenceDeltaEntry(
        evidence_id=item.evidence_id,
        title=item.title,
        direction=item.direction,
        verification_status=item.verification_status,
        published_at=item.published_at,
        available_at=item.available_at,
        source_ids=tuple(sorted(item.source_ids)),
        provenance_ids=tuple(sorted(item.provenance_ids)),
        changed_fields=tuple(sorted(changed)),
        states=states,
    )


_COMPARABLE_FIELDS = ("direction", "verification_status", "title")


def build_evidence_delta(
    baseline: RealDataVerificationResult,
    current: RealDataVerificationResult,
) -> EvidenceDeltaReport:
    """Full before/after research comparison for one symbol."""

    base_lineage = _lineage(baseline)
    curr_lineage = _lineage(current)

    base_ev = {item.evidence_id: item for item in base_lineage.evidence}
    curr_ev = {item.evidence_id: item for item in curr_lineage.evidence}

    new_evidence = [_delta_entry(curr_ev[k]) for k in sorted(curr_ev.keys() - base_ev.keys())]
    removed_evidence = [_delta_entry(base_ev[k]) for k in sorted(base_ev.keys() - curr_ev.keys())]

    changed_evidence = []
    for key in sorted(base_ev.keys() & curr_ev.keys()):
        b, c = base_ev[key], curr_ev[key]
        diff = tuple(
            f for f in _COMPARABLE_FIELDS if getattr(b, f) != getattr(c, f)
        )
        if diff:
            changed_evidence.append(
                _delta_entry(
                    c,
                    changed=diff,
                    states=StatePair(
                        previous="|".join(str(getattr(b, f)) for f in diff),
                        current="|".join(str(getattr(c, f)) for f in diff),
                    ),
                )
            )

    def conflicts(result):
        return {
            c.conflict_id: c
            for c in (result.intelligence.conflicts if result.intelligence else ())
        }

    base_conf = conflicts(baseline)
    curr_conf = conflicts(current)

    def conflict_delta(c):
        return ConflictDelta(
            conflict_id=c.conflict_id,
            topic=c.topic,
            management_involved=c.management_involved,
            first_title=c.first.title,
            second_title=c.second.title,
        )

    new_conflicts = [conflict_delta(curr_conf[k]) for k in sorted(curr_conf.keys() - base_conf.keys())]
    resolved_conflicts = [
        conflict_delta(base_conf[k]) for k in sorted(base_conf.keys() - curr_conf.keys())
    ]

    def gaps(result):
        intel = result.intelligence
        if intel is None or intel.research_gaps is None:
            return {}
        return {_gap_key(gap): gap for gap in intel.research_gaps.gaps}

    base_gaps = gaps(baseline)
    curr_gaps = gaps(current)

    new_gaps = [
        GapDelta(
            gap_key=k,
            category=curr_gaps[k].category,
            gap=curr_gaps[k].gap,
            current_status=curr_gaps[k].status,
        )
        for k in sorted(curr_gaps.keys() - base_gaps.keys())
    ]
    resolved_gaps = [
        GapDelta(
            gap_key=k,
            category=base_gaps[k].category,
            gap=base_gaps[k].gap,
            previous_status=base_gaps[k].status,
        )
        for k in sorted(base_gaps.keys() - curr_gaps.keys())
    ]

    base_sources = {
        s.source_name: s
        for s in (baseline.intelligence.source_statuses if baseline.intelligence else ())
    }
    freshness_changes = []
    for source in (
        current.intelligence.source_statuses if current.intelligence else ()
    ):
        prev_source = base_sources.get(source.source_name)
        if prev_source is None or prev_source.stale == source.stale:
            continue
        freshness_changes.append(
            SourceFreshnessChange(
                source_name=source.source_name,
                stale=StatePair(
                    previous=str(prev_source.stale), current=str(source.stale)
                ),
                days_since_latest=StatePair(
                    previous=(
                        str(prev_source.days_since_latest_published)
                        if prev_source.days_since_latest_published is not None
                        else None
                    ),
                    current=(
                        str(source.days_since_latest_published)
                        if source.days_since_latest_published is not None
                        else None
                    ),
                ),
            )
        )
    freshness_changes.sort(key=lambda s: s.source_name)

    def observations(result):
        insights = result.intelligence.deep_financial_insights if result.intelligence else None
        if insights is None:
            return {}
        return {_observation_key(o): o for o in insights.observations}

    base_obs = observations(baseline)
    curr_obs = observations(current)
    observation_changes = []
    removed_observations = []
    for key in sorted(curr_obs.keys()):
        c = curr_obs[key]
        b = base_obs.get(key)
        b_value = str(getattr(b, "value", "")) if b is not None else None
        c_value = str(getattr(c, "value", ""))
        if b is not None and b_value == c_value:
            continue
        observation_changes.append(
            FinancialObservationChange(
                metric=c.metric,
                period_end=str(getattr(c, "period_end", "")) or None,
                previous_value=b_value,
                current_value=c_value,
                unit=str(getattr(c, "unit", "")) or None,
                observation_type=str(getattr(c, "observation_type", "")) or None,
            )
        )
    for key in sorted(base_obs.keys() - curr_obs.keys()):
        b = base_obs[key]
        removed_observations.append(
            FinancialObservationChange(
                metric=b.metric,
                period_end=str(getattr(b, "period_end", "")) or None,
                previous_value=str(getattr(b, "value", "")),
                current_value=None,
                unit=str(getattr(b, "unit", "")) or None,
                observation_type=str(getattr(b, "observation_type", "")) or None,
            )
        )

    sections = (
        ("business_events", lambda i: i.business_events),
        ("management_commentary", lambda i: i.management_commentary),
        ("risk_intelligence", lambda i: i.risk_intelligence),
        ("indirect_intelligence", lambda i: i.indirect_intelligence),
        ("financial_intelligence_items", lambda i: i.financial_intelligence_items),
        ("other_intelligence", lambda i: i.other_intelligence),
    )
    item_set_deltas = []
    for name, getter in sections:
        base_section = intel_baseline = getter(baseline.intelligence) if baseline.intelligence else ()
        curr_section = getter(current.intelligence) if current.intelligence else ()
        base_ids = {i.item_id for i in base_section}
        curr_ids = {i.item_id for i in curr_section}
        if base_ids != curr_ids:
            item_set_deltas.append(
                ItemSetDelta(
                    section=name,
                    added=tuple(sorted(curr_ids - base_ids)),
                    removed=tuple(sorted(base_ids - curr_ids)),
                )
            )

    notes: list[str] = []
    if not any(
        (
            new_evidence,
            removed_evidence,
            changed_evidence,
            new_conflicts,
            resolved_conflicts,
            new_gaps,
            resolved_gaps,
            freshness_changes,
            observation_changes,
            removed_observations,
            item_set_deltas,
        )
    ):
        notes.append(
            "No recorded differences between the two research contexts."
        )

    return EvidenceDeltaReport(
        symbol=current.company,
        baseline_as_of=baseline.as_of,
        current_as_of=current.as_of,
        new_evidence=tuple(new_evidence),
        removed_evidence=tuple(removed_evidence),
        changed_evidence=tuple(changed_evidence),
        new_conflicts=tuple(new_conflicts),
        resolved_conflicts=tuple(resolved_conflicts),
        new_gaps=tuple(new_gaps),
        resolved_gaps=tuple(resolved_gaps),
        source_freshness_changes=tuple(freshness_changes),
        financial_observation_changes=tuple(observation_changes),
        removed_observations=tuple(removed_observations),
        item_set_deltas=tuple(item_set_deltas),
        notes=tuple(notes),
    )


# ---------------------------------------------------------------------------
# Coverage delta
# ---------------------------------------------------------------------------


class CoverageTransition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    detail: str = ""
    direction: str | None = None
    previous_state: str | None = None
    current_state: str | None = None
    reason: str = ""


class CoverageDeltaReport(BaseModel):
    """
    How research coverage itself moved between two contexts.

    Purely descriptive transitions of the *record* — never a quality
    judgement of the company.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    baseline_as_of: datetime
    current_as_of: datetime

    newly_covered_categories: tuple[CoverageTransition, ...] = ()
    became_uncovered_categories: tuple[CoverageTransition, ...] = ()

    state_transitions: tuple[CoverageTransition, ...] = ()

    conflicts_introduced: tuple[str, ...] = ()
    conflicts_resolved: tuple[str, ...] = ()

    gaps_opened: tuple[CoverageTransition, ...] = ()
    gaps_resolved: tuple[CoverageTransition, ...] = ()

    sources_became_stale: tuple[str, ...] = ()
    sources_became_fresh: tuple[str, ...] = ()

    notes: tuple[str, ...] = ()


def build_coverage_delta(
    baseline: RealDataVerificationResult,
    current: RealDataVerificationResult,
) -> CoverageDeltaReport:
    def coverage(result):
        intel = result.intelligence
        if intel is None or intel.status is None:
            return {}, ()
        cov = intel.status.coverage
        return dict(cov.by_category), tuple(cov.missing_categories)

    base_cov, base_missing = coverage(baseline)
    curr_cov, curr_missing = coverage(current)

    newly = [
        CoverageTransition(
            key=cat,
            direction="MISSING → AVAILABLE",
            current_state="COVERED",
            reason="Category now has recorded coverage items",
        )
        for cat in sorted(set(curr_cov) - set(base_cov))
        if curr_cov[cat] > 0
    ]
    uncovered = [
        CoverageTransition(
            key=cat,
            direction="AVAILABLE → MISSING",
            previous_state="COVERED",
            reason="Category no longer has recorded coverage items",
        )
        for cat in sorted(set(base_cov) - set(curr_cov))
        if base_cov[cat] > 0
    ]

    # Detect state transitions for categories present in both.
    state_transitions: list[CoverageTransition] = []
    for cat in sorted(set(base_cov) & set(curr_cov)):
        b_count = base_cov[cat]
        c_count = curr_cov[cat]
        if b_count > 0 and c_count == 0:
            state_transitions.append(
                CoverageTransition(
                    key=cat,
                    direction="AVAILABLE → MISSING",
                    previous_state="AVAILABLE",
                    current_state="MISSING",
                    reason=f"Coverage dropped from {b_count} to 0 items",
                )
            )
        elif b_count == 0 and c_count > 0:
            state_transitions.append(
                CoverageTransition(
                    key=cat,
                    direction="MISSING → AVAILABLE",
                    previous_state="MISSING",
                    current_state="AVAILABLE",
                    reason=f"Coverage increased from 0 to {c_count} items",
                )
            )

    def conflicts(result):
        return {
            c.conflict_id
            for c in (result.intelligence.conflicts if result.intelligence else ())
        }

    base_conf = conflicts(baseline)
    curr_conf = conflicts(current)

    def gaps(result):
        intel = result.intelligence
        if intel is None or intel.research_gaps is None:
            return {}
        return {_gap_key(gap): gap for gap in intel.research_gaps.gaps}

    base_gaps = gaps(baseline)
    curr_gaps = gaps(current)

    opened = [
        CoverageTransition(
            key=k,
            direction="GAP OPENED",
            detail=curr_gaps[k].category,
            current_state=curr_gaps[k].status,
            reason="New research gap detected",
        )
        for k in sorted(curr_gaps.keys() - base_gaps.keys())
    ]
    closed = [
        CoverageTransition(
            key=k,
            direction="GAP RESOLVED",
            detail=base_gaps[k].category,
            previous_state=base_gaps[k].status,
            reason="Research gap no longer present",
        )
        for k in sorted(base_gaps.keys() - curr_gaps.keys())
    ]

    base_sources = {
        s.source_name: s.stale
        for s in (baseline.intelligence.source_statuses if baseline.intelligence else ())
    }
    became_stale: list[str] = []
    became_fresh: list[str] = []
    for source in (
        current.intelligence.source_statuses if current.intelligence else ()
    ):
        prev_stale = base_sources.get(source.source_name)
        if prev_stale is False and source.stale:
            became_stale.append(source.source_name)
        elif prev_stale is True and not source.stale:
            became_fresh.append(source.source_name)

    notes: list[str] = []
    if not any(
        (
            newly,
            uncovered,
            state_transitions,
            curr_conf - base_conf,
            base_conf - curr_conf,
            opened,
            closed,
            became_stale,
            became_fresh,
        )
    ):
        notes.append("Coverage is unchanged between the two contexts.")

    return CoverageDeltaReport(
        symbol=current.company,
        baseline_as_of=baseline.as_of,
        current_as_of=current.as_of,
        newly_covered_categories=tuple(newly),
        became_uncovered_categories=tuple(uncovered),
        state_transitions=tuple(state_transitions),
        conflicts_introduced=tuple(sorted(curr_conf - base_conf)),
        conflicts_resolved=tuple(sorted(base_conf - curr_conf)),
        gaps_opened=tuple(opened),
        gaps_resolved=tuple(closed),
        sources_became_stale=tuple(sorted(became_stale)),
        sources_became_fresh=tuple(sorted(became_fresh)),
        notes=tuple(notes),
    )


# ---------------------------------------------------------------------------
# Calendar foundation (recorded / announced events only)
# ---------------------------------------------------------------------------


class CalendarEvent(BaseModel):
    """One recorded or explicitly announced dated event."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    title: str
    event_date: datetime
    effective_date: datetime | None = None
    announcement_date: datetime | None = None
    available_at: datetime | None = None
    state: str  # RECORDED or ANNOUNCED
    category: str | None = None
    verification_status: str | None = None
    source: str | None = None
    provenance: tuple[str, ...] = ()
    pit_available: bool
    note: str = ""


class CalendarResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: datetime
    range_from: datetime
    range_to: datetime
    symbols: tuple[str, ...] = ()
    events: tuple[CalendarEvent, ...] = ()
    announced_count: int = Field(ge=0)
    recorded_count: int = Field(ge=0)
    notes: tuple[str, ...] = ()


def build_calendar(
    results_by_symbol: dict[str, RealDataVerificationResult],
    *,
    range_from: datetime,
    range_to: datetime,
) -> CalendarResponse:
    """
    Recorded-event calendar.

    Only events that exist in the record are listed. Events dated after
    as_of are marked ANNOUNCED with an explicit note that they are
    announcements, never guarantees.
    """

    events: list[CalendarEvent] = []

    for symbol in sorted(results_by_symbol):
        result = results_by_symbol[symbol]
        intel = result.intelligence
        timeline = intel.timeline if intel is not None else None
        if timeline is None:
            continue

        for entry in timeline.entries:
            event_date = entry.timeline_at or entry.effective_at
            if event_date is None:
                continue
            if not (range_from <= event_date <= range_to):
                continue

            announced = event_date > result.as_of
            events.append(
                CalendarEvent(
                    event_id=entry.entry_id,
                    symbol=symbol,
                    title=entry.title,
                    event_date=event_date,
                    effective_date=entry.effective_at,
                    announcement_date=entry.published_at,
                    available_at=entry.available_at,
                    state="ANNOUNCED" if announced else "RECORDED",
                    category=(
                        entry.intel_category.value
                        if entry.intel_category is not None
                        else None
                    ),
                    verification_status=entry.verification_status.value,
                    source=entry.source.source_name,
                    provenance=(entry.provenance_id,) if entry.provenance_id else (),
                    pit_available=(
                        entry.available_at is not None
                        and entry.available_at <= result.as_of
                    ),
                    note=(
                        "Announced event date; recorded as an announcement "
                        "only, never as a guarantee."
                    )
                    if announced
                    else "",
                )
            )

    events.sort(key=lambda e: (e.event_date, e.event_id))
    announced = sum(1 for e in events if e.state == "ANNOUNCED")

    notes: list[str] = [
        "Events marked ANNOUNCED are recorded statements of intent; "
        "they are not guarantees of occurrence.",
    ]
    if announced:
        notes.append(
            f"{announced} event(s) are future-dated relative to as_of and "
            "are shown as announcements only."
        )
    if not events:
        notes.append("No recorded events in the requested range.")

    return CalendarResponse(
        as_of=max(r.as_of for r in results_by_symbol.values()),
        range_from=range_from,
        range_to=range_to,
        symbols=tuple(sorted(results_by_symbol)),
        events=tuple(events),
        announced_count=announced,
        recorded_count=len(events) - announced,
        notes=tuple(notes),
    )


__all__ = [
    "CalendarEvent",
    "CalendarResponse",
    "CONTEXT_SCHEMA_VERSION",
    "ChangeType",
    "ConflictDelta",
    "CoverageDeltaReport",
    "CoverageTransition",
    "EvidenceDeltaEntry",
    "EvidenceDeltaReport",
    "FinancialObservationChange",
    "GapDelta",
    "ItemSetDelta",
    "ResearchChange",
    "ResearchContextSnapshot",
    "SourceFreshnessChange",
    "StatePair",
    "build_calendar",
    "build_context_snapshot",
    "build_coverage_delta",
    "build_evidence_delta",
    "build_screen_entry_exit",
    "build_symbol_changes",
    "context_id_for",
    "parse_context_id",
]
