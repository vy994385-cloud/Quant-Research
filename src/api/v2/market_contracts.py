from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class MarketIndexContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: str
    price: float | None
    change: float | None
    change_pct: float | None
    trading_date: date | None


class MarketSecurityContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: str
    sector: str | None
    price: float | None
    change_pct: float | None
    volume: int | None
    average_volume_20d: float | None
    volume_ratio: float | None
    trading_date: date | None


class MarketSectorContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    securities: int
    advancing: int
    declining: int
    unchanged: int
    average_change_pct: float | None


class MarketBreadthContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    advancing: int
    declining: int
    unchanged: int
    total: int


class MarketCoverageContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    universe: str
    securities_available: int
    securities_with_prices: int
    securities_with_sector: int
    coverage_status: Literal["complete", "partial", "limited"]


class MarketOverviewContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: datetime
    price_date: date | None

    indices: list[MarketIndexContract]
    sector_indices: list[MarketIndexContract]
    breadth: MarketBreadthContract

    gainers: list[MarketSecurityContract]
    losers: list[MarketSecurityContract]
    active: list[MarketSecurityContract]
    sectors: list[MarketSectorContract]

    coverage: MarketCoverageContract
