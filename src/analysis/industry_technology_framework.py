from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Industry(str, Enum):
    """
    Broad industry classifications used to determine which
    future-technology dimensions are relevant.

    These classifications describe analytical context only.
    They do not represent investment recommendations.
    """

    TECHNOLOGY = "TECHNOLOGY"
    SEMICONDUCTORS = "SEMICONDUCTORS"
    FINANCIAL_SERVICES = "FINANCIAL_SERVICES"
    AUTOMOTIVE = "AUTOMOTIVE"
    PHARMA_BIOTECH = "PHARMA_BIOTECH"
    ENERGY = "ENERGY"
    MANUFACTURING = "MANUFACTURING"
    TELECOM = "TELECOM"
    RETAIL = "RETAIL"
    AEROSPACE_DEFENSE = "AEROSPACE_DEFENSE"
    CHEMICALS_MATERIALS = "CHEMICALS_MATERIALS"
    REAL_ESTATE = "REAL_ESTATE"
    CONSUMER = "CONSUMER"
    HEALTHCARE = "HEALTHCARE"
    UTILITIES = "UTILITIES"
    TRANSPORTATION = "TRANSPORTATION"
    OTHER = "OTHER"


@dataclass(frozen=True)
class IndustryTechnologyCriteria:
    """
    Industry-specific definition of what constitutes relevant
    future technology and innovation.

    The scoring engine remains industry-agnostic.

    This object only answers:

        "What should we look for in this industry?"

    It does not assign a company score.
    """

    industry: Industry

    technology_areas: tuple[str, ...]

    primary_dimensions: tuple[str, ...]

    secondary_dimensions: tuple[str, ...]

    excluded_as_standalone_driver: tuple[str, ...]


COMMON_PRIMARY_DIMENSIONS = (
    "TECHNOLOGY_RELEVANCE",
    "EXECUTION",
    "COMMERCIALIZATION",
    "STRATEGIC_IMPORTANCE",
)

COMMON_SECONDARY_DIMENSIONS = (
    "EVIDENCE_QUALITY",
    "MATERIALITY",
    "CONFIDENCE",
)


def _criteria(
    industry: Industry,
    technology_areas: tuple[str, ...],
    secondary: tuple[str, ...] = (),
    excluded: tuple[str, ...] = (),
) -> IndustryTechnologyCriteria:
    return IndustryTechnologyCriteria(
        industry=industry,
        technology_areas=technology_areas,
        primary_dimensions=COMMON_PRIMARY_DIMENSIONS,
        secondary_dimensions=(
            COMMON_SECONDARY_DIMENSIONS + secondary
        ),
        excluded_as_standalone_driver=excluded,
    )


