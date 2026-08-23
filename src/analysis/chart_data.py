"""
Chart-ready data layer for financial and research metrics.

Builds structured time-series data that the frontend can render
directly without reconstructing financial logic.

Every chart data point retains:
- period label (period_end ISO date)
- value (Decimal or None)
- unit (ABSOLUTE, PERCENTAGE, RATIO, CURRENCY)
- currency ("INR" for CURRENCY-unit series; values are absolute
  rupees in their raw reported scale — canonical crore rendering is
  a downstream display concern, never a re-scaling of these values)
- source/provenance
- as_of availability timestamp
- missing-data handling (null values preserved, no interpolation)

Deterministic rounding: derived percentage/ratio points are quantized
to four decimal places with ROUND_HALF_UP. This module never invents
values or interpolates missing data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any

from src.data.company.financials import FinancialSnapshot


class ChartUnit(str, Enum):
    """Unit of measurement for chart data points."""

    ABSOLUTE = "ABSOLUTE"
    PERCENTAGE = "PERCENTAGE"
    RATIO = "RATIO"
    CURRENCY = "CURRENCY"
    COUNT = "COUNT"


class ChartMetricCategory(str, Enum):
    """High-level category for organizing chart groups."""

    INCOME = "INCOME"
    CASH_FLOW = "CASH_FLOW"
    BALANCE_SHEET = "BALANCE_SHEET"
    RATIOS = "RATIOS"
    GROWTH = "GROWTH"
    EFFICIENCY = "EFFICIENCY"


@dataclass(frozen=True)
class ChartDataPoint:
    """A single data point in a chart time series."""

    period_end: str
    value: str | None
    available: bool
    as_of: str | None = None
    source: str | None = None


@dataclass(frozen=True)
class ChartSeries:
    """
    A named time series of data points for charting.

    The frontend receives this directly and renders it without
    any financial calculation. `currency` declares the currency
    for CURRENCY-unit series ("INR"); it is None for ratios and
    percentages, which carry no currency.
    """

    metric: str
    label: str
    unit: ChartUnit
    category: ChartMetricCategory
    data_points: tuple[ChartDataPoint, ...] = ()
    period_count: int = 0
    available_count: int = 0
    missing_count: int = 0
    source: str | None = None
    currency: str | None = None


@dataclass(frozen=True)
class ChartDataSet:
    """
    Complete chart-ready data set for a company.

    Contains multiple series organized by category, ready for
    the frontend to render as charts.
    """

    symbol: str
    as_of: str
    series: tuple[ChartSeries, ...] = ()
    categories: tuple[ChartMetricCategory, ...] = ()
    total_metrics: int = 0
    total_data_points: int = 0
    notes: tuple[str, ...] = ()


# ── Metric definitions ────────────────────────────────────────────


_CHART_METRICS: tuple[
    tuple[str, str, ChartUnit, ChartMetricCategory, str | None],
    ...] = (
    # Income statement
    (
        "revenue",
        "Revenue",
        ChartUnit.CURRENCY,
        ChartMetricCategory.INCOME,
        "net_profit",
    ),
    (
        "operating_profit",
        "Operating Profit",
        ChartUnit.CURRENCY,
        ChartMetricCategory.INCOME,
        None,
    ),
    (
        "net_profit",
        "Net Profit",
        ChartUnit.CURRENCY,
        ChartMetricCategory.INCOME,
        None,
    ),
    # Cash flow
    (
        "operating_cash_flow",
        "Operating Cash Flow",
        ChartUnit.CURRENCY,
        ChartMetricCategory.CASH_FLOW,
        None,
    ),
    (
        "free_cash_flow",
        "Free Cash Flow",
        ChartUnit.CURRENCY,
        ChartMetricCategory.CASH_FLOW,
        None,
    ),
    # Balance sheet
    (
        "total_debt",
        "Total Debt",
        ChartUnit.CURRENCY,
        ChartMetricCategory.BALANCE_SHEET,
        None,
    ),
    (
        "cash_and_equivalents",
        "Cash & Equivalents",
        ChartUnit.CURRENCY,
        ChartMetricCategory.BALANCE_SHEET,
        None,
    ),
    (
        "receivables",
        "Receivables",
        ChartUnit.CURRENCY,
        ChartMetricCategory.BALANCE_SHEET,
        None,
    ),
    (
        "payables",
        "Payables",
        ChartUnit.CURRENCY,
        ChartMetricCategory.BALANCE_SHEET,
        None,
    ),
    (
        "total_equity",
        "Total Equity",
        ChartUnit.CURRENCY,
        ChartMetricCategory.BALANCE_SHEET,
        None,
    ),
    (
        "total_assets",
        "Total Assets",
        ChartUnit.CURRENCY,
        ChartMetricCategory.BALANCE_SHEET,
        None,
    ),
)


def _decimal_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


# Deterministic presentation rounding for derived percentage/ratio
# points (ROUND_HALF_UP, matching src.research.report.presentation).
_RATIO_QUANTUM = Decimal("0.0001")


def _ratio_str(value: Decimal | None) -> str | None:
    """
    Render a derived ratio/percentage for presentation.

    Division produces full-precision Decimals (e.g. margins with 30+
    digits); chart points are display values and are quantized to a
    deterministic four-decimal-place representation.
    """

    if value is None:
        return None
    return str(
        value.quantize(_RATIO_QUANTUM, rounding=ROUND_HALF_UP)
    )


def _snapshot_as_of(snapshot: FinancialSnapshot) -> str | None:
    if snapshot.available_at is not None:
        return snapshot.available_at.isoformat()
    if snapshot.published_at is not None:
        return snapshot.published_at.isoformat()
    return None


def _build_series(
    snapshots: list[FinancialSnapshot],
    metric: str,
    label: str,
    unit: ChartUnit,
    category: ChartMetricCategory,
    symbol: str,
) -> ChartSeries:
    """Build a single chart series from financial snapshots."""

    points: list[ChartDataPoint] = []
    available_count = 0
    source: str | None = None

    for snapshot in snapshots:
        value = getattr(snapshot, metric, None)
        available = value is not None
        if available:
            available_count += 1

        if source is None and snapshot.source_name:
            source = snapshot.source_name

        points.append(
            ChartDataPoint(
                period_end=snapshot.period_end.isoformat(),
                value=_decimal_str(value),
                available=available,
                as_of=_snapshot_as_of(snapshot),
                source=snapshot.source_name,
            )
        )

    return ChartSeries(
        metric=metric,
        label=label,
        unit=unit,
        category=category,
        data_points=tuple(points),
        period_count=len(points),
        available_count=available_count,
        missing_count=len(points) - available_count,
        source=source,
        currency="INR" if unit == ChartUnit.CURRENCY else None,
    )


def _build_calculated_series(
    snapshots: list[FinancialSnapshot],
    metric: str,
    label: str,
    unit: ChartUnit,
    category: ChartMetricCategory,
    calc_fn,
) -> ChartSeries:
    """Build a calculated (derived) chart series."""

    points: list[ChartDataPoint] = []
    available_count = 0

    for snapshot in snapshots:
        value = calc_fn(snapshot)
        available = value is not None
        if available:
            available_count += 1

        points.append(
            ChartDataPoint(
                period_end=snapshot.period_end.isoformat(),
                value=_ratio_str(value),
                available=available,
                as_of=_snapshot_as_of(snapshot),
                source=snapshot.source_name,
            )
        )

    return ChartSeries(
        metric=metric,
        label=label,
        unit=unit,
        category=category,
        data_points=tuple(points),
        period_count=len(points),
        available_count=available_count,
        missing_count=len(points) - available_count,
    )


def _net_profit_margin(s: FinancialSnapshot):
    if s.revenue is None or s.net_profit is None or s.revenue == 0:
        return None
    return (s.net_profit / s.revenue) * 100


def _operating_margin(s: FinancialSnapshot):
    if s.revenue is None or s.operating_profit is None or s.revenue == 0:
        return None
    return (s.operating_profit / s.revenue) * 100


def _ocf_margin(s: FinancialSnapshot):
    if s.revenue is None or s.operating_cash_flow is None or s.revenue == 0:
        return None
    return (s.operating_cash_flow / s.revenue) * 100


def _fcf_margin(s: FinancialSnapshot):
    if s.revenue is None or s.free_cash_flow is None or s.revenue == 0:
        return None
    return (s.free_cash_flow / s.revenue) * 100


def _debt_to_equity(s: FinancialSnapshot):
    if s.total_debt is None or s.total_equity is None or s.total_equity == 0:
        return None
    return s.total_debt / s.total_equity


def _current_ratio_calc(s: FinancialSnapshot):
    if s.current_assets is None or s.current_liabilities is None or s.current_liabilities == 0:
        return None
    return s.current_assets / s.current_liabilities


def _cash_to_debt(s: FinancialSnapshot):
    if s.cash_and_equivalents is None or s.total_debt is None or s.total_debt == 0:
        return None
    return s.cash_and_equivalents / s.total_debt


_CALCULATED_METRICS: tuple[
    tuple[str, str, ChartUnit, ChartMetricCategory, Any],
    ...] = (
    (
        "net_profit_margin",
        "Net Profit Margin",
        ChartUnit.PERCENTAGE,
        ChartMetricCategory.RATIOS,
        _net_profit_margin,
    ),
    (
        "operating_margin",
        "Operating Margin",
        ChartUnit.PERCENTAGE,
        ChartMetricCategory.RATIOS,
        _operating_margin,
    ),
    (
        "ocf_margin",
        "OCF Margin",
        ChartUnit.PERCENTAGE,
        ChartMetricCategory.RATIOS,
        _ocf_margin,
    ),
    (
        "fcf_margin",
        "FCF Margin",
        ChartUnit.PERCENTAGE,
        ChartMetricCategory.RATIOS,
        _fcf_margin,
    ),
    (
        "debt_to_equity",
        "Debt / Equity",
        ChartUnit.RATIO,
        ChartMetricCategory.EFFICIENCY,
        _debt_to_equity,
    ),
    (
        "current_ratio",
        "Current Ratio",
        ChartUnit.RATIO,
        ChartMetricCategory.EFFICIENCY,
        _current_ratio_calc,
    ),
    (
        "cash_to_debt",
        "Cash / Debt",
        ChartUnit.RATIO,
        ChartMetricCategory.EFFICIENCY,
        _cash_to_debt,
    ),
)


def build_chart_data(
    snapshots: list[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> ChartDataSet:
    """
    Build a complete chart-ready data set from financial snapshots.

    Returns structured time-series data that the frontend can
    render directly without any financial calculation.
    """

    if not snapshots:
        return ChartDataSet(
            symbol=symbol,
            as_of=as_of.isoformat(),
            notes=("No financial snapshots available.",),
        )

    as_of_str = as_of.isoformat()
    series_list: list[ChartSeries] = []

    # Raw metrics
    for metric, label, unit, category, _source_metric in _CHART_METRICS:
        series_list.append(
            _build_series(snapshots, metric, label, unit, category, symbol)
        )

    # Calculated ratios
    for metric, label, unit, category, calc_fn in _CALCULATED_METRICS:
        series_list.append(
            _build_calculated_series(snapshots, metric, label, unit, category, calc_fn)
        )

    categories = tuple(dict.fromkeys(s.category for s in series_list))

    total_points = sum(s.period_count for s in series_list)
    total_available = sum(s.available_count for s in series_list)

    notes: list[str] = []
    if total_available < total_points:
        notes.append(
            f"{total_points - total_available} data points are missing "
            f"across {len(series_list)} series."
        )

    return ChartDataSet(
        symbol=symbol,
        as_of=as_of_str,
        series=tuple(series_list),
        categories=categories,
        total_metrics=len(series_list),
        total_data_points=total_points,
        notes=tuple(notes),
    )
