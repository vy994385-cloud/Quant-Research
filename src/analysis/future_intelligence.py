from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class FutureTechnologyArea(str, Enum):
    """
    Technology and innovation areas that may materially affect
    a company's future competitive position.

    The area itself does not imply that the activity is valuable.
    Evidence, execution, commercialization and strategic relevance
    determine the eventual score.
    """

    ARTIFICIAL_INTELLIGENCE = "ARTIFICIAL_INTELLIGENCE"
    AUTOMATION = "AUTOMATION"
    ROBOTICS = "ROBOTICS"
    SEMICONDUCTORS = "SEMICONDUCTORS"
    CLOUD = "CLOUD"
    CYBERSECURITY = "CYBERSECURITY"
    SOFTWARE = "SOFTWARE"
    DATA_INFRASTRUCTURE = "DATA_INFRASTRUCTURE"
    ENERGY_TECHNOLOGY = "ENERGY_TECHNOLOGY"
    BIOTECHNOLOGY = "BIOTECHNOLOGY"
    ADVANCED_MANUFACTURING = "ADVANCED_MANUFACTURING"
    SPACE = "SPACE"
    EVOLUTION_OF_PRODUCTS = "EVOLUTION_OF_PRODUCTS"
    OTHER = "OTHER"


class InnovationEvidenceStrength(str, Enum):
    VERIFIED = "VERIFIED"
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    UNVERIFIED = "UNVERIFIED"


class InnovationSignalDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


class FutureTechnologyIndustry(str, Enum):
    """
    Normalized industry families used to determine which forms
    of innovation are relevant.

    Industry classification itself does not generate a score.
    It only determines which technology areas are considered
    relevant when actual evidence is evaluated.
    """

    INFORMATION_TECHNOLOGY = "INFORMATION_TECHNOLOGY"
    SEMICONDUCTORS = "SEMICONDUCTORS"
    MANUFACTURING = "MANUFACTURING"
    AUTOMOTIVE = "AUTOMOTIVE"
    ENERGY = "ENERGY"
    PHARMA_BIOTECH = "PHARMA_BIOTECH"
    BANKING_FINANCIAL_SERVICES = "BANKING_FINANCIAL_SERVICES"
    TELECOMMUNICATIONS = "TELECOMMUNICATIONS"
    RETAIL_CONSUMER = "RETAIL_CONSUMER"
    AEROSPACE_DEFENSE = "AEROSPACE_DEFENSE"
    CHEMICALS_MATERIALS = "CHEMICALS_MATERIALS"
    MINING_METALS = "MINING_METALS"
    CONSTRUCTION_INFRASTRUCTURE = "CONSTRUCTION_INFRASTRUCTURE"
    AGRICULTURE = "AGRICULTURE"
    REAL_ESTATE = "REAL_ESTATE"
    UTILITIES = "UTILITIES"
    OTHER = "OTHER"


class IndustryInnovationCriteria(BaseModel):
    """
    Defines which technology areas are relevant for an industry.

    This is a relevance map, not a scoring shortcut.

    A company receives no benefit merely from belonging to an
    industry. Actual evidence must still exist.
    """

    model_config = ConfigDict(extra="forbid")

    industry: FutureTechnologyIndustry

    relevant_technology_areas: tuple[
        FutureTechnologyArea, ...
    ]

    rationale: str = Field(min_length=1)


