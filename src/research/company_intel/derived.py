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
from decimal import Decimal, InvalidOperation

from src.research.company_intel.models import (
    CorporateIntelItem,
    DeepFinancialInsights,
    DerivedObservation,
    FinancialPeriod,
    HiddenInformationInsights,
)
from src.research.company_intel.semantics import (
    SemanticCategory,
)
from src.research.report.presentation import (
    format_inr_amount,
    format_ratio_as_percent,
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
                    f"({format_inr_amount(observation.previous_value) or observation.previous_value}) "
                    "but is not "
                    "reported in the period ending "
                    f"{observation.period_end.isoformat()}."
                ),
                derivation=(
                    f"{observation.metric} was unavailable for the "
                    "period ending "
                    f"{observation.period_end.isoformat()}."
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


def _safe_decimal(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    try:
        if value.is_nan() or value.is_infinite():
            return None
    except InvalidOperation:
        return None
    return value


def _pct_change(
    current: Decimal | None, previous: Decimal | None
) -> Decimal | None:
    cur = _safe_decimal(current)
    prev = _safe_decimal(previous)
    if cur is None or prev is None:
        return None
    if prev == 0:
        return None
    return (cur - prev) / abs(prev)


def _sorted_periods(
    periods: tuple[FinancialPeriod, ...],
    symbol: str,
) -> list[FinancialPeriod]:
    return sorted(
        [p for p in periods if p.symbol == symbol],
        key=lambda p: p.period_end,
    )


def _revenue_receivables_divergence(
    periods: tuple[FinancialPeriod, ...],
    *,
    symbol: str,
    as_of: datetime,
) -> list[DerivedObservation]:
    ordered = _sorted_periods(periods, symbol)
    if len(ordered) < 2:
        return []

    observations: list[DerivedObservation] = []

    for i in range(1, len(ordered)):
        prev, curr = ordered[i - 1], ordered[i]
        rev_change = _pct_change(
            curr.metrics.get("revenue"),
            prev.metrics.get("revenue"),
        )
        rec_change = _pct_change(
            curr.metrics.get("receivables"),
            prev.metrics.get("receivables"),
        )

        if rev_change is None or rec_change is None:
            continue

        if rev_change > 0 and rec_change > rev_change * 2:
            observations.append(
                DerivedObservation(
                    observation_id=(
                        f"{symbol}:derived:rev-rec-divergence:"
                        f"{prev.period_end}:{curr.period_end}"
                    ),
                    symbol=symbol,
                    label=(
                        f"Receivables growing faster than revenue "
                        f"({curr.period_end.isoformat()})"
                    ),
                    semantic_category=(
                        SemanticCategory.OBSERVATION
                    ),
                    description=(
                        f"Revenue changed {format_ratio_as_percent(rev_change)} "
                        f"but receivables changed "
                        f"{format_ratio_as_percent(rec_change)} between "
                        f"{prev.period_end.isoformat()} and "
                        f"{curr.period_end.isoformat()}. "
                        "Receivables grew more than twice as fast as "
                        "revenue."
                    ),
                    derivation=(
                        "Receivables percentage change exceeded "
                        "twice the revenue percentage change."
                    ),
                    as_of=as_of,
                    severity="WARN",
                )
            )

    return observations


def _profit_cashflow_divergence(
    periods: tuple[FinancialPeriod, ...],
    *,
    symbol: str,
    as_of: datetime,
) -> list[DerivedObservation]:
    ordered = _sorted_periods(periods, symbol)
    if len(ordered) < 2:
        return []

    observations: list[DerivedObservation] = []

    for i in range(1, len(ordered)):
        prev, curr = ordered[i - 1], ordered[i]
        profit_change = _pct_change(
            curr.metrics.get("net_profit"),
            prev.metrics.get("net_profit"),
        )
        ocf_change = _pct_change(
            curr.metrics.get("operating_cash_flow"),
            prev.metrics.get("operating_cash_flow"),
        )

        if profit_change is None or ocf_change is None:
            continue

        if profit_change > Decimal("0.05") and ocf_change < Decimal("-0.05"):
            observations.append(
                DerivedObservation(
                    observation_id=(
                        f"{symbol}:derived:profit-cf-divergence:"
                        f"{prev.period_end}:{curr.period_end}"
                    ),
                    symbol=symbol,
                    label=(
                        f"Profit up but cash flow down "
                        f"({curr.period_end.isoformat()})"
                    ),
                    semantic_category=(
                        SemanticCategory.OBSERVATION
                    ),
                    description=(
                        f"Net profit changed "
                        f"{format_ratio_as_percent(profit_change)} but "
                        f"operating cash flow changed "
                        f"{format_ratio_as_percent(ocf_change)} "
                        f"between {prev.period_end.isoformat()} and "
                        f"{curr.period_end.isoformat()}. Profit "
                        "improved while cash generation weakened."
                    ),
                    derivation=(
                        "Net profit rose more than 5% while "
                        "operating cash flow fell more than 5%."
                    ),
                    as_of=as_of,
                    severity="WARN",
                )
            )

    return observations


def _margin_acceleration(
    periods: tuple[FinancialPeriod, ...],
    *,
    symbol: str,
    as_of: datetime,
) -> list[DerivedObservation]:
    ordered = _sorted_periods(periods, symbol)
    if len(ordered) < 3:
        return []

    observations: list[DerivedObservation] = []

    margins: list[tuple[datetime, Decimal]] = []
    for p in ordered:
        rev = _safe_decimal(p.metrics.get("revenue"))
        op = _safe_decimal(p.metrics.get("operating_profit"))
        if rev is not None and op is not None and rev != 0:
            margins.append((p.period_end, op / rev))

    if len(margins) < 3:
        return []

    deltas = [
        margins[i][1] - margins[i - 1][1]
        for i in range(1, len(margins))
    ]

    if len(deltas) < 2:
        return []

    if deltas[-1] > 0 and deltas[-2] > 0 and deltas[-1] > deltas[-2]:
        observations.append(
            DerivedObservation(
                observation_id=(
                    f"{symbol}:derived:margin-acceleration:"
                    f"{margins[-2][0]}:{margins[-1][0]}"
                ),
                symbol=symbol,
                label=(
                    f"Operating margin accelerating upward "
                    f"({margins[-1][0].isoformat()})"
                ),
                semantic_category=(
                    SemanticCategory.OBSERVATION
                ),
                description=(
                    f"Operating margin improved by "
                    f"{format_ratio_as_percent(deltas[-2])} "
                    f"then by {format_ratio_as_percent(deltas[-1])} "
                    "over the last three periods, indicating "
                    "accelerating margin expansion."
                ),
                derivation=(
                    "Operating margin improved in two consecutive "
                    "periods and the latest improvement was larger "
                    "than the previous one."
                ),
                as_of=as_of,
                severity="INFO",
            )
        )

    if deltas[-1] < 0 and deltas[-2] < 0 and deltas[-1] < deltas[-2]:
        observations.append(
            DerivedObservation(
                observation_id=(
                    f"{symbol}:derived:margin-deceleration:"
                    f"{margins[-2][0]}:{margins[-1][0]}"
                ),
                symbol=symbol,
                label=(
                    f"Operating margin accelerating downward "
                    f"({margins[-1][0].isoformat()})"
                ),
                semantic_category=(
                    SemanticCategory.OBSERVATION
                ),
                description=(
                    f"Operating margin declined by "
                    f"{format_ratio_as_percent(abs(deltas[-2]))} "
                    f"then by {format_ratio_as_percent(abs(deltas[-1]))} "
                    "over the last three periods, indicating "
                    "accelerating margin contraction."
                ),
                derivation=(
                    "Operating margin declined in two consecutive "
                    "periods and the latest decline was larger "
                    "than the previous one."
                ),
                as_of=as_of,
                severity="WARN",
            )
        )

    return observations


def _debt_cash_changes(
    periods: tuple[FinancialPeriod, ...],
    *,
    symbol: str,
    as_of: datetime,
) -> list[DerivedObservation]:
    ordered = _sorted_periods(periods, symbol)
    if len(ordered) < 2:
        return []

    observations: list[DerivedObservation] = []

    for i in range(1, len(ordered)):
        prev, curr = ordered[i - 1], ordered[i]
        debt_change = _pct_change(
            curr.metrics.get("total_debt"),
            prev.metrics.get("total_debt"),
        )
        cash_change = _pct_change(
            curr.metrics.get("cash_and_equivalents"),
            prev.metrics.get("cash_and_equivalents"),
        )

        if debt_change is None or cash_change is None:
            continue

        if debt_change > Decimal("0.10") and cash_change > Decimal("0.10"):
            observations.append(
                DerivedObservation(
                    observation_id=(
                        f"{symbol}:derived:debt-cash-both-rise:"
                        f"{prev.period_end}:{curr.period_end}"
                    ),
                    symbol=symbol,
                    label=(
                        f"Both debt and cash rising "
                        f"({curr.period_end.isoformat()})"
                    ),
                    semantic_category=(
                        SemanticCategory.OBSERVATION
                    ),
                    description=(
                        f"Total debt changed "
                        f"{format_ratio_as_percent(debt_change)} and cash "
                        f"changed {format_ratio_as_percent(cash_change)} "
                        f"between {prev.period_end.isoformat()} and "
                        f"{curr.period_end.isoformat()}. Both debt "
                        "and cash increased simultaneously."
                    ),
                    derivation=(
                        "Total debt rose more than 10% and cash "
                        "rose more than 10% in the same period."
                    ),
                    as_of=as_of,
                    severity="INFO",
                )
            )

        if debt_change > Decimal("0.10") and (
            cash_change is not None and cash_change < Decimal("-0.05")
        ):
            observations.append(
                DerivedObservation(
                    observation_id=(
                        f"{symbol}:derived:debt-rise-cash-fall:"
                        f"{prev.period_end}:{curr.period_end}"
                    ),
                    symbol=symbol,
                    label=(
                        f"Debt rising while cash declining "
                        f"({curr.period_end.isoformat()})"
                    ),
                    semantic_category=(
                        SemanticCategory.OBSERVATION
                    ),
                    description=(
                        f"Total debt changed "
                        f"{format_ratio_as_percent(debt_change)} and cash "
                        f"changed {format_ratio_as_percent(cash_change)} "
                        f"between {prev.period_end.isoformat()} and "
                        f"{curr.period_end.isoformat()}. The company "
                        "is taking on more debt while its cash "
                        "balance is shrinking."
                    ),
                    derivation=(
                        "Total debt rose more than 10% while cash "
                        "fell more than 5% in the same period."
                    ),
                    as_of=as_of,
                    severity="WARN",
                )
            )

    return observations


def _working_capital_shifts(
    periods: tuple[FinancialPeriod, ...],
    *,
    symbol: str,
    as_of: datetime,
) -> list[DerivedObservation]:
    ordered = _sorted_periods(periods, symbol)
    if len(ordered) < 2:
        return []

    observations: list[DerivedObservation] = []

    for i in range(1, len(ordered)):
        prev, curr = ordered[i - 1], ordered[i]
        prev_rev = _safe_decimal(prev.metrics.get("receivables"))
        prev_pay = _safe_decimal(prev.metrics.get("payables"))
        curr_rev = _safe_decimal(curr.metrics.get("receivables"))
        curr_pay = _safe_decimal(curr.metrics.get("payables"))

        if any(v is None for v in (prev_rev, prev_pay, curr_rev, curr_pay)):
            continue

        prev_wc = prev_rev - prev_pay
        curr_wc = curr_rev - curr_pay

        if prev_wc == 0:
            continue

        wc_change = (curr_wc - prev_wc) / abs(prev_wc)

        if wc_change > Decimal("0.20"):
            observations.append(
                DerivedObservation(
                    observation_id=(
                        f"{symbol}:derived:wc-expansion:"
                        f"{prev.period_end}:{curr.period_end}"
                    ),
                    symbol=symbol,
                    label=(
                        f"Working capital expanded significantly "
                        f"({curr.period_end.isoformat()})"
                    ),
                    semantic_category=(
                        SemanticCategory.OBSERVATION
                    ),
                    description=(
                        f"Receivables minus payables changed by "
                        f"{format_ratio_as_percent(wc_change)} between "
                        f"{prev.period_end.isoformat()} and "
                        f"{curr.period_end.isoformat()}, indicating "
                        "a significant working capital shift."
                    ),
                    derivation=(
                        "Working capital, the difference between "
                        "receivables and payables, changed more "
                        "than 20%."
                    ),
                    as_of=as_of,
                    severity="INFO",
                )
            )

    return observations


def _trajectory_changes(
    periods: tuple[FinancialPeriod, ...],
    *,
    symbol: str,
    as_of: datetime,
) -> list[DerivedObservation]:
    ordered = _sorted_periods(periods, symbol)
    if len(ordered) < 3:
        return []

    observations: list[DerivedObservation] = []

    for metric, label in (
        ("revenue", "revenue"),
        ("net_profit", "net profit"),
    ):
        values = [
            _safe_decimal(p.metrics.get(metric))
            for p in ordered[-3:]
        ]

        if any(v is None for v in values):
            continue

        changes = [
            values[i] - values[i - 1]
            for i in range(1, len(values))
        ]

        if len(changes) < 2:
            continue

        was_declining = changes[0] < 0
        now_rising = changes[1] > 0

        if was_declining and now_rising:
            observations.append(
                DerivedObservation(
                    observation_id=(
                        f"{symbol}:derived:trajectory-reversal:"
                        f"{metric}:{ordered[-3].period_end}:"
                        f"{ordered[-1].period_end}"
                    ),
                    symbol=symbol,
                    label=(
                        f"{label.capitalize()} trajectory reversed "
                        f"to growth "
                        f"({ordered[-1].period_end.isoformat()})"
                    ),
                    semantic_category=(
                        SemanticCategory.OBSERVATION
                    ),
                    description=(
                        f"{label.capitalize()} declined by "
                        f"{format_inr_amount(abs(changes[0])) or abs(changes[0])} "
                        f"then increased by "
                        f"{format_inr_amount(changes[1]) or changes[1]} over "
                        "the last three periods, "
                        "indicating a trajectory reversal."
                    ),
                    derivation=(
                        f"{label.capitalize()} declined and then "
                        "increased across three consecutive periods."
                    ),
                    as_of=as_of,
                    severity="INFO",
                )
            )

        was_rising = changes[0] > 0
        now_declining = changes[1] < 0

        if was_rising and now_declining:
            observations.append(
                DerivedObservation(
                    observation_id=(
                        f"{symbol}:derived:trajectory-reversal:"
                        f"{metric}:{ordered[-3].period_end}:"
                        f"{ordered[-1].period_end}"
                    ),
                    symbol=symbol,
                    label=(
                        f"{label.capitalize()} trajectory reversed "
                        f"to decline "
                        f"({ordered[-1].period_end.isoformat()})"
                    ),
                    semantic_category=(
                        SemanticCategory.OBSERVATION
                    ),
                    description=(
                        f"{label.capitalize()} increased by "
                        f"{format_inr_amount(changes[0]) or changes[0]} "
                        f"then declined by "
                        f"{format_inr_amount(abs(changes[1])) or abs(changes[1])} "
                        "over the last three "
                        "periods, indicating a trajectory reversal."
                    ),
                    derivation=(
                        f"{label.capitalize()} increased and then "
                        "declined across three consecutive periods."
                    ),
                    as_of=as_of,
                    severity="WARN",
                )
            )

    return observations


def build_hidden_information(
    items: tuple[CorporateIntelItem, ...],
    *,
    symbol: str,
    as_of: datetime,
    deep_financial_insights: DeepFinancialInsights | None,
    financial_periods: tuple[FinancialPeriod, ...] = (),
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
        *_revenue_receivables_divergence(
            financial_periods,
            symbol=symbol,
            as_of=as_of,
        ),
        *_profit_cashflow_divergence(
            financial_periods,
            symbol=symbol,
            as_of=as_of,
        ),
        *_margin_acceleration(
            financial_periods,
            symbol=symbol,
            as_of=as_of,
        ),
        *_debt_cash_changes(
            financial_periods,
            symbol=symbol,
            as_of=as_of,
        ),
        *_working_capital_shifts(
            financial_periods,
            symbol=symbol,
            as_of=as_of,
        ),
        *_trajectory_changes(
            financial_periods,
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
