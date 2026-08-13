from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.research.signals.models import ResearchSignal


class ResearchConclusion(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    MIXED = "MIXED"
    NEUTRAL = "NEUTRAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ResearchEvidence(BaseModel):
    """
    A concise, point-in-time piece of evidence included in a report.
    """

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    explanation: str = Field(min_length=1)

    symbol: str = Field(min_length=1)
    observation_at: datetime

    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()

    confidence: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    @field_validator("observation_at")
    @classmethod
    def require_timezone(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None:
            raise ValueError(
                "observation_at must be timezone-aware"
            )
        return value

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        value = value.strip().upper()

        if not value:
            raise ValueError("symbol cannot be empty")

        return value


class CompanyIntelligenceReport(BaseModel):
    """
    Report-level representation of normalized company intelligence.

    This is descriptive research evidence. It does not represent
    a trading or execution recommendation.
    """

    model_config = ConfigDict(extra="forbid")

    present: bool = False

    signal_count: int = Field(
        default=0,
        ge=0,
    )

    material_signal_count: int = Field(
        default=0,
        ge=0,
    )

    positive_signal_count: int = Field(
        default=0,
        ge=0,
    )

    negative_signal_count: int = Field(
        default=0,
        ge=0,
    )

    financial_observations: tuple[str, ...] = ()
    ownership_observations: tuple[str, ...] = ()
    management_observations: tuple[str, ...] = ()
    related_party_observations: tuple[str, ...] = ()
    event_observations: tuple[str, ...] = ()
    market_observations: tuple[str, ...] = ()
    risk_observations: tuple[str, ...] = ()

    future_readiness: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("100"),
    )

    ai_participation: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("100"),
    )

    innovation_execution: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("100"),
    )

    technology_diversification: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        le=Decimal("100"),
    )

    @property
    def is_mixed(self) -> bool:
        return (
            self.positive_signal_count > 0
            and self.negative_signal_count > 0
        )

    @property
    def has_observations(self) -> bool:
        return any(
            (
                self.financial_observations,
                self.ownership_observations,
                self.management_observations,
                self.related_party_observations,
                self.event_observations,
                self.market_observations,
                self.risk_observations,
            )
        )

    @property
    def has_future_intelligence(self) -> bool:
        return any(
            value is not None
            for value in (
                self.future_readiness,
                self.ai_participation,
                self.innovation_execution,
                self.technology_diversification,
            )
        )


class ResearchReport(BaseModel):
    """
    User-facing company research report.

    This is an evidence assembly layer. It does not claim
    to predict returns and does not fabricate missing evidence.
    """

    model_config = ConfigDict(extra="forbid")

    report_version: str = "1.0"

    symbol: str = Field(min_length=1)

    as_of: datetime

    conclusion: ResearchConclusion
    confidence: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
    )

    thesis: str = Field(min_length=1)

    features: tuple[str, ...] = ()
    signals: tuple[ResearchSignal, ...] = ()

    positive_evidence: tuple[ResearchEvidence, ...] = ()
    negative_evidence: tuple[ResearchEvidence, ...] = ()

    data_quality_notes: tuple[str, ...] = ()

    company_intelligence: CompanyIntelligenceReport = (
        CompanyIntelligenceReport()
    )

    company_intelligence_present: bool = False

    company_intelligence_signal_count: int = Field(
        default=0,
        ge=0,
    )

    company_intelligence_positive_count: int = Field(
        default=0,
        ge=0,
    )

    company_intelligence_negative_count: int = Field(
        default=0,
        ge=0,
    )

    @property
    def has_company_intelligence(self) -> bool:
        return self.company_intelligence_present

    @property
    def company_intelligence_is_mixed(self) -> bool:
        return (
            self.company_intelligence_positive_count > 0
            and self.company_intelligence_negative_count > 0
        )

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        value = value.strip().upper()

        if not value:
            raise ValueError("symbol cannot be empty")

        return value

    @field_validator("as_of")
    @classmethod
    def require_timezone(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None:
            raise ValueError(
                "as_of must be timezone-aware"
            )
        return value