INDUSTRY_INNOVATION_CRITERIA: dict[
    FutureTechnologyIndustry,
    IndustryInnovationCriteria,
] = {
    FutureTechnologyIndustry.INFORMATION_TECHNOLOGY:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.INFORMATION_TECHNOLOGY,
            relevant_technology_areas=(
                FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE,
                FutureTechnologyArea.CLOUD,
                FutureTechnologyArea.CYBERSECURITY,
                FutureTechnologyArea.SOFTWARE,
                FutureTechnologyArea.DATA_INFRASTRUCTURE,
                FutureTechnologyArea.AUTOMATION,
            ),
            rationale=(
                "Software, AI, cloud, cybersecurity, data infrastructure "
                "and automation are core technology-development vectors."
            ),
        ),

    FutureTechnologyIndustry.SEMICONDUCTORS:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.SEMICONDUCTORS,
            relevant_technology_areas=(
                FutureTechnologyArea.SEMICONDUCTORS,
                FutureTechnologyArea.ADVANCED_MANUFACTURING,
                FutureTechnologyArea.AUTOMATION,
                FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE,
                FutureTechnologyArea.DATA_INFRASTRUCTURE,
            ),
            rationale=(
                "Process technology, chip architecture, advanced packaging, "
                "manufacturing capability and specialized computing demand "
                "are central innovation vectors."
            ),
        ),

    FutureTechnologyIndustry.MANUFACTURING:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.MANUFACTURING,
            relevant_technology_areas=(
                FutureTechnologyArea.ADVANCED_MANUFACTURING,
                FutureTechnologyArea.AUTOMATION,
                FutureTechnologyArea.ROBOTICS,
                FutureTechnologyArea.ENERGY_TECHNOLOGY,
                FutureTechnologyArea.EVOLUTION_OF_PRODUCTS,
            ),
            rationale=(
                "Factory automation, robotics, production efficiency, "
                "energy efficiency and product modernization are relevant."
            ),
        ),

    FutureTechnologyIndustry.AUTOMOTIVE:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.AUTOMOTIVE,
            relevant_technology_areas=(
                FutureTechnologyArea.EVOLUTION_OF_PRODUCTS,
                FutureTechnologyArea.AUTOMATION,
                FutureTechnologyArea.ROBOTICS,
                FutureTechnologyArea.ENERGY_TECHNOLOGY,
                FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE,
                FutureTechnologyArea.ADVANCED_MANUFACTURING,
            ),
            rationale=(
                "Vehicle electrification, batteries, software, driver "
                "assistance, manufacturing and automation drive innovation."
            ),
        ),

    FutureTechnologyIndustry.ENERGY:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.ENERGY,
            relevant_technology_areas=(
                FutureTechnologyArea.ENERGY_TECHNOLOGY,
                FutureTechnologyArea.ADVANCED_MANUFACTURING,
                FutureTechnologyArea.AUTOMATION,
                FutureTechnologyArea.DATA_INFRASTRUCTURE,
            ),
            rationale=(
                "Generation technology, storage, grid systems, efficiency "
                "and operational technology are central future vectors."
            ),
        ),

    FutureTechnologyIndustry.PHARMA_BIOTECH:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.PHARMA_BIOTECH,
            relevant_technology_areas=(
                FutureTechnologyArea.BIOTECHNOLOGY,
                FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE,
                FutureTechnologyArea.DATA_INFRASTRUCTURE,
                FutureTechnologyArea.AUTOMATION,
            ),
            rationale=(
                "Drug discovery, biological platforms, clinical development, "
                "automation and data-driven research are relevant."
            ),
        ),

    FutureTechnologyIndustry.BANKING_FINANCIAL_SERVICES:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.BANKING_FINANCIAL_SERVICES,
            relevant_technology_areas=(
                FutureTechnologyArea.SOFTWARE,
                FutureTechnologyArea.CYBERSECURITY,
                FutureTechnologyArea.DATA_INFRASTRUCTURE,
                FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE,
                FutureTechnologyArea.AUTOMATION,
            ),
            rationale=(
                "Digital infrastructure, cybersecurity, automation, "
                "payments and data systems are important modernization areas."
            ),
        ),

    FutureTechnologyIndustry.TELECOMMUNICATIONS:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.TELECOMMUNICATIONS,
            relevant_technology_areas=(
                FutureTechnologyArea.DATA_INFRASTRUCTURE,
                FutureTechnologyArea.ADVANCED_MANUFACTURING,
                FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE,
                FutureTechnologyArea.AUTOMATION,
                FutureTechnologyArea.CLOUD,
            ),
            rationale=(
                "Network infrastructure, network automation, cloud systems "
                "and next-generation connectivity are key innovation areas."
            ),
        ),

    FutureTechnologyIndustry.RETAIL_CONSUMER:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.RETAIL_CONSUMER,
            relevant_technology_areas=(
                FutureTechnologyArea.SOFTWARE,
                FutureTechnologyArea.AUTOMATION,
                FutureTechnologyArea.DATA_INFRASTRUCTURE,
                FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE,
                FutureTechnologyArea.EVOLUTION_OF_PRODUCTS,
            ),
            rationale=(
                "Commerce platforms, logistics, personalization, automation "
                "and product evolution are relevant."
            ),
        ),

    FutureTechnologyIndustry.AEROSPACE_DEFENSE:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.AEROSPACE_DEFENSE,
            relevant_technology_areas=(
                FutureTechnologyArea.SPACE,
                FutureTechnologyArea.ADVANCED_MANUFACTURING,
                FutureTechnologyArea.ROBOTICS,
                FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE,
                FutureTechnologyArea.AUTOMATION,
            ),
            rationale=(
                "Propulsion, aerospace systems, autonomous systems, robotics "
                "and advanced manufacturing are core innovation vectors."
            ),
        ),

    FutureTechnologyIndustry.CHEMICALS_MATERIALS:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.CHEMICALS_MATERIALS,
            relevant_technology_areas=(
                FutureTechnologyArea.ADVANCED_MANUFACTURING,
                FutureTechnologyArea.ENERGY_TECHNOLOGY,
                FutureTechnologyArea.EVOLUTION_OF_PRODUCTS,
                FutureTechnologyArea.AUTOMATION,
            ),
            rationale=(
                "Process innovation, advanced materials, efficiency and "
                "manufacturing technology are relevant."
            ),
        ),

    FutureTechnologyIndustry.MINING_METALS:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.MINING_METALS,
            relevant_technology_areas=(
                FutureTechnologyArea.AUTOMATION,
                FutureTechnologyArea.ROBOTICS,
                FutureTechnologyArea.ADVANCED_MANUFACTURING,
                FutureTechnologyArea.ENERGY_TECHNOLOGY,
            ),
            rationale=(
                "Extraction automation, autonomous equipment, processing "
                "efficiency and energy technology are relevant."
            ),
        ),

    FutureTechnologyIndustry.CONSTRUCTION_INFRASTRUCTURE:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.CONSTRUCTION_INFRASTRUCTURE,
            relevant_technology_areas=(
                FutureTechnologyArea.ADVANCED_MANUFACTURING,
                FutureTechnologyArea.AUTOMATION,
                FutureTechnologyArea.ROBOTICS,
                FutureTechnologyArea.EVOLUTION_OF_PRODUCTS,
                FutureTechnologyArea.ENERGY_TECHNOLOGY,
            ),
            rationale=(
                "Construction technology, prefabrication, automation, "
                "robotics, materials and energy efficiency are relevant."
            ),
        ),

    FutureTechnologyIndustry.AGRICULTURE:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.AGRICULTURE,
            relevant_technology_areas=(
                FutureTechnologyArea.AUTOMATION,
                FutureTechnologyArea.ROBOTICS,
                FutureTechnologyArea.BIOTECHNOLOGY,
                FutureTechnologyArea.DATA_INFRASTRUCTURE,
                FutureTechnologyArea.ENERGY_TECHNOLOGY,
            ),
            rationale=(
                "Precision agriculture, biotechnology, automation, robotics "
                "and resource efficiency are relevant."
            ),
        ),

    FutureTechnologyIndustry.REAL_ESTATE:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.REAL_ESTATE,
            relevant_technology_areas=(
                FutureTechnologyArea.SOFTWARE,
                FutureTechnologyArea.DATA_INFRASTRUCTURE,
                FutureTechnologyArea.AUTOMATION,
                FutureTechnologyArea.ENERGY_TECHNOLOGY,
            ),
            rationale=(
                "Property technology, data systems, building automation "
                "and energy efficiency are relevant."
            ),
        ),

    FutureTechnologyIndustry.UTILITIES:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.UTILITIES,
            relevant_technology_areas=(
                FutureTechnologyArea.ENERGY_TECHNOLOGY,
                FutureTechnologyArea.DATA_INFRASTRUCTURE,
                FutureTechnologyArea.AUTOMATION,
                FutureTechnologyArea.CYBERSECURITY,
            ),
            rationale=(
                "Grid technology, operational systems, automation, "
                "cybersecurity and energy efficiency are relevant."
            ),
        ),

    FutureTechnologyIndustry.OTHER:
        IndustryInnovationCriteria(
            industry=FutureTechnologyIndustry.OTHER,
            relevant_technology_areas=(
                FutureTechnologyArea.EVOLUTION_OF_PRODUCTS,
                FutureTechnologyArea.AUTOMATION,
                FutureTechnologyArea.ADVANCED_MANUFACTURING,
                FutureTechnologyArea.SOFTWARE,
            ),
            rationale=(
                "Generic product evolution, automation, manufacturing and "
                "software modernization provide a conservative fallback."
            ),
        ),
}


