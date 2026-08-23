"""
Management analysis engine.

Analyzes management changes and derives:
  - Change frequency and pattern analysis
  - Capital allocation behavior from financial data
  - Execution evidence vs stated strategy

All analysis is deterministic and PIT-safe.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from src.data.company.management import ManagementChange
from src.data.company.financials import FinancialSnapshot


@dataclass(frozen=True)
class ManagementChangePattern:
    """Aggregated pattern of management changes."""

    pattern_id: str
    pattern_type: str
    change_count: int
    roles_affected: tuple[str, ...] = ()
    date_range: str = ""
    explanation: str = ""


@dataclass(frozen=True)
class CapitalAllocationSignal:
    """Observation about how management deploys capital."""

    signal_id: str
    signal_type: str
    direction: str
    title: str
    description: str
    metric: str
    value: str | None = None
    explanation: str = ""


@dataclass(frozen=True)
class ManagementAnalysisResult:
    """Complete management analysis for one company."""

    symbol: str
    as_of: str

    change_count: int = 0
    changes: tuple[ManagementChange, ...] = ()
    patterns: tuple[ManagementChangePattern, ...] = ()
    allocation_signals: tuple[CapitalAllocationSignal, ...] = ()

    coverage: dict[str, int] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    available_analyses: tuple[str, ...] = ()
    missing_analyses: tuple[str, ...] = ()


def _classify_change(change_type: str) -> str:
    ct = change_type.lower()
    if "resign" in ct or "step down" in ct:
        return "DEPARTURE"
    if "appoint" in ct or "hire" in ct or "elevate" in ct:
        return "APPOINTMENT"
    if "remov" in ct or "dismiss" in ct:
        return "REMOVAL"
    return "OTHER"


def compute_management_patterns(
    changes: Sequence[ManagementChange],
    symbol: str,
) -> tuple[ManagementChangePattern, ...]:
    """Identify patterns in management changes."""

    if not changes:
        return ()

    patterns: list[ManagementChangePattern] = []

    # Departure frequency
    departures = [c for c in changes if _classify_change(c.change_type) == "DEPARTURE"]
    if len(departures) >= 3:
        roles = tuple(sorted({c.role for c in departures}))
        dates = sorted(c.effective_date for c in departures)
        patterns.append(
            ManagementChangePattern(
                pattern_id=f"{symbol}_ELEVATED_DEPARTURES",
                pattern_type="ELEVATED_DEPARTURES",
                change_count=len(departures),
                roles_affected=roles,
                date_range=f"{dates[0]} to {dates[-1]}",
                explanation=(
                    f"{len(departures)} departures detected across "
                    f"roles: {', '.join(roles)}."
                ),
            )
        )

    # Role concentration
    role_counts = Counter(c.role for c in changes)
    for role, count in role_counts.items():
        if count >= 3:
            patterns.append(
                ManagementChangePattern(
                    pattern_id=f"{symbol}_ROLE_CHURN_{role.upper().replace(' ', '_')}",
                    pattern_type="ROLE_CHURN",
                    change_count=count,
                    roles_affected=(role,),
                    explanation=(
                        f"Role '{role}' has experienced "
                        f"{count} changes."
                    ),
                )
            )

    return tuple(patterns)


def compute_capital_allocation_signals(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
) -> tuple[CapitalAllocationSignal, ...]:
    """
    Derive capital allocation signals from financial data.

    Analyzes debt changes, cash position changes, and
    equity changes as proxies for capital allocation behavior.
    """

    if len(snapshots) < 2:
        return ()

    ordered = sorted(snapshots, key=lambda s: s.period_end)
    signals: list[CapitalAllocationSignal] = []

    for prev, curr in zip(ordered, ordered[1:]):
        period = curr.period_end.isoformat()

        # Debt reduction signal
        if prev.total_debt is not None and curr.total_debt is not None:
            debt_change = curr.total_debt - prev.total_debt
            if debt_change < 0 and prev.total_debt > 0:
                pct = (
                    (debt_change / prev.total_debt) * Decimal("100")
                ).quantize(Decimal("0.01"))
                signals.append(
                    CapitalAllocationSignal(
                        signal_id=f"{symbol}_DEBT_REDUCTION_{period}",
                        signal_type="DEBT_MANAGEMENT",
                        direction="POSITIVE",
                        title="Debt reduction",
                        description=f"Total debt reduced by {abs(debt_change)} ({abs(pct)}%)",
                        metric="total_debt_change",
                        value=str(debt_change),
                        explanation=f"Debt decreased from {prev.total_debt} to {curr.total_debt}.",
                    )
                )
            elif debt_change > 0 and prev.total_debt > 0:
                pct = (
                    (debt_change / prev.total_debt) * Decimal("100")
                ).quantize(Decimal("0.01"))
                if pct > Decimal("20"):
                    signals.append(
                        CapitalAllocationSignal(
                            signal_id=f"{symbol}_DEBT_INCREASE_{period}",
                            signal_type="DEBT_MANAGEMENT",
                            direction="NEGATIVE",
                            title="Significant debt increase",
                            description=f"Total debt increased by {debt_change} ({pct}%)",
                            metric="total_debt_change",
                            value=str(debt_change),
                            explanation=f"Debt increased from {prev.total_debt} to {curr.total_debt}.",
                        )
                    )

        # Cash accumulation signal
        if (
            prev.cash_and_equivalents is not None
            and curr.cash_and_equivalents is not None
        ):
            cash_change = curr.cash_and_equivalents - prev.cash_and_equivalents
            if cash_change > 0 and prev.cash_and_equivalents > 0:
                pct = (
                    (cash_change / prev.cash_and_equivalents) * Decimal("100")
                ).quantize(Decimal("0.01"))
                if pct > Decimal("20"):
                    signals.append(
                        CapitalAllocationSignal(
                            signal_id=f"{symbol}_CASH_ACCUMULATION_{period}",
                            signal_type="CASH_MANAGEMENT",
                            direction="POSITIVE",
                            title="Cash accumulation",
                            description=f"Cash increased by {cash_change} ({pct}%)",
                            metric="cash_change",
                            value=str(cash_change),
                            explanation=f"Cash increased from {prev.cash_and_equivalents} to {curr.cash_and_equivalents}.",
                        )
                    )

        # Free cash flow signal
        if curr.free_cash_flow is not None and curr.free_cash_flow > 0:
            signals.append(
                CapitalAllocationSignal(
                    signal_id=f"{symbol}_FCF_{period}",
                    signal_type="CASH_GENERATION",
                    direction="POSITIVE",
                    title="Positive free cash flow",
                    description=f"Free cash flow of {curr.free_cash_flow}",
                    metric="free_cash_flow",
                    value=str(curr.free_cash_flow),
                    explanation="Company generated positive free cash flow.",
                )
            )

    return tuple(signals)


def analyze_management(
    changes: Sequence[ManagementChange],
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> ManagementAnalysisResult:
    """
    Run the full management analysis pipeline.
    """

    notes: list[str] = []
    available: list[str] = []
    missing: list[str] = []

    # Change patterns
    patterns: tuple[ManagementChangePattern, ...] = ()
    if changes:
        patterns = compute_management_patterns(changes, symbol)
        available.append("management_patterns")
    else:
        missing.append("management_patterns")
        notes.append("No management change data available.")

    # Capital allocation
    alloc_signals: tuple[CapitalAllocationSignal, ...] = ()
    if len(snapshots) >= 2:
        alloc_signals = compute_capital_allocation_signals(snapshots, symbol)
        if alloc_signals:
            available.append("capital_allocation")
        else:
            missing.append("capital_allocation")
            notes.append("No capital allocation signals derivable from financial data.")
    else:
        missing.append("capital_allocation")
        notes.append("Capital allocation requires >= 2 financial periods.")

    return ManagementAnalysisResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        change_count=len(changes),
        changes=tuple(changes),
        patterns=patterns,
        allocation_signals=alloc_signals,
        notes=tuple(notes),
        available_analyses=tuple(available),
        missing_analyses=tuple(missing),
    )
