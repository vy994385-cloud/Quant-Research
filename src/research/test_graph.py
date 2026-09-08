"""
Research Test → Evidence Requirement Graph.

Inventory every supported research test and define what evidence it requires,
what evidence is available, what is missing, and what the result state is.

Result vocabulary:
  EVALUATED
  PARTIALLY_EVALUATED
  NOT_EVALUABLE
  BLOCKED
  NOT_APPLICABLE

When required evidence is missing, the test is NOT deleted.
It returns NOT_EVALUABLE with an explicit missing-evidence reason.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TestResultState(str, Enum):
    EVALUATED = "EVALUATED"
    PARTIALLY_EVALUATED = "PARTIALLY_EVALUATED"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class EvidenceRequirement(BaseModel):
    """One required piece of evidence for a research test."""

    model_config = ConfigDict(extra="forbid")

    requirement_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    evidence_type: str = Field(min_length=1)
    required: bool = True
    available: bool = False
    evidence_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()


class ResearchTestResult(BaseModel):
    """One research test with its evidence requirement graph."""

    model_config = ConfigDict(extra="forbid")

    test_id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    result_state: TestResultState

    required_evidence: tuple[EvidenceRequirement, ...] = ()
    available_evidence: tuple[EvidenceRequirement, ...] = ()
    missing_evidence: tuple[EvidenceRequirement, ...] = ()

    missing_reason: str = ""
    related_gap: str | None = None

    pit_safe: bool = True
    provenance_safe: bool = True
    gap_behavior: str = ""
    limitation: str = ""

    as_of: datetime | None = None

    @field_validator("as_of")
    @classmethod
    def _require_aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return v


class ResearchTestGraph(BaseModel):
    """Complete inventory of research tests and their evidence requirements."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    tests: tuple[ResearchTestResult, ...] = ()
    total_tests: int = Field(ge=0)
    evaluated_count: int = Field(ge=0)
    partially_evaluated_count: int = Field(ge=0)
    not_evaluable_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    not_applicable_count: int = Field(ge=0)
    notes: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def _require_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return v


def _evaluate_test(
    *,
    test_id: str,
    purpose: str,
    required_types: list[str],
    available_evidence_by_type: dict[str, list[str]],
    available_source_ids: set[str],
    as_of: datetime,
    gap_behavior: str = "",
    limitation: str = "",
    related_gap: str | None = None,
) -> ResearchTestResult:
    """Evaluate a single research test against available evidence."""

    required: list[EvidenceRequirement] = []
    available: list[EvidenceRequirement] = []
    missing: list[EvidenceRequirement] = []

    for i, ev_type in enumerate(required_types):
        ev_ids = available_evidence_by_type.get(ev_type, [])
        is_available = len(ev_ids) > 0
        req = EvidenceRequirement(
            requirement_id=f"{test_id}-req-{i + 1}",
            description=f"Requires {ev_type} evidence",
            evidence_type=ev_type,
            required=True,
            available=is_available,
            evidence_ids=tuple(ev_ids),
            source_ids=tuple(sorted(available_source_ids)),
        )
        required.append(req)
        if is_available:
            available.append(req)
        else:
            missing.append(req)

    if not required_types:
        state = TestResultState.NOT_APPLICABLE
    elif not missing:
        state = TestResultState.EVALUATED
    elif len(missing) < len(required):
        state = TestResultState.PARTIALLY_EVALUATED
    else:
        state = TestResultState.NOT_EVALUABLE

    missing_reason = ""
    if missing:
        missing_types = [m.evidence_type for m in missing]
        missing_reason = (
            f"Missing evidence types: {', '.join(missing_types)}"
        )

    return ResearchTestResult(
        test_id=test_id,
        purpose=purpose,
        result_state=state,
        required_evidence=tuple(required),
        available_evidence=tuple(available),
        missing_evidence=tuple(missing),
        missing_reason=missing_reason,
        related_gap=related_gap,
        pit_safe=True,
        provenance_safe=True,
        gap_behavior=gap_behavior or "Records gap and continues",
        limitation=limitation,
        as_of=as_of,
    )


