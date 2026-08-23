"""
Cross-domain intelligence module.

Builds transparent relationships between existing datasets:
  - fundamentals + market performance
  - events + market reaction
  - revenue growth + margin compression
  - earnings growth + CFO deterioration
  - technology investment + business evidence
  - debt vs cash generation

Every observation is descriptive only -- it flags evidence
worth noting, not predictions. Does NOT imply causality.

All observations carry full provenance and explicit
methodology.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Sequence

from src.data.company.financials import FinancialSnapshot


class CrossDomainDirection(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    MIXED = "MIXED"
    NEUTRAL = "NEUTRAL"


class CrossDomainSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class CrossDomainObservation:
    """
    A single cross-domain research observation.

    Links evidence from multiple domains to identify
    relationships worth noting.
    """

    observation_id: str
    symbol: str

    category: str
    observation_type: str

    # Domain 1 evidence
    domain_1_name: str
    domain_1_metric: str
    domain_2_name: str
    domain_2_metric: str

    domain_1_value: str | None = None
    domain_1_direction: str = "UNKNOWN"

    # Domain 2 evidence
    domain_2_value: str | None = None
    domain_2_direction: str = "UNKNOWN"

    # Cross-domain relationship
    relationship: str = ""  # e.g., "IMPROVING + WEAKENING"
    direction: str = CrossDomainDirection.NEUTRAL.value
    severity: str = CrossDomainSeverity.LOW.value

    explanation: str = ""
    limitations: tuple[str, ...] = ()

    source_name: str | None = None
    as_of: str | None = None

    calculation_method: str = ""
    calculation_inputs: dict[str, str] = field(default_factory=dict)

    related_metrics: tuple[str, ...] = ()
    supporting_data: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CrossDomainResult:
    """
    Complete cross-domain analysis for one company.
    """

    symbol: str
    as_of: str

    observations: tuple[CrossDomainObservation, ...] = ()
    observation_count: int = 0

    # Summary
    positive_count: int = 0
    negative_count: int = 0
    mixed_count: int = 0
    neutral_count: int = 0

    notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_observation_counter = 0


def _next_id(prefix: str) -> str:
    global _observation_counter
    _observation_counter += 1
    return f"XD-{prefix}-{_observation_counter:04d}"


def _safe_decimal(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if value.is_nan() or value.is_infinite():
        return None
    return value


def _pct_change(
    previous: Decimal | None,
    current: Decimal | None,
) -> Decimal | None:
    if previous is None or current is None:
        return None
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * Decimal("100")


# ---------------------------------------------------------------------------
# Cross-Domain Analysis Functions
# ---------------------------------------------------------------------------


def analyze_fundamental_market_divergence(
    snapshots: Sequence[FinancialSnapshot],
    market_return_20d: float | None,
    market_return_50d: float | None,
    symbol: str,
    as_of: datetime,
) -> list[CrossDomainObservation]:
    """
    Analyze divergence between fundamental improvement
    and market performance.

    Examples:
    - Improving fundamentals + weak market performance
    - Deteriorating fundamentals + strong market performance
    """
    observations: list[CrossDomainObservation] = []

    if len(snapshots) < 2:
        return observations

    ordered = sorted(snapshots, key=lambda s: s.period_end)

    # Calculate revenue growth
    first = ordered[0]
    last = ordered[-1]

    revenue_growth = _pct_change(first.revenue, last.revenue)

    # Calculate profit growth
    profit_growth = _pct_change(first.net_profit, last.net_profit)

    if revenue_growth is None or profit_growth is None:
        return observations

    # Determine fundamental direction
    if revenue_growth > Decimal("10") and profit_growth > Decimal("10"):
        fundamental_direction = "IMPROVING"
    elif revenue_growth < Decimal("-10") or profit_growth < Decimal("-10"):
        fundamental_direction = "DETERIORATING"
    else:
        fundamental_direction = "STABLE"

    # Determine market direction
    market_direction = "UNKNOWN"
    market_return = None

    if market_return_20d is not None:
        market_return = market_return_20d
        if market_return_20d > 0.05:
            market_direction = "STRONG"
        elif market_return_20d > 0:
            market_direction = "POSITIVE"
        elif market_return_20d > -0.05:
            market_direction = "NEGATIVE"
        else:
            market_direction = "WEAK"
    elif market_return_50d is not None:
        market_return = market_return_50d
        if market_return_50d > 0.10:
            market_direction = "STRONG"
        elif market_return_50d > 0:
            market_direction = "POSITIVE"
        elif market_return_50d > -0.10:
            market_direction = "NEGATIVE"
        else:
            market_direction = "WEAK"

    if market_direction == "UNKNOWN":
        return observations

    # Check for divergence
    if (
        fundamental_direction == "IMPROVING"
        and market_direction in ("NEGATIVE", "WEAK")
    ):
        observations.append(
            CrossDomainObservation(
                observation_id=_next_id("FM"),
                symbol=symbol,
                category="fundamental_market",
                observation_type="improving_fundamentals_weak_market",
                domain_1_name="fundamentals",
                domain_1_metric="revenue_profit_growth",
                domain_1_value=(
                    f"Revenue: {revenue_growth:.1f}%, "
                    f"Profit: {profit_growth:.1f}%"
                ),
                domain_1_direction="IMPROVING",
                domain_2_name="market",
                domain_2_metric="market_return",
                domain_2_value=f"{market_return:.1%}" if market_return else None,
                domain_2_direction=market_direction,
                relationship="IMPROVING + WEAK",
                direction=CrossDomainDirection.MIXED.value,
                severity=CrossDomainSeverity.MEDIUM.value,
                explanation=(
                    f"Fundamentals are improving (revenue "
                    f"growth {revenue_growth:.1f}%, profit "
                    f"growth {profit_growth:.1f}%) while market "
                    f"performance is {market_direction.lower()}. "
                    f"This divergence may indicate market "
                    f"underreaction or other factors."
                ),
                limitations=(
                    "Does not establish causality. "
                    "Market return is a simplified metric.",
                ),
                as_of=as_of.isoformat(),
                calculation_method=(
                    "Revenue/profit growth vs market return"
                ),
                calculation_inputs={
                    "revenue_growth": str(revenue_growth),
                    "profit_growth": str(profit_growth),
                    "market_return": str(market_return)
                    if market_return
                    else "None",
                },
                related_metrics=(
                    "revenue",
                    "net_profit",
                    "market_return",
                ),
            )
        )

    elif (
        fundamental_direction == "DETERIORATING"
        and market_direction in ("STRONG", "POSITIVE")
    ):
        observations.append(
            CrossDomainObservation(
                observation_id=_next_id("FM"),
                symbol=symbol,
                category="fundamental_market",
                observation_type="deteriorating_fundamentals_strong_market",
                domain_1_name="fundamentals",
                domain_1_metric="revenue_profit_growth",
                domain_1_value=(
                    f"Revenue: {revenue_growth:.1f}%, "
                    f"Profit: {profit_growth:.1f}%"
                ),
                domain_1_direction="DETERIORATING",
                domain_2_name="market",
                domain_2_metric="market_return",
                domain_2_value=f"{market_return:.1%}" if market_return else None,
                domain_2_direction=market_direction,
                relationship="DETERIORATING + STRONG",
                direction=CrossDomainDirection.MIXED.value,
                severity=CrossDomainSeverity.MEDIUM.value,
                explanation=(
                    f"Fundamentals are deteriorating (revenue "
                    f"growth {revenue_growth:.1f}%, profit "
                    f"growth {profit_growth:.1f}%) while market "
                    f"performance is {market_direction.lower()}. "
                    f"This divergence may indicate market "
                    f"overreaction or anticipation of recovery."
                ),
                limitations=(
                    "Does not establish causality. "
                    "Market return is a simplified metric.",
                ),
                as_of=as_of.isoformat(),
                calculation_method=(
                    "Revenue/profit growth vs market return"
                ),
                calculation_inputs={
                    "revenue_growth": str(revenue_growth),
                    "profit_growth": str(profit_growth),
                    "market_return": str(market_return)
                    if market_return
                    else "None",
                },
                related_metrics=(
                    "revenue",
                    "net_profit",
                    "market_return",
                ),
            )
        )

    return observations


def analyze_growth_margin_divergence(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[CrossDomainObservation]:
    """
    Analyze divergence between revenue growth and margin trends.

    Examples:
    - Revenue growth + margin compression
    - Revenue decline + margin expansion
    """
    observations: list[CrossDomainObservation] = []

    if len(snapshots) < 2:
        return observations

    ordered = sorted(snapshots, key=lambda s: s.period_end)

    # Calculate revenue growth
    first = ordered[0]
    last = ordered[-1]

    revenue_growth = _pct_change(first.revenue, last.revenue)

    # Calculate margin changes
    first_margin = None
    last_margin = None

    if (
        first.revenue is not None
        and first.revenue > 0
        and first.net_profit is not None
    ):
        first_margin = (first.net_profit / first.revenue) * Decimal("100")

    if (
        last.revenue is not None
        and last.revenue > 0
        and last.net_profit is not None
    ):
        last_margin = (last.net_profit / last.revenue) * Decimal("100")

    if revenue_growth is None or first_margin is None or last_margin is None:
        return observations

    margin_change = last_margin - first_margin

    # Check for divergence
    if revenue_growth > Decimal("10") and margin_change < Decimal("-5"):
        observations.append(
            CrossDomainObservation(
                observation_id=_next_id("GM"),
                symbol=symbol,
                category="growth_margin",
                observation_type="revenue_growth_margin_compression",
                domain_1_name="growth",
                domain_1_metric="revenue_growth",
                domain_1_value=f"{revenue_growth:.1f}%",
                domain_1_direction="IMPROVING",
                domain_2_name="margins",
                domain_2_metric="net_margin_change",
                domain_2_value=f"{margin_change:.1f}pp",
                domain_2_direction="DETERIORATING",
                relationship="GROWTH + MARGIN_COMPRESSION",
                direction=CrossDomainDirection.MIXED.value,
                severity=CrossDomainSeverity.MEDIUM.value,
                explanation=(
                    f"Revenue grew {revenue_growth:.1f}% but "
                    f"net margin declined by {abs(margin_change):.1f}pp "
                    f"(from {first_margin:.1f}% to {last_margin:.1f}%). "
                    f"This may indicate pricing pressure, cost "
                    f"inflation, or unfavorable mix shift."
                ),
                limitations=(
                    "Does not establish causality. "
                    "Margin change is period-end to period-end.",
                ),
                as_of=as_of.isoformat(),
                calculation_method=(
                    "Revenue growth vs net margin change"
                ),
                calculation_inputs={
                    "revenue_growth": str(revenue_growth),
                    "first_margin": str(first_margin),
                    "last_margin": str(last_margin),
                    "margin_change": str(margin_change),
                },
                related_metrics=(
                    "revenue",
                    "net_profit",
                ),
            )
        )

    elif revenue_growth < Decimal("-10") and margin_change > Decimal("5"):
        observations.append(
            CrossDomainObservation(
                observation_id=_next_id("GM"),
                symbol=symbol,
                category="growth_margin",
                observation_type="revenue_decline_margin_expansion",
                domain_1_name="growth",
                domain_1_metric="revenue_growth",
                domain_1_value=f"{revenue_growth:.1f}%",
                domain_1_direction="DETERIORATING",
                domain_2_name="margins",
                domain_2_metric="net_margin_change",
                domain_2_value=f"+{margin_change:.1f}pp",
                domain_2_direction="IMPROVING",
                relationship="DECLINE + MARGIN_EXPANSION",
                direction=CrossDomainDirection.MIXED.value,
                severity=CrossDomainSeverity.MEDIUM.value,
                explanation=(
                    f"Revenue declined {abs(revenue_growth):.1f}% "
                    f"but net margin improved by {margin_change:.1f}pp "
                    f"(from {first_margin:.1f}% to {last_margin:.1f}%). "
                    f"This may indicate cost-cutting or "
                    f"operational efficiency improvements."
                ),
                limitations=(
                    "Does not establish causality. "
                    "Margin improvement may not be sustainable.",
                ),
                as_of=as_of.isoformat(),
                calculation_method=(
                    "Revenue growth vs net margin change"
                ),
                calculation_inputs={
                    "revenue_growth": str(revenue_growth),
                    "first_margin": str(first_margin),
                    "last_margin": str(last_margin),
                    "margin_change": str(margin_change),
                },
                related_metrics=(
                    "revenue",
                    "net_profit",
                ),
            )
        )

    return observations


def analyze_earnings_cfo_divergence(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[CrossDomainObservation]:
    """
    Analyze divergence between earnings growth and CFO trends.

    Examples:
    - Earnings growth + CFO deterioration
    - Earnings decline + CFO improvement
    """
    observations: list[CrossDomainObservation] = []

    if len(snapshots) < 2:
        return observations

    ordered = sorted(snapshots, key=lambda s: s.period_end)

    first = ordered[0]
    last = ordered[-1]

    # Calculate earnings growth
    earnings_growth = _pct_change(first.net_profit, last.net_profit)

    # Calculate CFO growth
    cfo_growth = _pct_change(
        first.operating_cash_flow,
        last.operating_cash_flow,
    )

    if earnings_growth is None or cfo_growth is None:
        return observations

    # Check for divergence
    if earnings_growth > Decimal("20") and cfo_growth < Decimal("-10"):
        observations.append(
            CrossDomainObservation(
                observation_id=_next_id("EC"),
                symbol=symbol,
                category="earnings_cfo",
                observation_type="earnings_growth_cfo_deterioration",
                domain_1_name="earnings",
                domain_1_metric="net_profit_growth",
                domain_1_value=f"{earnings_growth:.1f}%",
                domain_1_direction="IMPROVING",
                domain_2_name="cash_flow",
                domain_2_metric="cfo_growth",
                domain_2_value=f"{cfo_growth:.1f}%",
                domain_2_direction="DETERIORATING",
                relationship="EARNINGS_GROWTH + CFO_DECLINE",
                direction=CrossDomainDirection.NEGATIVE.value,
                severity=CrossDomainSeverity.HIGH.value,
                explanation=(
                    f"Earnings grew {earnings_growth:.1f}% but "
                    f"operating cash flow declined {abs(cfo_growth):.1f}%. "
                    f"This significant divergence may indicate "
                    f"earnings quality concerns, working capital "
                    f"build-up, or revenue recognition issues."
                ),
                limitations=(
                    "Does not establish causality. "
                    "CFO decline may be due to timing.",
                ),
                as_of=as_of.isoformat(),
                calculation_method=(
                    "Net profit growth vs CFO growth"
                ),
                calculation_inputs={
                    "earnings_growth": str(earnings_growth),
                    "cfo_growth": str(cfo_growth),
                },
                related_metrics=(
                    "net_profit",
                    "operating_cash_flow",
                ),
            )
        )

    elif earnings_growth < Decimal("-20") and cfo_growth > Decimal("10"):
        observations.append(
            CrossDomainObservation(
                observation_id=_next_id("EC"),
                symbol=symbol,
                category="earnings_cfo",
                observation_type="earnings_decline_cfo_improvement",
                domain_1_name="earnings",
                domain_1_metric="net_profit_growth",
                domain_1_value=f"{earnings_growth:.1f}%",
                domain_1_direction="DETERIORATING",
                domain_2_name="cash_flow",
                domain_2_metric="cfo_growth",
                domain_2_value=f"+{cfo_growth:.1f}%",
                domain_2_direction="IMPROVING",
                relationship="EARNINGS_DECLINE + CFO_IMPROVEMENT",
                direction=CrossDomainDirection.MIXED.value,
                severity=CrossDomainSeverity.MEDIUM.value,
                explanation=(
                    f"Earnings declined {abs(earnings_growth):.1f}% "
                    f"but operating cash flow improved {cfo_growth:.1f}%. "
                    f"This may indicate one-time charges affecting "
                    f"earnings while core cash generation remains "
                    f"healthy."
                ),
                limitations=(
                    "Does not establish causality. "
                    "CFO improvement may not be sustainable.",
                ),
                as_of=as_of.isoformat(),
                calculation_method=(
                    "Net profit growth vs CFO growth"
                ),
                calculation_inputs={
                    "earnings_growth": str(earnings_growth),
                    "cfo_growth": str(cfo_growth),
                },
                related_metrics=(
                    "net_profit",
                    "operating_cash_flow",
                ),
            )
        )

    return observations


def analyze_debt_cashflow_divergence(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[CrossDomainObservation]:
    """
    Analyze divergence between debt growth and cash generation.

    Examples:
    - Debt growth + cash flow decline
    - Debt reduction + cash flow improvement
    """
    observations: list[CrossDomainObservation] = []

    if len(snapshots) < 2:
        return observations

    ordered = sorted(snapshots, key=lambda s: s.period_end)

    first = ordered[0]
    last = ordered[-1]

    # Calculate debt growth
    debt_growth = _pct_change(first.total_debt, last.total_debt)

    # Calculate CFO growth
    cfo_growth = _pct_change(
        first.operating_cash_flow,
        last.operating_cash_flow,
    )

    if debt_growth is None or cfo_growth is None:
        return observations

    # Check for divergence
    if debt_growth > Decimal("30") and cfo_growth < Decimal("-10"):
        observations.append(
            CrossDomainObservation(
                observation_id=_next_id("DC"),
                symbol=symbol,
                category="debt_cashflow",
                observation_type="debt_growth_cashflow_decline",
                domain_1_name="leverage",
                domain_1_metric="debt_growth",
                domain_1_value=f"+{debt_growth:.1f}%",
                domain_1_direction="DETERIORATING",
                domain_2_name="cash_flow",
                domain_2_metric="cfo_growth",
                domain_2_value=f"{cfo_growth:.1f}%",
                domain_2_direction="DETERIORATING",
                relationship="DEBT_GROWTH + CASHFLOW_DECLINE",
                direction=CrossDomainDirection.NEGATIVE.value,
                severity=CrossDomainSeverity.HIGH.value,
                explanation=(
                    f"Debt grew {debt_growth:.1f}% while "
                    f"operating cash flow declined "
                    f"{abs(cfo_growth):.1f}%. This may indicate "
                    f"leverage building without corresponding "
                    f"cash generation to service the debt."
                ),
                limitations=(
                    "Does not establish causality. "
                    "Debt increase may be for growth investments.",
                ),
                as_of=as_of.isoformat(),
                calculation_method=(
                    "Debt growth vs CFO growth"
                ),
                calculation_inputs={
                    "debt_growth": str(debt_growth),
                    "cfo_growth": str(cfo_growth),
                },
                related_metrics=(
                    "total_debt",
                    "operating_cash_flow",
                ),
            )
        )

    elif debt_growth < Decimal("-20") and cfo_growth > Decimal("10"):
        observations.append(
            CrossDomainObservation(
                observation_id=_next_id("DC"),
                symbol=symbol,
                category="debt_cashflow",
                observation_type="debt_reduction_cashflow_improvement",
                domain_1_name="leverage",
                domain_1_metric="debt_growth",
                domain_1_value=f"{debt_growth:.1f}%",
                domain_1_direction="IMPROVING",
                domain_2_name="cash_flow",
                domain_2_metric="cfo_growth",
                domain_2_value=f"+{cfo_growth:.1f}%",
                domain_2_direction="IMPROVING",
                relationship="DEBT_REDUCTION + CASHFLOW_IMPROVEMENT",
                direction=CrossDomainDirection.POSITIVE.value,
                severity=CrossDomainSeverity.LOW.value,
                explanation=(
                    f"Debt reduced by {abs(debt_growth):.1f}% "
                    f"while operating cash flow improved "
                    f"{cfo_growth:.1f}%. This indicates "
                    f"deleveraging with healthy cash generation."
                ),
                limitations=(
                    "Does not establish causality. "
                    "Debt reduction may be due to refinancing.",
                ),
                as_of=as_of.isoformat(),
                calculation_method=(
                    "Debt growth vs CFO growth"
                ),
                calculation_inputs={
                    "debt_growth": str(debt_growth),
                    "cfo_growth": str(cfo_growth),
                },
                related_metrics=(
                    "total_debt",
                    "operating_cash_flow",
                ),
            )
        )

    return observations


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


def analyze_cross_domain(
    *,
    symbol: str,
    as_of: datetime,
    snapshots: Sequence[FinancialSnapshot] = (),
    market_return_20d: float | None = None,
    market_return_50d: float | None = None,
) -> CrossDomainResult:
    """
    Complete cross-domain analysis for one company.

    Combines all cross-domain dimensions into a single
    result with full provenance.
    """
    if not snapshots:
        return CrossDomainResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            notes=("No financial data available.",),
        )

    observations: list[CrossDomainObservation] = []

    # Run all analyses
    observations.extend(
        analyze_fundamental_market_divergence(
            snapshots, market_return_20d, market_return_50d,
            symbol, as_of,
        )
    )
    observations.extend(
        analyze_growth_margin_divergence(
            snapshots, symbol, as_of
        )
    )
    observations.extend(
        analyze_earnings_cfo_divergence(
            snapshots, symbol, as_of
        )
    )
    observations.extend(
        analyze_debt_cashflow_divergence(
            snapshots, symbol, as_of
        )
    )

    # Calculate summary counts
    positive = sum(
        1 for o in observations
        if o.direction == CrossDomainDirection.POSITIVE.value
    )
    negative = sum(
        1 for o in observations
        if o.direction == CrossDomainDirection.NEGATIVE.value
    )
    mixed = sum(
        1 for o in observations
        if o.direction == CrossDomainDirection.MIXED.value
    )
    neutral = sum(
        1 for o in observations
        if o.direction == CrossDomainDirection.NEUTRAL.value
    )

    return CrossDomainResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        observations=tuple(observations),
        observation_count=len(observations),
        positive_count=positive,
        negative_count=negative,
        mixed_count=mixed,
        neutral_count=neutral,
        notes=(),
    )
