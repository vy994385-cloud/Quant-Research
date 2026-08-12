from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.analysis.financial_anomalies import FinancialAnomaly
from src.analysis.financial_risk_scoring import (
    financial_risk_score,
    financial_risk_signals,
)
from src.analysis.financial_ratios import (
    cash_conversion_ratio,
    debt_to_revenue,
    free_cash_flow_margin,
    net_profit_margin,
    receivables_to_revenue,
    revenue_growth,
)
from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
    IntelligenceDirection,
    IntelligenceSignal,
    build_company_research_snapshot,
)
from src.data.company.financials import FinancialSnapshot


def _direction(
    score: Decimal,
    positive: Decimal = Decimal("65"),
    negative: Decimal = Decimal("35"),
) -> IntelligenceDirection:
    if score >= positive:
        return IntelligenceDirection.POSITIVE

    if score <= negative:
        return IntelligenceDirection.NEGATIVE

    return IntelligenceDirection.NEUTRAL


def _fmt(value: Decimal | None) -> str:
    if value is None:
        return "unavailable"

    return f"{value:.2f}"


def _anomaly_signal(
    anomaly: FinancialAnomaly,
) -> IntelligenceSignal:
    severity = str(anomaly.severity).upper()

    materiality = {
        "LOW": 2,
        "MEDIUM": 3,
        "HIGH": 4,
        "CRITICAL": 5,
    }.get(severity, 2)

    return IntelligenceSignal(
        code=f"FINANCIAL_ANOMALY_{severity}",
        title=str(
            getattr(
                anomaly,
                "title",
                "Financial anomaly detected",
            )
        ),
        description=str(
            getattr(
                anomaly,
                "description",
                "A financial change requires review.",
            )
        ),
        direction=IntelligenceDirection.NEGATIVE,
        materiality=materiality,
        confidence=Decimal("0.80"),
    )