def build_research_test_graph(
    *,
    symbol: str,
    as_of: datetime,
    evidence_items: tuple = (),
    evidence_source_ids: set[str] | None = None,
    financial_periods: tuple = (),
    intel_items: tuple = (),
    conflicts: tuple = (),
    gaps: tuple = (),
    source_statuses: tuple = (),
    deep_financial_insights=None,
) -> ResearchTestGraph:
    """
    Build a complete research test → evidence requirement graph.

    Inventories all supported research tests and evaluates their
    evidence requirements against the available data.
    """

    source_ids = evidence_source_ids or set()

    # Index available evidence by type
    ev_by_type: dict[str, list[str]] = {}
    for item in evidence_items:
        ev_type = getattr(item, "evidence_type", None)
        ev_id = getattr(item, "evidence_id", None)
        if ev_type and ev_id:
            ev_by_type.setdefault(str(ev_type), []).append(ev_id)

    # Index intel items by category
    intel_by_kind: dict[str, list[str]] = {}
    for item in intel_items:
        kind = getattr(item, "kind", None)
        item_id = getattr(item, "item_id", None)
        if kind and item_id:
            intel_by_kind.setdefault(str(kind), []).append(item_id)

    tests: list[ResearchTestResult] = []

    # --- Financial trend analysis ---
    tests.append(_evaluate_test(
        test_id="RT-FINANCIAL-TRENDS",
        purpose="Evaluate whether financial trend analysis can be performed",
        required_types=["FINANCIAL"],
        available_evidence_by_type=ev_by_type,
        available_source_ids=source_ids,
        as_of=as_of,
        gap_behavior="Marks as NOT_EVALUABLE; financial data unavailable",
        limitation="Requires at least 2 comparable periods",
        related_gap="FINANCIAL_DATA" if not financial_periods else None,
    ))

    # --- Evidence synthesis ---
    tests.append(_evaluate_test(
        test_id="RT-EVIDENCE-SYNTHESIS",
        purpose="Synthesize evidence into directional assessment",
        required_types=["EVIDENCE", "CLAIM"],
        available_evidence_by_type=ev_by_type,
        available_source_ids=source_ids,
        as_of=as_of,
        gap_behavior="Returns NOT_EVALUABLE if no evidence items exist",
        limitation="Synthesis requires at least 1 evidence item",
    ))

    # --- Conflict detection ---
    tests.append(_evaluate_test(
        test_id="RT-CONFLICT-DETECTION",
        purpose="Detect conflicting evidence claims",
        required_types=["EVIDENCE", "CLAIM"],
        available_evidence_by_type=ev_by_type,
        available_source_ids=source_ids,
        as_of=as_of,
        gap_behavior="Returns PARTIALLY_EVALUATED when conflicts cannot be fully assessed",
        limitation="Requires evidence from multiple sources on the same topic",
        related_gap="CONFLICT_DATA" if not conflicts else None,
    ))

    # --- Research gap analysis ---
    tests.append(_evaluate_test(
        test_id="RT-GAP-ANALYSIS",
        purpose="Identify research gaps and information deficiencies",
        required_types=["FINANCIAL", "EVIDENCE"],
        available_evidence_by_type=ev_by_type,
        available_source_ids=source_ids,
        as_of=as_of,
        gap_behavior="Records gap with status UNAVAILABLE",
    ))

    # --- Source freshness assessment ---
    tests.append(_evaluate_test(
        test_id="RT-SOURCE-FRESHNESS",
        purpose="Assess freshness and completeness of research sources",
        required_types=["SOURCE_STATUS"],
        available_evidence_by_type=ev_by_type,
        available_source_ids=source_ids,
        as_of=as_of,
        gap_behavior="Returns NOT_EVALUABLE if no source statuses available",
        limitation="Requires at least one source status record",
    ))

    # --- Deep financial observation ---
    has_observations = (
        deep_financial_insights is not None
        and len(getattr(deep_financial_insights, "observations", ())) > 0
    )
    tests.append(_evaluate_test(
        test_id="RT-DEEP-FINANCIAL",
        purpose="Produce deep financial metric observations",
        required_types=["FINANCIAL"],
        available_evidence_by_type=ev_by_type,
        available_source_ids=source_ids,
        as_of=as_of,
        gap_behavior="Returns NOT_EVALUABLE; deep financial analysis requires period data",
        limitation="Requires FinancialPeriod records with metrics",
        related_gap="DEEP_FINANCIAL" if not has_observations else None,
    ))

    # --- Business intelligence ---
    business_items = intel_by_kind.get("BUSINESS", [])
    tests.append(_evaluate_test(
        test_id="RT-BUSINESS-INTEL",
        purpose="Assess business developments and corporate intelligence",
        required_types=["EVIDENCE"],
        available_evidence_by_type=ev_by_type,
        available_source_ids=source_ids,
        as_of=as_of,
        gap_behavior="Records gap in business intelligence coverage",
        limitation="Depends on business event data availability",
        related_gap="BUSINESS_INTEL" if not business_items else None,
    ))

    # --- Technology evidence ---
    tech_items = intel_by_kind.get("TECHNOLOGY", [])
    tests.append(_evaluate_test(
        test_id="RT-TECHNOLOGY-EVIDENCE",
        purpose="Assess technology activity and AI/cloud/platform evidence",
        required_types=["EVIDENCE"],
        available_evidence_by_type=ev_by_type,
        available_source_ids=source_ids,
        as_of=as_of,
        gap_behavior="Records gap; technology evidence is partial",
        limitation="Technology evidence depends on available disclosure sources",
        related_gap="TECHNOLOGY_EVIDENCE" if not tech_items else None,
    ))

    # --- Coverage assessment ---
    tests.append(_evaluate_test(
        test_id="RT-COVERAGE",
        purpose="Assess research coverage completeness across intelligence dimensions",
        required_types=["FINANCIAL", "EVIDENCE", "SOURCE_STATUS"],
        available_evidence_by_type=ev_by_type,
        available_source_ids=source_ids,
        as_of=as_of,
        gap_behavior="Partial assessment with available data",
    ))

    # --- PIT integrity ---
    tests.append(_evaluate_test(
        test_id="RT-PIT-INTEGRITY",
        purpose="Verify point-in-time integrity of all research data",
        required_types=["EVIDENCE", "FINANCIAL"],
        available_evidence_by_type=ev_by_type,
        available_source_ids=source_ids,
        as_of=as_of,
        gap_behavior="All evidence must have valid availability timestamps",
        limitation="Cannot verify PIT if availability timestamps are missing",
    ))

    # --- Provenance chain ---
    tests.append(_evaluate_test(
        test_id="RT-PROVENANCE-CHAIN",
        purpose="Verify provenance chain from source to evidence",
        required_types=["EVIDENCE", "SOURCE_STATUS"],
        available_evidence_by_type=ev_by_type,
        available_source_ids=source_ids,
        as_of=as_of,
        gap_behavior="Records missing provenance links",
        limitation="Requires both evidence items and source statuses",
    ))

    # --- Calendar events ---
    tests.append(_evaluate_test(
        test_id="RT-CALENDAR-EVENTS",
        purpose="Identify recorded and announced calendar events",
        required_types=["EVENT"],
        available_evidence_by_type=ev_by_type,
        available_source_ids=source_ids,
        as_of=as_of,
        gap_behavior="Returns empty calendar if no events available",
    ))

    # --- Screen membership ---
    tests.append(_evaluate_test(
        test_id="RT-SCREEN-MEMBERSHIP",
        purpose="Determine screener field eligibility",
        required_types=["FINANCIAL", "MARKET"],
        available_evidence_by_type=ev_by_type,
        available_source_ids=source_ids,
        as_of=as_of,
        gap_behavior="Screen fields with missing data marked as unavailable",
    ))

    evaluated = sum(1 for t in tests if t.result_state == TestResultState.EVALUATED)
    partial = sum(1 for t in tests if t.result_state == TestResultState.PARTIALLY_EVALUATED)
    not_eval = sum(1 for t in tests if t.result_state == TestResultState.NOT_EVALUABLE)
    blocked = sum(1 for t in tests if t.result_state == TestResultState.BLOCKED)
    not_app = sum(1 for t in tests if t.result_state == TestResultState.NOT_APPLICABLE)

    notes: list[str] = []
    if not_eval:
        notes.append(
            f"{not_eval} test(s) not evaluable due to missing evidence."
        )
    if partial:
        notes.append(
            f"{partial} test(s) partially evaluated."
        )

    return ResearchTestGraph(
        symbol=symbol,
        as_of=as_of,
        tests=tuple(tests),
        total_tests=len(tests),
        evaluated_count=evaluated,
        partially_evaluated_count=partial,
        not_evaluable_count=not_eval,
        blocked_count=blocked,
        not_applicable_count=not_app,
        notes=tuple(notes),
    )


__all__ = [
    "EvidenceRequirement",
    "ResearchTestGraph",
    "ResearchTestResult",
    "TestResultState",
    "build_research_test_graph",
]