class FutureTechnologySignal(BaseModel):
    """
    Evidence-backed observation about technology, innovation,
    commercialization or future-business positioning.

    This is not a price prediction.
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)

    technology_area: FutureTechnologyArea

    direction: InnovationSignalDirection

    materiality: int = Field(
        ge=1,
        le=5,
    )

    confidence: Decimal = Field(
        ge=0,
        le=1,
    )

    evidence_strength: InnovationEvidenceStrength

    evidence_codes: list[str] = Field(
        default_factory=list,
    )

    technology_relevance: Decimal = Field(
        default=Decimal("50"),
        ge=0,
        le=100,
    )

    execution_strength: Decimal = Field(
        default=Decimal("50"),
        ge=0,
        le=100,
    )

    commercialization_strength: Decimal = Field(
        default=Decimal("50"),
        ge=0,
        le=100,
    )

    strategic_importance: Decimal = Field(
        default=Decimal("50"),
        ge=0,
        le=100,
    )


class FutureTechnologyProfile(BaseModel):
    """
    Company-level future business and technology profile.

    Sector determines the relevance framework.

    Sector membership alone never creates a positive score.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    sector: str | None = None

    signals: list[FutureTechnologySignal] = Field(
        default_factory=list,
    )

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def positive_signal_count(self) -> int:
        return sum(
            signal.direction
            == InnovationSignalDirection.POSITIVE
            for signal in self.signals
        )

    @property
    def negative_signal_count(self) -> int:
        return sum(
            signal.direction
            == InnovationSignalDirection.NEGATIVE
            for signal in self.signals
        )

    @property
    def neutral_signal_count(self) -> int:
        return sum(
            signal.direction
            == InnovationSignalDirection.NEUTRAL
            for signal in self.signals
        )

    @property
    def material_signal_count(self) -> int:
        return sum(
            signal.materiality >= 4
            for signal in self.signals
        )

    @property
    def verified_signal_count(self) -> int:
        return sum(
            signal.evidence_strength
            == InnovationEvidenceStrength.VERIFIED
            for signal in self.signals
        )

    @property
    def technology_area_count(self) -> int:
        return len(
            {
                signal.technology_area
                for signal in self.signals
            }
        )

    @property
    def ai_signal_count(self) -> int:
        return sum(
            signal.technology_area
            == FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE
            for signal in self.signals
        )

    @property
    def is_mixed(self) -> bool:
        return (
            self.positive_signal_count > 0
            and self.negative_signal_count > 0
        )

    @property
    def has_verified_future_activity(self) -> bool:
        return self.verified_signal_count > 0

    @property
    def has_commercialization_evidence(self) -> bool:
        return any(
            signal.commercialization_strength
            >= Decimal("70")
            for signal in self.signals
        )

    @property
    def has_execution_evidence(self) -> bool:
        return any(
            signal.execution_strength
            >= Decimal("70")
            for signal in self.signals
        )


