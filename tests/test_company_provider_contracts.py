from datetime import date
from decimal import Decimal

import pytest

from src.data.company.events import CompanyEvent
from src.data.company.management import ManagementChange
from src.data.company.ownership import OwnershipSnapshot
from src.data.company.related_parties import RelatedPartyTransaction
from src.data.providers.company import (
    CompanyEventsDataProvider,
    ManagementDataProvider,
    OwnershipDataProvider,
    RelatedPartyDataProvider,
)


class FakeManagementProvider(ManagementDataProvider):
    def get_management_changes(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[ManagementChange]:
        return [
            ManagementChange(
                symbol=symbol,
                person_name="Test Person",
                role="CEO",
                change_type="APPOINTMENT",
                effective_date=date(2026, 1, 1),
            )
        ]


class FakeOwnershipProvider(OwnershipDataProvider):
    def get_ownership_snapshots(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[OwnershipSnapshot]:
        return [
            OwnershipSnapshot(
                symbol=symbol,
                period_end=date(2026, 3, 31),
                promoter_percentage=Decimal("45"),
                institutional_percentage=Decimal("30"),
                public_percentage=Decimal("25"),
            )
        ]


class FakeRelatedPartyProvider(RelatedPartyDataProvider):
    def get_related_party_transactions(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[RelatedPartyTransaction]:
        return [
            RelatedPartyTransaction(
                symbol=symbol,
                period_end=date(2026, 3, 31),
                related_party_name="Test Related Party",
                transaction_type="SALE",
                amount=Decimal("100000"),
            )
        ]


class FakeCompanyEventsProvider(CompanyEventsDataProvider):
    def get_company_events(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[CompanyEvent]:
        return [
            CompanyEvent(
                symbol=symbol,
                event_date=date(2026, 4, 1),
                category="CONTRACT",
                title="Major contract announced",
                description="Test company announced a major contract.",
                direction="POSITIVE",
                materiality=4,
            )
        ]


def test_management_provider_contract():
    provider = FakeManagementProvider()

    result = provider.get_management_changes(
        "TEST",
        date(2026, 1, 1),
        date(2026, 12, 31),
    )

    assert len(result) == 1
    assert result[0].symbol == "TEST"


def test_ownership_provider_contract():
    provider = FakeOwnershipProvider()

    result = provider.get_ownership_snapshots(
        "TEST",
        date(2026, 1, 1),
        date(2026, 12, 31),
    )

    assert len(result) == 1
    assert result[0].promoter_percentage == Decimal("45")


def test_related_party_provider_contract():
    provider = FakeRelatedPartyProvider()

    result = provider.get_related_party_transactions(
        "TEST",
        date(2026, 1, 1),
        date(2026, 12, 31),
    )

    assert len(result) == 1
    assert result[0].amount == Decimal("100000")


def test_company_events_provider_contract():
    provider = FakeCompanyEventsProvider()

    result = provider.get_company_events(
        "TEST",
        date(2026, 1, 1),
        date(2026, 12, 31),
    )

    assert len(result) == 1
    assert result[0].materiality == 4


def test_provider_contracts_are_abstract():
    with pytest.raises(TypeError):
        ManagementDataProvider()

    with pytest.raises(TypeError):
        OwnershipDataProvider()

    with pytest.raises(TypeError):
        RelatedPartyDataProvider()

    with pytest.raises(TypeError):
        CompanyEventsDataProvider()
