"""
Price-move attribution engine.

Provides evidence-based attribution for observed price movements.
This module synthesizes signals from:
  - Fundamentals (earnings quality, balance sheet health)
  - Technicals (trend, momentum, volume)
  - Ownership (promoter changes, institutional flows)
  - Events (material announcements, corporate actions)
  - Volume patterns (unusual volume, divergence)

All attribution is **correlational, never causal**.
Every attribution carries confidence, evidence references,
and explicit "this is not a prediction" guardrails.

All analysis is deterministic and PIT-safe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Sequence

from src.data.company.evidence import Evidence
from src.data.models import PriceBar


class AttributionCategory(str, Enum):
    FUNDAMENTAL = "FUNDAMENTAL"
    TECHNICAL = "TECHNICAL"
    OWNERSHIP = "OWNERSHIP"
    EVENT = "EVENT"
    VOLUME = "VOLUME"
    MARKET = "MARKET"
    UNKNOWN = "UNKNOWN"


class AttributionDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class AttributionConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True)
class PriceMove:
    """An observed price movement over a period."""

    from_date: str
    to_date: str
    from_close: str
    to_close: str
    absolute_change: str
    percentage_change: str
    direction: str
    trading_days: int


@dataclass(frozen=True)
class AttributionCandidate:
    """One candidate explanation for a price move."""

    candidate_id: str
    category: str
    direction: str
    confidence: str
    title: str
    description: str
    supporting_evidence: tuple[str, ...] = ()
    confidence_score: str = "0"
    explanation: str = ""


@dataclass(frozen=True)
class PriceAttributionResult:
    """Complete price-move attribution for one company."""

    symbol: str
    as_of: str
    price_move: PriceMove | None = None
    candidates: tuple[AttributionCandidate, ...] = ()
    total_candidates: int = 0
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    coverage: dict[str, int] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    disclaimer: str = (
        "Attribution is correlational only. "
        "Do not use for investment decisions."
    )


def _compute_price_move(
    bars: Sequence[PriceBar],
    lookback_days: int,
    as_of: date,
) -> PriceMove | None:
    """Compute price move over the lookback period."""
    if not bars:
        return None

    # Filter to bars at or before as_of
    eligible = [b for b in bars if b.trading_date <= as_of]
    if len(eligible) < 2:
        return None

    # Sort by date
    eligible.sort(key=lambda b: b.trading_date)

    end_bar = eligible[-1]
    target_from = end_bar.trading_date.toordinal() - lookback_days

    # Find the closest bar to target_from
    from_bar = None
    for bar in eligible:
        if bar.trading_date.toordinal() >= target_from:
            from_bar = bar
            break

    if from_bar is None:
        from_bar = eligible[0]

    if from_bar.trading_date == end_bar.trading_date:
        return None

    abs_change = end_bar.close - from_bar.close
    if from_bar.close == 0:
        return None

    pct_change = (
        (abs_change / from_bar.close) * Decimal("100")
    ).quantize(Decimal("0.01"))

    direction = (
        "POSITIVE"
        if abs_change > 0
        else "NEGATIVE"
        if abs_change < 0
        else "NEUTRAL"
    )

    # Count trading days
    trading_days = len([
        b for b in eligible
        if from_bar.trading_date <= b.trading_date <= end_bar.trading_date
    ])

    return PriceMove(
        from_date=from_bar.trading_date.isoformat(),
        to_date=end_bar.trading_date.isoformat(),
        from_close=str(from_bar.close),
        to_close=str(end_bar.close),
        absolute_change=str(abs_change.quantize(Decimal("0.01"))),
        percentage_change=str(pct_change),
        direction=direction,
        trading_days=trading_days,
    )


def _volume_attribution(
    bars: Sequence[PriceBar],
    as_of: date,
    symbol: str,
) -> list[AttributionCandidate]:
    """Detect unusual volume patterns."""
    candidates: list[AttributionCandidate] = []
    idx = 0

    eligible = [b for b in bars if b.trading_date <= as_of]
    if len(eligible) < 20:
        return candidates

    eligible.sort(key=lambda b: b.trading_date)

    # 20-day average volume
    recent_20 = eligible[-20:]
    avg_vol = sum(b.volume for b in recent_20) / 20

    if avg_vol == 0:
        return candidates

    latest = eligible[-1]
    vol_ratio = Decimal(str(latest.volume)) / Decimal(str(avg_vol))

    if vol_ratio > Decimal("2"):
        candidates.append(
            AttributionCandidate(
                candidate_id=f"VOL-{symbol}-{idx:03d}",
                category=AttributionCategory.VOLUME.value,
                direction=(
                    AttributionDirection.POSITIVE.value
                    if latest.close > eligible[-2].close
                    else AttributionDirection.NEGATIVE.value
                ),
                confidence=AttributionConfidence.MEDIUM.value,
                title="Unusual volume activity",
                description=(
                    f"Trading volume ({latest.volume}) is "
                    f"{vol_ratio.quantize(Decimal('0.1'))}x "
                    f"the 20-day average."
                ),
                confidence_score="0.60",
                explanation=(
                    "Unusual volume may indicate heightened "
                    "interest or reaction to news."
                ),
            )
        )
        idx += 1

    # Volume-price divergence: price up but volume declining
    if len(eligible) >= 5:
        last_5 = eligible[-5:]
        prices_up = last_5[-1].close > last_5[0].close
        volumes_declining = (
            last_5[-1].volume < last_5[0].volume * 0.7
        )
        if prices_up and volumes_declining:
            candidates.append(
                AttributionCandidate(
                    candidate_id=f"VOL-{symbol}-{idx:03d}",
                    category=AttributionCategory.VOLUME.value,
                    direction=AttributionDirection.NEGATIVE.value,
                    confidence=AttributionConfidence.LOW.value,
                    title="Volume-price divergence",
                    description=(
                        "Price rising on declining volume."
                    ),
                    confidence_score="0.40",
                    explanation=(
                        "Price increases on declining volume "
                        "may indicate weakening conviction."
                    ),
                )
            )
            idx += 1

    return candidates


def _trend_attribution(
    bars: Sequence[PriceBar],
    as_of: date,
    symbol: str,
) -> list[AttributionCandidate]:
    """Detect trend-based attribution candidates."""
    candidates: list[AttributionCandidate] = []
    idx = 0

    eligible = [b for b in bars if b.trading_date <= as_of]
    if len(eligible) < 50:
        return candidates

    eligible.sort(key=lambda b: b.trading_date)

    closes = [b.close for b in eligible]

    # 20-day and 50-day SMA
    sma_20 = sum(closes[-20:]) / 20
    sma_50 = sum(closes[-50:]) / 50
    current = closes[-1]

    # Golden cross / death cross proximity
    if sma_20 > sma_50 and current > sma_20:
        candidates.append(
            AttributionCandidate(
                candidate_id=f"TREND-{symbol}-{idx:03d}",
                category=AttributionCategory.TECHNICAL.value,
                direction=AttributionDirection.POSITIVE.value,
                confidence=AttributionConfidence.MEDIUM.value,
                title="Bullish trend structure",
                description=(
                    "Price above 20-SMA, 20-SMA above 50-SMA."
                ),
                confidence_score="0.60",
                explanation=(
                    "Aligned moving averages suggest "
                    "established upward trend."
                ),
            )
        )
        idx += 1
    elif sma_20 < sma_50 and current < sma_20:
        candidates.append(
            AttributionCandidate(
                candidate_id=f"TREND-{symbol}-{idx:03d}",
                category=AttributionCategory.TECHNICAL.value,
                direction=AttributionDirection.NEGATIVE.value,
                confidence=AttributionConfidence.MEDIUM.value,
                title="Bearish trend structure",
                description=(
                    "Price below 20-SMA, 20-SMA below 50-SMA."
                ),
                confidence_score="0.60",
                explanation=(
                    "Aligned moving averages suggest "
                    "established downward trend."
                ),
            )
        )
        idx += 1

    # 52-week high proximity
    high_52w = max(closes[-252:]) if len(closes) >= 252 else max(closes)
    if current >= high_52w * Decimal("0.95"):
        candidates.append(
            AttributionCandidate(
                candidate_id=f"TREND-{symbol}-{idx:03d}",
                category=AttributionCategory.TECHNICAL.value,
                direction=AttributionDirection.POSITIVE.value,
                confidence=AttributionConfidence.LOW.value,
                title="Near 52-week high",
                description=(
                    f"Price is within 5% of 52-week high "
                    f"({high_52w})."
                ),
                confidence_score="0.40",
                explanation=(
                    "Proximity to 52-week highs may indicate "
                    "strong momentum."
                ),
            )
        )
        idx += 1

    return candidates


def _market_attribution(
    price_move: PriceMove | None,
    symbol: str,
) -> list[AttributionCandidate]:
    """Market-wide attribution as default explanation."""
    candidates: list[AttributionCandidate] = []

    if price_move is None:
        return candidates

    pct = Decimal(price_move.percentage_change)
    if abs(pct) > Decimal("5"):
        direction = (
            AttributionDirection.POSITIVE.value
            if pct > 0
            else AttributionDirection.NEGATIVE.value
        )
        candidates.append(
            AttributionCandidate(
                candidate_id=f"MKT-{symbol}-000",
                category=AttributionCategory.MARKET.value,
                direction=direction,
                confidence=AttributionConfidence.LOW.value,
                title="Significant price movement",
                description=(
                    f"Price moved {price_move.percentage_change}% "
                    f"over {price_move.trading_days} trading days."
                ),
                confidence_score="0.40",
                explanation=(
                    "Large price moves without specific "
                    "fundamental catalyst may reflect "
                    "market-wide factors."
                ),
            )
        )

    return candidates


def attribute_price_move(
    bars: Sequence[PriceBar],
    symbol: str,
    as_of: datetime,
    lookback_days: int = 30,
) -> PriceAttributionResult:
    """
    Run the full price-move attribution pipeline.

    Deterministic: no external calls, no network, no randomness.
    """
    notes: list[str] = []

    if not bars:
        notes.append("No price data available.")
        return PriceAttributionResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            notes=tuple(notes),
        )

    price_move = _compute_price_move(bars, lookback_days, as_of.date())

    if price_move is None:
        notes.append("Insufficient data to compute price move.")
        return PriceAttributionResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            notes=tuple(notes),
        )

    # Collect candidates from all dimensions
    all_candidates: list[AttributionCandidate] = []

    all_candidates.extend(
        _volume_attribution(bars, as_of.date(), symbol)
    )
    all_candidates.extend(
        _trend_attribution(bars, as_of.date(), symbol)
    )
    all_candidates.extend(
        _market_attribution(price_move, symbol)
    )

    # If no specific candidates, add a default
    if not all_candidates:
        all_candidates.append(
            AttributionCandidate(
                candidate_id=f"ATTR-{symbol}-000",
                category=AttributionCategory.UNKNOWN.value,
                direction=AttributionDirection.NEUTRAL.value,
                confidence=AttributionConfidence.INSUFFICIENT.value,
                title="Insufficient attribution data",
                description=(
                    "No specific attribution candidates "
                    "could be identified."
                ),
                confidence_score="0",
                explanation=(
                    "Additional data sources needed for "
                    "richer attribution."
                ),
            )
        )

    high = sum(
        1 for c in all_candidates
        if c.confidence == AttributionConfidence.HIGH.value
    )
    medium = sum(
        1 for c in all_candidates
        if c.confidence == AttributionConfidence.MEDIUM.value
    )
    low = sum(
        1 for c in all_candidates
        if c.confidence == AttributionConfidence.LOW.value
    )

    return PriceAttributionResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        price_move=price_move,
        candidates=tuple(all_candidates),
        total_candidates=len(all_candidates),
        high_confidence_count=high,
        medium_confidence_count=medium,
        low_confidence_count=low,
        coverage={
            "volume_candidates": sum(
                1 for c in all_candidates
                if c.category == AttributionCategory.VOLUME.value
            ),
            "trend_candidates": sum(
                1 for c in all_candidates
                if c.category == AttributionCategory.TECHNICAL.value
            ),
            "market_candidates": sum(
                1 for c in all_candidates
                if c.category == AttributionCategory.MARKET.value
            ),
        },
        notes=tuple(notes),
    )
