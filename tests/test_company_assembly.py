from datetime import date
from decimal import Decimal

from src.analysis.company_assembly import (
    assemble_company_intelligence,
)
from src.analysis.company_intelligence import (
    EvidenceReference,
    IntelligenceDirection,
)
from src.data.company.events import CompanyEvent
from src.data.company.financials import FinancialSnapshot
from src.data.company.management import ManagementChange
from src.data.company.ownership import OwnershipSnapshot
from src.data.company.related_parties import RelatedPartyTransaction


def test_empty_company_assembly_is_valid():

    snapshot = assemble_company_intelligence(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
    )

    assert snapshot.symbol == "TEST"
    assert snapshot.signal_count == 0
    assert snapshot.direction == IntelligenceDirection.NEUTRAL


def test_financial_data_is_assembled():

    snapshot = assemble_company_intelligence(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        financial_snapshots=[
            FinancialSnapshot(
                symbol="TEST",
                period_end=date(2026, 3, 31),
                revenue=Decimal("1000"),
                net_profit=Decimal("100"),
                operating_cash_flow=Decimal("-20"),
            )
        ],
    )

    assert snapshot.signal_count == 1
    assert (
        snapshot.direction
        == IntelligenceDirection.NEGATIVE
    )

    assert len(snapshot.financial_observations) == 3


def test_management_data_is_assembled():

    snapshot = assemble_company_intelligence(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        management_changes=[
            ManagementChange(
                symbol="TEST",
                person_name="Example Person",
                role="Chief Financial Officer",
                change_type="RESIGNATION",
                effective_date=date(2026, 8, 1),
            )
        ],
    )

    assert snapshot.signal_count == 1
    assert snapshot.negative_signal_count == 1
    assert len(snapshot.management_observations) == 1


def test_ownership_data_is_assembled():

    snapshot = assemble_company_intelligence(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        ownership_snapshots=[
            OwnershipSnapshot(
                symbol="TEST",
                period_end=date(2026, 6, 30),
                promoter_percentage=Decimal("20"),
                institutional_percentage=Decimal("30"),
                public_percentage=Decimal("50"),
            )
        ],
    )

    assert snapshot.signal_count == 1
    assert len(snapshot.ownership_observations) == 3


def test_related_party_data_is_assembled():

    snapshot = assemble_company_intelligence(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        related_party_transactions=[
            RelatedPartyTransaction(
                symbol="TEST",
                period_end=date(2026, 3, 31),
                related_party_name="Example Holdings",
                transaction_type="SALE",
                amount=Decimal("15000000"),
            )
        ],
    )

    assert snapshot.signal_count == 1
    assert snapshot.signals[0].code == (
        "RELATED_PARTY_TRANSACTION"
    )


def test_company_events_are_assembled():

    snapshot = assemble_company_intelligence(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        company_events=[
            CompanyEvent(
                symbol="TEST",
                event_date=date(2026, 8, 1),
                category="MANAGEMENT",
                title="CFO appointed",
                description="A new CFO was appointed.",
                direction="NEUTRAL",
                materiality=3,
            )
        ],
    )

    assert snapshot.signal_count == 1
    assert snapshot.signals[0].code == "EVENT_MANAGEMENT"
    assert len(snapshot.event_observations) == 1


def test_multiple_categories_are_combined():

    snapshot = assemble_company_intelligence(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        financial_snapshots=[
            FinancialSnapshot(
                symbol="TEST",
                period_end=date(2026, 3, 31),
                net_profit=Decimal("100"),
                operating_cash_flow=Decimal("-20"),
            )
        ],
        management_changes=[
            ManagementChange(
                symbol="TEST",
                person_name="Example Person",
                role="CFO",
                change_type="RESIGNATION",
                effective_date=date(2026, 8, 1),
            )
        ],
        company_events=[
            CompanyEvent(
                symbol="TEST",
                event_date=date(2026, 8, 2),
                category="CORPORATE",
                title="Major announcement",
                description="A major announcement.",
                direction="POSITIVE",
                materiality=4,
            )
        ],
    )

    assert snapshot.signal_count == 3
    assert snapshot.positive_signal_count == 1
    assert snapshot.negative_signal_count == 2
    assert snapshot.is_mixed


def test_duplicate_identical_signals_are_removed():

    financial = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        net_profit=Decimal("100"),
        operating_cash_flow=Decimal("-20"),
    )

    snapshot = assemble_company_intelligence(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        financial_snapshots=[financial, financial],
    )

    assert snapshot.signal_count == 1


def test_different_financial_periods_are_not_collapsed():

    first = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2025, 3, 31),
        net_profit=Decimal("100"),
        operating_cash_flow=Decimal("-20"),
    )

    second = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        net_profit=Decimal("150"),
        operating_cash_flow=Decimal("-30"),
    )

    snapshot = assemble_company_intelligence(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        financial_snapshots=[first, second],
    )

    assert snapshot.signal_count == 1


def test_evidence_is_preserved():

    evidence = EvidenceReference(
        source_name="Example Exchange",
        source_type="REGULATORY",
        title="Corporate filing",
        published_date=date(2026, 8, 1),
        reliability_tier=1,
        reference="filing-123",
    )

    snapshot = assemble_company_intelligence(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        evidence=[evidence],
    )

    assert len(snapshot.evidence) == 1
    assert snapshot.evidence[0].reference == "filing-123"


def test_assembly_does_not_create_trade_signal():

    snapshot = assemble_company_intelligence(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
    )

    assert snapshot.is_trade_signal is False