def build_future_technology_profile(
    symbol: str,
    *,
    sector: str | None = None,
    signals: list[FutureTechnologySignal] | None = None,
) -> FutureTechnologyProfile:
    """
    Build a normalized future-technology profile.

    Sector is metadata used to select the appropriate innovation
    relevance framework. It does not itself affect scoring.
    """

    normalized_symbol = symbol.strip().upper()

    if not normalized_symbol:
        raise ValueError("symbol cannot be empty")

    normalized_sector = (
        sector.strip()
        if sector is not None
        else None
    )

    if normalized_sector == "":
        normalized_sector = None

    return FutureTechnologyProfile(
        symbol=normalized_symbol,
        sector=normalized_sector,
        signals=signals or [],
    )


def _evidence_weight(
    strength: InnovationEvidenceStrength,
) -> Decimal:
    return {
        InnovationEvidenceStrength.VERIFIED: Decimal("1.00"),
        InnovationEvidenceStrength.STRONG: Decimal("0.85"),
        InnovationEvidenceStrength.MODERATE: Decimal("0.65"),
        InnovationEvidenceStrength.WEAK: Decimal("0.35"),
        InnovationEvidenceStrength.UNVERIFIED: Decimal("0.00"),
    }[strength]


def _direction_value(
    direction: InnovationSignalDirection,
) -> Decimal:
    return {
        InnovationSignalDirection.POSITIVE: Decimal("100"),
        InnovationSignalDirection.NEGATIVE: Decimal("0"),
        InnovationSignalDirection.NEUTRAL: Decimal("50"),
        InnovationSignalDirection.MIXED: Decimal("50"),
    }[direction]


