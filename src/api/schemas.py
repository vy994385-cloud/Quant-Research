from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class StockSearchResult(BaseModel):
    symbol: str
    company_name: str | None = None
    score: str
    signal: str


class RankingResponse(BaseModel):
    horizon: str
    score: str
    signal: str
    confidence: str
    components: dict[str, str]


class StockResearchResponse(BaseModel):
    company: dict[str, Any]
    research_score: dict[str, Any]
    rankings: dict[str, RankingResponse]
    intelligence: dict[str, Any]
    financial_trends: list[dict[str, Any]]
    observations: dict[str, Any]
