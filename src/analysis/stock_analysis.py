from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
)
from src.analysis.research_coverage import (
    ResearchComponentStatus,
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


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------

MIN_SCORE = Decimal("0")
MAX_SCORE = Decimal("100")

# Used only at the ranking boundary when a dimension has no evidence.
#
# IMPORTANT:
# This is NOT presented as the company's actual score.
# Missing dimensions are tracked separately through
# future_intelligence_available() and research coverage.
#
# This fallback exists only because the current RankingInput model
# requires numeric values.
RANKING_MISSING_VALUE = Decimal("50")

SECTOR_FIT_MISSING_VALUE = Decimal("50")


# ---------------------------------------------------------------------
# Unified stock-analysis result
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class StockAnalysisReport:
    """
    Unified stock-research result.

    This is the analytical layer used by the research platform.

    It does NOT:
    - execute trades
    - place orders
    - guarantee returns
    - predict guaranteed market direction
    - represent investment advice

    The report combines:

    1. Fundamental research
    2. Financial trends
    3. Cash-flow quality
    4. Balance-sheet quality
    5. Risk
    6. Management
    7. Market behavior
    8. Evidence quality
    9. Future-oriented company intelligence
    10. Horizon-specific rankings
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
            and (
                self.company_intelligence.symbol
                .strip()
                .upper()
                == self.symbol.strip().upper()
            )
            and (
                self.market_snapshot.symbol
                .strip()
                .upper()
                == self.symbol.strip().upper()
            )
        )

    @property
    def future_intelligence_available(self) -> bool:
        """
        Whether at least one future-oriented research dimension
        has real evidence.

        This is intentionally separate from the ranking score.

        A company with no AI/future evidence must NOT be represented
        as though it actually scored 50.
        """

        return any(
            value is not None
            for value in (
                self.company_intelligence.future_readiness,
                self.company_intelligence.ai_participation,
                self.company_intelligence.innovation_execution,
                self.company_intelligence.technology_diversification,
            )
        )

    @property
    def future_intelligence_completeness(self) -> Decimal:
        """
        Percentage of future-oriented dimensions for which
        actual research evidence is available.

        Four dimensions are currently tracked:

        - future readiness
        - AI participation
        - innovation execution
        - technology diversification
        """

        values = (
            self.company_intelligence.future_readiness,
            self.company_intelligence.ai_participation,
            self.company_intelligence.innovation_execution,
            self.company_intelligence.technology_diversification,
        )

        available = sum(
            value is not None
            for value in values
        )

        return (
            Decimal(available)
            / Decimal("4")
        ) * Decimal("100")


# ---------------------------------------------------------------------
# Future intelligence
# ---------------------------------------------------------------------

def _future_intelligence_scores(
    company_intelligence: CompanyResearchSnapshot,
) -> dict[str, Decimal | None]:
    """
    Extract future-oriented intelligence.

    Missing evidence remains None.

    NEVER fabricate a company's future-readiness, AI participation,
    innovation, or technology diversification score.

    This is important for the platform's core philosophy:

        "absence of evidence" != "average company"

    The ranking layer converts None to a temporary numerical
    fallback only because the current ranking engine expects
    numeric inputs.
    """

    return {
        "future_readiness": (
            company_intelligence.future_readiness
        ),
        "ai_participation": (
            company_intelligence.ai_participation
        ),
        "innovation_execution": (
            company_intelligence.innovation_execution
        ),
        "technology_diversification": (
            company_intelligence.technology_diversification
        ),
    }


def _ranking_value(
    value: Decimal | None,
    *,
    fallback: Decimal = RANKING_MISSING_VALUE,
) -> Decimal:
    """
    Convert optional research evidence into a numeric value for
    the current ranking engine.

    IMPORTANT:

    This does NOT claim that the underlying company actually
    scored the fallback value.

    The true evidence state remains separate through
    available_components.
    """

    if value is None:
        return fallback

    return max(
        MIN_SCORE,
        min(MAX_SCORE, Decimal(value)),
    )


def _normalize_component_status(
    value: ResearchComponentStatus | str,
) -> ResearchComponentStatus:
    """
    Normalize financial evidence status.

    Supports both enum values and serialized strings.
    """

    if isinstance(value, ResearchComponentStatus):
        return value

    return ResearchComponentStatus(
        str(value).strip().upper()
    )


# ---------------------------------------------------------------------
# Main analysis builder
# ---------------------------------------------------------------------

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
    financial_component_statuses: dict[
        str,
        ResearchComponentStatus | str,
    ] | None = None,
) -> StockAnalysisReport:
    """
    Build the complete research view for one stock.

    All supplied component scores must be between 0 and 100.

    External data fetching does NOT happen here.

    This function is deliberately deterministic.

    Architecture:

        providers
            ↓
        normalized research context
            ↓
        analysis
            ↓
        scoring
            ↓
        horizon ranking
            ↓
        user-facing research report

    The analysis layer must never fabricate missing evidence.

    Financial evidence availability is passed separately from
    numeric financial scores so missing data cannot silently become
    positive, negative, or neutral evidence.
    """

    normalized_symbol = symbol.strip().upper()

    if not normalized_symbol:
        raise ValueError(
            "symbol cannot be empty"
        )

    intelligence_symbol = (
        company_intelligence.symbol
        .strip()
        .upper()
    )

    market_symbol = (
        market_snapshot.symbol
        .strip()
        .upper()
    )

    if intelligence_symbol != normalized_symbol:
        raise ValueError(
            "company intelligence symbol does not match analysis symbol"
        )

    if market_symbol != normalized_symbol:
        raise ValueError(
            "market snapshot symbol does not match analysis symbol"
        )

    if market_snapshot.trading_date != as_of_date:
        raise ValueError(
            "market snapshot date does not match analysis date"
        )

    # -----------------------------------------------------------------
    # Financial evidence coverage
    # -----------------------------------------------------------------

    normalized_financial_statuses = {
        name: _normalize_component_status(status)
        for name, status in (
            financial_component_statuses or {}
        ).items()
    }

    financial_component_names = {
        "fundamentals",
        "financial_trends",
        "cash_flow",
        "balance_sheet",
    }

    # Preserve backwards compatibility for existing callers that do
    # not yet provide financial coverage metadata.
    #
    # Once the market engine provides statuses, those statuses become
    # authoritative.
    component_availability: dict[
        str,
        ResearchComponentStatus,
    ] = {
        name: normalized_financial_statuses.get(
            name,
            ResearchComponentStatus.AVAILABLE,
        )
        for name in financial_component_names
    }

    # -----------------------------------------------------------------
    # Core research score
    # -----------------------------------------------------------------

    research_score = calculate_research_score(
        fundamentals=fundamentals,
        financial_trends=financial_trends,
        cash_flow=cash_flow,
        balance_sheet=balance_sheet,
        risk=risk,
        management=management,
        market_behavior=market_behavior,
        evidence_quality=evidence_quality,
        component_availability=component_availability,
    )

    # -----------------------------------------------------------------
    # Future intelligence
    # -----------------------------------------------------------------

    future_scores = _future_intelligence_scores(
        company_intelligence
    )

    # -----------------------------------------------------------------
    # Ranking input
    #
    # The ranking engine requires numeric compatibility values, but
    # it is evidence-aware through `available_components`.
    #
    # Missing future-intelligence dimensions therefore remain
    # excluded from the ranking instead of being treated as neutral.
    # -----------------------------------------------------------------

    future_available_components = {
        name
        for name, value in future_scores.items()
        if value is not None
    }

    available_components = frozenset(
        {
            # Core research dimensions.
            "research_score",

            # Financial components are included only when their
            # evidence is actually usable.
            *{
                name
                for name, status in component_availability.items()
                if status
                in {
                    ResearchComponentStatus.AVAILABLE,
                    ResearchComponentStatus.PARTIAL,
                }
            },

            "risk",
            "momentum",
            "trend_strength",
            "liquidity",
            "volatility",
            "relative_strength",
            "catalyst_strength",
            "valuation",
            "management",
            "evidence_quality",

            # Future-oriented dimensions are included only when
            # actual research evidence exists.
            *future_available_components,
        }
    )

    base_input = RankingInput(
        symbol=normalized_symbol,

        research_score=research_score.total,

        fundamentals=fundamentals,
        financial_trends=financial_trends,
        cash_flow=cash_flow,
        balance_sheet=balance_sheet,
        risk=risk,

        momentum=_market_momentum(
            market_snapshot
        ),

        trend_strength=_trend_strength(
            market_snapshot
        ),

        liquidity=liquidity,

        volatility=_volatility_score(
            market_snapshot
        ),

        relative_strength=relative_strength,

        catalyst_strength=catalyst_strength,
        valuation=valuation,
        management=management,
        evidence_quality=evidence_quality,

        # Numeric compatibility values remain required by the
        # RankingInput model. The ranker excludes these values
        # whenever their component is absent from
        # `available_components`.
        future_readiness=_ranking_value(
            future_scores["future_readiness"]
        ),

        ai_participation=_ranking_value(
            future_scores["ai_participation"]
        ),

        innovation_execution=_ranking_value(
            future_scores["innovation_execution"]
        ),

        technology_diversification=_ranking_value(
            future_scores["technology_diversification"]
        ),

        # Sector-specific intelligence is not wired yet.
        # Therefore it is deliberately NOT included in
        # available_components.
        sector_fit=SECTOR_FIT_MISSING_VALUE,

        available_components=available_components,
    )

    # -----------------------------------------------------------------
    # Horizon-specific rankings
    # -----------------------------------------------------------------

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

    # -----------------------------------------------------------------
    # Final immutable research report
    # -----------------------------------------------------------------

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


# ---------------------------------------------------------------------
# Market feature transformations
# ---------------------------------------------------------------------

def _market_momentum(
    snapshot: MarketFeatureSnapshot,
) -> Decimal:
    """
    Convert descriptive 20-day momentum into a normalized
    0-100 research factor.

    +20% or greater -> 100
    0%              -> 50
    -20% or lower   -> 0

    This is descriptive normalization, not a forecast.
    """

    value = snapshot.technical.momentum

    if value is None:
        return RANKING_MISSING_VALUE

    return _normalize_percent(value)


def _trend_strength(
    snapshot: MarketFeatureSnapshot,
) -> Decimal:
    """
    Estimate current trend strength from:

    - latest close vs SMA-5
    - latest close vs SMA-20
    - SMA-5 vs SMA-20

    This is a descriptive market feature.

    It is not a prediction.
    """

    technical = snapshot.technical

    if (
        technical.sma_5 is None
        or technical.sma_20 is None
    ):
        return RANKING_MISSING_VALUE

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
        MIN_SCORE,
        min(MAX_SCORE, score),
    )


def _volatility_score(
    snapshot: MarketFeatureSnapshot,
) -> Decimal:
    """
    Convert realized 20-day volatility into a descriptive
    risk-adjusted score.

    Lower realized volatility receives a higher score.

    This is provisional and must eventually be calibrated
    against the actual research universe and historical outcomes.
    """

    volatility = (
        snapshot.technical.volatility_20d
    )

    if volatility is None:
        return RANKING_MISSING_VALUE

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


# ---------------------------------------------------------------------
# Numeric normalization
# ---------------------------------------------------------------------

def _normalize_percent(
    value: Decimal,
) -> Decimal:
    """
    Convert a percentage-style momentum value into 0-100.

    +20% or greater -> 100
    -20% or lower   -> 0
    0%              -> 50
    """

    value = Decimal(value)

    lower = Decimal("-20")
    upper = Decimal("20")

    if value <= lower:
        return MIN_SCORE

    if value >= upper:
        return MAX_SCORE

    normalized = (
        (value - lower)
        / (upper - lower)
    ) * MAX_SCORE

    return max(
        MIN_SCORE,
        min(MAX_SCORE, normalized),
    )


# ---------------------------------------------------------------------
# Latest market observation
# ---------------------------------------------------------------------

def _latest_close(
    snapshot: MarketFeatureSnapshot,
) -> Decimal:
    """
    Return the actual latest observed close.

    IMPORTANT:

    Never substitute SMA-5/SMA-20 for the latest market price.
    """

    latest_close = (
        snapshot.technical.latest_close
    )

    if latest_close is None:
        raise ValueError(
            "Market snapshot does not contain latest_close"
        )

    return Decimal(latest_close)