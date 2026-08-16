"""
Deep financial information model and deterministic builder.

Produces a deep, point-in-time view of a company's reporting history:

- comparable series of reporting periods (same period type and
  consolidation scope are never mixed);
- per-metric observations labeled REPORTED / DERIVED / UNAVAILABLE;
- deterministic derived metrics (margins, cash conversion, return on
  assets, net debt) with an explicit `derivation` for every value so
  each number can be reproduced and audited.

This is descriptive research output. Nothing here is a prediction and
no figure is invented: UNAVAILABLE observations state honestly that a
figure is missing from the recorded evidence.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from src.research.company_intel.models import (
    DeepFinancialInsights,
    DeepFinancialSeries,
    DeepMetricObservation,
    FinancialIntelligence,
    FinancialPeriod,
)
from src.research.company_intel.semantics import (
    FinancialObservationType,
)

# Standard tracked metrics. A metric is surfaced as UNAVAILABLE for a
# period only when it is reported in at least one other period of the
# same series, so gaps in reporting become visible without noise.
_TRACKED_METRICS = (
    "revenue",
    "operating_profit",
    "net_profit",
    "operating_cash_flow",
    "free_cash_flow",
    "total_assets",
    "total_debt",
    "cash_and_equivalents",
    "receivables",
    "payables",
)

# Derived metrics computed deterministically from reported figures.
# Each entry is (metric name, required reported inputs, derivation
# template). The derivation template is rendered with the current
# period_id so the computation can be reproduced exactly.
_DERIVED_DEFINITIONS = (
    (
        "operating_margin",
        ("operating_profit", "revenue"),
        "operating_profit({period_id}) / revenue({period_id})",
    ),
    (
        "net_margin",
        ("net_profit", "revenue"),
        "net_profit({period_id}) / revenue({period_id})",
    ),
    (
        "cash_conversion",
        ("operating_cash_flow", "net_profit"),
        "operating_cash_flow({period_id}) / net_profit({period_id})",
    ),
    (
        "return_on_assets",
        ("net_profit", "total_assets"),
        "net_profit({period_id}) / total_assets({period_id})",
    ),
    (
        "net_debt",
        ("total_debt", "cash_and_equivalents"),
        "total_debt({period_id}) - cash_and_equivalents({period_id})",
    ),
)


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")


def _delta(
    value: Decimal | None,
    previous: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    if value is None or previous is None:
        return (None, None)

    change = value - previous

    if previous == 0:
        return (change, None)

    return (change, change / abs(previous))


def _derived_value(
    period: FinancialPeriod,
    inputs: Sequence[str],
    metric_name: str,
) -> Decimal | None:
    parts = [period.metrics.get(name) for name in inputs]

    if any(part is None for part in parts):
        return None

    if metric_name == "net_debt":
        return parts[0] - parts[1]

    return parts[0] / parts[1]


def _series_key(period: FinancialPeriod) -> tuple[str, str]:
    return (
        period.period_type.value,
        period.consolidation.value,
    )


def _build_series_observations(
    *,
    symbol: str,
    ordered: Sequence[FinancialPeriod],
) -> tuple[DeepFinancialSeries, list[DeepMetricObservation]]:
    period_type = ordered[0].period_type
    consolidation = ordered[0].consolidation

    series_id = (
        f"{symbol}:{period_type.value}:{consolidation.value}"
    )

    metric_names = tuple(
        sorted(
            {metric for period in ordered for metric in period.metrics}
        )
    )

    series = DeepFinancialSeries(
        series_id=series_id,
        symbol=symbol,
        period_type=period_type,
        consolidation=consolidation,
        period_count=len(ordered),
        period_ends=tuple(
            period.period_end for period in ordered
        ),
        metrics=metric_names,
    )

    reported_metrics = set(metric_names)
    observations: list[DeepMetricObservation] = []

    for metric in sorted(set(_TRACKED_METRICS) | reported_metrics):
        for index, period in enumerate(ordered):
            previous = ordered[index - 1] if index > 0 else None

            value = period.metrics.get(metric)
            previous_value = (
                previous.metrics.get(metric)
                if previous is not None
                else None
            )

            if value is None:
                # Surface a reporting gap only when the metric is
                # reported elsewhere in the same series.
                if metric in reported_metrics:
                    observations.append(
                        _observation(
                            symbol=symbol,
                            metric=metric,
                            period=period,
                            observation_type=(
                                FinancialObservationType.UNAVAILABLE
                            ),
                            value=None,
                            previous_value=previous_value,
                            delta=None,
                            delta_pct=None,
                            derivation=(
                                f"not reported for {period.period_id}"
                            ),
                        )
                    )
                continue

            change, change_pct = _delta(value, previous_value)

            observations.append(
                _observation(
                    symbol=symbol,
                    metric=metric,
                    period=period,
                    observation_type=(
                        FinancialObservationType.REPORTED
                    ),
                    value=value,
                    previous_value=previous_value,
                    delta=change,
                    delta_pct=change_pct,
                    derivation=(
                        f"reported value for {period.period_id}"
                        if previous is None
                        else (
                            f"reported value for {period.period_id} "
                            f"compared against {previous.period_id}"
                        )
                    ),
                )
            )

    for metric_name, inputs, formula in _DERIVED_DEFINITIONS:
        for index, period in enumerate(ordered):
            previous = ordered[index - 1] if index > 0 else None

            value = _derived_value(period, inputs, metric_name)
            previous_value = (
                _derived_value(previous, inputs, metric_name)
                if previous is not None
                else None
            )

            if value is None and previous_value is None:
                continue

            observation_type = (
                FinancialObservationType.DERIVED
                if value is not None
                else FinancialObservationType.UNAVAILABLE
            )

            change, change_pct = _delta(value, previous_value)

            observations.append(
                _observation(
                    symbol=symbol,
                    metric=metric_name,
                    period=period,
                    observation_type=observation_type,
                    value=value,
                    previous_value=previous_value,
                    delta=change,
                    delta_pct=change_pct,
                    derivation=(
                        formula.format(period_id=period.period_id)
                        if value is not None
                        else (
                            "not derivable: input figure missing for "
                            f"{period.period_id}"
                        )
                    ),
                )
            )

    return series, observations


def _observation(
    *,
    symbol: str,
    metric: str,
    period: FinancialPeriod,
    observation_type: FinancialObservationType,
    value: Decimal | None,
    previous_value: Decimal | None,
    delta: Decimal | None,
    delta_pct: Decimal | None,
    derivation: str,
) -> DeepMetricObservation:
    return DeepMetricObservation(
        observation_id=f"{period.period_id}:{metric}",
        symbol=symbol,
        metric=metric,
        period_id=period.period_id,
        period_end=period.period_end,
        period_type=period.period_type,
        consolidation=period.consolidation,
        observation_type=observation_type,
        value=value,
        previous_value=previous_value,
        delta=delta,
        delta_pct=delta_pct,
        derivation=derivation,
        published_at=period.published_at,
        available_at=period.available_at,
        provenance_id=period.provenance_id,
    )


def build_deep_financial_insights(
    financial_intelligence: FinancialIntelligence | None,
    *,
    as_of: datetime,
) -> DeepFinancialInsights | None:
    """
    Build the deep financial insights for a company at `as_of`.

    Returns None when no financial intelligence is available. Only
    periods knowable at `as_of` are included.
    """

    if financial_intelligence is None:
        return None

    _require_aware(as_of)

    symbol = financial_intelligence.symbol

    known = [
        period
        for period in financial_intelligence.periods
        if period.is_known_at(as_of)
    ]

    if not known:
        return DeepFinancialInsights(
            symbol=symbol,
            as_of=as_of,
            series=(),
            observations=(),
            comparability_notes=(
                "No reporting periods were knowable at as_of.",
            ),
            financial_type_counts={},
        )

    groups: dict[tuple[str, str], list[FinancialPeriod]] = {}

    for period in known:
        groups.setdefault(_series_key(period), []).append(period)

    series: list[DeepFinancialSeries] = []
    observations: list[DeepMetricObservation] = []

    for key, group in sorted(groups.items()):
        ordered = tuple(sorted(group, key=lambda p: p.period_end))

        series_entry, series_observations = _build_series_observations(
            symbol=symbol,
            ordered=ordered,
        )

        series.append(series_entry)
        observations.extend(series_observations)

    comparability_notes: list[str] = []

    if len(series) > 1:
        comparability_notes.append(
            "Reporting history spans multiple series (period type / "
            "consolidation scope). Each series is analyzed "
            "independently; figures across series must not be compared "
            "directly."
        )

    if any(
        entry.period_type.value == "QUARTERLY"
        for entry in series
    ) and any(
        entry.period_type.value == "ANNUAL"
        for entry in series
    ):
        comparability_notes.append(
            "Both quarterly and annual series are present. Quarterly "
            "figures are not comparable to annual figures."
        )

    financial_type_counts = dict(
        Counter(
            observation.observation_type.value
            for observation in observations
        )
    )

    return DeepFinancialInsights(
        symbol=symbol,
        as_of=as_of,
        series=tuple(series),
        observations=tuple(
            sorted(
                observations,
                key=lambda obs: (
                    obs.period_end,
                    obs.period_id,
                    obs.metric,
                ),
            )
        ),
        comparability_notes=tuple(comparability_notes),
        financial_type_counts=financial_type_counts,
    )


__all__ = [
    "build_deep_financial_insights",
]
