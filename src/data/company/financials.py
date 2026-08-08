from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FinancialSnapshot(BaseModel):
    """
    Normalized financial information for a reporting period.

    Values should eventually come from company filings or
    other verified financial sources.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    period_end: date

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
