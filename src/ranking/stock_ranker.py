from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


Horizon = Literal[
    "INTRADAY",
    "SWING",
    "LONG_TERM",
]


@dataclass(frozen=True)
class RankingInput:
    """
    Unified company-ranking research input.

    All values are normalized to 0-100.

    Existing research components remain supported for backwards
    compatibility. Future-oriented intelligence is now explicitly
    represented rather than being hidden inside a generic score.

    A missing future-intelligence component uses a neutral baseline
    rather than assuming either strength or weakness.
    """

    symbol: str

    research_score: Decimal
    fundamentals: Decimal
    financial_trends: Decimal
    cash_flow: Decimal
    balance_sheet: Decimal
    risk: Decimal
    momentum: Decimal
    trend_strength: Decimal
    liquidity: Decimal
    volatility: Decimal
    relative_strength: Decimal
    catalyst_strength: Decimal
    valuation: Decimal
    management: Decimal
    evidence_quality: Decimal

    future_readiness: Decimal = Decimal("50")
    ai_participation: Decimal = Decimal("50")
    innovation_execution: Decimal = Decimal("50")
    technology_diversification: Decimal = Decimal("50")
    sector_fit: Decimal = Decimal("50")


@dataclass(frozen=True)
class StockRanking:
    """
    Unified research ranking.

    This is a research prioritization score, not a prediction of
    future returns and not a trading instruction.
    """

    symbol: str
    horizon: Horizon
    score: Decimal
    rank_signal: str
    confidence: Decimal
    components: dict[str, Decimal]

    @property
    def priority(self) -> str:
        return self.rank_signal

    @property
    def is_high_priority(self) -> bool:
        return self.rank_signal == "HIGH_PRIORITY"


# ---------------------------------------------------------------------
# Horizon-specific weights
# ---------------------------------------------------------------------

_WEIGHTS: dict[Horizon, dict[str, Decimal]] = {
    "INTRADAY": {
        "research_score": Decimal("0.05"),
        "fundamentals": Decimal("0.03"),
        "financial_trends": Decimal("0.02"),
        "cash_flow": Decimal("0.01"),
        "balance_sheet": Decimal("0.01"),
        "risk": Decimal("0.06"),
        "momentum": Decimal("0.18"),
        "trend_strength": Decimal("0.16"),
        "liquidity": Decimal("0.12"),
        "volatility": Decimal("0.10"),
        "relative_strength": Decimal("0.14"),
        "catalyst_strength": Decimal("0.07"),
        "valuation": Decimal("0.01"),
        "management": Decimal("0.01"),
        "evidence_quality": Decimal("0.03"),
        "future_readiness": Decimal("0.00"),
        "ai_participation": Decimal("0.00"),
        "innovation_execution": Decimal("0.00"),
        "technology_diversification": Decimal("0.00"),
        "sector_fit": Decimal("0.00"),
    },
    "SWING": {
        "research_score": Decimal("0.08"),
        "fundamentals": Decimal("0.05"),
        "financial_trends": Decimal("0.06"),
        "cash_flow": Decimal("0.04"),
        "balance_sheet": Decimal("0.03"),
        "risk": Decimal("0.08"),
        "momentum": Decimal("0.10"),
        "trend_strength": Decimal("0.10"),
        "liquidity": Decimal("0.08"),
        "volatility": Decimal("0.05"),
        "relative_strength": Decimal("0.10"),
        "catalyst_strength": Decimal("0.07"),
        "valuation": Decimal("0.04"),
        "management": Decimal("0.03"),
        "evidence_quality": Decimal("0.04"),
        "future_readiness": Decimal("0.01"),
        "ai_participation": Decimal("0.00"),
        "innovation_execution": Decimal("0.01"),
        "technology_diversification": Decimal("0.00"),
        "sector_fit": Decimal("0.03"),
    },
    "LONG_TERM": {
        "research_score": Decimal("0.08"),
        "fundamentals": Decimal("0.12"),
        "financial_trends": Decimal("0.10"),
        "cash_flow": Decimal("0.09"),
        "balance_sheet": Decimal("0.07"),
        "risk": Decimal("0.08"),
        "momentum": Decimal("0.02"),
        "trend_strength": Decimal("0.02"),
        "liquidity": Decimal("0.02"),
        "volatility": Decimal("0.02"),
        "relative_strength": Decimal("0.02"),
        "catalyst_strength": Decimal("0.03"),
        "valuation": Decimal("0.06"),
        "management": Decimal("0.06"),
        "evidence_quality": Decimal("0.05"),
        "future_readiness": Decimal("0.06"),
        "ai_participation": Decimal("0.03"),
        "innovation_execution": Decimal("0.05"),
        "technology_diversification": Decimal("0.03"),
        "sector_fit": Decimal("0.08"),
    },
}


