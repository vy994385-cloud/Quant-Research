from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SourceTier(str, Enum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    ALTERNATIVE = "ALTERNATIVE"


class SourceDomain(str, Enum):
    MARKET = "MARKET"
    FUNDAMENTALS = "FUNDAMENTALS"
    MACRO = "MACRO"
    MONETARY_POLICY = "MONETARY_POLICY"
    REGULATORY = "REGULATORY"
    CORPORATE_ACTIONS = "CORPORATE_ACTIONS"
    NEWS = "NEWS"
    ESTIMATES = "ESTIMATES"
    COMMODITIES = "COMMODITIES"
    FX = "FX"
    RATES = "RATES"
    ALTERNATIVE = "ALTERNATIVE"


@dataclass(frozen=True)
class ResearchSource:
    """
    Canonical description of an external research source.

    This describes the source itself, not individual observations.
    Retrieved observations must carry their own provenance.
    """

    source_id: str
    name: str
    provider: str

    tier: SourceTier
    domain: SourceDomain

    base_url: str
    description: str

    supports_historical: bool
    supports_point_in_time: bool
    supports_revisions: bool

    requires_api_key: bool = False
    licensed_data: bool = False
    enabled: bool = True

    def __post_init__(self) -> None:
        for field_name in (
            "source_id",
            "name",
            "provider",
            "base_url",
            "description",
        ):
            value = getattr(self, field_name)

            if not value.strip():
                raise ValueError(
                    f"{field_name} cannot be empty"
                )

        if not self.base_url.startswith(
            ("http://", "https://")
        ):
            raise ValueError(
                "base_url must be an HTTP or HTTPS URL"
            )


RESEARCH_SOURCES: tuple[ResearchSource, ...] = (
    ResearchSource(
        source_id="sec_edgar",
        name="SEC EDGAR",
        provider="U.S. Securities and Exchange Commission",
        tier=SourceTier.PRIMARY,
        domain=SourceDomain.FUNDAMENTALS,
        base_url="https://www.sec.gov/edgar",
        description=(
            "SEC filings, submissions and XBRL company facts."
        ),
        supports_historical=True,
        supports_point_in_time=True,
        supports_revisions=True,
        requires_api_key=False,
    ),

    ResearchSource(
        source_id="fred",
        name="FRED / ALFRED",
        provider="Federal Reserve Bank of St. Louis",
        tier=SourceTier.PRIMARY,
        domain=SourceDomain.MACRO,
        base_url="https://fred.stlouisfed.org",
        description=(
            "Macroeconomic and financial time series with "
            "historical real-time periods and vintage data."
        ),
        supports_historical=True,
        supports_point_in_time=True,
        supports_revisions=True,
        requires_api_key=True,
    ),

    ResearchSource(
        source_id="bls",
        name="BLS Public Data",
        provider="U.S. Bureau of Labor Statistics",
        tier=SourceTier.PRIMARY,
        domain=SourceDomain.MACRO,
        base_url="https://www.bls.gov/developers/",
        description=(
            "Employment, inflation, labor and price statistics."
        ),
        supports_historical=True,
        supports_point_in_time=False,
        supports_revisions=True,
        requires_api_key=False,
    ),

    ResearchSource(
        source_id="bea",
        name="BEA Data API",
        provider="U.S. Bureau of Economic Analysis",
        tier=SourceTier.PRIMARY,
        domain=SourceDomain.MACRO,
        base_url="https://www.bea.gov/",
        description=(
            "GDP, income, industry and national-account statistics."
        ),
        supports_historical=True,
        supports_point_in_time=False,
        supports_revisions=True,
        requires_api_key=True,
    ),

    ResearchSource(
        source_id="federal_reserve",
        name="Federal Reserve",
        provider="Board of Governors of the Federal Reserve System",
        tier=SourceTier.PRIMARY,
        domain=SourceDomain.MONETARY_POLICY,
        base_url="https://www.federalreserve.gov/",
        description=(
            "Monetary-policy decisions, statements and official "
            "economic information."
        ),
        supports_historical=True,
        supports_point_in_time=True,
        supports_revisions=True,
        requires_api_key=False,
    ),

    ResearchSource(
        source_id="rbi_dbie",
        name="RBI DBIE",
        provider="Reserve Bank of India",
        tier=SourceTier.PRIMARY,
        domain=SourceDomain.MACRO,
        base_url="https://data.rbi.org.in/",
        description=(
            "Indian monetary, banking, financial and economic statistics."
        ),
        supports_historical=True,
        supports_point_in_time=False,
        supports_revisions=True,
        requires_api_key=False,
    ),

    ResearchSource(
        source_id="sebi",
        name="SEBI",
        provider="Securities and Exchange Board of India",
        tier=SourceTier.PRIMARY,
        domain=SourceDomain.REGULATORY,
        base_url="https://www.sebi.gov.in/",
        description=(
            "Indian securities-market regulation, reports and statistics."
        ),
        supports_historical=True,
        supports_point_in_time=False,
        supports_revisions=True,
        requires_api_key=False,
    ),

    ResearchSource(
        source_id="nse_india",
        name="NSE India",
        provider="National Stock Exchange of India",
        tier=SourceTier.PRIMARY,
        domain=SourceDomain.MARKET,
        base_url="https://www.nseindia.com/",
        description=(
            "Indian exchange market and historical market information."
        ),
        supports_historical=True,
        supports_point_in_time=True,
        supports_revisions=False,
        requires_api_key=False,
        licensed_data=True,
    ),

    ResearchSource(
        source_id="bse_india",
        name="BSE India",
        provider="BSE Ltd.",
        tier=SourceTier.PRIMARY,
        domain=SourceDomain.MARKET,
        base_url="https://www.bseindia.com/",
        description=(
            "Indian exchange market, corporate and historical information."
        ),
        supports_historical=True,
        supports_point_in_time=True,
        supports_revisions=False,
        requires_api_key=False,
        licensed_data=True,
    ),

    ResearchSource(
        source_id="company_ir",
        name="Company Investor Relations",
        provider="Individual public companies",
        tier=SourceTier.PRIMARY,
        domain=SourceDomain.FUNDAMENTALS,
        base_url="https://www.example.com/",
        description=(
            "Company announcements, earnings material, presentations "
            "and investor communications."
        ),
        supports_historical=True,
        supports_point_in_time=True,
        supports_revisions=False,
        requires_api_key=False,
    ),

    ResearchSource(
        source_id="licensed_news",
        name="Licensed News Provider",
        provider="Licensed provider",
        tier=SourceTier.SECONDARY,
        domain=SourceDomain.NEWS,
        base_url="https://www.example.com/",
        description=(
            "Licensed real-time and historical news/event coverage."
        ),
        supports_historical=True,
        supports_point_in_time=True,
        supports_revisions=False,
        licensed_data=True,
        enabled=False,
    ),

    ResearchSource(
        source_id="licensed_estimates",
        name="Licensed Analyst Estimates",
        provider="Licensed provider",
        tier=SourceTier.SECONDARY,
        domain=SourceDomain.ESTIMATES,
        base_url="https://www.example.com/",
        description=(
            "Historical analyst estimates, consensus data and revisions."
        ),
        supports_historical=True,
        supports_point_in_time=True,
        supports_revisions=True,
        licensed_data=True,
        enabled=False,
    ),
)


def get_source(source_id: str) -> ResearchSource:
    """
    Return one registered research source.
    """

    key = source_id.strip().lower()

    for source in RESEARCH_SOURCES:
        if source.source_id == key:
            return source

    raise KeyError(
        f"unknown research source: {source_id}"
    )


def enabled_sources() -> tuple[ResearchSource, ...]:
    """
    Return currently enabled research sources.
    """

    return tuple(
        source
        for source in RESEARCH_SOURCES
        if source.enabled
    )


def sources_by_domain(
    domain: SourceDomain,
) -> tuple[ResearchSource, ...]:
    """
    Return all sources covering a research domain.
    """

    return tuple(
        source
        for source in RESEARCH_SOURCES
        if source.domain == domain
    )


def point_in_time_sources() -> tuple[ResearchSource, ...]:
    """
    Return sources explicitly marked as supporting
    point-in-time historical research.
    """

    return tuple(
        source
        for source in RESEARCH_SOURCES
        if source.supports_point_in_time
    )


def primary_sources() -> tuple[ResearchSource, ...]:
    """
    Return all primary sources.
    """

    return tuple(
        source
        for source in RESEARCH_SOURCES
        if source.tier == SourceTier.PRIMARY
    )