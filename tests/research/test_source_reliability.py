import pytest

from src.research.source_reliability import (
    SourceProfile,
    SourceReliabilityTier,
    get_default_source_profile,
    requires_independent_confirmation,
)


def test_source_profile_requires_name() -> None:
    with pytest.raises(
        ValueError,
        match="name cannot be empty",
    ):
        SourceProfile(
            name=" ",
            tier=SourceReliabilityTier.TIER_1,
            source_type="COMPANY",
        )


def test_sec_is_tier_one() -> None:
    profile = get_default_source_profile("SEC")

    assert profile is not None
    assert profile.tier == SourceReliabilityTier.TIER_1
    assert profile.official is True


def test_social_media_requires_confirmation() -> None:
    profile = get_default_source_profile("Social Media")

    assert profile is not None
    assert requires_independent_confirmation(profile) is True


def test_major_newswire_does_not_require_confirmation_by_default() -> None:
    profile = get_default_source_profile("Major Newswire")

    assert profile is not None
    assert profile.tier == SourceReliabilityTier.TIER_2
    assert requires_independent_confirmation(profile) is False


def test_unknown_source_requires_confirmation() -> None:
    profile = SourceProfile(
        name="Unknown Source",
        tier=SourceReliabilityTier.UNKNOWN,
        source_type="UNKNOWN",
    )

    assert requires_independent_confirmation(profile) is True


def test_source_lookup_is_case_insensitive() -> None:
    profile = get_default_source_profile("sec")

    assert profile is not None
    assert profile.name == "SEC"
