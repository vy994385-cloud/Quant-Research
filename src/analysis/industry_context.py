"""
Industry context module.

Provides structured industry/sector context for a company based on
its business profile. This module enriches existing data with
industry-relevant context without converting it into rankings
or recommendations.

Context is descriptive only:
- What characteristics define this industry
- What technology areas are relevant
- What research questions are important for this sector
- How does this company's profile compare to industry norms

This module does NOT assign scores or recommend companies.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.data.company.business_profile import BusinessProfile


@dataclass(frozen=True)
class IndustryCharacteristic:
    """One characteristic of an industry."""

    name: str
    description: str
    relevance: str = "STANDARD"


@dataclass(frozen=True)
class IndustryResearchQuestion:
    """A research question relevant to this industry."""

    question: str
    category: str
    priority: str = "STANDARD"


@dataclass(frozen=True)
class IndustryContextResult:
    """
    Industry context for a company.

    Describes what is relevant to research in this industry.
    Does NOT rank or score companies within the industry.
    """

    symbol: str
    sector: str | None = None
    industry: str | None = None
    country: str | None = None

    characteristics: tuple[IndustryCharacteristic, ...] = ()
    relevant_metrics: tuple[str, ...] = ()
    research_questions: tuple[IndustryResearchQuestion, ...] = ()
    relevant_technology_areas: tuple[str, ...] = ()
    industry_risks: tuple[str, ...] = ()

    company_context: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


# ── Sector-specific definitions ───────────────────────────────────

_SECTOR_CHARACTERISTICS: dict[str, tuple[IndustryCharacteristic, ...]] = {
    "Technology": (
        IndustryCharacteristic(
            name="Innovation Cycles",
            description="Rapid product cycles and technology obsolescence risk.",
        ),
        IndustryCharacteristic(
            name="R&D Intensity",
            description="Significant investment in research and development.",
        ),
        IndustryCharacteristic(
            name="Scalability",
            description="Low marginal cost of serving additional customers.",
        ),
        IndustryCharacteristic(
            name="Network Effects",
            description="Platform and ecosystem dynamics can create competitive moats.",
        ),
    ),
    "Financial Services": (
        InterestCoverage := IndustryCharacteristic(
            name="Interest Rate Sensitivity",
            description="Performance influenced by interest rate environment.",
        ),
        IndustryCharacteristic(
            name="Regulatory Environment",
            description="Heavily regulated with capital adequacy requirements.",
        ),
        IndustryCharacteristic(
            name="Credit Risk",
            description="Asset quality driven by borrower creditworthiness.",
        ),
        IndustryCharacteristic(
            name="Deposit Franchise",
            description="Stable funding base is a key competitive advantage.",
        ),
    ),
    "Healthcare": (
        IndustryCharacteristic(
            name="Regulatory Approval",
            description="Product commercialization dependent on regulatory pathways.",
        ),
        IndustryCharacteristic(
            name="Pipeline Value",
            description="Future value driven by research pipeline and clinical trials.",
        ),
        IndustryCharacteristic(
            name="Patent Cliffs",
            description="Revenue exposure to patent expiration events.",
        ),
    ),
    "Energy": (
        IndustryCharacteristic(
            name="Commodity Price Exposure",
            description="Revenue directly linked to commodity prices.",
        ),
        IndustryCharacteristic(
            name="Capital Intensity",
            description="High upfront capital requirements for exploration and production.",
        ),
        IndustryCharacteristic(
            name="Reserve Life",
            description="Asset base defined by proven reserves and production rates.",
        ),
    ),
    "Consumer": (
        IndustryCharacteristic(
            name="Brand Value",
            description="Consumer brand recognition drives pricing power.",
        ),
        IndustryCharacteristic(
            name="Distribution Network",
            description="Physical and digital distribution reach is a competitive factor.",
        ),
        IndustryCharacteristic(
            name="Consumer Sentiment",
            description="Demand influenced by consumer confidence and spending patterns.",
        ),
    ),
    "Manufacturing": (
        IndustryCharacteristic(
            name="Capacity Utilization",
            description="Fixed cost structure makes utilization a key driver.",
        ),
        IndustryCharacteristic(
            name="Raw Material Costs",
            description="Input cost volatility impacts margins.",
        ),
        IndustryCharacteristic(
            name="Order Book",
            description="Backlog and forward orders indicate future revenue visibility.",
        ),
    ),
}

_SECTOR_METRICS: dict[str, tuple[str, ...]] = {
    "Technology": (
        "revenue_growth",
        "operating_margin",
        "free_cash_flow",
        "total_debt",
        "research_and_development",
    ),
    "Financial Services": (
        "net_profit_margin",
        "return_on_equity",
        "total_debt",
        "cash_and_equivalents",
        "current_ratio",
    ),
    "Healthcare": (
        "revenue_growth",
        "net_profit_margin",
        "operating_cash_flow",
        "total_debt",
        "free_cash_flow",
    ),
    "Energy": (
        "revenue",
        "operating_profit",
        "total_debt",
        "free_cash_flow",
        "total_assets",
    ),
    "Consumer": (
        "revenue",
        "net_profit_margin",
        "operating_cash_flow",
        "receivables",
        "total_debt",
    ),
    "Manufacturing": (
        "revenue",
        "operating_profit",
        "total_assets",
        "total_debt",
        "current_ratio",
    ),
}

_SECTOR_RISKS: dict[str, tuple[str, ...]] = {
    "Technology": (
        "Rapid technology obsolescence",
        "Key-person dependency in R&D",
        "Customer concentration in enterprise sales",
        "Cybersecurity exposure",
        "Regulatory changes in data privacy",
    ),
    "Financial Services": (
        "Credit quality deterioration",
        "Interest rate margin compression",
        "Regulatory capital requirements",
        "Systemic risk exposure",
        "Technology disruption in financial services",
    ),
    "Healthcare": (
        "Clinical trial failure risk",
        "Regulatory rejection or delay",
        "Patent expiration exposure",
        "Pricing pressure from payers",
        "Pipeline dependency",
    ),
    "Energy": (
        "Commodity price volatility",
        "Reserve depletion risk",
        "Environmental regulation changes",
        "Energy transition risk",
        "Capital project execution risk",
    ),
    "Consumer": (
        "Consumer demand slowdown",
        "Competitive intensity",
        "Raw material cost inflation",
        "Brand erosion risk",
        "Distribution channel disruption",
    ),
    "Manufacturing": (
        "Raw material price volatility",
        "Capacity utilization risk",
        "Supply chain disruption",
        "Export dependency",
        "Currency exposure",
    ),
}

_SECTOR_TECHNOLOGY: dict[str, tuple[str, ...]] = {
    "Technology": (
        "Artificial Intelligence", "Cloud Computing", "Cybersecurity",
        "Data Analytics", "Software Platforms",
    ),
    "Financial Services": (
        "Fintech", "Digital Banking", "Blockchain", "RegTech",
        "Payment Systems",
    ),
    "Healthcare": (
        "Biotechnology", "Digital Health", "Medical Devices",
        "Pharmaceutical R&D", "Telemedicine",
    ),
    "Energy": (
        "Renewable Energy", "Energy Storage", "Smart Grid",
        "Carbon Capture", "LNG Technology",
    ),
    "Consumer": (
        "E-commerce", "Supply Chain Technology", "Digital Marketing",
        "Customer Data Analytics", "Automation",
    ),
    "Manufacturing": (
        "Industrial Automation", "IoT", "Additive Manufacturing",
        "Robotics", "Digital Twin",
    ),
}


def build_industry_context(
    profile: BusinessProfile,
    symbol: str,
) -> IndustryContextResult:
    """
    Build industry context from a company's business profile.

    Returns descriptive context about the industry.
    Does NOT rank or score the company.
    """

    sector = profile.sector
    industry = profile.industry
    country = profile.country

    characteristics: tuple[IndustryCharacteristic, ...] = ()
    relevant_metrics: tuple[str, ...] = ()
    industry_risks: tuple[str, ...] = ()
    technology_areas: tuple[str, ...] = ()

    if sector:
        characteristics = _SECTOR_CHARACTERISTICS.get(sector, ())
        relevant_metrics = _SECTOR_METRICS.get(sector, ())
        industry_risks = _SECTOR_RISKS.get(sector, ())
        technology_areas = _SECTOR_TECHNOLOGY.get(sector, ())

    research_questions: list[IndustryResearchQuestion] = []

    if relevant_metrics:
        research_questions.append(
            IndustryResearchQuestion(
                question=(
                    "How do this company's financial metrics compare "
                    "to sector-relevant metrics?"
                ),
                category="FINANCIAL",
            )
        )

    if industry_risks:
        research_questions.append(
            IndustryResearchQuestion(
                question=(
                    "What sector-specific risks does this company face "
                    "based on its industry classification?"
                ),
                category="RISK",
            )
        )

    if technology_areas:
        research_questions.append(
            IndustryResearchQuestion(
                question=(
                    "What technology areas are relevant to this "
                    f"company's {sector} sector?"
                ),
                category="TECHNOLOGY",
            )
        )

    company_context: list[str] = []

    if profile.has_business_summary:
        company_context.append(
            "Business description available from provider."
        )
    if profile.has_sector:
        company_context.append(f"Sector: {sector}")
    if profile.has_industry:
        company_context.append(f"Industry: {industry}")
    if country:
        company_context.append(f"Country: {country}")
    if profile.has_employees:
        company_context.append(
            f"Employees: {profile.full_time_employees}"
        )

    notes: list[str] = []
    if not sector:
        notes.append(
            "Sector classification not available; "
            "industry context is limited."
        )
    if not characteristics:
        notes.append(
            f"No predefined characteristics for sector '{sector}'."
        )

    return IndustryContextResult(
        symbol=symbol,
        sector=sector,
        industry=industry,
        country=country,
        characteristics=characteristics,
        relevant_metrics=relevant_metrics,
        research_questions=tuple(research_questions),
        relevant_technology_areas=technology_areas,
        industry_risks=industry_risks,
        company_context=tuple(company_context),
        notes=tuple(notes),
    )
