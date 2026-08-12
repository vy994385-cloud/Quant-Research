from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from src.data.company.events import CompanyEvent
from src.data.company.management import ManagementChange
from src.data.company.ownership import OwnershipSnapshot
from src.data.company.related_parties import RelatedPartyTransaction


class ManagementDataProvider(ABC):
    """
    Provider contract for normalized management changes.

    Providers retrieve facts only. They do not score or interpret
    the company.
    """

    @abstractmethod
    def get_management_changes(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[ManagementChange]:
        raise NotImplementedError


class OwnershipDataProvider(ABC):
    """
    Provider contract for normalized ownership snapshots.
    """

    @abstractmethod
    def get_ownership_snapshots(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[OwnershipSnapshot]:
        raise NotImplementedError


class RelatedPartyDataProvider(ABC):
    """
    Provider contract for normalized related-party transactions.
    """

    @abstractmethod
    def get_related_party_transactions(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[RelatedPartyTransaction]:
        raise NotImplementedError


class CompanyEventsDataProvider(ABC):
    """
    Provider contract for normalized company events.

    Events may later include filings, material announcements,
    management developments, regulatory events, acquisitions,
    major contracts, etc.
    """

    @abstractmethod
    def get_company_events(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> list[CompanyEvent]:
        raise NotImplementedError
