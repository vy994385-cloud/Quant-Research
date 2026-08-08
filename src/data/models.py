from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PriceBar(BaseModel):
    """
    Normalized daily OHLCV market-data record.

    Field-level validation happens during model construction.
    Cross-field market-data validation is exposed through
    is_valid_ohlc so ingestion/validation layers can decide
    whether a record should be accepted.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    trading_date: date

    open: Decimal = Field(gt=0)
    high: Decimal = Field(gt=0)
    low: Decimal = Field(gt=0)
    close: Decimal = Field(gt=0)

    volume: int = Field(ge=0)

    adjusted_close: Decimal | None = Field(
        default=None,
        gt=0,
    )

    @property
    def is_valid_ohlc(self) -> bool:
        return (
            self.low <= self.open
            and self.low <= self.close
            and self.high >= self.open
            and self.high >= self.close
            and self.high >= self.low
        )
