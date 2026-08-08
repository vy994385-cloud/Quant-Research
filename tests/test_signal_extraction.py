from datetime import date
from decimal import Decimal

from src.analysis.company_intelligence import (
    EvidenceReference,
    IntelligenceDirection,
)
from src.analysis.signal_extraction import (
    attach_evidence,
    event_signal,
    financial_signals,
    management_signals,
    ownership_signals,
    related_party_signals,
)
from src.data.company.events import CompanyEvent
from src.data.company.financials import FinancialSnapshot
from src.data.company.management import ManagementChange
from src.data.company.ownership import OwnershipSnapshot
from src.data.company.related_parties import RelatedPartyTransaction


def test_financial_divergence_creates_negative_signal():

    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        net_profit=Decimal("100"),
        operating_cash_flow=Decimal("-20"),
    )

    signals = financial_signals(snapshot)

    assert len(signals) == 1
    assert signals[0].code == "PROFIT_CASH_FLOW_DIVERGENCE"
    assert signals[0].direction == IntelligenceDirection.NEGATIVE
    assert signals[0].materiality == 4


def test_normal_financials_create_no_divergence_signal():

    snapshot = FinancialSnapshot(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        net_profit=Decimal("100"),
        operating_cash_flow=Decimal("80"),
    )

    assert financial_signals(snapshot) == []


def test_management_resignation_creates_negative_signal():

    change = ManagementChange(
        symbol="TEST",
        person_name="Example Person",
        role="Chief Financial Officer",
        change_type="RESIGNATION",
        effective_date=date(2026, 8, 1),
    )

    signals = management_signals(change)

    assert len(signals) == 1
    assert signals[0].direction == IntelligenceDirection.NEGATIVE
    assert signals[0].materiality == 4


def test_management_appointment_is_neutral():

    change = ManagementChange(
        symbol="TEST",
        person_name="Example Person",
        role="Chief Financial Officer",
        change_type="APPOINTMENT",
        effective_date=date(2026, 8, 1),
    )

    signals = management_signals(change)

    assert len(signals) == 1
    assert signals[0].direction == IntelligenceDirection.NEUTRAL


def test_low_promoter_ownership_is_screening_signal():

    snapshot = OwnershipSnapshot(
        symbol="TEST",
        period_end=date(2026, 6, 30),
        promoter_percentage=Decimal("20"),
        institutional_percentage=Decimal("30"),
        public_percentage=Decimal("50"),
    )

    signals = ownership_signals(snapshot)

    assert len(signals) == 1
    assert signals[0].code == "LOW_PROMOTER_OWNERSHIP"
    assert signals[0].direction == IntelligenceDirection.NEUTRAL


def test_normal_promoter_ownership_creates_no_signal():

    snapshot = OwnershipSnapshot(
        symbol="TEST",
        period_end=date(2026, 6, 30),
        promoter_percentage=Decimal("52"),
        institutional_percentage=Decimal("20"),
        public_percentage=Decimal("28"),
    )

    assert ownership_signals(snapshot) == []


def test_related_party_transaction_creates_signal():

    transaction = RelatedPartyTransaction(
        symbol="TEST",
        period_end=date(2026, 3, 31),
        related_party_name="Example Holdings",
        transaction_type="SALE",
        amount=Decimal("15000000"),
    )

    signals = related_party_signals(transaction)

    assert len(signals) == 1
    assert signals[0].code == "RELATED_PARTY_TRANSACTION"
    assert signals[0].direction == IntelligenceDirection.NEUTRAL
    assert signals[0].materiality == 3


def test_company_event_preserves_direction_and_materiality():

    event = CompanyEvent(
        symbol="TEST",
        event_date=date(2026, 8, 1),
        category="MANAGEMENT",
        title="CFO appointed",
        description="A new CFO was appointed.",
        direction="NEUTRAL",
        materiality=3,
    )

    signal = event_signal(event)

    assert signal.code == "EVENT_MANAGEMENT"
    assert signal.direction == IntelligenceDirection.NEUTRAL
    assert signal.materiality == 3


def test_evidence_can_be_attached_without_losing_signal():

    signal = event_signal(
        CompanyEvent(
            symbol="TEST",
            event_date=date(2026, 8, 1),
            category="CORPORATE",
            title="Corporate announcement",
            description="A corporate announcement was published.",
            direction="POSITIVE",
            materiality=4,
        )
    )

    evidence = EvidenceReference(
        source_name="Example Exchange",
        source_type="REGULATORY",
        title="Corporate announcement",
        published_date=date(2026, 8, 1),
        reliability_tier=1,
        reference="example-ref",
    )

    enriched = attach_evidence(signal, evidence)

    assert enriched.code == signal.code
    assert enriched.direction == signal.direction
    assert enriched.materiality == signal.materiality
    assert len(enriched.evidence) == 1
    assert enriched.evidence[0].reliability_tier == 1
