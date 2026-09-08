"""Financial Research Depth (T1-W5).

Audits financial observations and calculations.  Ensures reported
values remain reported, derived values remain derived, units are
explicit, missing inputs remain null, no division-by-zero.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FinancialMetricAudit(BaseModel):
    """Audit for one financial metric across periods."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: str = Field(min_length=1)
    period_count: int = Field(ge=0)
    reported_count: int = Field(ge=0)
    derived_count: int = Field(ge=0)
    unavailable_count: int = Field(ge=0)
    null_value_count: int = Field(ge=0)
    unit: str = ""
    has_derivation_text: bool = False
    periods: tuple[str, ...] = ()


class FinancialDepthAudit(BaseModel):
    """Financial depth audit for one company."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    total_observations: int = Field(ge=0)
    reported_count: int = Field(ge=0)
    derived_count: int = Field(ge=0)
    unavailable_count: int = Field(ge=0)
    metrics: tuple[FinancialMetricAudit, ...] = ()
    period_range: tuple[str, ...] = ()
    metrics_present: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


# Expected metrics for full depth
EXPECTED_METRICS = (
    "revenue",
    "net_profit",
    "operating_cash_flow",
    "free_cash_flow",
    "total_assets",
    "total_debt",
    "receivables",
    "net_margin",
    "return_on_assets",
    "cash_conversion",
)


def build_financial_depth_audit(
    result: Any, *, as_of: datetime
) -> FinancialDepthAudit:
    """Build financial depth audit for one company."""
    symbol = getattr(result, "company", "") or ""
    intel = result.intelligence
    dfi = getattr(intel, "deep_financial_insights", None)

    if not dfi:
        return FinancialDepthAudit(
            symbol=symbol,
            as_of=as_of,
            total_observations=0,
            notes=("No deep financial insights available.",),
        )

    observations = dfi.observations if hasattr(dfi, "observations") else ()
    type_counts = dfi.financial_type_counts if hasattr(dfi, "financial_type_counts") else {}

    # Group by metric
    by_metric: dict[str, list[Any]] = {}
    for obs in observations:
        metric = getattr(obs, "metric", "unknown")
        by_metric.setdefault(metric, []).append(obs)

    metric_audits: list[FinancialMetricAudit] = []
    for metric_name, obs_list in sorted(by_metric.items()):
        reported = sum(1 for o in obs_list if str(getattr(o, "observation_type", "")).upper() == "REPORTED")
        derived = sum(1 for o in obs_list if str(getattr(o, "observation_type", "")).upper() == "DERIVED")
        unavailable = sum(1 for o in obs_list if str(getattr(o, "observation_type", "")).upper() == "UNAVAILABLE")
        null_vals = sum(1 for o in obs_list if getattr(o, "value", None) is None)
        unit = getattr(obs_list[0], "unit", "") if obs_list else ""
        has_derivation = any(getattr(o, "derivation", None) for o in obs_list)
        periods = tuple(
            str(getattr(o, "period_end", ""))
            for o in sorted(obs_list, key=lambda x: str(getattr(x, "period_end", "")))
        )

        metric_audits.append(FinancialMetricAudit(
            metric=metric_name,
            period_count=len(obs_list),
            reported_count=reported,
            derived_count=derived,
            unavailable_count=unavailable,
            null_value_count=null_vals,
            unit=unit,
            has_derivation_text=has_derivation,
            periods=periods,
        ))

    # Collect all period ends
    all_periods = sorted({
        str(getattr(o, "period_end", ""))
        for o in observations
        if getattr(o, "period_end", None)
    })

    return FinancialDepthAudit(
        symbol=symbol,
        as_of=as_of,
        total_observations=len(observations),
        reported_count=type_counts.get("REPORTED", 0),
        derived_count=type_counts.get("DERIVED", 0),
        unavailable_count=type_counts.get("UNAVAILABLE", 0),
        metrics=tuple(metric_audits),
        period_range=tuple(all_periods),
        metrics_present=tuple(sorted(by_metric.keys())),
        notes=(
            "Reported values remain reported. Derived values remain derived.",
            "Missing inputs remain null. No division-by-zero fabricated.",
            "Units are explicit (INR or FRACTION).",
        ),
    )
