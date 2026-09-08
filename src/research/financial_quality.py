"""
Financial Research Quality — deterministic research observations.

Improves research usefulness around:
  revenue, profit, cash flow, free cash flow, assets, debt,
  receivables, margins, cash conversion, returns

Observations classified as REPORTED or DERIVED.
Missing inputs remain null. Division-by-zero remains null.
No fabricated interpolation.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ObservationOrigin(str, Enum):
    REPORTED = "REPORTED"
    DERIVED = "DERIVED"


class FinancialQualityObservation(BaseModel):
    """One deterministic financial research observation."""

    model_config = ConfigDict(extra="forbid")

    observation_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    category: str = Field(min_length=1)
    origin: ObservationOrigin

    value: Decimal | None = None
    unit: str = "INR"
    period_end: date | None = None
    period_type: str | None = None

    previous_value: Decimal | None = None
    delta: Decimal | None = None
    delta_pct: Decimal | None = None

    derivation: str | None = None
    derivation_inputs: tuple[str, ...] = ()

    available: bool = True
    null_reason: str | None = None

    as_of: datetime | None = None
    source_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def _require_aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return v


class FinancialQualityReport(BaseModel):
    """Complete financial research quality report for a company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    as_of: datetime
    observations: tuple[FinancialQualityObservation, ...] = ()
    observation_count: int = Field(ge=0)
    reported_count: int = Field(ge=0)
    derived_count: int = Field(ge=0)
    null_count: int = Field(ge=0)
    categories: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def _require_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        return v


def _safe_div(a: Decimal | None, b: Decimal | None) -> Decimal | None:
    if a is None or b is None or b == 0:
        return None
    try:
        result = a / b
        return result.quantize(Decimal("0.000001"))
    except (InvalidOperation, ArithmeticError):
        return None


def _safe_delta(curr: Decimal | None, prev: Decimal | None) -> Decimal | None:
    if curr is None or prev is None:
        return None
    return curr - prev


def _safe_delta_pct(curr: Decimal | None, prev: Decimal | None) -> Decimal | None:
    if curr is None or prev is None or prev == 0:
        return None
    try:
        result = (curr - prev) / abs(prev)
        return result.quantize(Decimal("0.000001"))
    except (InvalidOperation, ArithmeticError):
        return None


def _get_metric(period, name: str) -> Decimal | None:
    return period.metrics.get(name)


