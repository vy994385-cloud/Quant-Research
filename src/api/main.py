from datetime import date
from decimal import Decimal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.analysis.company_intelligence import (
    EvidenceReference,
    IntelligenceDirection,
    IntelligenceSignal,
    build_company_research_snapshot,
)
from src.analysis.financial_trends import FinancialTrend
from src.analysis.financial_trends_engine import summarize_trends
from src.analysis.research_scoring import calculate_research_score


app = FastAPI(
    title="Quant Research API",
    version="0.1.0",
    description=(
        "Research and company-intelligence API. "
        "This service provides descriptive analytical evidence "
        "and does not issue trading instructions."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "quant-research-api",
        "version": "0.1.0",
    }


@app.get("/api/research/demo")
def demo_research() -> dict:
    """
    Deterministic research payload used by the first UI.

    This endpoint intentionally uses synthetic data so the
    visual layer can be developed independently of external
    market-data providers.
    """

    trends = [
        FinancialTrend(
            metric="revenue",
            direction="INCREASING",
            observations=2,
            average_change=Decimal("850"),
            explanation=(
                "Revenue increased across the supplied "
                "reporting periods."
            ),
            change=Decimal("850"),
        ),
        FinancialTrend(
            metric="net_profit",
            direction="INCREASING",
            observations=2,
            average_change=Decimal("210"),
            explanation=(
                "Net profit increased across the supplied "
                "reporting periods."
            ),
            change=Decimal("210"),
        ),
        FinancialTrend(
            metric="operating_cash_flow",
            direction="INCREASING",
            observations=2,
            average_change=Decimal("175"),
            explanation=(
                "Operating cash flow increased across the "
                "supplied reporting periods."
            ),
            change=Decimal("175"),
        ),
        FinancialTrend(
            metric="total_debt",
            direction="DECREASING",
            observations=2,
            average_change=Decimal("-120"),
            explanation=(
                "Total debt decreased across the supplied "
                "reporting periods."
            ),
            change=Decimal("-120"),
        ),
        FinancialTrend(
            metric="receivables",
            direction="INCREASING",
            observations=2,
            average_change=Decimal("95"),
            explanation=(
                "Receivables increased across the supplied "
                "reporting periods."
            ),
            change=Decimal("95"),
        ),
    ]

    summaries = summarize_trends(trends)

    signals = [
        IntelligenceSignal(
            code="REVENUE_GROWTH",
            title="Revenue growth",
            description=(
                "Revenue shows a persistent increasing "
                "direction across the supplied periods."
            ),
            direction=IntelligenceDirection.POSITIVE,
            materiality=4,
            confidence=Decimal("0.91"),
        ),
        IntelligenceSignal(
            code="DEBT_REDUCTION",
            title="Debt reduction",
            description=(
                "Total debt has declined across the supplied "
                "reporting periods."
            ),
            direction=IntelligenceDirection.POSITIVE,
            materiality=4,
            confidence=Decimal("0.88"),
        ),
        IntelligenceSignal(
            code="RECEIVABLES_GROWTH",
            title="Receivables increasing",
            description=(
                "Receivables are increasing and should be "
                "monitored alongside revenue and cash flow."
            ),
            direction=IntelligenceDirection.NEGATIVE,
            materiality=3,
            confidence=Decimal("0.76"),
        ),
    ]

    evidence = [
        EvidenceReference(
            source_name="Research Dataset",
            source_type="ANALYTICAL",
            title="Synthetic company research dataset",
            published_date=date(2026, 8, 8),
            reliability_tier=3,
            reference="demo-company-001",
        )
    ]

    snapshot = build_company_research_snapshot(
        symbol="DEMO",
        company_name="Demo Industries",
        as_of_date=date(2026, 8, 8),
        signals=signals,
        financial_observations=[
            "Revenue: 8,450",
            "Net profit: 1,240",
            "Operating cash flow: 1,110",
            "Free cash flow: 920",
        ],
        ownership_observations=[
            "Promoter ownership: 51.2%",
            "Institutional ownership: 27.4%",
            "Public ownership: 21.4%",
        ],
        management_observations=[
            "No material management change detected.",
        ],
        event_observations=[
            "Quarterly financial results available.",
        ],
        market_observations=[
            "Price structure is currently constructive.",
            "Relative strength remains above baseline.",
        ],
        risk_observations=[
            "Receivables growth requires monitoring.",
        ],
        evidence=evidence,
    )

    score = calculate_research_score(
        fundamentals=Decimal("82"),
        financial_trends=Decimal("86"),
        cash_flow=Decimal("84"),
        balance_sheet=Decimal("81"),
        risk=Decimal("68"),
        management=Decimal("78"),
        market_behavior=Decimal("80"),
        evidence_quality=Decimal("88"),
    )

    return {
        "company": {
            "symbol": snapshot.symbol,
            "name": snapshot.company_name,
            "as_of": snapshot.as_of_date.isoformat(),
        },
        "research_score": {
            "total": str(score.total),
            "signal": score.signal,
            "confidence": str(score.confidence),
            "components": {
                "fundamentals": str(score.fundamentals),
                "financial_trends": str(score.financial_trends),
                "cash_flow": str(score.cash_flow),
                "balance_sheet": str(score.balance_sheet),
                "risk": str(score.risk),
                "management": str(score.management),
                "market_behavior": str(score.market_behavior),
                "evidence_quality": str(score.evidence_quality),
            },
        },
        "intelligence": {
            "direction": snapshot.direction.value,
            "signal_count": snapshot.signal_count,
            "material_signal_count": snapshot.material_signal_count,
            "positive_signal_count": snapshot.positive_signal_count,
            "negative_signal_count": snapshot.negative_signal_count,
            "signals": [
                {
                    "code": signal.code,
                    "title": signal.title,
                    "description": signal.description,
                    "direction": signal.direction.value,
                    "materiality": signal.materiality,
                    "confidence": str(signal.confidence),
                }
                for signal in snapshot.signals
            ],
        },
        "financial_trends": [
            {
                "metric": summary.metric,
                "direction": summary.direction,
                "observations": summary.observations,
                "average_change": str(summary.average_change),
                "positive_periods": summary.positive_periods,
                "negative_periods": summary.negative_periods,
                "stable_periods": summary.stable_periods,
                "consistency": str(summary.consistency),
                "explanation": summary.explanation,
            }
            for summary in summaries
        ],
        "observations": {
            "financial": snapshot.financial_observations,
            "ownership": snapshot.ownership_observations,
            "management": snapshot.management_observations,
            "events": snapshot.event_observations,
            "market": snapshot.market_observations,
            "risk": snapshot.risk_observations,
        },
        "evidence": [
            {
                "source_name": item.source_name,
                "source_type": item.source_type,
                "title": item.title,
                "published_date": (
                    item.published_date.isoformat()
                    if item.published_date
                    else None
                ),
                "reliability_tier": item.reliability_tier,
                "reference": item.reference,
            }
            for item in snapshot.evidence
        ],
        "is_trade_signal": snapshot.is_trade_signal,
    }