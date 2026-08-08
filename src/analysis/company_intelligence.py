from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class IntelligenceDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"


class EvidenceReference(BaseModel):
    """
    A traceable reference supporting an observation.

    The intelligence layer should describe evidence rather than
    pretending that an observation is automatically true or predictive.
    """

    model_config = ConfigDict(extra="forbid")

    source_name: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    title: str = Field(min_length=1)

    published_date: date | None = None

    reliability_tier: int = Field(ge=1, le=5)

    reference: str | None = None


class IntelligenceSignal(BaseModel):
    """
    A normalized research observation.

    This is deliberately not a trading signal.
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)

    direction: IntelligenceDirection

    materiality: int = Field(ge=1, le=5)

    confidence: Decimal = Field(ge=0, le=1)

    evidence: list[EvidenceReference] = Field(
        default_factory=list
    )


class CompanyResearchSnapshot(BaseModel):
    """
    Unified company-intelligence snapshot.

    This object combines observations from the company's
    financial, ownership, management, event, market and
    risk-analysis layers.

    It does NOT produce a BUY or SELL recommendation.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    company_name: str | None = None

    as_of_date: date

    direction: IntelligenceDirection = (
        IntelligenceDirection.NEUTRAL
    )

    signals: list[IntelligenceSignal] = Field(
        default_factory=list
    )

    financial_observations: list[str] = Field(
        default_factory=list
    )

    ownership_observations: list[str] = Field(
        default_factory=list
    )

    management_observations: list[str] = Field(
        default_factory=list
    )

    related_party_observations: list[str] = Field(
        default_factory=list
    )

    event_observations: list[str] = Field(
        default_factory=list
    )

    market_observations: list[str] = Field(
        default_factory=list
    )

    risk_observations: list[str] = Field(
        default_factory=list
    )

    evidence: list[EvidenceReference] = Field(
        default_factory=list
    )

    @property
    def signal_count(self) -> int:
        return len(self.signals)

    @property
    def material_signal_count(self) -> int:
        return sum(
            signal.materiality >= 4
            for signal in self.signals
        )

    @property
    def positive_signal_count(self) -> int:
        return sum(
            signal.direction
            == IntelligenceDirection.POSITIVE
            for signal in self.signals
        )

    @property
    def negative_signal_count(self) -> int:
        return sum(
            signal.direction
            == IntelligenceDirection.NEGATIVE
            for signal in self.signals
        )

    @property
    def is_mixed(self) -> bool:
        return (
            self.positive_signal_count > 0
            and self.negative_signal_count > 0
        )

    @property
    def is_trade_signal(self) -> bool:
        """
        Explicitly prevents this research snapshot from
        being interpreted as an execution instruction.
        """

        return False


def build_company_research_snapshot(
    symbol: str,
    as_of_date: date,
    *,
    company_name: str | None = None,
    signals: list[IntelligenceSignal] | None = None,
    financial_observations: list[str] | None = None,
    ownership_observations: list[str] | None = None,
    management_observations: list[str] | None = None,
    related_party_observations: list[str] | None = None,
    event_observations: list[str] | None = None,
    market_observations: list[str] | None = None,
    risk_observations: list[str] | None = None,
    evidence: list[EvidenceReference] | None = None,
) -> CompanyResearchSnapshot:
    """
    Build a normalized company research snapshot.

    Direction is derived only from the supplied research signals.
    It is descriptive, not predictive.
    """

    normalized_signals = signals or []

    positive = sum(
        signal.direction == IntelligenceDirection.POSITIVE
        for signal in normalized_signals
    )

    negative = sum(
        signal.direction == IntelligenceDirection.NEGATIVE
        for signal in normalized_signals
    )

    if positive > 0 and negative > 0:
        direction = IntelligenceDirection.MIXED
    elif positive > negative:
        direction = IntelligenceDirection.POSITIVE
    elif negative > positive:
        direction = IntelligenceDirection.NEGATIVE
    else:
        direction = IntelligenceDirection.NEUTRAL

    return CompanyResearchSnapshot(
        symbol=symbol,
        company_name=company_name,
        as_of_date=as_of_date,
        direction=direction,
        signals=normalized_signals,
        financial_observations=financial_observations or [],
        ownership_observations=ownership_observations or [],
        management_observations=management_observations or [],
        related_party_observations=related_party_observations or [],
        event_observations=event_observations or [],
        market_observations=market_observations or [],
        risk_observations=risk_observations or [],
        evidence=evidence or [],
    )
