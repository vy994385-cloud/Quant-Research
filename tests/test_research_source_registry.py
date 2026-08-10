from src.research.source_catalog import (
    SourceDomain,
    SourceTier,
)
from src.research.source_registry import (
    ResearchSourceRegistry,
)


def test_registry_loads_catalog():
    registry = ResearchSourceRegistry()

    assert "sec_edgar" in registry.names
    assert "fred" in registry.names
    assert "rbi_dbie" in registry.names


def test_registry_gets_source():
    registry = ResearchSourceRegistry()

    source = registry.get("SEC_EDGAR")

    assert source.source_id == "sec_edgar"


def test_registry_filters_by_domain():
    registry = ResearchSourceRegistry()

    sources = registry.by_domain(
        SourceDomain.MACRO
    )

    assert any(
        source.source_id == "fred"
        for source in sources
    )


def test_registry_filters_by_tier():
    registry = ResearchSourceRegistry()

    sources = registry.by_tier(
        SourceTier.PRIMARY
    )

    assert all(
        source.tier == SourceTier.PRIMARY
        for source in sources
    )


def test_registry_returns_point_in_time_sources():
    registry = ResearchSourceRegistry()

    sources = registry.point_in_time_ready()

    assert any(
        source.source_id == "sec_edgar"
        for source in sources
    )