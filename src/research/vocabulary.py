"""
Canonical Research Vocabulary (T1-W4).

Central module defining all normalized status/state vocabulary for the
research product. These are the canonical enums that new contracts should
reference. Existing module-local enums are NOT removed — this is additive.

Rules:
- No scoring, ranking, or recommendation vocabularies
- No causal language
- Missing → NOT_EVALUABLE + explicit reason; never delete tests
- Conflict Explorer never auto-selects a winner
"""

from __future__ import annotations

from enum import StrEnum


# ── Research Availability ──────────────────────────────────────────────

class ResearchAvailability(StrEnum):
    """How available is research data for a given area/company."""

    AVAILABLE = "AVAILABLE"
    LIMITED = "LIMITED"
    MISSING = "MISSING"
    STALE = "STALE"
    CONFLICTING = "CONFLICTING"
    INSUFFICIENT = "INSUFFICIENT"
    BLOCKED = "BLOCKED"


# ── Research Test State ───────────────────────────────────────────────

class ResearchTestState(StrEnum):
    """Whether a research test can be evaluated given available evidence."""

    EVALUATED = "EVALUATED"
    PARTIALLY_EVALUATED = "PARTIALLY_EVALUATED"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# ── Evidence Epistemic State ──────────────────────────────────────────

class EvidenceEpistemicType(StrEnum):
    """How a piece of evidence was produced (epistemological origin)."""

    REPORTED = "REPORTED"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"


class EvidenceEpistemicStrength(StrEnum):
    """Evidence strength / confidence level for business/tech observations."""

    STRONG = "STRONG"
    PARTIAL = "PARTIAL"
    WEAK = "WEAK"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


# ── Source Freshness ──────────────────────────────────────────────────

class SourceFreshness(StrEnum):
    """How fresh a data source is relative to its staleness threshold."""

    CURRENT = "CURRENT"
    STALE = "STALE"
    MISSING = "MISSING"
    DEGRADED = "DEGRADED"
    UNKNOWN = "UNKNOWN"


# ── Conflict Status ───────────────────────────────────────────────────

class ConflictResolution(StrEnum):
    """Resolution state of an evidence conflict."""

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    PARTIAL = "PARTIAL"


# ── Research Gap Status ───────────────────────────────────────────────

class ResearchGapStatus(StrEnum):
    """State of a research gap."""

    KNOWN = "KNOWN"
    PARTIALLY_KNOWN = "PARTIALLY_KNOWN"
    UNAVAILABLE = "UNAVAILABLE"
    CONFLICTING = "CONFLICTING"
    STALE = "STALE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


# ── Research Direction ────────────────────────────────────────────────

class ResearchDirection(StrEnum):
    """Directional coloring of an observation or evidence item."""

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


# ── Observation Severity ──────────────────────────────────────────────

class ObservationSeverity(StrEnum):
    """Severity level for observations and findings."""

    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ── Observation Origin ────────────────────────────────────────────────

class ObservationOrigin(StrEnum):
    """Whether an observation was directly reported or computed."""

    REPORTED = "REPORTED"
    DERIVED = "DERIVED"


# ── Verification Status ───────────────────────────────────────────────

class VerificationStatus(StrEnum):
    """How strongly a piece of intelligence is verified."""

    CONFIRMED = "CONFIRMED"
    REPORTED = "REPORTED"
    ALLEGED = "ALLEGED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    RESOLVED = "RESOLVED"


# ── Section Status ────────────────────────────────────────────────────

class SectionStatus(StrEnum):
    """Completeness of a research report section."""

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# ── Ownership Capability ──────────────────────────────────────────────

class OwnershipCapability(StrEnum):
    """Whether ownership data is available and in what capacity."""

    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"
    MISSING = "MISSING"


# ── Schema Versions ───────────────────────────────────────────────────

SNAPSHOT_SCHEMA_VERSION = "1.0.0"
SECTION_REGISTRY_SCHEMA_VERSION = "1.0.0"
VOCABULARY_VERSION = "1.0.0"
