from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class RankingOutcome:
    """
    Point-in-time outcome of a historical ranking observation.

    The outcome date must be strictly after the ranking date.
    Forward return is calculated from the ranking price to the
    future evaluation price.
    """

    symbol: str
    ranking_date: date
    outcome_date: date
    horizon: str
    entry_price: Decimal
    outcome_price: Decimal
    forward_return: Decimal
    benchmark_return: Decimal | None = None
    excess_return: Decimal | None = None

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        horizon = self.horizon.strip().upper()

        if not symbol:
            raise ValueError("symbol cannot be empty")

        if not horizon:
            raise ValueError("horizon cannot be empty")

        if self.outcome_date <= self.ranking_date:
            raise ValueError(
                "outcome_date must be after ranking_date"
            )

        if self.entry_price <= Decimal("0"):
            raise ValueError(
                "entry_price must be greater than zero"
            )

        if self.outcome_price <= Decimal("0"):
            raise ValueError(
                "outcome_price must be greater than zero"
            )

        expected_return = (
            self.outcome_price / self.entry_price
        ) - Decimal("1")

        if self.forward_return != expected_return:
            raise ValueError(
                "forward_return does not match entry and outcome prices"
            )

        if (
            self.benchmark_return is not None
            and self.excess_return != (
                self.forward_return - self.benchmark_return
            )
        ):
            raise ValueError(
                "excess_return does not match forward and benchmark returns"
            )

        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "horizon", horizon)

    @property
    def is_positive(self) -> bool:
        return self.forward_return > Decimal("0")

    @property
    def is_benchmark_outperforming(self) -> bool:
        if self.excess_return is None:
            return False

        return self.excess_return > Decimal("0")


def build_ranking_outcome(
    *,
    symbol: str,
    ranking_date: date,
    outcome_date: date,
    horizon: str,
    entry_price: Decimal,
    outcome_price: Decimal,
    benchmark_return: Decimal | None = None,
) -> RankingOutcome:
    """
    Build a leakage-safe historical ranking outcome.

    No ranking information is modified here. This function only
    calculates what happened after the ranking observation.
    """

    if entry_price <= Decimal("0"):
        raise ValueError(
            "entry_price must be greater than zero"
        )

    if outcome_price <= Decimal("0"):
        raise ValueError(
            "outcome_price must be greater than zero"
        )

    if outcome_date <= ranking_date:
        raise ValueError(
            "outcome_date must be after ranking_date"
        )

    forward_return = (
        outcome_price / entry_price
    ) - Decimal("1")

    excess_return = None

    if benchmark_return is not None:
        excess_return = (
            forward_return - benchmark_return
        )

    return RankingOutcome(
        symbol=symbol,
        ranking_date=ranking_date,
        outcome_date=outcome_date,
        horizon=horizon,
        entry_price=entry_price,
        outcome_price=outcome_price,
        forward_return=forward_return,
        benchmark_return=benchmark_return,
        excess_return=excess_return,
    )


__all__ = [
    "RankingOutcome",
    "build_ranking_outcome",
]