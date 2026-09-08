"""Research Test Execution (T1-W5).

Evaluates each T1-W3 research test against actual recorded data.
Returns descriptive state: EVALUATED, PARTIALLY_EVALUATED,
NOT_EVALUABLE, BLOCKED, NOT_APPLICABLE.  Never hides tests because
evidence is incomplete.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TestExecutionState(StrEnum):
    EVALUATED = "EVALUATED"
    PARTIALLY_EVALUATED = "PARTIALLY_EVALUATED"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class TestExecution(BaseModel):
    """Execution state for one research test."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    test_id: str = Field(min_length=1)
    test_name: str = Field(min_length=1)
    state: TestExecutionState
    required_evidence: tuple[str, ...] = ()
    available_evidence: tuple[str, ...] = ()
    missing_evidence: tuple[str, ...] = ()
    related_gap_ids: tuple[str, ...] = ()
    as_of: datetime
    provenance: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


class TestExecutionReport(BaseModel):
    """Research test execution report for one company."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    tests: tuple[TestExecution, ...] = ()
    state_counts: dict[str, int] = Field(default_factory=dict)
    total_tests: int = Field(ge=0)


# ── Test definitions ─────────────────────────────────────────────────
TEST_DEFINITIONS: list[dict[str, Any]] = [
    {
        "test_id": "TEST-FIN-COVERAGE",
        "test_name": "Financial Data Coverage",
        "required_domains": ["financials"],
        "required_evidence": ["financial_periods", "financial_metrics"],
    },
    {
        "test_id": "TEST-FIN-DEPTH",
        "test_name": "Financial Statement Depth",
        "required_domains": ["financials"],
        "required_evidence": ["balance_sheet", "cash_flow", "income_statement"],
    },
    {
        "test_id": "TEST-FIN-QUALITY",
        "test_name": "Financial Data Quality",
        "required_domains": ["financials"],
        "required_evidence": ["source_attribution", "period_consistency"],
    },
    {
        "test_id": "TEST-BIZ-COVERAGE",
        "test_name": "Business Evidence Coverage",
        "required_domains": ["business"],
        "required_evidence": ["business_events", "management_commentary"],
    },
    {
        "test_id": "TEST-TECH-COVERAGE",
        "test_name": "Technology Evidence Coverage",
        "required_domains": ["technology"],
        "required_evidence": ["tech_evidence", "ai_evidence"],
    },
    {
        "test_id": "TEST-EVT-COVERAGE",
        "test_name": "Event Timeline Coverage",
        "required_domains": ["events"],
        "required_evidence": ["timeline_entries", "corporate_actions"],
    },
    {
        "test_id": "TEST-RISK-COVERAGE",
        "test_name": "Risk Intelligence Coverage",
        "required_domains": ["risk"],
        "required_evidence": ["risk_items", "regulatory_items"],
    },
    {
        "test_id": "TEST-MKT-COVERAGE",
        "test_name": "Market Intelligence Coverage",
        "required_domains": ["market"],
        "required_evidence": ["indirect_intelligence", "sector_items"],
    },
    {
        "test_id": "TEST-SRC-COVERAGE",
        "test_name": "Source Coverage",
        "required_domains": ["sources"],
        "required_evidence": ["source_statuses"],
    },
    {
        "test_id": "TEST-EVD-COVERAGE",
        "test_name": "Evidence Lineage Coverage",
        "required_domains": ["evidence"],
        "required_evidence": ["evidence_items", "provenance"],
    },
    {
        "test_id": "TEST-CONFLICT-DETECT",
        "test_name": "Conflict Detection",
        "required_domains": ["business", "market"],
        "required_evidence": ["conflicting_claims"],
    },
    {
        "test_id": "TEST-GAP-COVERAGE",
        "test_name": "Research Gap Completeness",
        "required_domains": ["financials", "business", "events"],
        "required_evidence": ["gap_definitions"],
    },
    {
        "test_id": "TEST-PIT-ENFORCEMENT",
        "test_name": "Point-in-Time Enforcement",
        "required_domains": ["financials", "evidence"],
        "required_evidence": ["available_at_timestamps", "pit_checks"],
    },
]


def _check_domain(result: Any, domain: str) -> bool:
    """Check if a domain has data."""
    intel = result.intelligence
    coverage = getattr(intel, "coverage", None) or {}
    if isinstance(coverage, dict):
        return domain.upper() in coverage or any(
            domain.upper() in k.upper() for k in coverage.keys()
        )
    return False


def _check_evidence(result: Any, evidence_type: str) -> bool:
    """Check if specific evidence type exists."""
    evidence = result.evidence_items or ()
    intel = result.intelligence

    if evidence_type == "financial_periods":
        fi = getattr(intel, "financial_intelligence", None)
        return bool(fi and fi.period_count > 0)
    elif evidence_type == "financial_metrics":
        dfi = getattr(intel, "deep_financial_insights", None)
        return bool(dfi and len(dfi.observations) > 0)
    elif evidence_type == "balance_sheet":
        bsd = getattr(intel, "balance_sheet_deep", None)
        return bool(bsd and bsd.observation_count > 0)
    elif evidence_type == "cash_flow":
        cfq = getattr(intel, "cash_flow_quality", None)
        return bool(cfq and cfq.observation_count > 0)
    elif evidence_type == "income_statement":
        fi = getattr(intel, "financial_intelligence", None)
        return bool(fi and fi.statement_count > 0)
    elif evidence_type == "source_attribution":
        return any(
            getattr(s, "provenance_completeness", False)
            for s in (getattr(intel, "source_statuses", ()) or ())
        )
    elif evidence_type == "period_consistency":
        fi = getattr(intel, "financial_intelligence", None)
        return bool(fi and fi.period_count >= 2)
    elif evidence_type == "business_events":
        return bool(getattr(intel, "business_events", ()) or ())
    elif evidence_type == "management_commentary":
        return bool(getattr(intel, "management_commentary", ()) or ())
    elif evidence_type == "tech_evidence":
        items = getattr(intel, "items", ()) or ()
        return any(
            "tech" in (getattr(i, "topic", "") or "").lower()
            or "ai" in (getattr(i, "topic", "") or "").lower()
            for i in items
        )
    elif evidence_type == "ai_evidence":
        items = getattr(intel, "items", ()) or ()
        return any(
            "ai" in (getattr(i, "title", "") or "").lower()
            for i in items
        )
    elif evidence_type == "timeline_entries":
        tl = getattr(intel, "timeline", None)
        return bool(tl and hasattr(tl, "entries") and len(tl.entries) > 0)
    elif evidence_type == "corporate_actions":
        items = getattr(intel, "items", ()) or ()
        return any(
            getattr(i, "event_type", None) is not None
            for i in items
        )
    elif evidence_type == "risk_items":
        return bool(getattr(intel, "risk_intelligence", ()) or ())
    elif evidence_type == "regulatory_items":
        items = getattr(intel, "items", ()) or ()
        return any(
            "regulatory" in (getattr(i, "topic", "") or "").lower()
            for i in items
        )
    elif evidence_type == "indirect_intelligence":
        return bool(getattr(intel, "indirect_intelligence", ()) or ())
    elif evidence_type == "sector_items":
        items = getattr(intel, "items", ()) or ()
        return any(
            "sector" in (getattr(i, "topic", "") or "").lower()
            or "industry" in (getattr(i, "topic", "") or "").lower()
            for i in items
        )
    elif evidence_type == "source_statuses":
        return bool(getattr(intel, "source_statuses", ()) or ())
    elif evidence_type == "evidence_items":
        return bool(evidence)
    elif evidence_type == "provenance":
        return bool(getattr(intel, "provenance_ids", ()) or ())
    elif evidence_type == "conflicting_claims":
        return bool(getattr(intel, "conflicts", ()) or ())
    elif evidence_type == "gap_definitions":
        gaps = getattr(intel, "research_gaps", None)
        return bool(gaps and hasattr(gaps, "gaps") and len(gaps.gaps) > 0)
    elif evidence_type == "available_at_timestamps":
        evidence = result.evidence_items or ()
        return any(getattr(e, "observation_at", None) for e in evidence)
    elif evidence_type == "pit_checks":
        return bool(getattr(result, "pit_checks", None))
    return False


def _get_missing_gaps(result: Any, required_domains: list[str]) -> tuple[str, ...]:
    """Get gap IDs related to required domains."""
    intel = result.intelligence
    gaps = getattr(intel, "research_gaps", None)
    if not gaps or not hasattr(gaps, "gaps"):
        return ()
    gap_list = list(gaps.gaps)
    domain_map = {
        "financials": "financial_data",
        "business": "business_profile",
        "events": "events",
        "technology": "technology",
        "risk": "risk",
        "market": "market",
    }
    return tuple(
        getattr(g, "gap_id", "")
        for g in gap_list
        if getattr(g, "category", "") in [domain_map.get(d, d) for d in required_domains]
    )


def _get_provenance(result: Any) -> tuple[str, ...]:
    """Get provenance IDs from result."""
    intel = result.intelligence
    return tuple(getattr(intel, "provenance_ids", ()) or ())


def evaluate_test(
    result: Any,
    test_def: dict[str, Any],
    *,
    as_of: datetime,
) -> TestExecution:
    """Evaluate a single research test against recorded data."""
    required = test_def["required_evidence"]
    available = [e for e in required if _check_evidence(result, e)]
    missing = [e for e in required if not _check_evidence(result, e)]

    # Determine state
    if not required:
        state = TestExecutionState.NOT_APPLICABLE
    elif len(available) == len(required):
        state = TestExecutionState.EVALUATED
    elif len(available) > 0:
        state = TestExecutionState.PARTIALLY_EVALUATED
    else:
        # Check if blocked by missing data
        gaps = _get_missing_gaps(result, test_def.get("required_domains", []))
        if gaps:
            state = TestExecutionState.BLOCKED
        else:
            state = TestExecutionState.NOT_EVALUABLE

    return TestExecution(
        test_id=test_def["test_id"],
        test_name=test_def["test_name"],
        state=state,
        required_evidence=tuple(required),
        available_evidence=tuple(available),
        missing_evidence=tuple(missing),
        related_gap_ids=_get_missing_gaps(result, test_def.get("required_domains", [])),
        as_of=as_of,
        provenance=_get_provenance(result),
    )


def build_test_execution_report(
    result: Any, *, as_of: datetime
) -> TestExecutionReport:
    """Build research test execution report for one company."""
    symbol = getattr(result, "company", "") or ""

    tests = tuple(evaluate_test(result, td, as_of=as_of) for td in TEST_DEFINITIONS)

    state_counts: dict[str, int] = {}
    for t in tests:
        state_counts[t.state.value] = state_counts.get(t.state.value, 0) + 1

    return TestExecutionReport(
        symbol=symbol,
        as_of=as_of,
        tests=tests,
        state_counts=state_counts,
        total_tests=len(tests),
    )