def _normalize_sector(
    sector: str | None,
) -> FutureTechnologyIndustry:
    """
    Convert common sector/industry labels into the normalized
    industry framework.

    Unknown labels intentionally fall back to OTHER rather than
    receiving a technology score simply because they contain a
    fashionable keyword.
    """

    if not sector:
        return FutureTechnologyIndustry.OTHER

    value = sector.strip().lower()

    aliases = {
        FutureTechnologyIndustry.INFORMATION_TECHNOLOGY: {
            "information technology",
            "information technology services",
            "it",
            "technology",
            "software",
            "software & services",
            "internet",
            "application software",
        },
        FutureTechnologyIndustry.SEMICONDUCTORS: {
            "semiconductor",
            "semiconductors",
            "semiconductor equipment",
            "chips",
        },
        FutureTechnologyIndustry.MANUFACTURING: {
            "manufacturing",
            "industrial",
            "industrials",
            "industrial products",
            "engineering",
        },
        FutureTechnologyIndustry.AUTOMOTIVE: {
            "automotive",
            "automobiles",
            "auto",
            "auto components",
            "automobile",
        },
        FutureTechnologyIndustry.ENERGY: {
            "energy",
            "oil & gas",
            "oil and gas",
            "renewable energy",
            "power",
            "power generation",
        },
        FutureTechnologyIndustry.PHARMA_BIOTECH: {
            "pharmaceuticals",
            "pharma",
            "biotechnology",
            "biotech",
            "life sciences",
        },
        FutureTechnologyIndustry.BANKING_FINANCIAL_SERVICES: {
            "banking",
            "banks",
            "financial services",
            "finance",
            "insurance",
            "fintech",
        },
        FutureTechnologyIndustry.TELECOMMUNICATIONS: {
            "telecommunications",
            "telecom",
            "communication services",
        },
        FutureTechnologyIndustry.RETAIL_CONSUMER: {
            "retail",
            "consumer",
            "consumer discretionary",
            "consumer staples",
            "e-commerce",
            "ecommerce",
          },
        FutureTechnologyIndustry.AEROSPACE_DEFENSE: {
            "aerospace",
            "defense",
            "defence",
            "aerospace & defense",
            "aerospace and defense",
        },
        FutureTechnologyIndustry.CHEMICALS_MATERIALS: {
            "chemicals",
            "chemical",
            "materials",
            "specialty chemicals",
        },
        FutureTechnologyIndustry.MINING_METALS: {
            "mining",
            "metals",
            "mining & metals",
            "steel",
            "aluminium",
            "aluminum",
        },
        FutureTechnologyIndustry.CONSTRUCTION_INFRASTRUCTURE: {
            "construction",
            "infrastructure",
            "engineering construction",
            "building materials",
        },
        FutureTechnologyIndustry.AGRICULTURE: {
            "agriculture",
            "farming",
            "agri",
            "agrochemicals",
        },
        FutureTechnologyIndustry.REAL_ESTATE: {
            "real estate",
            "reit",
            "property",
        },
        FutureTechnologyIndustry.UTILITIES: {
            "utilities",
            "utility",
        },
    }

    for industry, labels in aliases.items():
        if value in labels:
            return industry

    return FutureTechnologyIndustry.OTHER


