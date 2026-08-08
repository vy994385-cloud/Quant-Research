from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


Horizon = Literal["INTRADAY", "SWING", "LONG_TERM"]


@dataclass(frozen=True)
class RankingInput:
    """
    Normalized research inputs for one security.

    Every component is expected to be in the range 0-100.
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


@dataclass(frozen=True)
class StockRanking:
    symbol: str
    horizon: Horizon
    score: Decimal
    rank_signal: str
    confidence: Decimal
    components: dict[str, Decimal]


# Strategy-specific weights.
#
# These are starting research weights, not claimed optimal weights.
# They must eventually be tested with historical walk-forward data.
_WEIGHTS: dict[Horizon, dict[str, Decimal]] = {
    "INTRADAY": {
        "momentum": Decimal("0.20"),
        "trend_strength": Decimal("0.18"),
        "liquidity": Decimal("0.18"),
        "volatility": Decimal("0.12"),
        "relative_strength": Decimal("0.12"),
        "catalyst_strength": Decimal("0.10"),
        "research_score": Decimal("0.10"),
    },
    "SWING": {
        "momentum": Decimal("0.16"),
        "trend_strength": Decimal("0.16"),
        "relative_strength": Decimal("0.14"),
        "catalyst_strength": Decimal("0.14"),
        "research_score": Decimal("0.16"),
        "financial_trends": Decimal("0.08"),
        "cash_flow": Decimal("0.06"),
        "risk": Decimal("0.10"),
    },
    "LONG_TERM": {
        "fundamentals": Decimal("0.18"),
        "financial_trends": Decimal("0.16"),
        "cash_flow": Decimal("0.14"),
        "balance_sheet": Decimal("0.12"),
        "management": Decimal("0.10"),
        "valuation": Decimal("0.10"),
        "risk": Decimal("0.08"),
        "research_score": Decimal("0.12"),
    },
}


def _validate_score(value: Decimal, name: str) -> Decimal:
    value = Decimal(value)

    if value < Decimal("0") or value > Decimal("100"):
        raise ValueError(
            f"{name} must be between 0 and 100"
        )

    return value


def _validate_input(data: RankingInput) -> None:
    for name, value in vars(data).items():
        if name == "symbol":
            continue

        _validate_score(value, name)


def _confidence(
    components: list[Decimal],
) -> Decimal:
    if not components:
        return Decimal("0")

    mean = sum(components) / Decimal(len(components))

    dispersion = (
        sum(abs(value - mean) for value in components)
        / Decimal(len(components))
    )

    confidence = Decimal("100") - dispersion

    return max(
        Decimal("0"),
        min(Decimal("100"), confidence),
    )


def _signal(score: Decimal) -> str:
    if score >= Decimal("75"):
        return "HIGH_PRIORITY"

    if score >= Decimal("60"):
        return "WATCH"

    if score >= Decimal("45"):
        return "NEUTRAL"

    return "LOW_PRIORITY"


def rank_stock(
    data: RankingInput,
    horizon: Horizon,
) -> StockRanking:
    """
    Produce a strategy-specific research ranking.

    This function deliberately contains no future-return prediction.
    It combines normalized research factors into a transparent score.

    The weights are provisional and must be validated through
    out-of-sample historical testing before being treated as production
    parameters.
    """

    if horizon not in _WEIGHTS:
        raise ValueError(
            f"Unsupported horizon: {horizon}"
        )

    _validate_input(data)

    weights = _WEIGHTS[horizon]

    available_components: dict[str, Decimal] = {}

    for name in weights:
        available_components[name] = getattr(data, name)

    score = sum(
        available_components[name] * weight
        for name, weight in weights.items()
    )

    score = max(
        Decimal("0"),
        min(Decimal("100"), score),
    )

    confidence = _confidence(
        list(available_components.values())
    )

    return StockRanking(
        symbol=data.symbol,
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

    Ties are resolved deterministically using the symbol so repeated
    runs produce the same ordering.
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
