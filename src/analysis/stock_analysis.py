from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
)
from src.analysis.research_scoring import (
    ResearchScore,
    calculate_research_score,
)
from src.features.market_snapshot import (
    MarketFeatureSnapshot,
)
from src.ranking.stock_ranker import (
    RankingInput,
    StockRanking,
    rank_stock,
)


@dataclass(frozen=True)
class StockAnalysisReport:
    """
    Unified stock-research result.

    This is a research and ranking object.

    It does not:
    - execute trades
    - predict guaranteed returns
    - place orders
    - represent investment advice
    """

    symbol: str
    as_of_date: date

    research_score: ResearchScore
    company_intelligence: CompanyResearchSnapshot
    market_snapshot: MarketFeatureSnapshot

    intraday: StockRanking
    swing: StockRanking
    long_term: StockRanking

    @property
    def highest_priority_horizon(self) -> str:
        rankings = {
            "INTRADAY": self.intraday.score,
            "SWING": self.swing.score,
            "LONG_TERM": self.long_term.score,
        }

        return max(
            rankings,
            key=rankings.get,
        )

    @property
    def average_ranking_score(self) -> Decimal:
        return (
            self.intraday.score
            + self.swing.score
            + self.long_term.score
        ) / Decimal("3")

    @property
    def is_research_ready(self) -> bool:
        return (
            self.symbol.strip() != ""
            and self.company_intelligence.symbol == self.symbol
            and self.market_snapshot.symbol == self.symbol
        )


def build_stock_analysis(
    *,
    symbol: str,
    as_of_date: date,
    company_intelligence: CompanyResearchSnapshot,
    market_snapshot: MarketFeatureSnapshot,

    fundamentals: Decimal,
    financial_trends: Decimal,
    cash_flow: Decimal,
    balance_sheet: Decimal,
    risk: Decimal,
    management: Decimal,
    market_behavior: Decimal,
    evidence_quality: Decimal,

    liquidity: Decimal,
    relative_strength: Decimal,
    catalyst_strength: Decimal,
    valuation: Decimal,
) -> StockAnalysisReport:
    """
    Build the complete research view for one stock.

    All supplied component scores must be between 0 and 100.

    The function is intentionally deterministic. It does not fetch
    external data and does not make execution decisions.
    """

    normalized_symbol = symbol.strip().upper()

    if not normalized_symbol:
        raise ValueError("symbol cannot be empty")

    if company_intelligence.symbol.strip().upper() != normalized_symbol:
        raise ValueError(
            "company intelligence symbol does not match analysis symbol"
        )

    if market_snapshot.symbol.strip().upper() != normalized_symbol:
        raise ValueError(
            "market snapshot symbol does not match analysis symbol"
        )

    if market_snapshot.trading_date != as_of_date:
        raise ValueError(
            "market snapshot date does not match analysis date"
        )

    research_score = calculate_research_score(
        fundamentals=fundamentals,
        financial_trends=financial_trends,
        cash_flow=cash_flow,
        balance_sheet=balance_sheet,
        risk=risk,
        management=management,
        market_behavior=market_behavior,
        evidence_quality=evidence_quality,
    )

    base_input = RankingInput(
        symbol=normalized_symbol,
        research_score=research_score.total,

        fundamentals=fundamentals,
        financial_trends=financial_trends,
        cash_flow=cash_flow,
        balance_sheet=balance_sheet,
        risk=risk,

        momentum=_market_momentum(market_snapshot),
        trend_strength=_trend_strength(market_snapshot),
        liquidity=liquidity,
        volatility=_volatility_score(market_snapshot),
        relative_strength=relative_strength,

        catalyst_strength=catalyst_strength,
        valuation=valuation,
        management=management,
        evidence_quality=evidence_quality,
    )

    intraday = rank_stock(
        base_input,
        "INTRADAY",
    )

    swing = rank_stock(
        base_input,
        "SWING",
    )

    long_term = rank_stock(
        base_input,
        "LONG_TERM",
    )

    return StockAnalysisReport(
        symbol=normalized_symbol,
        as_of_date=as_of_date,
        research_score=research_score,
        company_intelligence=company_intelligence,
        market_snapshot=market_snapshot,
        intraday=intraday,
        swing=swing,
        long_term=long_term,
    )


def _market_momentum(
    snapshot: MarketFeatureSnapshot,
) -> Decimal:
    """
    Convert the descriptive 20-day momentum feature into a
    normalized 0-100 research factor.

    This is deliberately a simple provisional transformation.
    It must eventually be calibrated using historical data.
    """

    value = snapshot.technical.momentum

    if value is None:
        return Decimal("50")

    return _normalize_percent(value)


def _trend_strength(
    snapshot: MarketFeatureSnapshot,
) -> Decimal:
    """
    Estimate trend strength from price position relative to
    available moving averages.

    This is a research feature, not a prediction.
    """

    technical = snapshot.technical

    if (
        technical.sma_5 is None
        or technical.sma_20 is None
    ):
        return Decimal("50")

    close = _latest_close(snapshot)

    score = Decimal("50")

    if close > technical.sma_5:
        score += Decimal("15")
    elif close < technical.sma_5:
        score -= Decimal("15")

    if close > technical.sma_20:
        score += Decimal("20")
    elif close < technical.sma_20:
        score -= Decimal("20")

    if technical.sma_5 > technical.sma_20:
        score += Decimal("10")
    elif technical.sma_5 < technical.sma_20:
        score -= Decimal("10")

    return max(
        Decimal("0"),
        min(Decimal("100"), score),
    )


def _volatility_score(
    snapshot: MarketFeatureSnapshot,
) -> Decimal:
    """
    Convert volatility into a risk-adjusted descriptive score.

    Lower realized volatility receives a higher score.

    This is intentionally provisional and must be validated
    against the eventual strategy universe.
    """

    volatility = snapshot.technical.volatility_20d

    if volatility is None:
        return Decimal("50")

    if volatility <= Decimal("1"):
        return Decimal("90")

    if volatility <= Decimal("2"):
        return Decimal("80")

    if volatility <= Decimal("3"):
        return Decimal("70")

    if volatility <= Decimal("5"):
        return Decimal("55")

    if volatility <= Decimal("8"):
        return Decimal("40")

    return Decimal("25")


def _normalize_percent(
    value: Decimal,
) -> Decimal:
    """
    Convert a percentage-style momentum value into 0-100.

    +20% or greater -> 100
    -20% or lower   -> 0
    0%              -> 50
    """

    lower = Decimal("-20")
    upper = Decimal("20")

    if value <= lower:
        return Decimal("0")

    if value >= upper:
        return Decimal("100")

    return (
        (value - lower)
        / (upper - lower)
    ) * Decimal("100")


def _latest_close(
    snapshot: MarketFeatureSnapshot,
) -> Decimal:
    """
    Return the actual latest observed close.

    The close is stored directly in TechnicalFeatures.
    Never substitute an SMA for the current market price.
    """

    latest_close = snapshot.technical.latest_close

    if latest_close is None:
        raise ValueError(
            "Market snapshot does not contain latest_close"
        )

    return latest_close