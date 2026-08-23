"""
Cash-flow quality analysis module.

Analyzes operating cash flow, free cash flow, and working-capital
behavior to derive structured research observations.

Every observation carries full provenance, calculation inputs,
and PIT metadata. This module does NOT produce scores or
recommendations -- it produces evidence-based observations.

All calculations use Decimal precision for determinism.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Sequence

from src.data.company.financials import FinancialSnapshot


class CashFlowDirection(str, Enum):
    IMPROVING = "IMPROVING"
    DETERIORATING = "DETERIORATING"
    STABLE = "STABLE"
    UNKNOWN = "UNKNOWN"


class CashFlowSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class CashFlowQualityObservation:
    """
    A single cash-flow quality research observation.

    Carries full provenance and calculation inputs for
    reproducibility and audit.
    """

    observation_id: str
    symbol: str

    category: str
    observation_type: str

    period: str
    metric: str

    value: str | None = None
    previous_value: str | None = None
    change: str | None = None
    change_pct: str | None = None

    direction: str = CashFlowDirection.UNKNOWN.value
    severity: str = CashFlowSeverity.LOW.value

    calculation_method: str = ""
    calculation_inputs: dict[str, str] = field(default_factory=dict)

    source_name: str | None = None
    source_type: str | None = None
    source_url: str | None = None

    available_at: str | None = None
    as_of: str | None = None
    effective_at: str | None = None

    status: str = "AVAILABLE"
    explanation: str = ""
    limitations: tuple[str, ...] = ()

    related_metrics: tuple[str, ...] = ()
    supporting_data: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CashFlowQualityResult:
    """
    Complete cash-flow quality analysis for one company.
    """

    symbol: str
    as_of: str

    observations: tuple[CashFlowQualityObservation, ...] = ()

    # Summary metrics (derived, not scored)
    avg_cfo_to_net_income: str | None = None
    avg_fcf_conversion: str | None = None
    avg_capex_intensity: str | None = None
    avg_dso: str | None = None
    avg_dio: str | None = None
    avg_dpo: str | None = None

    direction: str = CashFlowDirection.UNKNOWN.value
    period_count: int = 0
    notes: tuple[str, ...] = ()

    @property
    def observation_count(self) -> int:
        return len(self.observations)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_observation_counter = 0


def _next_id(prefix: str) -> str:
    global _observation_counter
    _observation_counter += 1
    return f"{prefix}-{_observation_counter:06d}"


def _safe_decimal(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    if value.is_nan() or value.is_infinite():
        return None
    return value


def _fmt(value: Decimal | None, decimals: int = 2) -> str:
    if value is None:
        return "unavailable"
    return f"{value:.{decimals}f}"


def _pct_change(
    previous: Decimal | None,
    current: Decimal | None,
) -> Decimal | None:
    if previous is None or current is None:
        return None
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * Decimal("100")


def _determine_direction(
    current: Decimal | None,
    previous: Decimal | None,
    higher_is_better: bool = True,
) -> str:
    if current is None or previous is None:
        return CashFlowDirection.UNKNOWN.value

    if current > previous:
        return (
            CashFlowDirection.IMPROVING.value
            if higher_is_better
            else CashFlowDirection.DETERIORATING.value
        )
    if current < previous:
        return (
            CashFlowDirection.DETERIORATING.value
            if higher_is_better
            else CashFlowDirection.IMPROVING.value
        )
    return CashFlowDirection.STABLE.value


def _determine_severity(
    observation_type: str,
    value: Decimal | None,
    threshold_high: Decimal | None = None,
    threshold_medium: Decimal | None = None,
) -> str:
    if value is None:
        return CashFlowSeverity.LOW.value

    if threshold_high is not None and abs(value) > threshold_high:
        return CashFlowSeverity.HIGH.value
    if threshold_medium is not None and abs(value) > threshold_medium:
        return CashFlowSeverity.MEDIUM.value
    return CashFlowSeverity.LOW.value


# ---------------------------------------------------------------------------
# Core Analysis Functions
# ---------------------------------------------------------------------------


def _snapshot_source(
    snapshot: FinancialSnapshot,
) -> tuple[str | None, str | None, str | None]:
    return (
        snapshot.source_name,
        snapshot.source_type,
        snapshot.source_url,
    )


def _snapshot_as_of(
    snapshot: FinancialSnapshot,
) -> tuple[str | None, str | None, str | None]:
    available = None
    if snapshot.available_at is not None:
        available = snapshot.available_at.isoformat()
    elif snapshot.published_at is not None:
        available = snapshot.published_at.isoformat()

    effective = None
    if snapshot.effective_at is not None:
        effective = snapshot.effective_at.isoformat()

    published = None
    if snapshot.published_at is not None:
        published = snapshot.published_at.isoformat()

    return available, effective, published


def analyze_cfo_to_net_income(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[CashFlowQualityObservation]:
    """
    Analyze CFO/net_income relationship across periods.

    A ratio >= 1.0 indicates cash earnings are backed by cash flow.
    A ratio < 0.5 may indicate accrual-heavy earnings.
    Negative CFO with positive net income is a divergence flag.
    """
    observations: list[CashFlowQualityObservation] = []

    ordered = sorted(snapshots, key=lambda s: s.period_end)

    for i, snapshot in enumerate(ordered):
        if (
            snapshot.net_profit is None
            or snapshot.operating_cash_flow is None
        ):
            continue

        if snapshot.net_profit == 0:
            continue

        ratio = (
            snapshot.operating_cash_flow / snapshot.net_profit
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        src = _snapshot_source(snapshot)
        ao, eff, pub = _snapshot_as_of(snapshot)

        # Determine direction based on ratio
        if ratio >= Decimal("1.0"):
            direction = CashFlowDirection.IMPROVING.value
            explanation = (
                f"CFO is {ratio}x net income, indicating "
                "cash earnings are well-supported by cash flow."
            )
        elif ratio >= Decimal("0.5"):
            direction = CashFlowDirection.STABLE.value
            explanation = (
                f"CFO is {ratio}x net income, indicating "
                "partial cash conversion of earnings."
            )
        elif ratio >= Decimal("0"):
            direction = CashFlowDirection.DETERIORATING.value
            explanation = (
                f"CFO is only {ratio}x net income, indicating "
                "low cash conversion of reported earnings."
            )
        else:
            direction = CashFlowDirection.DETERIORATING.value
            explanation = (
                f"CFO is negative ({ratio}x) while net income "
                "is positive, indicating a cash-profit divergence."
            )

        # Calculate change from previous period
        change = None
        change_pct = None
        prev_value = None
        if i > 0:
            prev = ordered[i - 1]
            if (
                prev.net_profit is not None
                and prev.operating_cash_flow is not None
                and prev.net_profit != 0
            ):
                prev_ratio = (
                    prev.operating_cash_flow / prev.net_profit
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                prev_value = str(prev_ratio)
                change = str(
                    (ratio - prev_ratio).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                )
                change_pct = str(
                    _pct_change(prev_ratio, ratio)
                )

        observations.append(
            CashFlowQualityObservation(
                observation_id=_next_id("CFQ"),
                symbol=symbol,
                category="cash_flow_quality",
                observation_type="cfo_to_net_income",
                period=snapshot.period_end.isoformat(),
                metric="cfo_to_net_income",
                value=str(ratio),
                previous_value=prev_value,
                change=change,
                change_pct=change_pct,
                direction=direction,
                severity=_determine_severity(
                    "cfo_to_net_income",
                    ratio,
                    threshold_high=Decimal("0.5"),
                    threshold_medium=Decimal("0.8"),
                ),
                calculation_method=(
                    "Operating cash flow / Net profit"
                ),
                calculation_inputs={
                    "operating_cash_flow": str(
                        snapshot.operating_cash_flow
                    ),
                    "net_profit": str(snapshot.net_profit),
                },
                source_name=src[0],
                source_type=src[1],
                source_url=src[2],
                available_at=ao,
                as_of=as_of.isoformat(),
                effective_at=eff,
                explanation=explanation,
                limitations=(
                    "Does not account for working capital "
                    "timing or non-cash items.",
                ),
                related_metrics=(
                    "operating_cash_flow",
                    "net_profit",
                ),
                supporting_data={
                    "cfo": str(snapshot.operating_cash_flow),
                    "net_income": str(snapshot.net_profit),
                    "period": snapshot.period_end.isoformat(),
                },
            )
        )

    return observations


def analyze_fcf_conversion(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[CashFlowQualityObservation]:
    """
    Analyze free cash flow conversion from operating cash flow.

    FCF = OCF - CapEx (where CapEx = OCF - FCF if both available)
    FCF conversion = FCF / OCF
    """
    observations: list[CashFlowQualityObservation] = []

    ordered = sorted(snapshots, key=lambda s: s.period_end)

    for i, snapshot in enumerate(ordered):
        if (
            snapshot.operating_cash_flow is None
            or snapshot.free_cash_flow is None
        ):
            continue

        if snapshot.operating_cash_flow == 0:
            continue

        conversion = (
            snapshot.free_cash_flow / snapshot.operating_cash_flow
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Derive CapEx if not explicitly available
        capex = snapshot.operating_cash_flow - snapshot.free_cash_flow
        capex_intensity = None
        if snapshot.revenue is not None and snapshot.revenue > 0:
            capex_intensity = (
                (capex / snapshot.revenue) * Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        src = _snapshot_source(snapshot)
        ao, eff, pub = _snapshot_as_of(snapshot)

        # Determine direction
        if conversion >= Decimal("0.8"):
            direction = CashFlowDirection.IMPROVING.value
            explanation = (
                f"FCF conversion is {conversion}x OCF, indicating "
                "strong cash generation after capital expenditure."
            )
        elif conversion >= Decimal("0.5"):
            direction = CashFlowDirection.STABLE.value
            explanation = (
                f"FCF conversion is {conversion}x OCF, indicating "
                "moderate cash generation after capital expenditure."
            )
        elif conversion >= Decimal("0"):
            direction = CashFlowDirection.DETERIORATING.value
            explanation = (
                f"FCF conversion is only {conversion}x OCF, "
                "indicating significant capital expenditure "
                "consuming operating cash flow."
            )
        else:
            direction = CashFlowDirection.DETERIORATING.value
            explanation = (
                f"FCF is negative ({conversion}x OCF), indicating "
                "capital expenditure exceeds operating cash flow."
            )

        # Calculate change from previous period
        change = None
        change_pct = None
        prev_value = None
        if i > 0:
            prev = ordered[i - 1]
            if (
                prev.operating_cash_flow is not None
                and prev.free_cash_flow is not None
                and prev.operating_cash_flow != 0
            ):
                prev_conversion = (
                    prev.free_cash_flow / prev.operating_cash_flow
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                prev_value = str(prev_conversion)
                change = str(
                    (conversion - prev_conversion).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                )
                change_pct = str(
                    _pct_change(prev_conversion, conversion)
                )

        observations.append(
            CashFlowQualityObservation(
                observation_id=_next_id("CFQ"),
                symbol=symbol,
                category="cash_flow_quality",
                observation_type="fcf_conversion",
                period=snapshot.period_end.isoformat(),
                metric="fcf_conversion",
                value=str(conversion),
                previous_value=prev_value,
                change=change,
                change_pct=change_pct,
                direction=direction,
                severity=_determine_severity(
                    "fcf_conversion",
                    conversion,
                    threshold_high=Decimal("0.3"),
                    threshold_medium=Decimal("0.5"),
                ),
                calculation_method=(
                    "Free cash flow / Operating cash flow"
                ),
                calculation_inputs={
                    "free_cash_flow": str(
                        snapshot.free_cash_flow
                    ),
                    "operating_cash_flow": str(
                        snapshot.operating_cash_flow
                    ),
                },
                source_name=src[0],
                source_type=src[1],
                source_url=src[2],
                available_at=ao,
                as_of=as_of.isoformat(),
                effective_at=eff,
                explanation=explanation,
                limitations=(
                    "CapEx derived from OCF-FCF difference. "
                    "Does not distinguish growth vs maintenance CapEx.",
                ),
                related_metrics=(
                    "operating_cash_flow",
                    "free_cash_flow",
                ),
                supporting_data={
                    "ocf": str(snapshot.operating_cash_flow),
                    "fcf": str(snapshot.free_cash_flow),
                    "derived_capex": str(capex),
                    "capex_intensity": (
                        str(capex_intensity)
                        if capex_intensity is not None
                        else "unavailable"
                    ),
                    "period": snapshot.period_end.isoformat(),
                },
            )
        )

    return observations


def analyze_working_capital_behavior(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[CashFlowQualityObservation]:
    """
    Analyze working capital behavior: DSO, DIO, DPO.

    Uses revenue and COGS proxies where available.
    DSO = (Receivables / Revenue) * 365
    DIO = (Inventory / COGS) * 365 (uses revenue as proxy)
    DPO = (Payables / COGS) * 365 (uses revenue as proxy)
    """
    observations: list[CashFlowQualityObservation] = []

    ordered = sorted(snapshots, key=lambda s: s.period_end)

    for i, snapshot in enumerate(ordered):
        if snapshot.revenue is None or snapshot.revenue <= 0:
            continue

        src = _snapshot_source(snapshot)
        ao, eff, pub = _snapshot_as_of(snapshot)

        # DSO (Days Sales Outstanding)
        if snapshot.receivables is not None:
            dso = (
                (snapshot.receivables / snapshot.revenue)
                * Decimal("365")
            ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

            prev_dso = None
            change = None
            change_pct = None
            if i > 0:
                prev = ordered[i - 1]
                if (
                    prev.receivables is not None
                    and prev.revenue is not None
                    and prev.revenue > 0
                ):
                    prev_dso = (
                        (prev.receivables / prev.revenue)
                        * Decimal("365")
                    ).quantize(
                        Decimal("0.1"), rounding=ROUND_HALF_UP
                    )
                    change = str(
                        (dso - prev_dso).quantize(
                            Decimal("0.1"), rounding=ROUND_HALF_UP
                        )
                    )
                    change_pct = str(
                        _pct_change(prev_dso, dso)
                    )

            # DSO direction: lower is generally better (faster collection)
            direction = _determine_direction(
                dso, prev_dso, higher_is_better=False
            )

            observations.append(
                CashFlowQualityObservation(
                    observation_id=_next_id("CFQ"),
                    symbol=symbol,
                    category="cash_flow_quality",
                    observation_type="dso",
                    period=snapshot.period_end.isoformat(),
                    metric="days_sales_outstanding",
                    value=str(dso),
                    previous_value=str(prev_dso)
                    if prev_dso is not None
                    else None,
                    change=change,
                    change_pct=change_pct,
                    direction=direction,
                    severity=_determine_severity(
                        "dso",
                        dso,
                        threshold_high=Decimal("90"),
                        threshold_medium=Decimal("60"),
                    ),
                    calculation_method=(
                        "(Receivables / Revenue) * 365"
                    ),
                    calculation_inputs={
                        "receivables": str(snapshot.receivables),
                        "revenue": str(snapshot.revenue),
                    },
                    source_name=src[0],
                    source_type=src[1],
                    source_url=src[2],
                    available_at=ao,
                    as_of=as_of.isoformat(),
                    effective_at=eff,
                    explanation=(
                        f"Days sales outstanding is {dso} days. "
                        + (
                            "This is above the 60-day threshold, "
                            "indicating potential collection "
                            "efficiency concerns."
                            if dso > Decimal("60")
                            else "This is within normal range."
                        )
                    ),
                    limitations=(
                        "Uses period-end receivables, not average. "
                        "Seasonal businesses may show distorted DSO.",
                    ),
                    related_metrics=("receivables", "revenue"),
                    supporting_data={
                        "receivables": str(snapshot.receivables),
                        "revenue": str(snapshot.revenue),
                        "period": snapshot.period_end.isoformat(),
                    },
                )
            )

        # DIO (Days Inventory Outstanding)
        if snapshot.inventory is not None:
            dio = (
                (snapshot.inventory / snapshot.revenue)
                * Decimal("365")
            ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

            prev_dio = None
            change = None
            change_pct = None
            if i > 0:
                prev = ordered[i - 1]
                if (
                    prev.inventory is not None
                    and prev.revenue is not None
                    and prev.revenue > 0
                ):
                    prev_dio = (
                        (prev.inventory / prev.revenue)
                        * Decimal("365")
                    ).quantize(
                        Decimal("0.1"), rounding=ROUND_HALF_UP
                    )
                    change = str(
                        (dio - prev_dio).quantize(
                            Decimal("0.1"), rounding=ROUND_HALF_UP
                        )
                    )
                    change_pct = str(
                        _pct_change(prev_dio, dio)
                    )

            # DIO direction: lower is generally better (faster turnover)
            direction = _determine_direction(
                dio, prev_dio, higher_is_better=False
            )

            observations.append(
                CashFlowQualityObservation(
                    observation_id=_next_id("CFQ"),
                    symbol=symbol,
                    category="cash_flow_quality",
                    observation_type="dio",
                    period=snapshot.period_end.isoformat(),
                    metric="days_inventory_outstanding",
                    value=str(dio),
                    previous_value=str(prev_dio)
                    if prev_dio is not None
                    else None,
                    change=change,
                    change_pct=change_pct,
                    direction=direction,
                    severity=_determine_severity(
                        "dio",
                        dio,
                        threshold_high=Decimal("120"),
                        threshold_medium=Decimal("90"),
                    ),
                    calculation_method=(
                        "(Inventory / Revenue) * 365"
                    ),
                    calculation_inputs={
                        "inventory": str(snapshot.inventory),
                        "revenue": str(snapshot.revenue),
                    },
                    source_name=src[0],
                    source_type=src[1],
                    source_url=src[2],
                    available_at=ao,
                    as_of=as_of.isoformat(),
                    effective_at=eff,
                    explanation=(
                        f"Days inventory outstanding is {dio} days. "
                        + (
                            "This is above the 90-day threshold, "
                            "indicating potential inventory "
                            "management concerns."
                            if dio > Decimal("90")
                            else "This is within normal range."
                        )
                    ),
                    limitations=(
                        "Uses revenue as COGS proxy. "
                        "Uses period-end inventory, not average.",
                    ),
                    related_metrics=("inventory", "revenue"),
                    supporting_data={
                        "inventory": str(snapshot.inventory),
                        "revenue": str(snapshot.revenue),
                        "period": snapshot.period_end.isoformat(),
                    },
                )
            )

        # DPO (Days Payables Outstanding)
        if snapshot.payables is not None:
            dpo = (
                (snapshot.payables / snapshot.revenue)
                * Decimal("365")
            ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

            prev_dpo = None
            change = None
            change_pct = None
            if i > 0:
                prev = ordered[i - 1]
                if (
                    prev.payables is not None
                    and prev.revenue is not None
                    and prev.revenue > 0
                ):
                    prev_dpo = (
                        (prev.payables / prev.revenue)
                        * Decimal("365")
                    ).quantize(
                        Decimal("0.1"), rounding=ROUND_HALF_UP
                    )
                    change = str(
                        (dpo - prev_dpo).quantize(
                            Decimal("0.1"), rounding=ROUND_HALF_UP
                        )
                    )
                    change_pct = str(
                        _pct_change(prev_dpo, dpo)
                    )

            # DPO direction: higher is generally better (slower payment)
            direction = _determine_direction(
                dpo, prev_dpo, higher_is_better=True
            )

            observations.append(
                CashFlowQualityObservation(
                    observation_id=_next_id("CFQ"),
                    symbol=symbol,
                    category="cash_flow_quality",
                    observation_type="dpo",
                    period=snapshot.period_end.isoformat(),
                    metric="days_payables_outstanding",
                    value=str(dpo),
                    previous_value=str(prev_dpo)
                    if prev_dpo is not None
                    else None,
                    change=change,
                    change_pct=change_pct,
                    direction=direction,
                    severity=_determine_severity(
                        "dpo",
                        dpo,
                        threshold_high=Decimal("90"),
                        threshold_medium=Decimal("60"),
                    ),
                    calculation_method=(
                        "(Payables / Revenue) * 365"
                    ),
                    calculation_inputs={
                        "payables": str(snapshot.payables),
                        "revenue": str(snapshot.revenue),
                    },
                    source_name=src[0],
                    source_type=src[1],
                    source_url=src[2],
                    available_at=ao,
                    as_of=as_of.isoformat(),
                    effective_at=eff,
                    explanation=(
                        f"Days payables outstanding is {dpo} days. "
                        + (
                            "This is above the 60-day threshold, "
                            "indicating extended supplier payment "
                            "terms."
                            if dpo > Decimal("60")
                            else "This is within normal range."
                        )
                    ),
                    limitations=(
                        "Uses revenue as COGS proxy. "
                        "Uses period-end payables, not average.",
                    ),
                    related_metrics=("payables", "revenue"),
                    supporting_data={
                        "payables": str(snapshot.payables),
                        "revenue": str(snapshot.revenue),
                        "period": snapshot.period_end.isoformat(),
                    },
                )
            )

    return observations


def analyze_cash_generation_trend(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> list[CashFlowQualityObservation]:
    """
    Analyze cash generation trend across periods.

    Looks at OCF growth, FCF growth, and OCF/Revenue margin trend.
    """
    observations: list[CashFlowQualityObservation] = []

    ordered = sorted(snapshots, key=lambda s: s.period_end)

    if len(ordered) < 2:
        return observations

    # OCF margin trend
    ocf_margins: list[tuple[str, Decimal]] = []
    for snapshot in ordered:
        if (
            snapshot.operating_cash_flow is not None
            and snapshot.revenue is not None
            and snapshot.revenue > 0
        ):
            margin = (
                (snapshot.operating_cash_flow / snapshot.revenue)
                * Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            ocf_margins.append(
                (snapshot.period_end.isoformat(), margin)
            )

    if len(ocf_margins) >= 2:
        first_margin = ocf_margins[0][1]
        last_margin = ocf_margins[-1][1]
        margin_change = last_margin - first_margin

        direction = _determine_direction(
            last_margin, first_margin, higher_is_better=True
        )

        src = _snapshot_source(ordered[-1])
        ao, eff, pub = _snapshot_as_of(ordered[-1])

        observations.append(
            CashFlowQualityObservation(
                observation_id=_next_id("CFQ"),
                symbol=symbol,
                category="cash_flow_quality",
                observation_type="ocf_margin_trend",
                period=(
                    f"{ocf_margins[0][0]} to {ocf_margins[-1][0]}"
                ),
                metric="ocf_margin",
                value=str(last_margin),
                previous_value=str(first_margin),
                change=str(
                    margin_change.quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                ),
                direction=direction,
                severity=_determine_severity(
                    "ocf_margin_trend",
                    margin_change,
                    threshold_high=Decimal("5"),
                    threshold_medium=Decimal("2"),
                ),
                calculation_method=(
                    "OCF margin trend: (OCF/Revenue)*100 "
                    "across reporting periods"
                ),
                calculation_inputs={
                    "first_margin": str(first_margin),
                    "last_margin": str(last_margin),
                    "periods": str(len(ocf_margins)),
                },
                source_name=src[0],
                source_type=src[1],
                source_url=src[2],
                available_at=ao,
                as_of=as_of.isoformat(),
                effective_at=eff,
                explanation=(
                    f"OCF margin changed from {first_margin}% "
                    f"to {last_margin}% "
                    f"({margin_change:+.2f}pp) over "
                    f"{len(ocf_margins)} periods."
                ),
                limitations=(
                    "Uses period-end values. "
                    "Seasonal variations not captured.",
                ),
                related_metrics=(
                    "operating_cash_flow",
                    "revenue",
                ),
                supporting_data={
                    "first_period": ocf_margins[0][0],
                    "last_period": ocf_margins[-1][0],
                    "first_margin": str(first_margin),
                    "last_margin": str(last_margin),
                    "margin_change_pp": str(margin_change),
                },
            )
        )

    return observations


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------


def analyze_cash_flow_quality(
    *,
    symbol: str,
    as_of: datetime,
    snapshots: Sequence[FinancialSnapshot],
) -> CashFlowQualityResult:
    """
    Complete cash-flow quality analysis for one company.

    Combines all cash-flow quality dimensions into a single
    result with full provenance.
    """
    if not snapshots:
        return CashFlowQualityResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            notes=("No financial data available.",),
        )

    observations: list[CashFlowQualityObservation] = []

    # Run all analyses
    observations.extend(
        analyze_cfo_to_net_income(snapshots, symbol, as_of)
    )
    observations.extend(
        analyze_fcf_conversion(snapshots, symbol, as_of)
    )
    observations.extend(
        analyze_working_capital_behavior(snapshots, symbol, as_of)
    )
    observations.extend(
        analyze_cash_generation_trend(snapshots, symbol, as_of)
    )

    # Calculate summary metrics
    cfo_ratios = [
        Decimal(o.value)
        for o in observations
        if o.observation_type == "cfo_to_net_income"
        and o.value != "unavailable"
    ]
    fcf_conversions = [
        Decimal(o.value)
        for o in observations
        if o.observation_type == "fcf_conversion"
        and o.value != "unavailable"
    ]
    dso_values = [
        Decimal(o.value)
        for o in observations
        if o.observation_type == "dso"
        and o.value != "unavailable"
    ]
    dio_values = [
        Decimal(o.value)
        for o in observations
        if o.observation_type == "dio"
        and o.value != "unavailable"
    ]
    dpo_values = [
        Decimal(o.value)
        for o in observations
        if o.observation_type == "dpo"
        and o.value != "unavailable"
    ]

    avg_cfo = (
        str(
            (sum(cfo_ratios) / len(cfo_ratios)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        )
        if cfo_ratios
        else None
    )
    avg_fcf = (
        str(
            (sum(fcf_conversions) / len(fcf_conversions)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        )
        if fcf_conversions
        else None
    )
    avg_dso = (
        str(
            (sum(dso_values) / len(dso_values)).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
        )
        if dso_values
        else None
    )
    avg_dio = (
        str(
            (sum(dio_values) / len(dio_values)).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
        )
        if dio_values
        else None
    )
    avg_dpo = (
        str(
            (sum(dpo_values) / len(dpo_values)).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
        )
        if dpo_values
        else None
    )

    # Determine overall direction
    improving = sum(
        1
        for o in observations
        if o.direction == CashFlowDirection.IMPROVING.value
    )
    deteriorating = sum(
        1
        for o in observations
        if o.direction == CashFlowDirection.DETERIORATING.value
    )

    if improving > deteriorating:
        overall_direction = CashFlowDirection.IMPROVING.value
    elif deteriorating > improving:
        overall_direction = CashFlowDirection.DETERIORATING.value
    else:
        overall_direction = CashFlowDirection.STABLE.value

    return CashFlowQualityResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        observations=tuple(observations),
        avg_cfo_to_net_income=avg_cfo,
        avg_fcf_conversion=avg_fcf,
        avg_dso=avg_dso,
        avg_dio=avg_dio,
        avg_dpo=avg_dpo,
        direction=overall_direction,
        period_count=len(snapshots),
        notes=(),
    )