def _validate_score(
    value: Decimal,
    name: str,
) -> Decimal:
    value = Decimal(value)

    if value < Decimal("0") or value > Decimal("100"):
        raise ValueError(
            f"{name} must be between 0 and 100"
        )

    return value


def _validate_input(
    data: RankingInput,
) -> None:
    if not data.symbol.strip():
        raise ValueError("symbol cannot be empty")

    for name, value in vars(data).items():
        if name == "symbol":
            continue

        _validate_score(value, name)


def _confidence(
    components: list[Decimal],
) -> Decimal:
    """
    Measure internal consistency of the research components.

    This is NOT probability of a profitable trade.
    """

    if not components:
        return Decimal("0")

    mean = sum(components) / Decimal(len(components))

    dispersion = (
        sum(
            abs(value - mean)
            for value in components
        )
        / Decimal(len(components))
    )

    confidence = Decimal("100") - dispersion

    return max(
        Decimal("0"),
        min(Decimal("100"), confidence),
    )


def _signal(
    score: Decimal,
) -> str:
    if score >= Decimal("75"):
        return "HIGH_PRIORITY"

    if score >= Decimal("60"):
        return "WATCH"

    if score >= Decimal("45"):
        return "NEUTRAL"

    return "LOW_PRIORITY"


def _normalise_weights(
    weights: dict[str, Decimal],
) -> dict[str, Decimal]:
    total = sum(
        weights.values(),
        Decimal("0"),
    )

    if total <= Decimal("0"):
        raise ValueError(
            "ranking weights must have a positive total"
        )

    return {
        name: weight / total
        for name, weight in weights.items()
    }


def rank_stock(
    data: RankingInput,
    horizon: Horizon,
) -> StockRanking:
    """
    Produce a transparent, horizon-specific research ranking.

    The score combines financial quality, market behavior,
    evidence quality and future-oriented business intelligence.

    It does NOT predict future returns.

    The weights are research parameters and must be validated
    through out-of-sample testing before production use.
    """

    if horizon not in _WEIGHTS:
        raise ValueError(
            f"Unsupported horizon: {horizon}"
        )

    _validate_input(data)

    weights = _normalise_weights(
        _WEIGHTS[horizon]
    )

    available_components: dict[str, Decimal] = {}

    for name in weights:
        available_components[name] = Decimal(
            getattr(data, name)
        )

    score = sum(
        available_components[name] * weight
        for name, weight in weights.items()
    )

    score = max(
        Decimal("0"),
        min(Decimal("100"), score),
    )

    # Use only meaningful weighted components for confidence.
    confidence_components = [
        available_components[name]
        for name, weight in weights.items()
        if weight > Decimal("0")
    ]

    confidence = _confidence(
        confidence_components
    )

    return StockRanking(
        symbol=data.symbol.strip().upper(),
        horizon=horizon,
        score=score,
        rank_signal=_signal(score),
        confidence=confidence,
        components=available_components,
    )


def rank_stocks(
    stocks: list[RankingInput],
    horizon: Horizon,
) -> list[StockRanking]:
    """
    Rank a universe of securities from highest to lowest score.

    Ties are resolved deterministically by symbol.
    """

    rankings = [
        rank_stock(stock, horizon)
        for stock in stocks
    ]

    rankings.sort(
        key=lambda item: (
            -item.score,
            item.symbol,
        )
    )

    return rankings
