from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class StockSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    company_name: str | None = None
    score: str
    signal: str
    confidence: str | None = None
    research_ready: bool = False


class RankingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    company_name: str | None = None
    horizon: str
    score: str
    signal: str
    confidence: str
    priority: int | None = None
    is_high_priority: bool = False
    components: dict[str, str] = {}


class StockRankingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    company_name: str | None = None
    rankings: dict[str, RankingResponse]


class StockUniverseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    count: int
    results: list[StockSearchResult]


class StockResearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: dict[str, Any]
    research_score: dict[str, Any]
    rankings: dict[str, RankingResponse]
    highest_priority_horizon: str | None = None
    average_ranking_score: str | None = None
    research_ready: bool = False
    intelligence: dict[str, Any]
    financial_trends: list[dict[str, Any]] = []
    observations: dict[str, Any]
    evidence: list[dict[str, Any]] = []
    is_trade_signal: bool = False