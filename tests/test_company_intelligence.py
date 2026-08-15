from datetime import date
from decimal import Decimal

from src.data.company.evidence import Evidence
from src.data.company.events import CompanyEvent
from src.data.company.financials import FinancialSnapshot
from src.data.company.management import ManagementChange
from src.data.company.ownership import OwnershipSnapshot
from src.data.company.related_parties import RelatedPartyTransaction


def test_high_quality_evidence():
    evidence = Evidence(
        evidence_id="evidence-1",
        source_name="Example Exchange",
        source_type="REGULATORY",
        title="Corporate announcement",
        reliability_tier=1,
    )

    assert evidence.is_high_quality


def test_financial_snapshot_detects_profit_cash_divergence():
    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        revenue=Decimal("1000"),
        net_profit=Decimal("100"),
        operating_cash_flow=Decimal("-20"),
    )

    assert snapshot.profit_cash_flow_divergence


def test_management_change():
    change = ManagementChange(
        symbol="TEST",
        person_name="Example Person",
        role="Chief Financial Officer",
        change_type="RESIGNATION",
        effective_date=date(2026, 8, 1),
    )

    assert change.change_type == "RESIGNATION"


def test_ownership_snapshot():
    ownership = OwnershipSnapshot(
        symbol="TEST",
        period_end=date(2026, 6, 30),
        promoter_percentage=Decimal("52.5"),
        institutional_percentage=Decimal("21.0"),
        public_percentage=Decimal("26.5"),
    )

    assert ownership.promoter_percentage == Decimal("52.5")


def test_related_party_transaction():
    transaction = RelatedPartyTransaction(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        related_party_name="Example Holdings",
        transaction_type="SALE",
        amount=Decimal("15000000"),
    )

    assert transaction.amount == Decimal("15000000")


def test_company_event():
    event = CompanyEvent(
        symbol="TEST",
        event_date=date(2026, 8, 1),
        category="MANAGEMENT",
        title="CFO appointed",
        description="A new CFO was appointed.",
        direction="NEUTRAL",
        materiality=3,
    )

    assert event.materiality == 3
    assert event.direction == "NEUTRAL"
