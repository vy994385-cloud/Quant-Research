"""
Business profile data model.

Structured metadata about a company's business operations:
sector, industry, employee count, geography, and descriptive summary.

This data is sourced from Yahoo Finance assetProfile/summaryProfile
modules and never invented by the platform.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BusinessProfile(BaseModel):
    """
    Structured business profile for a company.

    All fields are optional because not every company
    exposes all profile data through the provider.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    company_name: str | None = None

    sector: str | None = None

    industry: str | None = None

    country: str | None = None

    full_time_employees: int | None = Field(
        default=None,
        ge=0,
    )

    business_summary: str | None = None

    website: str | None = None

    # Valuation metrics from defaultKeyStatistics
    beta: float | None = None

    trailing_pe: float | None = None

    forward_pe: float | None = None

    peg_ratio: float | None = None

    price_to_book: float | None = None

    price_to_sales_trailing_12m: float | None = None

    enterprise_value: float | None = None

    profit_margin: float | None = None

    gross_margin: float | None = None

    operating_margin: float | None = None

    ebitda_margin: float | None = None

    book_value: float | None = None

    shares_outstanding: int | None = None

    float_shares: int | None = None

    held_percent_insiders: float | None = None

    held_percent_institutions: float | None = None

    short_ratio: float | None = None

    dividend_yield: float | None = None

    source_name: str | None = None

    source_type: str | None = None

    @property
    def has_sector(self) -> bool:
        return self.sector is not None and len(self.sector) > 0

    @property
    def has_industry(self) -> bool:
        return self.industry is not None and len(self.industry) > 0

    @property
    def has_employees(self) -> bool:
        return self.full_time_employees is not None

    @property
    def has_business_summary(self) -> bool:
        return self.business_summary is not None and len(self.business_summary) > 0

    @property
    def coverage_fields(self) -> tuple[str, ...]:
        """Return which profile fields are populated."""
        available: list[str] = []
        if self.company_name is not None:
            available.append("company_name")
        if self.has_sector:
            available.append("sector")
        if self.has_industry:
            available.append("industry")
        if self.country is not None:
            available.append("country")
        if self.has_employees:
            available.append("full_time_employees")
        if self.has_business_summary:
            available.append("business_summary")
        if self.website is not None:
            available.append("website")
        return tuple(available)

    @property
    def missing_fields(self) -> tuple[str, ...]:
        """Return which key profile fields are missing."""
        all_fields = (
            "company_name",
            "sector",
            "industry",
            "country",
            "full_time_employees",
            "business_summary",
            "website",
        )
        available = set(self.coverage_fields)
        return tuple(
            field for field in all_fields if field not in available
        )
