"""
Deep technical research orchestrator.

Combines all technical indicator computation with observation
building into a single typed result. Primary entry point for
Phase 2 technical research backend.

All analysis is deterministic and PIT-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Sequence

from src.analysis.technical_indicators import (
    TechnicalIndicatorResult,
    compute_technical_indicators,
)
from src.analysis.technical_observations import (
    TechnicalObservationSet,
    build_technical_observations,
)
from src.data.models import PriceBar


@dataclass(frozen=True)
class DeepTechnicalResult:
    """
    Complete deep technical research result for one company.

    Combines all technical analysis dimensions into a single
    serializable dataclass.
    """

    symbol: str
    as_of: str
    trading_date: str

    # Core indicator result
    indicators: TechnicalIndicatorResult | None = None

    # Unified observations
    observation_set: TechnicalObservationSet | None = None

    # Coverage
    bars_used: int = 0
    available_indicators: tuple[str, ...] = ()
    missing_indicators: tuple[str, ...] = ()

    # Notes
    notes: tuple[str, ...] = ()

    @property
    def has_observations(self) -> bool:
        return (
            self.observation_set is not None
            and self.observation_set.total_count > 0
        )

    @property
    def positive_count(self) -> int:
        if self.observation_set is None:
            return 0
        return self.observation_set.positive_count

    @property
    def negative_count(self) -> int:
        if self.observation_set is None:
            return 0
        return self.observation_set.negative_count

    @property
    def neutral_count(self) -> int:
        if self.observation_set is None:
            return 0
        return self.observation_set.neutral_count


def analyze_deep_technicals(
    bars: Sequence[PriceBar],
    benchmark_bars: Sequence[PriceBar] | None,
    symbol: str,
    as_of: datetime,
) -> DeepTechnicalResult:
    """
    Run the full deep technical analysis pipeline.

    Deterministic and returns empty result when data is insufficient.

    PIT enforcement: only bars with trading_date <= as_of are used.
    """
    notes: list[str] = []

    # PIT filter: reject bars with trading_date > as_of
    pit_bars = [
        b for b in bars
        if (
            b.trading_date <= as_of.date()
            if as_of.tzinfo is None
            else datetime.combine(
                b.trading_date, datetime.min.time()
            ).replace(tzinfo=as_of.tzinfo) <= as_of
        )
    ]
    pit_benchmark = None
    if benchmark_bars is not None:
        pit_benchmark = [
            b for b in benchmark_bars
            if (
                b.trading_date <= as_of.date()
                if as_of.tzinfo is None
                else datetime.combine(
                    b.trading_date, datetime.min.time()
                ).replace(tzinfo=as_of.tzinfo) <= as_of
            )
        ]

    rejected = len(bars) - len(pit_bars)
    if rejected > 0:
        notes.append(
            f"PIT filter: {rejected} bar(s) rejected "
            f"(trading_date > as_of)."
        )

    if not pit_bars:
        notes.append("No price data available.")
        return DeepTechnicalResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            trading_date="",
            notes=tuple(notes),
        )

    # Compute indicators
    indicators = compute_technical_indicators(
        pit_bars, pit_benchmark
    )

    # Build observations
    observation_set = build_technical_observations(indicators, as_of)

    return DeepTechnicalResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        trading_date=indicators.trading_date,
        indicators=indicators,
        observation_set=observation_set,
        bars_used=indicators.bars_used,
        available_indicators=observation_set.available_indicators,
        missing_indicators=observation_set.missing_indicators,
        notes=tuple(notes),
    )