def build_financial_company_intelligence(
    *,
    symbol: str,
    as_of_date: date,
    snapshots: list[FinancialSnapshot],
) -> CompanyResearchSnapshot:
    """
    Convert normalized financial statements into human-readable
    company intelligence.

    This layer describes observed evidence. It does not predict
    stock returns and does not produce trade instructions.
    """

    ordered = sorted(
        snapshots,
        key=lambda snapshot: snapshot.period_end,
    )

    if not ordered:
        return build_company_research_snapshot(
            symbol=symbol,
            as_of_date=as_of_date,
            financial_observations=[
                "No annual financial statements were available."
            ],
            risk_observations=[
                "Financial risk could not be assessed because "
                "historical financial data was unavailable."
            ],
        )

    current = ordered[-1]
    previous = (
        ordered[-2]
        if len(ordered) >= 2
        else None
    )

    observations: list[str] = []
    risk_observations: list[str] = []
    signals: list[IntelligenceSignal] = []

    npm = net_profit_margin(current)
    fcf = free_cash_flow_margin(current)
    cash_conversion = cash_conversion_ratio(current)
    debt_ratio = debt_to_revenue(current)
    receivables_ratio = receivables_to_revenue(current)

    observations.append(
        f"Net profit margin: {_fmt(npm)}%."
    )

    observations.append(
        f"Free cash flow margin: {_fmt(fcf)}%."
    )

    observations.append(
        f"Operating cash conversion: {_fmt(cash_conversion)}%."
    )

    observations.append(
        f"Debt-to-revenue: {_fmt(debt_ratio)}."
    )

    observations.append(
        f"Receivables-to-revenue: {_fmt(receivables_ratio)}%."
    )

    if previous is not None:
        growth = revenue_growth(
            previous,
            current,
        )

        observations.append(
            f"Year-over-year revenue growth: "
            f"{_fmt(growth)}%."
        )

        growth_direction = _direction(
            growth,
            positive=Decimal("10"),
            negative=Decimal("0"),
        )

        signals.append(
            IntelligenceSignal(
                code="REVENUE_GROWTH",
                title="Revenue growth",
                description=(
                    f"Revenue changed by {_fmt(growth)}% "
                    f"year over year."
                ),
                direction=growth_direction,
                materiality=3,
                confidence=Decimal("0.95"),
            )
        )

    if npm is not None:
        signals.append(
            IntelligenceSignal(
                code="PROFITABILITY",
                title="Profitability",
                description=(
                    f"Net profit margin is {_fmt(npm)}%."
                ),
                direction=_direction(npm),
                materiality=3,
                confidence=Decimal("0.95"),
            )
        )

    if fcf is not None:
        signals.append(
            IntelligenceSignal(
                code="FREE_CASH_FLOW",
                title="Free cash flow quality",
                description=(
                    f"Free cash flow margin is {_fmt(fcf)}%."
                ),
                direction=_direction(
                    fcf,
                    positive=Decimal("10"),
                    negative=Decimal("0"),
                ),
                materiality=3,
                confidence=Decimal("0.95"),
            )
        )

    if cash_conversion is not None:
        signals.append(
            IntelligenceSignal(
                code="CASH_CONVERSION",
                title="Cash conversion",
                description=(
                    f"Operating cash conversion is "
                    f"{_fmt(cash_conversion)}%."
                ),
                direction=_direction(
                    cash_conversion,
                    positive=Decimal("100"),
                    negative=Decimal("70"),
                ),
                materiality=3,
                confidence=Decimal("0.90"),
            )
        )

    if debt_ratio is not None:
        debt_direction = (
            IntelligenceDirection.POSITIVE
            if debt_ratio <= Decimal("0.10")
            else (
                IntelligenceDirection.NEGATIVE
                if debt_ratio >= Decimal("0.50")
                else IntelligenceDirection.NEUTRAL
            )
        )

        signals.append(
            IntelligenceSignal(
                code="LEVERAGE",
                title="Balance-sheet leverage",
                description=(
                    f"Debt-to-revenue is {_fmt(debt_ratio)}."
                ),
                direction=debt_direction,
                materiality=3,
                confidence=Decimal("0.90"),
            )
        )

    if receivables_ratio is not None:
        receivables_direction = (
            IntelligenceDirection.POSITIVE
            if receivables_ratio <= Decimal("15")
            else (
                IntelligenceDirection.NEGATIVE
                if receivables_ratio >= Decimal("35")
                else IntelligenceDirection.NEUTRAL
            )
        )

        signals.append(
            IntelligenceSignal(
                code="RECEIVABLES_QUALITY",
                title="Receivables quality",
                description=(
                    f"Receivables represent "
                    f"{_fmt(receivables_ratio)}% of revenue."
                ),
                direction=receivables_direction,
                materiality=3,
                confidence=Decimal("0.85"),
            )
        )

    if current.profit_cash_flow_divergence:
        risk_observations.append(
            "Reported net profit is positive while operating "
            "cash flow is negative; this divergence requires "
            "specific investigation."
        )

        signals.append(
            IntelligenceSignal(
                code="PROFIT_CASH_DIVERGENCE",
                title="Profit and cash-flow divergence",
                description=(
                    "Net profit is positive while operating "
                    "cash flow is negative."
                ),
                direction=IntelligenceDirection.NEGATIVE,
                materiality=5,
                confidence=Decimal("0.95"),
            )
        )

    anomalies = financial_risk_signals(
        ordered
    )

    for anomaly in anomalies:
        signals.append(
            _anomaly_signal(anomaly)
        )

        risk_observations.append(
            str(
                getattr(
                    anomaly,
                    "description",
                    "Financial anomaly detected.",
                )
            )
        )

    risk_score = financial_risk_score(
        ordered
    )

    if risk_score >= Decimal("75"):
        risk_observations.insert(
            0,
            f"Observed financial risk-quality score: "
            f"{risk_score:.2f}/100."
        )
    elif risk_score <= Decimal("40"):
        risk_observations.insert(
            0,
            f"Elevated observed financial risk. "
            f"Risk-quality score: {risk_score:.2f}/100."
        )
    else:
        risk_observations.insert(
            0,
            f"Observed financial risk-quality score: "
            f"{risk_score:.2f}/100."
        )

    return build_company_research_snapshot(
        symbol=symbol,
        as_of_date=as_of_date,
        signals=signals,
        financial_observations=observations,
        risk_observations=risk_observations,
    )