def industry_innovation_criteria(
    sector: str | None,
) -> IndustryInnovationCriteria:
    """
    Return the innovation framework applicable to a sector.

    This function only determines relevance. It does not score
    the company.
    """

    industry = _normalize_sector(sector)

    return INDUSTRY_INNOVATION_CRITERIA[industry]


def _industry_relevance_multiplier(
    profile: FutureTechnologyProfile,
    signal: FutureTechnologySignal,
) -> Decimal:
    """
    Determine whether a signal belongs to the company's relevant
    innovation framework.

    Relevant technology receives a modest multiplier.

    The multiplier is deliberately conservative so industry
    classification cannot overpower evidence quality.
    """

    criteria = industry_innovation_criteria(
        profile.sector
    )

    if signal.technology_area in (
        criteria.relevant_technology_areas
    ):
        return Decimal("1.00")

    return Decimal("0.70")


def _weighted_signal_score(
    signal: FutureTechnologySignal,
    *,
    relevance_multiplier: Decimal = Decimal("1"),
) -> Decimal:
    """
    Score one innovation observation.

    The same scoring dimensions are used across every industry.
    Industry-specific logic enters only through relevance.
    """

    direction_score = _direction_value(
        signal.direction
    )

    quality_score = (
        signal.execution_strength * Decimal("0.30")
        + signal.commercialization_strength * Decimal("0.30")
        + signal.technology_relevance * Decimal("0.20")
        + signal.strategic_importance * Decimal("0.20")
    )

    if signal.direction == InnovationSignalDirection.POSITIVE:
        base_score = (
            direction_score * Decimal("0.60")
            + quality_score * Decimal("0.40")
        )

    elif signal.direction == InnovationSignalDirection.NEGATIVE:
        negative_quality = (
            Decimal("100") - quality_score
        )

        base_score = (
            direction_score * Decimal("0.60")
            + negative_quality * Decimal("0.40")
        )

    else:
        base_score = direction_score

    return (
        base_score * relevance_multiplier
        + Decimal("50")
        * (Decimal("1") - relevance_multiplier)
    )


