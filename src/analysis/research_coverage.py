from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class ResearchComponentStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    MISSING = "MISSING"
    UNVERIFIED = "UNVERIFIED"
    STALE = "STALE"
    CONFLICTING = "CONFLICTING"


@dataclass(frozen=True)
class ResearchComponentCoverage:
    """
    Evidence state for one research component.

    Status describes evidence quality/availability.
    It must never be inferred from a numeric score alone.
    """

    component: str
    status: ResearchComponentStatus
    score_contribution: bool

    @property
    def is_usable(self) -> bool:
        return self.score_contribution

    @property
    def coverage_percentage(self) -> int:
        if self.status == ResearchComponentStatus.AVAILABLE:
            return 100

        if self.status == ResearchComponentStatus.PARTIAL:
            return 50

        return 0


@dataclass(frozen=True)
class ResearchCoverage:
    """
    Aggregate research-data coverage.

    Coverage is intentionally separate from the research score.
    """

    components: tuple[ResearchComponentCoverage, ...]

    @property
    def total_components(self) -> int:
        return len(self.components)

    @property
    def available_components(self) -> int:
        return sum(
            component.status
            == ResearchComponentStatus.AVAILABLE
            for component in self.components
        )

    @property
    def usable_components(self) -> int:
        return sum(
            component.is_usable
            for component in self.components
        )

    @property
    def coverage(self):
        from decimal import Decimal

        if not self.components:
            return Decimal("0")

        return (
            Decimal(self.usable_components)
            / Decimal(self.total_components)
            * Decimal("100")
        )

    @property
    def status(self) -> str:
        if not self.components:
            return "INSUFFICIENT"

        statuses = {
            component.status
            for component in self.components
        }

        if statuses == {
            ResearchComponentStatus.AVAILABLE
        }:
            return "COMPLETE"

        if self.usable_components > 0:
            return "PARTIAL"

        return "INSUFFICIENT"

    @property
    def missing_components(self) -> tuple[str, ...]:
        return tuple(
            component.component
            for component in self.components
            if not component.is_usable
        )

    @property
    def by_component(
        self,
    ) -> Mapping[str, ResearchComponentCoverage]:
        return {
            component.component: component
            for component in self.components
        }
