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

    `available_components` identifies which dimensions have
    actual research evidence.

    A component can therefore retain a numeric compatibility
    value while still being excluded from the ranking when its
    evidence is unavailable.

    This prevents:

        missing evidence == neutral evidence

    from silently affecting rankings.
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

    # None means every component is considered available.
    #
    # This preserves backwards compatibility with existing callers
    # and tests while allowing new research pipelines to explicitly
    # identify missing evidence.
    available_components: frozenset[str] | None = None


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

    # Components that were not backed by evidence and therefore
    # were excluded from the weighted score.
    missing_components: tuple[str, ...] = ()

    # Percentage of the configured ranking weight supported by
    # available research evidence.
    coverage: Decimal = Decimal("100")

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
        if name in {
            "symbol",
            "available_components",
        }:
            continue

        _validate_score(value, name)

    if data.available_components is not None:
        known_components = set(
            _WEIGHTS["LONG_TERM"].keys()
        )

        unknown = (
            set(data.available_components)
            - known_components
        )

        if unknown:
            raise ValueError(
                "unknown ranking components: "
                + ", ".join(sorted(unknown))
            )


def _confidence(
    components: list[Decimal],
) -> Decimal:
    """
    Measure internal consistency of the available research
    components.

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

    Missing evidence is excluded from the weighted score rather
    than being interpreted as a neutral 50.

    The remaining available weights are normalized so the score
    remains on a 0-100 scale.

    Coverage reports how much of the configured horizon weighting
    was actually supported by evidence.

    The score does NOT predict future returns.
    """

    if horizon not in _WEIGHTS:
        raise ValueError(
            f"Unsupported horizon: {horizon}"
        )

    _validate_input(data)

    raw_weights = _WEIGHTS[horizon]

    weights = _normalise_weights(
        raw_weights
    )

    if data.available_components is None:
        available = set(raw_weights.keys())
    else:
        available = set(
            data.available_components
        )

    # A zero-weight component contributes nothing and does not
    # affect coverage.
    weighted_components = {
        name: value
        for name, value in raw_weights.items()
        if value > Decimal("0")
    }

    available_weight = sum(
        weight
        for name, weight in weighted_components.items()
        if name in available
    )

    configured_weight = sum(
        weighted_components.values(),
        Decimal("0"),
    )

    if available_weight <= Decimal("0"):
        raise ValueError(
            "ranking requires at least one available "
            "weighted component"
        )

    # Coverage describes how much of the original configured
    # ranking was backed by evidence.
    coverage = (
        available_weight
        / configured_weight
    ) * Decimal("100")

    # Renormalize only over available evidence.
    available_normalized_weights = {
        name: (
            weight
            / available_weight
        )
        for name, weight in weighted_components.items()
        if name in available
    }

    available_components: dict[str, Decimal] = {
        name: Decimal(
            getattr(data, name)
        )
        for name in raw_weights
    }

    score = sum(
        available_components[name]
        * weight
        for name, weight
        in available_normalized_weights.items()
    )

    score = max(
        Decimal("0"),
        min(Decimal("100"), score),
    )

    confidence_components = [
        available_components[name]
        for name in available_normalized_weights
    ]

    confidence = _confidence(
        confidence_components
    )

    missing_components = tuple(
        name
        for name, weight in weighted_components.items()
        if name not in available
    )

    return StockRanking(
        symbol=data.symbol.strip().upper(),
        horizon=horizon,
        score=score,
        rank_signal=_signal(score),
        confidence=confidence,
        components=available_components,
        missing_components=missing_components,
        coverage=coverage,
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
