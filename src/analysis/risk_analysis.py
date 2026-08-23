"""
Structured risk analysis engine.

Derives risk observations across multiple dimensions:
  - Concentration risk (segment, revenue)
  - Geographic risk
  - Technology/sector risk
  - Competitive risk
  - Execution risk (management changes, capital allocation)
  - Capital intensity risk
  - Financial risk (leverage, liquidity)
  - Strategic risk

All analysis is deterministic. Observations are factual
and never present investment recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from src.data.company.business_profile import BusinessProfile
from src.data.company.financials import FinancialSnapshot
from src.data.company.management import ManagementChange


@dataclass(frozen=True)
class RiskObservation:
    """A single risk observation with severity and evidence."""

    risk_id: str
    risk_dimension: str
    severity: str
    title: str
    description: str
    evidence_ids: tuple[str, ...] = ()
    explanation: str = ""


@dataclass(frozen=True)
class RiskAnalysisResult:
    """Complete risk analysis for one company."""

    symbol: str
    as_of: str

    observations: tuple[RiskObservation, ...] = ()

    dimension_counts: dict[str, int] = field(default_factory=dict)
    severity_counts: dict[str, int] = field(default_factory=dict)

    coverage: dict[str, int] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    available_analyses: tuple[str, ...] = ()
    missing_analyses: tuple[str, ...] = ()


# Sector-specific risk keywords
_TECHNOLOGY_SECTORS = {"Technology", "Information Technology", "TECHNOLOGY"}
_FINANCIAL_SECTORS = {"Financial Services", "Banks", "FINANCIAL SERVICES"}
_ENERGY_SECTORS = {"Energy", "Oil & Gas", "ENERGY"}
_HEALTHCARE_SECTORS = {"Healthcare", "Health Care", "Pharmaceuticals", "HEALTHCARE"}


def _detect_sector_risks(
    profile: BusinessProfile | None,
    symbol: str,
) -> tuple[RiskObservation, ...]:
    """Detect sector-specific risk factors."""

    if profile is None or profile.sector is None:
        return ()

    risks: list[RiskObservation] = []
    sector = profile.sector.strip()

    if sector in _TECHNOLOGY_SECTORS:
        risks.append(
            RiskObservation(
                risk_id=f"{symbol}_TECH_RISK",
                risk_dimension="TECHNOLOGY",
                severity="MEDIUM",
                title="Technology sector risk",
                description="Technology sector exposure introduces obsolescence and disruption risk.",
                explanation="Technology companies face rapid innovation cycles and competitive disruption.",
            )
        )

    if sector in _FINANCIAL_SECTORS:
        risks.append(
            RiskObservation(
                risk_id=f"{symbol}_FINANCIAL_SECTOR_RISK",
                risk_dimension="REGULATORY",
                severity="MEDIUM",
                title="Financial sector regulatory risk",
                description="Financial sector operations are subject to regulatory changes.",
                explanation="Regulatory changes can impact financial sector business models and profitability.",
            )
        )

    if sector in _ENERGY_SECTORS:
        risks.append(
            RiskObservation(
                risk_id=f"{symbol}_ENERGY_RISK",
                risk_dimension="COMMODITY",
                severity="MEDIUM",
                title="Commodity price risk",
                description="Energy sector operations are exposed to commodity price volatility.",
                explanation="Oil and gas prices directly impact energy company revenues and margins.",
            )
        )

    if sector in _HEALTHCARE_SECTORS:
        risks.append(
            RiskObservation(
                risk_id=f"{symbol}_HEALTHCARE_RISK",
                risk_dimension="REGULATORY",
                severity="MEDIUM",
                title="Healthcare regulatory risk",
                description="Healthcare sector operations face regulatory and approval risks.",
                explanation="Drug approvals, pricing regulations, and patent expirations create uncertainty.",
            )
        )

    return tuple(risks)


def _detect_financial_risks(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
) -> tuple[RiskObservation, ...]:
    """Detect financial risk factors from metrics."""

    if not snapshots:
        return ()

    risks: list[RiskObservation] = []
    latest = snapshots[-1]

    # Leverage risk
    if (
        latest.total_debt is not None
        and latest.shareholders_equity is not None
        and latest.shareholders_equity > 0
    ):
        debt_eq = latest.total_debt / latest.shareholders_equity
        if debt_eq > Decimal("2"):
            risks.append(
                RiskObservation(
                    risk_id=f"{symbol}_LEVERAGE_RISK",
                    risk_dimension="FINANCIAL",
                    severity="HIGH",
                    title="High leverage risk",
                    description=f"Debt-to-equity ratio of {debt_eq.quantize(Decimal('0.01'))} exceeds 2.0 threshold.",
                    explanation="High leverage increases financial risk and reduces flexibility.",
                )
            )
        elif debt_eq > Decimal("1"):
            risks.append(
                RiskObservation(
                    risk_id=f"{symbol}_MODERATE_LEVERAGE",
                    risk_dimension="FINANCIAL",
                    severity="LOW",
                    title="Moderate leverage",
                    description=f"Debt-to-equity ratio of {debt_eq.quantize(Decimal('0.01'))} is moderate.",
                    explanation="Leverage is within manageable range but warrants monitoring.",
                )
            )

    # Liquidity risk
    if (
        latest.current_assets is not None
        and latest.current_liabilities is not None
        and latest.current_liabilities > 0
    ):
        current_ratio = latest.current_assets / latest.current_liabilities
        if current_ratio < Decimal("1"):
            risks.append(
                RiskObservation(
                    risk_id=f"{symbol}_LIQUIDITY_RISK",
                    risk_dimension="FINANCIAL",
                    severity="HIGH",
                    title="Liquidity risk",
                    description=f"Current ratio of {current_ratio.quantize(Decimal('0.01'))} is below 1.0.",
                    explanation="Current liabilities exceed current assets, indicating potential liquidity pressure.",
                )
            )

    # Profit-cash divergence risk
    if latest.profit_cash_flow_divergence:
        risks.append(
            RiskObservation(
                risk_id=f"{symbol}_CASH_DIVERGENCE",
                risk_dimension="FINANCIAL",
                severity="MEDIUM",
                title="Profit-cash flow divergence",
                description="Net profit is positive while operating cash flow is negative.",
                explanation="Divergence between profit and cash flow may indicate earnings quality concerns.",
            )
        )

    return tuple(risks)


def _detect_concentration_risks(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
) -> tuple[RiskObservation, ...]:
    """Detect concentration risks from segment data."""

    if not snapshots:
        return ()

    risks: list[RiskObservation] = []
    latest = snapshots[-1]

    if not latest.segments:
        return ()

    total = latest.revenue
    if total is None or total == 0:
        return ()

    for seg in latest.segments:
        if seg.revenue is not None:
            share = seg.revenue / total
            if share > Decimal("0.7"):
                risks.append(
                    RiskObservation(
                        risk_id=f"{symbol}_SEGMENT_CONC_{seg.segment_name.upper().replace(' ', '_')}",
                        risk_dimension="CONCENTRATION",
                        severity="MEDIUM",
                        title=f"Revenue concentration in '{seg.segment_name}'",
                        description=(
                            f"Segment '{seg.segment_name}' represents "
                            f"{(share * Decimal('100')).quantize(Decimal('0.01'))}% of revenue."
                        ),
                        explanation="High segment concentration increases vulnerability to segment-specific downturns.",
                    )
                )

    return tuple(risks)


def _detect_execution_risks(
    changes: Sequence[ManagementChange],
    symbol: str,
) -> tuple[RiskObservation, ...]:
    """Detect execution risks from management change patterns."""

    if len(changes) < 3:
        return ()

    departures = sum(
        1 for c in changes
        if "resign" in c.change_type.lower() or "step down" in c.change_type.lower()
    )

    if departures >= 3:
        return (
            RiskObservation(
                risk_id=f"{symbol}_EXECUTION_RISK",
                risk_dimension="EXECUTION",
                severity="MEDIUM",
                title="Elevated management turnover",
                description=f"{departures} departures detected in management changes.",
                explanation="Frequent management departures can indicate organizational instability.",
            ),
        )

    return ()


def analyze_risks(
    snapshots: Sequence[FinancialSnapshot],
    profile: BusinessProfile | None,
    management_changes: Sequence[ManagementChange],
    symbol: str,
    as_of: datetime,
) -> RiskAnalysisResult:
    """
    Run the full risk analysis pipeline.
    """

    notes: list[str] = []
    available: list[str] = []
    missing: list[str] = []

    all_observations: list[RiskObservation] = []

    # Sector risks
    if profile is not None:
        sector_risks = _detect_sector_risks(profile, symbol)
        all_observations.extend(sector_risks)
        if sector_risks:
            available.append("sector_risks")
        else:
            missing.append("sector_risks")
            notes.append("No sector-specific risks detected from profile.")
    else:
        missing.append("sector_risks")
        notes.append("No business profile available for sector risk detection.")

    # Financial risks
    if snapshots:
        fin_risks = _detect_financial_risks(snapshots, symbol)
        all_observations.extend(fin_risks)
        if fin_risks:
            available.append("financial_risks")
        else:
            missing.append("financial_risks")
            notes.append("No financial risks detected from available metrics.")
    else:
        missing.append("financial_risks")
        notes.append("No financial data available for risk detection.")

    # Concentration risks
    if snapshots:
        conc_risks = _detect_concentration_risks(snapshots, symbol)
        all_observations.extend(conc_risks)
        if conc_risks:
            available.append("concentration_risks")
        else:
            missing.append("concentration_risks")
            notes.append("No concentration risks detected.")
    else:
        missing.append("concentration_risks")

    # Execution risks
    if management_changes:
        exec_risks = _detect_execution_risks(management_changes, symbol)
        all_observations.extend(exec_risks)
        if exec_risks:
            available.append("execution_risks")
        else:
            missing.append("execution_risks")
            notes.append("No execution risks detected from management changes.")
    else:
        missing.append("execution_risks")
        notes.append("No management change data for execution risk detection.")

    # Counts
    dimension_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    for obs in all_observations:
        dimension_counts[obs.risk_dimension] = dimension_counts.get(obs.risk_dimension, 0) + 1
        severity_counts[obs.severity] = severity_counts.get(obs.severity, 0) + 1

    return RiskAnalysisResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        observations=tuple(all_observations),
        dimension_counts=dimension_counts,
        severity_counts=severity_counts,
        notes=tuple(notes),
        available_analyses=tuple(available),
        missing_analyses=tuple(missing),
    )