def future_readiness_score(
    profile: FutureTechnologyProfile,
) -> Decimal:
    """
    Produce a descriptive 0-100 future-readiness score.

    This is NOT a predicted stock return.

    The score is based on evidence rather than sector popularity.

    Every industry uses the same evidence framework:

        evidence
        × materiality
        × confidence
        × execution/commercialization quality
        × strategic relevance

    The industry framework only determines how relevant a technology
    area is to that company's actual business.
    """

    if not profile.signals:
        return Decimal("50")

    weighted_total = Decimal("0")
    total_weight = Decimal("0")

    for signal in profile.signals:

        evidence_weight = _evidence_weight(
            signal.evidence_strength
        )

        materiality_weight = (
            Decimal(signal.materiality)
            / Decimal("5")
        )

        confidence_weight = signal.confidence

        weight = (
            evidence_weight
            * materiality_weight
            * confidence_weight
        )

        if weight <= 0:
            continue

        relevance_multiplier = (
            _industry_relevance_multiplier(
                profile,
                signal,
            )
        )

        signal_score = _weighted_signal_score(
            signal,
            relevance_multiplier=relevance_multiplier,
        )

        weighted_total += (
            signal_score * weight
        )

        total_weight += weight

    if total_weight <= 0:
        return Decimal("50")

    score = weighted_total / total_weight

    return max(
        Decimal("0"),
        min(Decimal("100"), score),
    )



def sector_fit_score(
    profile: FutureTechnologyProfile,
) -> Decimal | None:
    """
    Measure how strongly demonstrated company innovation fits the
    technology vectors that are relevant to its industry.

    Sector membership alone creates no score.

    A score is returned only when there is usable, evidence-backed
    technology activity. Unverified or zero-weight evidence does not
    create artificial neutral evidence.

    The calculation uses the existing future-intelligence framework:

        industry relevance
        × evidence strength
        × materiality
        × confidence
        × execution
        × commercialization
        × technology relevance
        × strategic importance

    This is a descriptive research factor, not a price prediction.
    """

    if not profile.signals:
        return None

    weighted_total = Decimal("0")
    total_weight = Decimal("0")

    criteria = industry_innovation_criteria(profile.sector)

    for signal in profile.signals:
        evidence_weight = _evidence_weight(
            signal.evidence_strength
        )

        materiality_weight = (
            Decimal(signal.materiality) / Decimal("5")
        )

        weight = (
            evidence_weight
            * materiality_weight
            * signal.confidence
        )

        if weight <= 0:
            continue

        relevant = (
            signal.technology_area
            in criteria.relevant_technology_areas
        )

        # Relevant technology receives full consideration.
        # Unrelated technology is deliberately discounted rather
        # than treated as equally valuable to the industry.
        relevance_multiplier = (
            Decimal("1.00")
            if relevant
            else Decimal("0.70")
        )

        quality_score = (
            signal.execution_strength * Decimal("0.30")
            + signal.commercialization_strength * Decimal("0.30")
            + signal.technology_relevance * Decimal("0.20")
            + signal.strategic_importance * Decimal("0.20")
        )

        if signal.direction == InnovationSignalDirection.POSITIVE:
            direction_score = (
                Decimal("60") + quality_score * Decimal("0.40")
            )
        elif signal.direction == InnovationSignalDirection.NEGATIVE:
            direction_score = (
                Decimal("40") - quality_score * Decimal("0.40")
            )
        elif signal.direction == InnovationSignalDirection.NEUTRAL:
            direction_score = Decimal("50")
        else:
            direction_score = Decimal("50")

        signal_score = (
            direction_score * relevance_multiplier
            + Decimal("50")
            * (Decimal("1") - relevance_multiplier)
        )

        weighted_total += signal_score * weight
        total_weight += weight

    if total_weight <= 0:
        return None

    score = weighted_total / total_weight

    return max(
        Decimal("0"),
        min(Decimal("100"), score),
    )


