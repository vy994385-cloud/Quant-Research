"""
Analyst and market intelligence data models.

Structured data from Yahoo Finance quote summary modules:
  - recommendationTrend: analyst buy/hold/sell recommendations
  - upgradeDowngradeHistory: analyst rating changes
  - earningsHistory: historical earnings surprises
  - calendarEvents: ex-dividend dates, earnings dates
  - summaryDetail: market cap, P/E, dividend yield, 52-week range

All fields are factual and never invented.
"""

from __future__ import annotations

from datetime import date as DateType
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AnalystRecommendation(BaseModel):
    """
    One period's analyst recommendation summary.
    """

    model_config = ConfigDict(extra="forbid")

    period: str = Field(min_length=1)

    strong_buy: int = Field(default=0, ge=0)

    buy: int = Field(default=0, ge=0)

    hold: int = Field(default=0, ge=0)

    sell: int = Field(default=0, ge=0)

    strong_sell: int = Field(default=0, ge=0)

    @property
    def total_analysts(self) -> int:
        return self.strong_buy + self.buy + self.hold + self.sell + self.strong_sell

    @property
    def consensus_score(self) -> Optional[float]:
        """Weighted consensus: 1=strong_sell, 5=strong_buy."""
        total = self.total_analysts
        if total == 0:
            return None
        weighted = (
            self.strong_sell * 1
            + self.sell * 2
            + self.hold * 3
            + self.buy * 4
            + self.strong_buy * 5
        )
        return round(weighted / total, 2)


class AnalystRatingChange(BaseModel):
    """
    One analyst rating change event.
    """

    model_config = ConfigDict(extra="forbid")

    firm: str = Field(min_length=1)

    analyst_name: Optional[str] = None

    action: str = Field(min_length=1)

    from_grade: Optional[str] = None

    to_grade: Optional[str] = None

    rating_date: Optional[DateType] = None

    source_name: Optional[str] = None
    source_type: Optional[str] = None


class EarningsSurprise(BaseModel):
    """
    One historical earnings surprise record.
    """

    model_config = ConfigDict(extra="forbid")

    period_ending: Optional[DateType] = None

    reported_eps: Optional[float] = None

    estimated_eps: Optional[float] = None

    surprise_amount: Optional[float] = None

    surprise_percentage: Optional[float] = None

    @property
    def beat_estimate(self) -> Optional[bool]:
        if self.reported_eps is None or self.estimated_eps is None:
            return None
        return self.reported_eps > self.estimated_eps

    @property
    def meets_estimate(self) -> Optional[bool]:
        if self.reported_eps is None or self.estimated_eps is None:
            return None
        return self.reported_eps == self.estimated_eps


class CalendarEvent(BaseModel):
    """
    One upcoming or recent calendar event.
    """

    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1)

    event_date: Optional[DateType] = None

    description: Optional[str] = None

    source_name: Optional[str] = None
    source_type: Optional[str] = None


class MarketValuation(BaseModel):
    """
    Market valuation data from summaryDetail and
    defaultKeyStatistics modules.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    market_cap: Optional[float] = None

    enterprise_value: Optional[float] = None

    trailing_pe: Optional[float] = None

    forward_pe: Optional[float] = None

    peg_ratio: Optional[float] = None

    price_to_book: Optional[float] = None

    price_to_sales: Optional[float] = None

    enterprise_to_revenue: Optional[float] = None

    enterprise_to_ebitda: Optional[float] = None

    dividend_yield: Optional[float] = None

    trailing_annual_dividend_yield: Optional[float] = None

    five_year_avg_dividend_yield: Optional[float] = None

    beta: Optional[float] = None

    fifty_two_week_high: Optional[float] = None

    fifty_two_week_low: Optional[float] = None

    fifty_day_average: Optional[float] = None

    two_hundred_day_average: Optional[float] = None

    avg_volume_10d: Optional[int] = None

    shares_outstanding: Optional[int] = None

    float_shares: Optional[int] = None

    source_name: Optional[str] = None
    source_type: Optional[str] = None


class AnalystIntelligence(BaseModel):
    """
    Combined analyst intelligence: recommendations, rating
    changes, and earnings history.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    recommendations: tuple[AnalystRecommendation, ...] = ()

    rating_changes: tuple[AnalystRatingChange, ...] = ()

    earnings_surprises: tuple[EarningsSurprise, ...] = ()

    calendar_events: tuple[CalendarEvent, ...] = ()

    valuation: Optional[MarketValuation] = None

    source_name: Optional[str] = None
    source_type: Optional[str] = None

    @property
    def has_recommendations(self) -> bool:
        return len(self.recommendations) > 0

    @property
    def has_rating_changes(self) -> bool:
        return len(self.rating_changes) > 0

    @property
    def has_earnings_history(self) -> bool:
        return len(self.earnings_surprises) > 0

    @property
    def recommendation_count(self) -> int:
        return len(self.recommendations)

    @property
    def rating_change_count(self) -> int:
        return len(self.rating_changes)

    @property
    def earnings_surprise_count(self) -> int:
        return len(self.earnings_surprises)
