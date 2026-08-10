from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SourceReliabilityTier(str, Enum):
    """
    Reliability classification for research sources.

    This measures source quality and provenance, not the truth
    of an individual claim.
    """

    TIER_1 = "TIER_1"
    TIER_2 = "TIER_2"
    TIER_3 = "TIER_3"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SourceProfile:
    """
    Immutable description of a research source.
    """

    name: str
    tier: SourceReliabilityTier
    source_type: str
    official: bool = False
    requires_confirmation: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("name cannot be empty")

        if not self.source_type.strip():
            raise ValueError("source_type cannot be empty")


DEFAULT_SOURCE_PROFILES: tuple[SourceProfile, ...] = (
    SourceProfile(
        name="SEC",
        tier=SourceReliabilityTier.TIER_1,
        source_type="REGULATORY",
        official=True,
    ),
    SourceProfile(
        name="Federal Reserve",
        tier=SourceReliabilityTier.TIER_1,
        source_type="CENTRAL_BANK",
        official=True,
    ),
    SourceProfile(
        name="Company Filing",
        tier=SourceReliabilityTier.TIER_1,
        source_type="COMPANY",
        official=True,
    ),
    SourceProfile(
        name="Company Investor Relations",
        tier=SourceReliabilityTier.TIER_1,
        source_type="COMPANY",
        official=True,
    ),
    SourceProfile(
        name="Exchange",
        tier=SourceReliabilityTier.TIER_1,
        source_type="EXCHANGE",
        official=True,
    ),
    SourceProfile(
        name="Major Newswire",
        tier=SourceReliabilityTier.TIER_2,
        source_type="NEWSWIRE",
        official=False,
    ),
    SourceProfile(
        name="Financial Media",
        tier=SourceReliabilityTier.TIER_2,
        source_type="FINANCIAL_MEDIA",
        official=False,
    ),
    SourceProfile(
        name="Analyst Research",
        tier=SourceReliabilityTier.TIER_2,
        source_type="ANALYST",
        official=False,
        requires_confirmation=True,
    ),
    SourceProfile(
        name="Aggregator",
        tier=SourceReliabilityTier.TIER_3,
        source_type="AGGREGATOR",
        official=False,
        requires_confirmation=True,
    ),
    SourceProfile(
        name="Social Media",
        tier=SourceReliabilityTier.TIER_3,
        source_type="SOCIAL",
        official=False,
        requires_confirmation=True,
    ),
)


def get_default_source_profile(
    name: str,
) -> SourceProfile | None:
    """
    Return the default profile matching a source name.
    """

    normalized = name.strip().lower()

    for profile in DEFAULT_SOURCE_PROFILES:
        if profile.name.lower() == normalized:
            return profile

    return None


def requires_independent_confirmation(
    profile: SourceProfile,
) -> bool:
    """
    Return whether the source should normally be independently
    confirmed before being treated as a high-confidence fact.
    """

    return (
        profile.requires_confirmation
        or profile.tier
        in {
            SourceReliabilityTier.TIER_3,
            SourceReliabilityTier.UNKNOWN,
        }
    )
