"""
Competitive analysis engine.

Derives competitive positioning from financial data:
  - Peer benchmarking integration
  - Financial ratio comparison
  - Competitive positioning signals
  - Industry structure observations

All analysis is deterministic. Peer data must be supplied
by the caller; this module never fetches external data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from src.data.company.financials import FinancialSnapshot


@dataclass(frozen=True)
class CompetitiveMetric:
    """One metric comparison against peers."""

    metric: str
    company_value: str | None = None
    peer_median: str | None = None
    percentile: str = ""
    position: str = "UNKNOWN"
    explanation: str = ""


@dataclass(frozen=True)
class CompetitiveSignal:
    """A competitive positioning observation."""

    signal_id: str
    signal_type: str
    direction: str
    title: str
    description: str
    metric: str
    company_value: str | None = None
    peer_value: str | None = None
    explanation: str = ""


@dataclass(frozen=True)
class CompetitiveAnalysisResult:
    """Complete competitive analysis for one company."""

    symbol: str
    as_of: str

    has_peer_data: bool = False
    peer_count: int = 0

    metrics: tuple[CompetitiveMetric, ...] = ()
    signals: tuple[CompetitiveSignal, ...] = ()

    coverage: dict[str, int] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    available_analyses: tuple[str, ...] = ()
    missing_analyses: tuple[str, ...] = ()


def _median(values: list[Decimal]) -> Decimal:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def _percentile_rank(
    value: Decimal, values: list[Decimal]
) -> Decimal:
    below_or_equal = sum(
        candidate <= value for candidate in values
    )
    return (
        Decimal(below_or_equal) / Decimal(len(values))
    ) * Decimal("100")


def compute_financial_metric_comparison(
    company: FinancialSnapshot,
    peers: list[FinancialSnapshot],
    metric: str,
) -> CompetitiveMetric | None:
    """Compare one financial metric against peers."""

    company_value = getattr(company, metric, None)
    if company_value is None:
        return None

    peer_values = []
    for p in peers:
        val = getattr(p, metric, None)
        if val is not None:
            peer_values.append(val)

    if not peer_values:
        return CompetitiveMetric(
            metric=metric,
            company_value=str(company_value),
            position="NO_PEERS",
            explanation=f"No peer data available for {metric}.",
        )

    peer_median = _median(peer_values)
    percentile = _percentile_rank(company_value, peer_values)

    if percentile >= Decimal("75"):
        position = "ABOVE_PEERS"
    elif percentile >= Decimal("25"):
        position = "INLINE_WITH_PEERS"
    else:
        position = "BELOW_PEERS"

    return CompetitiveMetric(
        metric=metric,
        company_value=str(company_value),
        peer_median=str(peer_median),
        percentile=str(percentile.quantize(Decimal("0.01"))),
        position=position,
        explanation=(
            f"{metric}: company={company_value}, "
            f"peer_median={peer_median}, "
            f"percentile={percentile.quantize(Decimal('0.01'))}"
        ),
    )


_METRICS_TO_COMPARE = (
    "revenue",
    "operating_profit",
    "net_profit",
    "total_debt",
    "total_assets",
    "shareholders_equity",
)


def compute_competitive_signals(
    metrics: tuple[CompetitiveMetric, ...],
    symbol: str,
) -> tuple[CompetitiveSignal, ...]:
    """Derive competitive positioning signals from metric comparisons."""

    signals: list[CompetitiveSignal] = []

    for m in metrics:
        if m.position == "ABOVE_PEERS":
            signals.append(
                CompetitiveSignal(
                    signal_id=f"{symbol}_COMP_{m.metric.upper()}",
                    signal_type="FINANCIAL_POSITION",
                    direction="POSITIVE",
                    title=f"{m.metric} above peers",
                    description=(
                        f"{m.metric} is in the top quartile "
                        f"relative to peers (percentile={m.percentile})."
                    ),
                    metric=m.metric,
                    company_value=m.company_value,
                    peer_value=m.peer_median,
                )
            )
        elif m.position == "BELOW_PEERS":
            signals.append(
                CompetitiveSignal(
                    signal_id=f"{symbol}_COMP_{m.metric.upper()}",
                    signal_type="FINANCIAL_POSITION",
                    direction="NEGATIVE",
                    title=f"{m.metric} below peers",
                    description=(
                        f"{m.metric} is in the bottom quartile "
                        f"relative to peers (percentile={m.percentile})."
                    ),
                    metric=m.metric,
                    company_value=m.company_value,
                    peer_value=m.peer_median,
                )
            )

    return tuple(signals)


def analyze_competitive(
    company_snapshot: FinancialSnapshot,
    peer_snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> CompetitiveAnalysisResult:
    """
    Run the full competitive analysis pipeline.

    Compares the company's financials against peers and
    derives positioning signals.
    """

    notes: list[str] = []
    available: list[str] = []
    missing: list[str] = []

    has_peers = len(peer_snapshots) > 0

    if not has_peers:
        notes.append("No peer data supplied; competitive analysis is limited.")
        missing.append("peer_comparison")
        return CompetitiveAnalysisResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            has_peer_data=False,
            notes=tuple(notes),
            missing_analyses=tuple(missing),
        )

    # Compare metrics
    metrics: list[CompetitiveMetric] = []
    for metric_name in _METRICS_TO_COMPARE:
        result = compute_financial_metric_comparison(
            company_snapshot, list(peer_snapshots), metric_name
        )
        if result is not None:
            metrics.append(result)

    if metrics:
        available.append("peer_comparison")
    else:
        missing.append("peer_comparison")
        notes.append("No metrics could be compared against peers.")

    # Derive signals
    signals = compute_competitive_signals(tuple(metrics), symbol)

    return CompetitiveAnalysisResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        has_peer_data=True,
        peer_count=len(peer_snapshots),
        metrics=tuple(metrics),
        signals=signals,
        coverage={m.metric: 1 for m in metrics},
        notes=tuple(notes),
        available_analyses=tuple(available),
        missing_analyses=tuple(missing),
    )