def innovation_execution_score(
    profile: FutureTechnologyProfile,
) -> Decimal:
    """
    Measure how strongly innovation activity is supported by
    execution and commercialization evidence.

    This metric deliberately uses the same criteria across
    industries. It does not assume that AI, software or any other
    technology is inherently superior.
    """

    if not profile.signals:
        return Decimal("50")

    weighted_total = Decimal("0")
    total_weight = Decimal("0")

    execution_terms = {
        "commercial",
        "commercialized",
        "commercialization",
        "deployed",
        "deployment",
        "production",
        "product",
        "launched",
        "launch",
        "revenue",
        "customer",
        "customers",
        "adoption",
        "operational",
        "implementation",
        "implemented",
        "contract",
        "contracts",
        "sold",
        "sales",
    }

    for signal in profile.signals:

        text = (
            f"{signal.title} "
            f"{signal.description}"
        ).lower()

        matched_terms = sum(
            term in text
            for term in execution_terms
        )

        explicit_execution_factor = (
            min(
                Decimal("1"),
                Decimal(matched_terms)
                / Decimal("3"),
            )
        )

        evidence_weight = _evidence_weight(
            signal.evidence_strength
        )

        materiality_weight = (
            Decimal(signal.materiality)
            / Decimal("5")
        )

        weight = (
            evidence_weight
            * materiality_weight
            * signal.confidence
        )

        if weight <= 0:
            continue

        dimension_score = (
            signal.execution_strength
            * Decimal("0.55")
            + signal.commercialization_strength
            * Decimal("0.45")
        )

        keyword_adjusted_score = (
            dimension_score * Decimal("0.70")
            + (
                Decimal("50")
                + Decimal("50")
                * explicit_execution_factor
            )
            * Decimal("0.30")
        )

        weighted_total += (
            keyword_adjusted_score * weight
        )

        total_weight += weight

    if total_weight <= 0:
        return Decimal("50")

    score = weighted_total / total_weight

    return max(
        Decimal("0"),
        min(Decimal("100"), score),
    )


def technology_diversification_score(
    profile: FutureTechnologyProfile,
) -> Decimal:
    """
    Measure breadth of credible innovation activity.

    Only positive, non-unverified technology activity counts.

    No technology receives extra credit merely because it is
    fashionable.
    """

    areas = {
        signal.technology_area
        for signal in profile.signals
        if (
            signal.direction
            == InnovationSignalDirection.POSITIVE
            and signal.evidence_strength
            != InnovationEvidenceStrength.UNVERIFIED
        )
    }

    count = len(areas)

    if count == 0:
        return Decimal("0")

    scores = {
        1: Decimal("65"),
        2: Decimal("72"),
        3: Decimal("78"),
        4: Decimal("82"),
        5: Decimal("86"),
        6: Decimal("89"),
        7: Decimal("92"),
        8: Decimal("94"),
    }

    if count >= 8:
        return Decimal("95")

    return scores[count]


def ai_participation_score(
    profile: FutureTechnologyProfile,
) -> Decimal:
    """
    Measure demonstrated AI participation specifically.

    AI is NOT treated as a universal future-technology requirement.

    Therefore:

        no AI signals -> 0

    This is intentional.

    A manufacturing company, energy company, bank or pharmaceutical
    company can receive a strong future-readiness score without any
    AI activity if it demonstrates meaningful innovation in the
    technology areas relevant to its own industry.
    """

    ai_signals = [
        signal
        for signal in profile.signals
        if signal.technology_area
        == FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE
    ]

    if not ai_signals:
        return Decimal("0")

    weighted_total = Decimal("0")
    total_weight = Decimal("0")

    for signal in ai_signals:

        weight = (
            _evidence_weight(
                signal.evidence_strength
            )
            * (
                Decimal(signal.materiality)
                / Decimal("5")
            )
            * signal.confidence
        )

        if weight <= 0:
            continue

        activity_score = (
            signal.execution_strength
            * Decimal("0.35")
            + signal.commercialization_strength
            * Decimal("0.35")
            + signal.strategic_importance
            * Decimal("0.20")
            + signal.technology_relevance
            * Decimal("0.10")
        )

        weighted_total += (
            activity_score * weight
        )

        total_weight += weight

    if total_weight <= 0:
        return Decimal("0")

    score = weighted_total / total_weight

    return max(
        Decimal("0"),
        min(Decimal("100"), score),
    )