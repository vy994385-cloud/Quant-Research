from src.research.source_catalog import (
    SourceDomain,
    SourceTier,
    enabled_sources,
    get_source,
    point_in_time_sources,
    sources_by_domain,
)


def test_sec_source_is_registered():
    source = get_source("sec_edgar")

    assert source.provider == (
        "U.S. Securities and Exchange Commission"
    )

    assert source.tier == SourceTier.PRIMARY
    assert source.domain == SourceDomain.FUNDAMENTALS
    assert source.supports_point_in_time is True


def test_fred_source_is_registered():
    source = get_source("fred")

    assert source.domain == SourceDomain.MACRO
    assert source.supports_historical is True
    assert source.supports_revisions is True


def test_indian_primary_sources_exist():
    assert get_source("rbi_dbie").tier == SourceTier.PRIMARY
    assert get_source("sebi").tier == SourceTier.PRIMARY
    assert get_source("nse_india").tier == SourceTier.PRIMARY
    assert get_source("bse_india").tier == SourceTier.PRIMARY


def test_enabled_sources_exclude_disabled_sources():
    sources = enabled_sources()

    names = {
        source.source_id
        for source in sources
    }

    assert "sec_edgar" in names
    assert "fred" in names
    assert "newswire" not in names
    assert "analyst_estimates" not in names


def test_point_in_time_sources_are_explicit():
    sources = point_in_time_sources()

    names = {
        source.source_id
        for source in sources
    }

    assert "sec_edgar" in names
    assert "fred" in names
    assert "nse_india" in names


def test_sources_can_be_filtered_by_domain():
    sources = sources_by_domain(
        SourceDomain.MACRO
    )

    names = {
        source.source_id
        for source in sources
    }

    assert "fred" in names
    assert "bls" in names
    assert "bea" in names
    assert "rbi_dbie" in names