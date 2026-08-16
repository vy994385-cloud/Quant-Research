from datetime import date, datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class FinancialSnapshot(BaseModel):
    """
    Normalized financial information for a reporting period.

    Values should eventually come from company filings or
    other verified financial sources.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    period_end: date

    period_start: date | None = None

    # Optional reporting-period metadata. Plain strings keep this
    # data-layer model decoupled from research-layer enums.
    period_type: str | None = None
    consolidation: str | None = None

    # Point-in-time metadata. `published_at` is when the company
    # reported the numbers; `available_at` is when the platform
    # could first know about them (defaults to the archival time).
    published_at: datetime | None = None
    available_at: datetime | None = None

    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None

    currency: str | None = None

    @field_validator("published_at", "available_at")
    @classmethod
    def _require_aware_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value

    revenue: Decimal | None = None
    operating_profit: Decimal | None = None
    net_profit: Decimal | None = None

    operating_cash_flow: Decimal | None = None
    free_cash_flow: Decimal | None = None

    total_assets: Decimal | None = None
    total_debt: Decimal | None = None
    cash_and_equivalents: Decimal | None = None

    receivables: Decimal | None = None
    payables: Decimal | None = None

    @property
    def profit_cash_flow_divergence(self) -> bool:
        """
        Basic screening flag.

        This is NOT a fraud detector.

        It only indicates that both profit and operating cash
        flow are available and have opposite signs.
        """

        if (
            self.net_profit is None
            or self.operating_cash_flow is None
        ):
            return False

        return (
            self.net_profit > 0
            and self.operating_cash_flow < 0
        )