def build_financial_quality(
    *,
    symbol: str,
    as_of: datetime,
    financial_periods: tuple = (),
    evidence_items: tuple = (),
    provenance_ids: set[str] | None = None,
) -> FinancialQualityReport:
    """
    Build deterministic financial research quality observations
    from recorded financial periods.

    Observations are REPORTED when directly from source data,
    DERIVED when computed from reported values.
    """

    prov_ids = provenance_ids or set()
    observations: list[FinancialQualityObservation] = []
    obs_counter = 0

    # Sort periods by period_end for delta calculations
    sorted_periods = sorted(financial_periods, key=lambda p: p.period_end)

    for idx, period in enumerate(sorted_periods):
        pe = period.period_end
        pt = period.period_type.value if hasattr(period, "period_type") else None

        # --- REPORTED metrics ---
        reported_metrics = [
            ("revenue", "REVENUE", "Revenue"),
            ("net_profit", "NET_PROFIT", "Net Profit"),
            ("total_assets", "TOTAL_ASSETS", "Total Assets"),
            ("total_debt", "TOTAL_DEBT", "Total Debt"),
            ("cash_and_equivalents", "CASH", "Cash & Equivalents"),
            ("receivables", "RECEIVABLES", "Receivables"),
            ("operating_cash_flow", "OCF", "Operating Cash Flow"),
            ("capital_expenditure", "CAPEX", "Capital Expenditure"),
            ("free_cash_flow", "FCF", "Free Cash Flow"),
            ("shareholders_equity", "EQUITY", "Shareholders Equity"),
        ]

        prev = sorted_periods[idx - 1] if idx > 0 else None

        for metric_key, category, label in reported_metrics:
            value = _get_metric(period, metric_key)
            prev_value = _get_metric(prev, metric_key) if prev else None

            obs_counter += 1
            observations.append(
                FinancialQualityObservation(
                    observation_id=f"fqr-{symbol}-{pe}-{obs_counter}",
                    symbol=symbol,
                    metric=label,
                    category=category,
                    origin=ObservationOrigin.REPORTED,
                    value=value,
                    unit="INR",
                    period_end=pe,
                    period_type=pt,
                    previous_value=prev_value,
                    delta=_safe_delta(value, prev_value),
                    delta_pct=_safe_delta_pct(value, prev_value),
                    available=value is not None,
                    null_reason=None if value is not None else f"No {label} data for period {pe}",
                    as_of=as_of,
                    source_ids=(period.source_name,) if period.source_name else (),
                    provenance_ids=(period.provenance_id,) if period.provenance_id else (),
                )
            )

        # --- DERIVED metrics ---
        revenue = _get_metric(period, "revenue")
        net_profit = _get_metric(period, "net_profit")
        ocf = _get_metric(period, "operating_cash_flow")
        fcf = _get_metric(period, "free_cash_flow")
        total_assets = _get_metric(period, "total_assets")
        shareholders_equity = _get_metric(period, "shareholders_equity")

        derived_metrics = [
            ("net_profit_margin", "MARGIN", "Net Profit Margin",
             _safe_div(net_profit, revenue),
             "net_profit / revenue",
             ("net_profit", "revenue")),
            ("operating_cash_flow_margin", "MARGIN", "OCF Margin",
             _safe_div(ocf, revenue),
             "operating_cash_flow / revenue",
             ("operating_cash_flow", "revenue")),
            ("free_cash_flow_margin", "MARGIN", "FCF Margin",
             _safe_div(fcf, revenue),
             "free_cash_flow / revenue",
             ("free_cash_flow", "revenue")),
            ("cash_conversion", "CASH_CONVERSION", "Cash Conversion",
             _safe_div(ocf, net_profit),
             "operating_cash_flow / net_profit",
             ("operating_cash_flow", "net_profit")),
            ("return_on_assets", "RETURN", "Return on Assets",
             _safe_div(net_profit, total_assets),
             "net_profit / total_assets",
             ("net_profit", "total_assets")),
            ("return_on_equity", "RETURN", "Return on Equity",
             _safe_div(net_profit, shareholders_equity),
             "net_profit / shareholders_equity",
             ("net_profit", "shareholders_equity")),
        ]

        prev_derived = {}
        if prev:
            for dcat, dlabel in [("MARGIN", "net_profit_margin"), ("RETURN", "return_on_assets")]:
                pass

        for metric_key, category, label, value, derivation, inputs in derived_metrics:
            obs_counter += 1

            null_reason = None
            available = True
            if value is None:
                available = False
                missing_inputs = [i for i in inputs if _get_metric(period, i) is None]
                if missing_inputs:
                    null_reason = f"Missing inputs: {', '.join(missing_inputs)}"
                else:
                    null_reason = "Could not derive value"

            observations.append(
                FinancialQualityObservation(
                    observation_id=f"fqr-{symbol}-{pe}-{obs_counter}",
                    symbol=symbol,
                    metric=label,
                    category=category,
                    origin=ObservationOrigin.DERIVED,
                    value=value,
                    unit="FRACTION",
                    period_end=pe,
                    period_type=pt,
                    derivation=derivation,
                    derivation_inputs=inputs,
                    available=available,
                    null_reason=null_reason,
                    as_of=as_of,
                    source_ids=(period.source_name,) if period.source_name else (),
                    provenance_ids=(period.provenance_id,) if period.provenance_id else (),
                )
            )

    observations.sort(key=lambda o: (o.period_end or date.min, o.observation_id))

    reported_count = sum(1 for o in observations if o.origin == ObservationOrigin.REPORTED)
    derived_count = sum(1 for o in observations if o.origin == ObservationOrigin.DERIVED)
    null_count = sum(1 for o in observations if not o.available)
    categories = tuple(sorted({o.category for o in observations}))

    notes: list[str] = []
    if not observations:
        notes.append("No financial periods available for quality analysis.")
    if null_count:
        notes.append(f"{null_count} observation(s) are null due to missing inputs.")
    if not financial_periods:
        notes.append("No financial periods provided.")

    return FinancialQualityReport(
        symbol=symbol,
        as_of=as_of,
        observations=tuple(observations),
        observation_count=len(observations),
        reported_count=reported_count,
        derived_count=derived_count,
        null_count=null_count,
        categories=categories,
        notes=tuple(notes),
    )


__all__ = [
    "FinancialQualityObservation",
    "FinancialQualityReport",
    "ObservationOrigin",
    "build_financial_quality",
]
