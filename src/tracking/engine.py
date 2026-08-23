"""
Company tracking engine.

Builds tracking results from available company data by detecting
meaningful changes across financial, news, corporate-action,
anomaly, and evidence domains.

This module is descriptive only: it surfaces what changed and
provides evidence traceability. It does NOT generate trading
signals, alerts, or investment recommendations.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from src.data.company.financials import FinancialSnapshot
from src.tracking.models import (
    ChangeDomain,
    CompanyTrackingResult,
    TrackingChange,
    TrackingSeverity,
)


def _detect_financial_changes(
    snapshots: list[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[TrackingChange]:
    """Detect meaningful financial changes between periods."""

    changes: list[TrackingChange] = []

    if len(snapshots) < 2:
        return changes

    prev = snapshots[-2]
    curr = snapshots[-1]

    # Revenue change
    if prev.revenue and curr.revenue and prev.revenue != 0:
        change_pct = ((curr.revenue - prev.revenue) / abs(prev.revenue)) * 100
        if abs(change_pct) > 10:
            severity = (
                TrackingSeverity.SIGNIFICANT
                if abs(change_pct) > 25
                else TrackingSeverity.NOTABLE
            )
            direction = "increased" if change_pct > 0 else "decreased"
            changes.append(
                TrackingChange(
                    change_id=f"{symbol}-rev-{curr.period_end}",
                    symbol=symbol,
                    domain=ChangeDomain.FINANCIAL,
                    severity=severity,
                    title=f"Revenue {direction} {abs(change_pct):.1f}%",
                    description=(
                        f"Revenue changed from {prev.revenue} to "
                        f"{curr.revenue} between {prev.period_end} "
                        f"and {curr.period_end}."
                    ),
                    previous_value=str(prev.revenue),
                    current_value=str(curr.revenue),
                    change_date=curr.period_end,
                    as_of=as_of,
                )
            )

    # Net profit change
    if prev.net_profit and curr.net_profit and prev.net_profit != 0:
        change_pct = ((curr.net_profit - prev.net_profit) / abs(prev.net_profit)) * 100
        if abs(change_pct) > 15:
            severity = (
                TrackingSeverity.SIGNIFICANT
                if abs(change_pct) > 30
                else TrackingSeverity.NOTABLE
            )
            direction = "increased" if change_pct > 0 else "decreased"
            changes.append(
                TrackingChange(
                    change_id=f"{symbol}-np-{curr.period_end}",
                    symbol=symbol,
                    domain=ChangeDomain.FINANCIAL,
                    severity=severity,
                    title=f"Net profit {direction} {abs(change_pct):.1f}%",
                    description=(
                        f"Net profit changed from {prev.net_profit} to "
                        f"{curr.net_profit} between {prev.period_end} "
                        f"and {curr.period_end}."
                    ),
                    previous_value=str(prev.net_profit),
                    current_value=str(curr.net_profit),
                    change_date=curr.period_end,
                    as_of=as_of,
                )
            )

    # Debt change
    if prev.total_debt and curr.total_debt and prev.total_debt != 0:
        change_pct = ((curr.total_debt - prev.total_debt) / abs(prev.total_debt)) * 100
        if abs(change_pct) > 10:
            severity = (
                TrackingSeverity.SIGNIFICANT
                if abs(change_pct) > 20
                else TrackingSeverity.NOTABLE
            )
            direction = "increased" if change_pct > 0 else "decreased"
            changes.append(
                TrackingChange(
                    change_id=f"{symbol}-debt-{curr.period_end}",
                    symbol=symbol,
                    domain=ChangeDomain.FINANCIAL,
                    severity=severity,
                    title=f"Total debt {direction} {abs(change_pct):.1f}%",
                    description=(
                        f"Total debt changed from {prev.total_debt} to "
                        f"{curr.total_debt} between {prev.period_end} "
                        f"and {curr.period_end}."
                    ),
                    previous_value=str(prev.total_debt),
                    current_value=str(curr.total_debt),
                    change_date=curr.period_end,
                    as_of=as_of,
                )
            )

    # Cash flow vs profit divergence
    if (
        prev.net_profit
        and prev.operating_cash_flow
        and curr.net_profit
        and curr.operating_cash_flow
    ):
        prev_divergent = (
            prev.net_profit > 0 and prev.operating_cash_flow < 0
        )
        curr_divergent = (
            curr.net_profit > 0 and curr.operating_cash_flow < 0
        )
        if curr_divergent and not prev_divergent:
            changes.append(
                TrackingChange(
                    change_id=f"{symbol}-cfdiv-{curr.period_end}",
                    symbol=symbol,
                    domain=ChangeDomain.ANOMALY,
                    severity=TrackingSeverity.SIGNIFICANT,
                    title="Cash-flow divergence emerged",
                    description=(
                        f"Net profit is positive ({curr.net_profit}) "
                        f"but operating cash flow is negative "
                        f"({curr.operating_cash_flow}) in period "
                        f"ending {curr.period_end}."
                    ),
                    previous_value=str(prev.operating_cash_flow),
                    current_value=str(curr.operating_cash_flow),
                    change_date=curr.period_end,
                    as_of=as_of,
                )
            )

    return changes


def build_tracking_result(
    snapshots: list[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> CompanyTrackingResult:
    """
    Build a tracking result from financial snapshots.

    Detects meaningful changes across the available data.
    """

    financial_changes = _detect_financial_changes(
        snapshots, symbol, as_of
    )

    all_changes = tuple(
        sorted(
            financial_changes,
            key=lambda c: (
                c.severity.value,
                c.change_date or as_of.date(),
            ),
            reverse=True,
        )
    )

    return CompanyTrackingResult.from_changes(
        symbol=symbol,
        as_of=as_of,
        changes=all_changes,
    )
