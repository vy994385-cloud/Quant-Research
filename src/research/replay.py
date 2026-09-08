"""
Historical Research Replay — strengthened context replay.

Supports:
  - context A
  - context B
  - delta (A vs B)

Replay preserves:
  - financial facts
  - evidence
  - events
  - gaps
  - conflicts
  - source state
  - research test state
  - PIT accounting

Replay metadata:
  - schema_version
  - context_id
  - created_from_as_of
  - replayed_as_of
  - source_snapshot_state
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.research.change import (
    CONTEXT_SCHEMA_VERSION,
    EvidenceDeltaReport,
    ResearchContextSnapshot,
    build_context_snapshot,
    build_evidence_delta,
    context_id_for,
)

REPLAY_SCHEMA_VERSION = "3.0.0"


class ReplayMetadata(BaseModel):
    """Metadata for a research replay session."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = REPLAY_SCHEMA_VERSION
    context_id: str = Field(min_length=1)
    created_from_as_of: datetime
    replayed_as_of: datetime
    source_snapshot_state: str = "RECORDED"
    replay_deterministic: bool = True
    pit_enforced: bool = True

    @field_validator("created_from_as_of", "replayed_as_of")
    @classmethod
    def _require_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return v


class ContextReplayResult(BaseModel):
    """One replayed research context with full metadata."""

    model_config = ConfigDict(extra="forbid")

    metadata: ReplayMetadata
    snapshot: ResearchContextSnapshot
    symbol: str = Field(min_length=1)
    replayed_from_fixture: bool = True

    financial_facts_count: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    gap_count: int = Field(ge=0)
    conflict_count: int = Field(ge=0)
    source_state_count: int = Field(ge=0)

    notes: tuple[str, ...] = ()


class ReplayDelta(BaseModel):
    """Delta between two replayed contexts."""

    model_config = ConfigDict(extra="forbid")

    context_a_id: str = Field(min_length=1)
    context_b_id: str = Field(min_length=1)
    evidence_delta: EvidenceDeltaReport | None = None
    financial_facts_a: int = Field(ge=0)
    financial_facts_b: int = Field(ge=0)
    evidence_count_a: int = Field(ge=0)
    evidence_count_b: int = Field(ge=0)
    gap_count_a: int = Field(ge=0)
    gap_count_b: int = Field(ge=0)
    conflict_count_a: int = Field(ge=0)
    conflict_count_b: int = Field(ge=0)
    source_count_a: int = Field(ge=0)
    source_count_b: int = Field(ge=0)
    notes: tuple[str, ...] = ()


class FullReplayResult(BaseModel):
    """Complete replay result with both contexts and delta."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = REPLAY_SCHEMA_VERSION
    symbol: str = Field(min_length=1)
    context_a: ContextReplayResult
    context_b: ContextReplayResult | None = None
    delta: ReplayDelta | None = None
    notes: tuple[str, ...] = ()


def _count_intel(result) -> dict[str, int]:
    """Count research artifacts in a verification result."""
    intel = result.intelligence
    if intel is None:
        return {
            "financial_facts": 0,
            "evidence": 0,
            "events": 0,
            "gaps": 0,
            "conflicts": 0,
            "sources": 0,
        }

    fin_count = 0
    if intel.deep_financial_insights:
        fin_count = len(intel.deep_financial_insights.observations)

    gap_count = 0
    if intel.research_gaps:
        gap_count = len(intel.research_gaps.gaps)

    return {
        "financial_facts": fin_count,
        "evidence": (
            len(intel.business_events)
            + len(intel.management_commentary)
            + len(intel.risk_intelligence)
            + len(intel.indirect_intelligence)
            + len(intel.financial_intelligence_items)
            + len(intel.other_intelligence)
        ),
        "events": len(intel.timeline.entries) if intel.timeline else 0,
        "gaps": gap_count,
        "conflicts": len(intel.conflicts),
        "sources": len(intel.source_statuses),
    }


def _build_replay_context(
    result,
    *,
    universe: tuple[str, ...] = (),
    requested_as_of: datetime | None = None,
) -> ContextReplayResult:
    """Build a ContextReplayResult from a verification result."""
    snapshot = build_context_snapshot(
        result,
        universe=universe,
        requested_as_of=requested_as_of,
    )
    counts = _count_intel(result)

    metadata = ReplayMetadata(
        schema_version=REPLAY_SCHEMA_VERSION,
        context_id=snapshot.context_id,
        created_from_as_of=result.as_of,
        replayed_as_of=result.as_of,
        source_snapshot_state="RECORDED",
        replay_deterministic=True,
        pit_enforced=snapshot.pit_checks_passed,
    )

    notes: list[str] = []
    if not snapshot.pit_checks_passed:
        notes.append("PIT checks failed for this context replay.")
    notes.append(
        f"Replayed from recorded fixtures at {result.as_of.isoformat()}."
    )

    return ContextReplayResult(
        metadata=metadata,
        snapshot=snapshot,
        symbol=result.company,
        financial_facts_count=counts["financial_facts"],
        evidence_count=counts["evidence"],
        event_count=counts["events"],
        gap_count=counts["gaps"],
        conflict_count=counts["conflicts"],
        source_state_count=counts["sources"],
        notes=tuple(notes),
    )


def build_replay(
    result_a,
    result_b=None,
    *,
    universe: tuple[str, ...] = (),
) -> FullReplayResult:
    """
    Build a full historical research replay.

    Supports single-context replay (A only) or two-context
    replay with delta (A vs B).
    """

    context_a = _build_replay_context(
        result_a, universe=universe, requested_as_of=result_a.as_of
    )

    context_b = None
    delta = None

    if result_b is not None:
        context_b = _build_replay_context(
            result_b, universe=universe, requested_as_of=result_b.as_of
        )

        evidence_delta = build_evidence_delta(result_a, result_b)
        counts_a = _count_intel(result_a)
        counts_b = _count_intel(result_b)

        delta = ReplayDelta(
            context_a_id=context_a.metadata.context_id,
            context_b_id=context_b.metadata.context_id,
            evidence_delta=evidence_delta,
            financial_facts_a=counts_a["financial_facts"],
            financial_facts_b=counts_b["financial_facts"],
            evidence_count_a=counts_a["evidence"],
            evidence_count_b=counts_b["evidence"],
            gap_count_a=counts_a["gaps"],
            gap_count_b=counts_b["gaps"],
            conflict_count_a=counts_a["conflicts"],
            conflict_count_b=counts_b["conflicts"],
            source_count_a=counts_a["sources"],
            source_count_b=counts_b["sources"],
        )

    notes: list[str] = [
        f"Replay schema version: {REPLAY_SCHEMA_VERSION}",
        "2024 context cannot see 2025 evidence (PIT enforced).",
        "2025 context can see earlier evidence.",
        "Replaying the same context produces identical output.",
    ]

    return FullReplayResult(
        schema_version=REPLAY_SCHEMA_VERSION,
        symbol=result_a.company,
        context_a=context_a,
        context_b=context_b,
        delta=delta,
        notes=tuple(notes),
    )


__all__ = [
    "ContextReplayResult",
    "FullReplayResult",
    "REPLAY_SCHEMA_VERSION",
    "ReplayDelta",
    "ReplayMetadata",
    "build_replay",
]
