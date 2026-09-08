"""
Research Section Registry (T1-W4).

Deterministic registry describing research sections. Each section
represents a domain of research data for a company. The registry
makes it possible for the frontend to know what's available without
fetching all data.

This is metadata, not scoring.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.research.vocabulary import (
    ResearchAvailability,
    SECTION_REGISTRY_SCHEMA_VERSION,
    SourceFreshness,
)


class SectionEntry(BaseModel):
    """
    One research section in the registry.

    Each entry defines, only where useful:
    - section_id: deterministic identifier
    - title: human-readable name
    - domain: research domain
    - available: whether data is available
    - item_count: number of items in this section
    - freshness_state: how fresh the data is
    - coverage_state: coverage availability
    - as_of: when this section was captured
    - source_count: how many sources contribute
    - limitations: any known limitations
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    section_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    domain: str = Field(default="", description="Research domain")
    available: bool = Field(default=False)
    item_count: int = Field(default=0, ge=0)
    freshness_state: SourceFreshness = Field(default=SourceFreshness.UNKNOWN)
    coverage_state: ResearchAvailability = Field(default=ResearchAvailability.MISSING)
    as_of: datetime | None = None
    source_count: int = Field(default=0, ge=0)
    limitations: str | None = None


class ResearchSectionRegistry(BaseModel):
    """
    Deterministic registry of all research sections for a company.

    Sections: OVERVIEW, FINANCIALS, BUSINESS, MARKET, TECHNOLOGY,
    EVENTS, EVIDENCE, COVERAGE, PROVENANCE.

    This is metadata, not scoring.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = Field(default=SECTION_REGISTRY_SCHEMA_VERSION)
    symbol: str = Field(min_length=1)
    as_of: datetime

    sections: tuple[SectionEntry, ...] = ()
    total_sections: int = Field(default=0, ge=0)
    available_sections: int = Field(default=0, ge=0)
    unavailable_sections: int = Field(default=0, ge=0)

    notes: tuple[str, ...] = ()


# ── Canonical Section Definitions ─────────────────────────────────────

CANONICAL_SECTIONS: tuple[tuple[str, str, str], ...] = (
    ("overview", "Overview", "identity"),
    ("financials", "Financials", "financial"),
    ("business", "Business", "business"),
    ("market", "Market", "market"),
    ("technology", "Technology", "technology"),
    ("events", "Events", "events"),
    ("evidence", "Evidence", "evidence"),
    ("coverage", "Coverage", "coverage"),
    ("provenance", "Provenance", "provenance"),
)
