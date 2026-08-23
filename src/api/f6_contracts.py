"""
F6 — Research Product Expansion API contracts.

Pydantic models for chart data, company news, corporate actions,
industry context, and tracking endpoints.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


# =====================================================================
# Chart Data contracts
# =====================================================================


class ContractChartDataPoint(BaseModel):
    """A single data point in a chart time series."""

    model_config = ConfigDict(extra="forbid")

    period_end: str
    value: str | None = None
    available: bool
    as_of: str | None = None
    source: str | None = None


class ContractChartSeries(BaseModel):
    """A named time series of data points for charting.

    `currency` declares the currency for CURRENCY-unit series
    ("INR"); it is null for ratios and percentages.
    """

    model_config = ConfigDict(extra="forbid")

    metric: str
    label: str
    unit: str
    category: str
    currency: str | None = None
    data_points: list[ContractChartDataPoint] = []
    period_count: int = 0
    available_count: int = 0
    missing_count: int = 0
    source: str | None = None


class ContractChartDataSet(BaseModel):
    """Complete chart-ready data set for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    as_of: str
    series: list[ContractChartSeries] = []
    categories: list[str] = []
    total_metrics: int = 0
    total_data_points: int = 0
    notes: list[str] = []


class CompanyChartDataContract(BaseModel):
    """Chart data response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    chart_data: ContractChartDataSet | None = None


# =====================================================================
# Company News contracts
# =====================================================================


class ContractCompanyNewsItem(BaseModel):
    """A single news item for a company."""

    model_config = ConfigDict(extra="forbid")

    news_id: str
    symbol: str
    headline: str
    summary: str = ""
    category: str
    direction: str = "UNKNOWN"
    source_name: str = ""
    source_url: str = ""
    source_type: str = ""
    published_at: str | None = None
    available_at: str | None = None
    event_date: str | None = None
    related_metrics: list[str] = []
    evidence_refs: list[str] = []
    as_of: str | None = None
    provenance_id: str | None = None


class ContractCompanyNewsResult(BaseModel):
    """Aggregated news results for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    as_of: str
    items: list[ContractCompanyNewsItem] = []
    item_count: int = 0
    category_counts: dict[str, int] = {}
    source_count: int = 0
    source_names: list[str] = []
    notes: list[str] = []


class CompanyNewsContract(BaseModel):
    """News response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    news: ContractCompanyNewsResult | None = None


# =====================================================================
# Corporate Actions contracts
# =====================================================================


class ContractCorporateActionItem(BaseModel):
    """A single corporate action for a company."""

    model_config = ConfigDict(extra="forbid")

    action_id: str
    symbol: str
    action_type: str
    title: str
    description: str = ""
    announcement_date: str | None = None
    effective_date: str | None = None
    record_date: str | None = None
    value: str | None = None
    ratio: str | None = None
    source_name: str = ""
    source_url: str = ""
    provenance_id: str | None = None
    published_at: str | None = None
    available_at: str | None = None
    as_of: str | None = None


class ContractCorporateActionResult(BaseModel):
    """Aggregated corporate actions for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    as_of: str
    items: list[ContractCorporateActionItem] = []
    item_count: int = 0
    type_counts: dict[str, int] = {}
    source_count: int = 0
    notes: list[str] = []


class CompanyCorporateActionsContract(BaseModel):
    """Corporate actions response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    corporate_actions: ContractCorporateActionResult | None = None


# =====================================================================
# Industry Context contracts
# =====================================================================


class ContractIndustryCharacteristic(BaseModel):
    """One characteristic of an industry."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    relevance: str = "STANDARD"


class ContractIndustryResearchQuestion(BaseModel):
    """A research question relevant to this industry."""

    model_config = ConfigDict(extra="forbid")

    question: str
    category: str
    priority: str = "STANDARD"


class ContractIndustryContextResult(BaseModel):
    """Industry context for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    characteristics: list[ContractIndustryCharacteristic] = []
    relevant_metrics: list[str] = []
    research_questions: list[ContractIndustryResearchQuestion] = []
    relevant_technology_areas: list[str] = []
    industry_risks: list[str] = []
    company_context: list[str] = []
    notes: list[str] = []


class CompanyIndustryContextContract(BaseModel):
    """Industry context response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    industry_context: ContractIndustryContextResult | None = None


# =====================================================================
# Tracking contracts
# =====================================================================


class ContractTrackingChange(BaseModel):
    """A single tracked change for a company."""

    model_config = ConfigDict(extra="forbid")

    change_id: str
    symbol: str
    domain: str
    severity: str = "INFO"
    title: str
    description: str = ""
    previous_value: str | None = None
    current_value: str | None = None
    change_date: str | None = None
    evidence_refs: list[str] = []
    source_names: list[str] = []
    as_of: str | None = None


class ContractTrackingResult(BaseModel):
    """Tracking result for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    as_of: str
    changes: list[ContractTrackingChange] = []
    change_count: int = 0
    domain_counts: dict[str, int] = {}
    significant_count: int = 0
    notable_count: int = 0
    notes: list[str] = []


class CompanyTrackingContract(BaseModel):
    """Tracking response for one company."""

    model_config = ConfigDict(extra="forbid")

    company: dict[str, object]
    tracking: ContractTrackingResult | None = None


__all__ = [
    "CompanyChartDataContract",
    "CompanyCorporateActionsContract",
    "CompanyIndustryContextContract",
    "CompanyNewsContract",
    "CompanyTrackingContract",
    "ContractChartDataPoint",
    "ContractChartDataSet",
    "ContractChartSeries",
    "ContractCompanyNewsItem",
    "ContractCompanyNewsResult",
    "ContractCorporateActionItem",
    "ContractCorporateActionResult",
    "ContractIndustryCharacteristic",
    "ContractIndustryContextResult",
    "ContractIndustryResearchQuestion",
    "ContractTrackingChange",
    "ContractTrackingResult",
]