INDUSTRY_CRITERIA: dict[
    Industry,
    IndustryTechnologyCriteria,
] = {
    Industry.TECHNOLOGY: _criteria(
        Industry.TECHNOLOGY,
        (
            "ARTIFICIAL_INTELLIGENCE",
            "CLOUD",
            "SOFTWARE",
            "CYBERSECURITY",
            "DATA_INFRASTRUCTURE",
            "AUTOMATION",
            "SEMICONDUCTORS",
        ),
        secondary=(
            "PRODUCT_MODERNIZATION",
            "PLATFORM_ADOPTION",
        ),
        excluded=(
            "AI_HYPE_WITHOUT_EXECUTION",
        ),
    ),

    Industry.SEMICONDUCTORS: _criteria(
        Industry.SEMICONDUCTORS,
        (
            "SEMICONDUCTORS",
            "ADVANCED_MANUFACTURING",
            "ARTIFICIAL_INTELLIGENCE",
            "AUTOMATION",
            "DATA_INFRASTRUCTURE",
        ),
        secondary=(
            "PROCESS_NODE_ADVANCEMENT",
            "ADVANCED_PACKAGING",
            "MANUFACTURING_YIELD",
            "R_AND_D_PRODUCTIVITY",
            "CAPACITY_EXPANSION",
        ),
        excluded=(
            "AI_MENTION_WITHOUT_SEMICONDUCTOR_RELEVANCE",
        ),
    ),

    Industry.FINANCIAL_SERVICES: _criteria(
        Industry.FINANCIAL_SERVICES,
        (
            "SOFTWARE",
            "CLOUD",
            "CYBERSECURITY",
            "AUTOMATION",
            "DATA_INFRASTRUCTURE",
        ),
        secondary=(
            "DIGITAL_BANKING",
            "PAYMENTS",
            "FRAUD_PREVENTION",
            "OPERATIONAL_EFFICIENCY",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.AUTOMOTIVE: _criteria(
        Industry.AUTOMOTIVE,
        (
            "AUTOMATION",
            "ROBOTICS",
            "ENERGY_TECHNOLOGY",
            "SOFTWARE",
            "ADVANCED_MANUFACTURING",
            "ARTIFICIAL_INTELLIGENCE",
        ),
        secondary=(
            "ELECTRIC_VEHICLES",
            "BATTERY_TECHNOLOGY",
            "ADAS",
            "AUTONOMOUS_DRIVING",
            "SOFTWARE_DEFINED_VEHICLES",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.PHARMA_BIOTECH: _criteria(
        Industry.PHARMA_BIOTECH,
        (
            "BIOTECHNOLOGY",
            "ARTIFICIAL_INTELLIGENCE",
            "DATA_INFRASTRUCTURE",
            "ADVANCED_MANUFACTURING",
        ),
        secondary=(
            "CLINICAL_PROGRESS",
            "DRUG_PIPELINE",
            "PLATFORM_TECHNOLOGY",
            "REGULATORY_PROGRESS",
            "MANUFACTURING_CAPABILITY",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.ENERGY: _criteria(
        Industry.ENERGY,
        (
            "ENERGY_TECHNOLOGY",
            "ADVANCED_MANUFACTURING",
            "AUTOMATION",
            "DATA_INFRASTRUCTURE",
        ),
        secondary=(
            "ENERGY_STORAGE",
            "RENEWABLE_TECHNOLOGY",
            "GRID_TECHNOLOGY",
            "EFFICIENCY",
            "POWER_GENERATION_TECHNOLOGY",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.MANUFACTURING: _criteria(
        Industry.MANUFACTURING,
        (
            "ADVANCED_MANUFACTURING",
            "AUTOMATION",
            "ROBOTICS",
            "SOFTWARE",
            "ENERGY_TECHNOLOGY",
        ),
        secondary=(
            "PROCESS_EFFICIENCY",
            "PRODUCTION_YIELD",
            "MATERIALS_INNOVATION",
            "FACTORY_AUTOMATION",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.TELECOM: _criteria(
        Industry.TELECOM,
        (
            "SOFTWARE",
            "CLOUD",
            "DATA_INFRASTRUCTURE",
            "CYBERSECURITY",
            "AUTOMATION",
        ),
        secondary=(
            "NETWORK_MODERNIZATION",
            "FIBER",
            "FIFTH_GENERATION_NETWORKS",
            "SIXTH_GENERATION_RESEARCH",
            "NETWORK_AUTOMATION",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.RETAIL: _criteria(
        Industry.RETAIL,
        (
            "SOFTWARE",
            "AUTOMATION",
            "ROBOTICS",
            "DATA_INFRASTRUCTURE",
        ),
        secondary=(
            "DIGITAL_COMMERCE",
            "SUPPLY_CHAIN_TECHNOLOGY",
            "LOGISTICS",
            "INVENTORY_AUTOMATION",
            "CUSTOMER_PLATFORM",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.AEROSPACE_DEFENSE: _criteria(
        Industry.AEROSPACE_DEFENSE,
        (
            "SPACE",
            "ROBOTICS",
            "AUTOMATION",
            "ADVANCED_MANUFACTURING",
            "ARTIFICIAL_INTELLIGENCE",
        ),
        secondary=(
            "PROPULSION",
            "SATELLITE_TECHNOLOGY",
            "AUTONOMOUS_SYSTEMS",
            "ADVANCED_MATERIALS",
            "MANUFACTURING_CAPABILITY",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.CHEMICALS_MATERIALS: _criteria(
        Industry.CHEMICALS_MATERIALS,
        (
            "ADVANCED_MANUFACTURING",
            "ENERGY_TECHNOLOGY",
            "BIOTECHNOLOGY",
        ),
        secondary=(
            "NEW_MATERIALS",
            "PROCESS_EFFICIENCY",
            "SPECIALTY_PRODUCTS",
            "RESOURCE_EFFICIENCY",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.REAL_ESTATE: _criteria(
        Industry.REAL_ESTATE,
        (
            "SOFTWARE",
            "AUTOMATION",
            "ENERGY_TECHNOLOGY",
        ),
        secondary=(
            "PROPERTY_TECHNOLOGY",
            "CONSTRUCTION_TECHNOLOGY",
            "ENERGY_EFFICIENCY",
            "BUILDING_AUTOMATION",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.CONSUMER: _criteria(
        Industry.CONSUMER,
        (
            "SOFTWARE",
            "AUTOMATION",
            "ADVANCED_MANUFACTURING",
        ),
        secondary=(
            "PRODUCT_INNOVATION",
            "DISTRIBUTION_TECHNOLOGY",
            "MANUFACTURING_MODERNIZATION",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.HEALTHCARE: _criteria(
        Industry.HEALTHCARE,
        (
            "BIOTECHNOLOGY",
            "SOFTWARE",
            "DATA_INFRASTRUCTURE",
            "AUTOMATION",
            "ARTIFICIAL_INTELLIGENCE",
        ),
        secondary=(
            "DIAGNOSTICS",
            "MEDICAL_DEVICES",
            "DIGITAL_HEALTH",
            "CLINICAL_WORKFLOW",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.UTILITIES: _criteria(
        Industry.UTILITIES,
        (
            "ENERGY_TECHNOLOGY",
            "AUTOMATION",
            "DATA_INFRASTRUCTURE",
            "CYBERSECURITY",
        ),
        secondary=(
            "GRID_MODERNIZATION",
            "STORAGE",
            "GENERATION_EFFICIENCY",
            "INFRASTRUCTURE_AUTOMATION",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.TRANSPORTATION: _criteria(
        Industry.TRANSPORTATION,
        (
            "AUTOMATION",
            "ROBOTICS",
            "SOFTWARE",
            "ENERGY_TECHNOLOGY",
        ),
        secondary=(
            "LOGISTICS_TECHNOLOGY",
            "FLEET_MODERNIZATION",
            "ELECTRIFICATION",
            "ROUTE_OPTIMIZATION",
        ),
        excluded=(
            "AI_AS_A_STANDALONE_POSITIVE",
        ),
    ),

    Industry.OTHER: _criteria(
        Industry.OTHER,
        (
            "SOFTWARE",
            "AUTOMATION",
            "ADVANCED_MANUFACTURING",
            "ENERGY_TECHNOLOGY",
            "BIOTECHNOLOGY",
        ),
        secondary=(
            "PRODUCT_INNOVATION",
            "PROCESS_IMPROVEMENT",
        ),
        excluded=(
            "UNRELATED_TECHNOLOGY_HYPE",
        ),
    ),
}


def get_industry_technology_criteria(
    industry: Industry,
) -> IndustryTechnologyCriteria:
    """
    Return the standardized technology framework for an industry.

    The returned framework defines relevance only. It does not
    calculate a company score.
    """

    try:
        return INDUSTRY_CRITERIA[industry]
    except KeyError as exc:
        raise ValueError(
            f"No technology framework defined for industry: {industry}"
        ) from exc


def industry_supports_ai(
    industry: Industry,
) -> bool:
    """
    Determine whether AI is an explicitly relevant technology area
    for the industry.

    This does NOT mean AI automatically increases the score.
    Evidence must still demonstrate material, relevant activity.
    """

    criteria = get_industry_technology_criteria(industry)

    return (
        "ARTIFICIAL_INTELLIGENCE"
        in criteria.technology_areas
    )


def is_relevant_technology_area(
    industry: Industry,
    technology_area: str,
) -> bool:
    """
    Determine whether a technology area belongs to the industry's
    defined future-technology framework.
    """

    criteria = get_industry_technology_criteria(industry)

    return technology_area in criteria.technology_areas