from datetime import date, datetime, timezone
from decimal import Decimal

from src.analysis.company_intelligence import CompanyResearchSnapshot
from src.analysis.future_intelligence import (
    FutureTechnologyArea,
    FutureTechnologySignal,
    InnovationEvidenceStrength,
    InnovationSignalDirection,
    build_future_technology_profile,
)
from src.data.company.financials import FinancialSnapshot
from src.research.features.financial_trends import FinancialTrendSummary
from src.research.intelligence import build_research_intelligence


AS_OF = datetime(2026, 8, 15, 12, tzinfo=timezone.utc)


def snapshots():
    return [
        FinancialSnapshot(
            symbol="TEST",
            period_end=date(2024, 3, 31),
            revenue=Decimal("100"),
            net_profit=Decimal("12"),
            operating_cash_flow=Decimal("14"),
            receivables=Decimal("10"),
            total_debt=Decimal("20"),
        ),
        FinancialSnapshot(
            symbol="TEST",
            period_end=date(2025, 3, 31),
            revenue=Decimal("110"),
            net_profit=Decimal("13"),
            operating_cash_flow=Decimal("15"),
            receivables=Decimal("45"),
            total_debt=Decimal("40"),
        ),
    ]


def test_financial_intelligence_contains_ratios_anomaly_and_lineage():
    intelligence = build_research_intelligence(
        symbol="TEST",
        as_of=AS_OF,
        financial_snapshots=snapshots(),
        trend_summaries=[
            FinancialTrendSummary(
                metric="revenue",
                direction="INCREASING",
                observations=2,
                average_change=Decimal("10"),
                positive_periods=1,
                negative_periods=0,
                stable_periods=0,
                consistency=Decimal("1"),
                explanation="Revenue increased.",
            ),
            FinancialTrendSummary(
                metric="total_debt",
                direction="INCREASING",
                observations=2,
                average_change=Decimal("20"),
                positive_periods=1,
                negative_periods=0,
                stable_periods=0,
                consistency=Decimal("1"),
                explanation="Debt increased.",
            ),
        ],
        provenance_ids=("financial-record-1",),
    )

    section = intelligence.financial_quality
    assert section.status.value == "MIXED"
    assert section.positive_evidence
    assert section.negative_evidence
    assert any("Cash conversion" in item.claim for item in section.observations)
    assert "financial-record-1" in section.provenance_ids


def test_future_technology_is_evidence_classified_and_customer_is_unknown():
    profile = build_future_technology_profile(
        "TEST",
        signals=[
            FutureTechnologySignal(
                code="AI_PRODUCT",
                title="Disclosed AI product",
                description="A source-backed AI product is disclosed.",
                technology_area=FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE,
                direction=InnovationSignalDirection.POSITIVE,
                materiality=4,
                confidence=Decimal("0.8"),
                evidence_strength=InnovationEvidenceStrength.VERIFIED,
                evidence_codes=["filing-1"],
            )
        ],
    )
    snapshot = CompanyResearchSnapshot(
        symbol="TEST",
        as_of_date=date(2026, 8, 10),
        future_technology_profile=profile,
    )
    intelligence = build_research_intelligence(
        symbol="TEST", as_of=AS_OF, company_snapshot=snapshot
    )

    assert intelligence.future_technology.status.value == "SUPPORTED"
    assert intelligence.future_technology.positive_evidence[0].source_ids == (
        "filing-1",
    )
    assert intelligence.customer_intelligence.status.value == "UNKNOWN"
    assert intelligence.customer_intelligence.unknown


def test_future_financial_snapshot_is_excluded_from_point_in_time_intelligence():
    future = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2027, 3, 31),
        revenue=Decimal("999"),
    )
    intelligence = build_research_intelligence(
        symbol="TEST", as_of=AS_OF, financial_snapshots=[future]
    )

    assert intelligence.financial_quality.status.value == "UNKNOWN"
    assert not intelligence.financial_quality.observations
