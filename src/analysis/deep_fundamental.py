"""
Deep fundamental research orchestrator.

Combines trajectory analysis, earnings quality, balance-sheet
quality, fundamental anomaly detection, cash-flow quality,
and deep balance-sheet analysis into a single typed result.
This is the primary entry point for the Phase 1B
fundamental research backend.

All analysis is deterministic and returns None/empty when
the underlying data is insufficient.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from src.analysis.balance_sheet_deep import (
    BalanceSheetDeepResult,
    analyze_balance_sheet_deep,
)
from src.analysis.balance_sheet_quality import (
    BalanceSheetObservation,
    analyze_balance_sheet_quality,
)
from src.analysis.cash_flow_quality import (
    CashFlowQualityResult,
    analyze_cash_flow_quality,
)
from src.analysis.earnings_quality import (
    EarningsQualityObservation,
    analyze_earnings_quality,
)
from src.analysis.financial_anomalies import (
    FinancialAnomaly,
    analyze_financial_change,
)
from src.analysis.financial_trends import (
    FinancialTrend,
    multi_period_trends,
)
from src.analysis.fundamental_observations import (
    FundamentalObservationSet,
    build_fundamental_observations,
)
from src.analysis.fundamental_trajectories import (
    TrajectoryAnalysis,
    analyze_all_trajectories,
)
from src.data.company.financials import FinancialSnapshot


@dataclass(frozen=True)
class DeepFundamentalResult:
    """
    Complete deep fundamental research result for one company.

    Combines all analysis dimensions into a single serialisable
    dataclass.
    """

    symbol: str
    as_of: str

    period_count: int = 0
    first_period: str = ""
    last_period: str = ""

    # Trajectory analysis
    trajectories: tuple[TrajectoryAnalysis, ...] = ()
    margin_trajectories: tuple = ()
    leverage_trajectories: tuple = ()

    # Earnings quality
    earnings_quality_observations: tuple[
        EarningsQualityObservation, ...
    ] = ()
    cash_profit_comparisons: tuple = ()

    # Balance-sheet quality
    balance_sheet_observations: tuple[
        BalanceSheetObservation, ...
    ] = ()

    # Fundamental anomalies (extending existing system)
    anomalies: tuple[FinancialAnomaly, ...] = ()

    # Multi-period financial trends (from existing engine)
    financial_trends: tuple[FinancialTrend, ...] = ()

    # Cash-flow quality analysis (new)
    cash_flow_quality: CashFlowQualityResult | None = None

    # Deep balance-sheet analysis (new)
    balance_sheet_deep: BalanceSheetDeepResult | None = None

    # Unified observations with provenance
    observation_set: FundamentalObservationSet | None = None

    # Coverage and notes
    available_analyses: tuple[str, ...] = ()
    missing_analyses: tuple[str, ...] = ()
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


def _ordered_snapshots(
    snapshots: Sequence[FinancialSnapshot],
) -> list[FinancialSnapshot]:
    return sorted(snapshots, key=lambda s: s.period_end)


def _pit_filter_snapshots(
    snapshots: Sequence[FinancialSnapshot],
    as_of: datetime,
) -> list[FinancialSnapshot]:
    """Filter snapshots to only those available at or before as_of.

    Rejects snapshots where available_at is None (unverifiable
    provenance) or available_at > as_of (future data leak).
    """
    filtered: list[FinancialSnapshot] = []
    for s in snapshots:
        if s.available_at is None:
            continue
        if s.available_at > as_of:
            continue
        filtered.append(s)
    return filtered


def analyze_deep_fundamentals(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> DeepFundamentalResult:
    """
    Run the full deep fundamental analysis pipeline.

    This is the primary entry point.  It is deterministic and
    returns an empty result when data is insufficient.

    PIT enforcement: only snapshots with available_at <= as_of
    are used. Snapshots with missing available_at are rejected.
    """
    pit_snapshots = _pit_filter_snapshots(snapshots, as_of)
    ordered = _ordered_snapshots(pit_snapshots)

    notes: list[str] = []
    available: list[str] = []
    missing: list[str] = []

    rejected_count = len(snapshots) - len(pit_snapshots)
    if rejected_count > 0:
        notes.append(
            f"PIT filter: {rejected_count} snapshot(s) rejected "
            f"(missing available_at or available_at > as_of)."
        )

    if not ordered:
        notes.append("No financial data available.")

        return DeepFundamentalResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            notes=tuple(notes),
            missing_analyses=(
                "trajectories",
                "earnings_quality",
                "balance_sheet_quality",
                "anomalies",
                "financial_trends",
                "cash_flow_quality",
                "balance_sheet_deep",
            ),
        )

    first_period = ordered[0].period_end.isoformat()
    last_period = ordered[-1].period_end.isoformat()

    # ---- Trajectory analysis ----
    trajectory_results: dict = {}
    trajectories: tuple[TrajectoryAnalysis, ...] = ()
    margin_trajectories: tuple = ()
    leverage_trajectories: tuple = ()

    if len(ordered) >= 2:
        trajectory_results = analyze_all_trajectories(
            ordered, symbol
        )
        trajectories = tuple(
            trajectory_results.get("trajectories", [])
        )
        margin_trajectories = tuple(
            trajectory_results.get("margin_trajectories", [])
        )
        leverage_trajectories = tuple(
            trajectory_results.get("leverage_trajectories", [])
        )
        available.append("trajectories")
    else:
        missing.append("trajectories")
        notes.append(
            "Trajectory analysis requires >= 2 periods."
        )

    # ---- Earnings quality ----
    eq_observations: list[EarningsQualityObservation] = []
    cash_profit: tuple = ()

    if len(ordered) >= 2:
        eq_observations = analyze_earnings_quality(ordered)
        available.append("earnings_quality")
    else:
        missing.append("earnings_quality")
        notes.append(
            "Earnings quality analysis requires >= 2 periods."
        )

    # ---- Balance-sheet quality ----
    bs_observations: list[BalanceSheetObservation] = []

    if len(ordered) >= 2:
        bs_observations = analyze_balance_sheet_quality(ordered)
        available.append("balance_sheet_quality")
    else:
        missing.append("balance_sheet_quality")
        notes.append(
            "Balance-sheet quality analysis requires >= 2 periods."
        )

    # ---- Fundamental anomalies ----
    anomaly_results: list[FinancialAnomaly] = []

    if len(ordered) >= 2:
        for prev, curr in zip(ordered, ordered[1:]):
            anomaly_results.extend(
                analyze_financial_change(prev, curr)
            )
        available.append("anomalies")
    else:
        missing.append("anomalies")
        notes.append(
            "Anomaly detection requires >= 2 periods."
        )

    # ---- Multi-period financial trends (existing engine) ----
    financial_trends: tuple[FinancialTrend, ...] = ()

    if len(ordered) >= 2:
        financial_trends = tuple(multi_period_trends(ordered))
        available.append("financial_trends")
    else:
        missing.append("financial_trends")

    # ---- Cash-flow quality analysis (new) ----
    cash_flow_quality: CashFlowQualityResult | None = None

    if ordered:
        cash_flow_quality = analyze_cash_flow_quality(
            symbol=symbol,
            as_of=as_of,
            snapshots=ordered,
        )
        available.append("cash_flow_quality")
    else:
        missing.append("cash_flow_quality")

    # ---- Deep balance-sheet analysis (new) ----
    balance_sheet_deep: BalanceSheetDeepResult | None = None

    if ordered:
        balance_sheet_deep = analyze_balance_sheet_deep(
            symbol=symbol,
            as_of=as_of,
            snapshots=ordered,
        )
        available.append("balance_sheet_deep")
    else:
        missing.append("balance_sheet_deep")

    # ---- Build unified observations ----
    observation_set: FundamentalObservationSet | None = None

    if len(ordered) >= 2:
        observation_set = build_fundamental_observations(
            symbol=symbol,
            as_of=as_of,
            snapshots=ordered,
            trajectory_results=trajectory_results,
            earnings_quality_results=eq_observations,
            balance_sheet_results=bs_observations,
            anomaly_results=anomaly_results,
        )

    return DeepFundamentalResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        period_count=len(ordered),
        first_period=first_period,
        last_period=last_period,
        trajectories=trajectories,
        margin_trajectories=margin_trajectories,
        leverage_trajectories=leverage_trajectories,
        earnings_quality_observations=tuple(eq_observations),
        cash_profit_comparisons=cash_profit,
        balance_sheet_observations=tuple(bs_observations),
        anomalies=tuple(anomaly_results),
        financial_trends=financial_trends,
        cash_flow_quality=cash_flow_quality,
        balance_sheet_deep=balance_sheet_deep,
        observation_set=observation_set,
        available_analyses=tuple(available),
        missing_analyses=tuple(missing),
        notes=tuple(notes),
    )
