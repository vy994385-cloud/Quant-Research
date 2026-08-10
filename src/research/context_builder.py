from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from src.research.context import ResearchContext
from src.research.provenance import DataProvenance, is_known_at


@dataclass(frozen=True)
class ContextObservation:
    """
    One research observation together with the provenance required
    to decide whether it was knowable at a historical timestamp.
    """

    value: Any
    provenance: DataProvenance
    domain: str
    observation_id: str = ""

    def __post_init__(self) -> None:
        domain = self.domain.strip().lower()

        if not domain:
            raise ValueError("domain cannot be empty")

        object.__setattr__(self, "domain", domain)

        if self.observation_id is not None:
            object.__setattr__(
                self,
                "observation_id",
                self.observation_id.strip(),
            )


@dataclass(frozen=True)
class ContextBuildResult:
    """
    Auditable result of point-in-time context construction.

    accepted observations are the only observations exposed to
    downstream research.

    rejected observations remain measurable so the research system
    can explain why data disappeared from a historical snapshot.
    """

    context: ResearchContext
    accepted_count: int
    rejected_count: int
    rejected_missing_availability: int
    rejected_not_known_at: int

    @property
    def total_seen(self) -> int:
        return self.accepted_count + self.rejected_count


class ResearchContextBuilder:
    """
    Deterministic point-in-time research context assembler.

    This is a hard boundary between external/raw data and strategy
    research.

    An observation is eligible only when:

        provenance.available_at <= as_of

    Missing available_at is rejected because treating unknown
    availability as known would introduce look-ahead bias.
    """

    _SUPPORTED_DOMAINS = {
        "market",
        "fundamentals",
        "macro",
        "events",
        "corporate_actions",
    }

    def build(
        self,
        *,
        symbol: str,
        as_of: datetime,
        observations: Iterable[ContextObservation],
    ) -> ContextBuildResult:
        symbol = symbol.strip()

        if not symbol:
            raise ValueError("symbol cannot be empty")

        if as_of.tzinfo is None:
            raise ValueError(
                "as_of must be timezone-aware"
            )

        accepted: dict[str, list[Any]] = {
            "market": [],
            "fundamentals": [],
            "macro": [],
            "events": [],
            "corporate_actions": [],
        }

        accepted_sources: set[str] = set()

        accepted_count = 0
        rejected_count = 0
        rejected_missing_availability = 0
        rejected_not_known_at = 0

        materialized = list(observations)

        # Deterministic ordering prevents upstream iteration order
        # from changing a research snapshot.
        materialized.sort(
            key=lambda item: (
                item.domain,
                item.observation_id,
                item.provenance.record_id or "",
                item.provenance.source,
            )
        )

        for observation in materialized:
            if observation.domain not in self._SUPPORTED_DOMAINS:
                raise ValueError(
                    f"unsupported research domain: "
                    f"{observation.domain}"
                )

            provenance = observation.provenance

            if provenance.available_at is None:
                rejected_count += 1
                rejected_missing_availability += 1
                continue

            if not is_known_at(provenance, as_of):
                rejected_count += 1
                rejected_not_known_at += 1
                continue

            accepted[observation.domain].append(
                observation.value
            )

            accepted_sources.add(
                provenance.source.strip().lower()
            )

            accepted_count += 1

        context = ResearchContext(
            symbol=symbol,
            timestamp=as_of,
            market=tuple(accepted["market"]),
            fundamentals=tuple(
                accepted["fundamentals"]
            ),
            macro=tuple(accepted["macro"]),
            events=tuple(accepted["events"]),
            corporate_actions=tuple(
                accepted["corporate_actions"]
            ),
            source_ids=tuple(sorted(accepted_sources)),
        )

        return ContextBuildResult(
            context=context,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            rejected_missing_availability=(
                rejected_missing_availability
            ),
            rejected_not_known_at=rejected_not_known_at,
        )
