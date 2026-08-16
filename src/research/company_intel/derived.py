"""
Hidden / less-obvious information derived from recorded evidence.

This layer surfaces facts that are present in the recorded evidence
but not obvious at first glance:

- co-occurring claims on the same topic (e.g. a management statement
  alongside a reported order-intake decline) without ever resolving
  which side is correct;
- financial disclosure gaps (a standard metric reported in one
  comparable period but missing in another);
- reporting comparability notes from the deep financial model.

Every observation is deterministic, labeled from the semantic
vocabulary, and carries an explicit derivation. No inference is
upgraded to a fact and no claim is resolved automatically.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from src.research.company_intel.models import (
    CorporateIntelItem,
    DeepFinancialInsights,
    DerivedObservation,
    HiddenInformationInsights,
)
from src.research.company_intel.semantics import (
    SemanticCategory,
)

_REPORTED_MANAGEMENT = {
    SemanticCategory.MANAGEMENT_COMMENTARY,
    SemanticCategory.REPORTED_CLAIM,
    SemanticCategory.ALLEGATION,
}


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")


def _co_occurring_claims(
    items: tuple[CorporateIntelItem, ...],
    *,
    symbol: str,
    as_of: datetime,
) -> list[DerivedObservation]:
    by_topic: dict[str, list[CorporateIntelItem]] = defaultdict(list)

    for item in items:
        if item.topic:
            by_topic[item.topic].append(item)

    observations: list[DerivedObservation] = []

    for topic, group in sorted(by_topic.items()):
        categories = {
            item.semantic_category
            for item in group
            if item.semantic_category in _REPORTED_MANAGEMENT
        }

        if len(categories) < 2:
            continue

        ordered = sorted(
            group,
            key=lambda item: item.item_id,
        )

        category_names = ", ".join(
            sorted(category.value for category in categories)
        )

        observations.append(
            DerivedObservation(
                observation_id=(
                    f"{symbol}:derived:topic:{topic}"
                ),
                symbol=symbol,
                label=f"Contrasting evidence on {topic}",
                semantic_category=SemanticCategory.OBSERVATION,
                description=(
                    f"{len(ordered)} evidence items on '{topic}' are "
                    "knowable at as_of with differing semantic "
                    "categories: "
                    + "; ".join(
                        f"'{item.title}' ({item.semantic_category.value})"
                        for item in ordered
                    )
                    + ". Both sides are presented as evidence; the "
                    "system does not resolve which is correct."
                ),
                derivation=(
                    f"grouped by topic '{topic}' across "
                    f"{category_names}"
                ),
                source_ids=tuple(
                    sorted(
                        {item.source.source_name for item in ordered}
                    )
                ),
                provenance_ids=tuple(
                    sorted(
                        {
                            item.provenance_id
                            for item in ordered
                            if item.provenance_id
                        }
                    )
                ),
                related_item_ids=tuple(
                    item.item_id for item in ordered
                ),
                as_of=as_of,
            )
        )

    return observations


def _financial_gap_observations(
    insights: DeepFinancialInsights | None,
    *,
    symbol: str,
    as_of: datetime,
) -> list[DerivedObservation]:
    if insights is None:
        return []

    observations: list[DerivedObservation] = []

    for observation in insights.observations:
        if observation.observation_type.value != "UNAVAILABLE":
            continue

        if observation.previous_value is None:
            continue

        observations.append(
            DerivedObservation(
                observation_id=(
                    f"{symbol}:derived:gap:{observation.period_id}:"
                    f"{observation.metric}"
                ),
                symbol=symbol,
                label=(
                    f"{observation.metric} not reported for "
                    f"{observation.period_end.isoformat()}"
                ),
                semantic_category=SemanticCategory.OBSERVATION,
                description=(
                    f"{observation.metric} was reported in the prior "
                    "comparable period "
                    f"({observation.previous_value}) but is not "
                    "reported in the period ending "
                    f"{observation.period_end.isoformat()}."
                ),
                derivation=(
                    f"period {observation.period_id}: "
                    f"{observation.metric} unavailable"
                ),
                provenance_ids=(
                    (observation.provenance_id,)
                    if observation.provenance_id
                    else ()
                ),
                as_of=as_of,
            )
        )

    return observations


def _comparability_observations(
    insights: DeepFinancialInsights | None,
    *,
    symbol: str,
    as_of: datetime,
) -> list[DerivedObservation]:
    if insights is None:
        return []

    observations: list[DerivedObservation] = []

    for index, note in enumerate(insights.comparability_notes):
        observations.append(
            DerivedObservation(
                observation_id=(
                    f"{symbol}:derived:comparability:{index}"
                ),
                symbol=symbol,
                label="Reporting comparability",
                semantic_category=SemanticCategory.OBSERVATION,
                description=note,
                derivation=(
                    "derived from the reporting-period series in the "
                    "deep financial model"
                ),
                as_of=as_of,
            )
        )

    return observations


def build_hidden_information(
    items: tuple[CorporateIntelItem, ...],
    *,
    symbol: str,
    as_of: datetime,
    deep_financial_insights: DeepFinancialInsights | None,
) -> HiddenInformationInsights:
    """
    Build hidden / less-obvious information for a company at `as_of`.

    Only items knowable at `as_of` are considered; derived
    observations are always deterministic and non-editorializing.
    """

    _require_aware(as_of)

    observations = [
        *_co_occurring_claims(items, symbol=symbol, as_of=as_of),
        *_financial_gap_observations(
            deep_financial_insights,
            symbol=symbol,
            as_of=as_of,
        ),
        *_comparability_observations(
            deep_financial_insights,
            symbol=symbol,
            as_of=as_of,
        ),
    ]

    notes: list[str] = []

    if observations:
        notes.append(
            "Hidden information is derived deterministically from "
            "recorded evidence and is labeled by semantic category; "
            "no claim is resolved automatically."
        )

    return HiddenInformationInsights(
        symbol=symbol,
        as_of=as_of,
        observations=tuple(
            sorted(
                observations,
                key=lambda obs: obs.observation_id,
            )
        ),
        notes=tuple(notes),
    )


__all__ = [
    "build_hidden_information",
]
