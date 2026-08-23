"""
Business analysis engine.

Analyzes business model data derived from financial snapshots:
  - Segment revenue concentration
  - Revenue diversification (Herfindahl index)
  - Segment trends across periods
  - Business quality signals from financial metrics
  - Geographic exposure from profile data

All analysis is deterministic. No external data is fetched;
all inputs must be provided by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from src.data.company.business_profile import BusinessProfile
from src.data.company.financials import FinancialSnapshot


@dataclass(frozen=True)
class SegmentShare:
    """One segment's share of total revenue."""

    segment_name: str
    revenue: str | None = None
    share_pct: str = ""
    evidence_count: int = 0


@dataclass(frozen=True)
class SegmentConcentration:
    """Revenue concentration within a single period."""

    period: str
    total_revenue: str | None = None
    segment_count: int = 0
    dominant_segment: str = ""
    dominant_segment_pct: str = ""
    hhi: str = ""
    concentration_level: str = "UNKNOWN"
    segment_shares: tuple[SegmentShare, ...] = ()
    explanation: str = ""


@dataclass(frozen=True)
class SegmentTrend:
    """Multi-period trend for one segment."""

    segment_name: str
    direction: str = "UNKNOWN"
    periods_analyzed: int = 0
    first_period: str = ""
    last_period: str = ""
    first_revenue: str | None = None
    last_revenue: str | None = None
    share_change: str = ""
    explanation: str = ""


@dataclass(frozen=True)
class BusinessQualitySignal:
    """A business quality observation derived from financial data."""

    signal_id: str
    signal_type: str
    direction: str
    title: str
    description: str
    metric: str
    value: str | None = None
    threshold: str = ""
    explanation: str = ""


@dataclass(frozen=True)
class BusinessAnalysisResult:
    """Complete business analysis for one company."""

    symbol: str
    as_of: str

    has_profile: bool = False
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    employees: int | None = None

    segment_concentrations: tuple[SegmentConcentration, ...] = ()
    segment_trends: tuple[SegmentTrend, ...] = ()
    quality_signals: tuple[BusinessQualitySignal, ...] = ()

    coverage: dict[str, int] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    available_analyses: tuple[str, ...] = ()
    missing_analyses: tuple[str, ...] = ()


def _ordered_snapshots(
    snapshots: Sequence[FinancialSnapshot],
) -> list[FinancialSnapshot]:
    return sorted(snapshots, key=lambda s: s.period_end)


def _decimal_or_none(value: Decimal | None) -> Decimal | None:
    if value is None:
        return None
    return value


def compute_segment_concentration(
    snapshot: FinancialSnapshot,
) -> SegmentConcentration:
    """
    Compute Herfindahl index and concentration level
    for a single financial period's segments.
    """

    if not snapshot.segments:
        return SegmentConcentration(
            period=snapshot.period_end.isoformat(),
            segment_count=0,
            concentration_level="NO_SEGMENTS",
            explanation="No segment data available for this period.",
        )

    total_revenue = snapshot.revenue
    if total_revenue is None or total_revenue == 0:
        return SegmentConcentration(
            period=snapshot.period_end.isoformat(),
            segment_count=len(snapshot.segments),
            concentration_level="NO_TOTAL_REVENUE",
            explanation="Total revenue unavailable; cannot compute segment shares.",
        )

    shares: list[SegmentShare] = []
    hhi_numerator = Decimal(0)

    for seg in snapshot.segments:
        if seg.revenue is None:
            shares.append(
                SegmentShare(
                    segment_name=seg.segment_name,
                    revenue=None,
                    share_pct="",
                )
            )
            continue

        share_pct = (
            (seg.revenue / total_revenue) * Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        shares.append(
            SegmentShare(
                segment_name=seg.segment_name,
                revenue=str(seg.revenue),
                share_pct=str(share_pct),
            )
        )

        hhi_numerator += share_pct ** 2

    hhi = hhi_numerator.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Concentration levels (standard HHI thresholds)
    # < 1500: Unconcentrated
    # 1500-2500: Moderately concentrated
    # > 2500: Highly concentrated
    if hhi < Decimal("1500"):
        concentration_level = "UNCONCENTRATED"
    elif hhi <= Decimal("2500"):
        concentration_level = "MODERATELY_CONCENTRATED"
    else:
        concentration_level = "HIGHLY_CONCENTRATED"

    # Find dominant segment
    dominant_segment = ""
    dominant_pct = Decimal(0)
    for s in shares:
        if s.share_pct:
            pct = Decimal(s.share_pct)
            if pct > dominant_pct:
                dominant_pct = pct
                dominant_segment = s.segment_name

    return SegmentConcentration(
        period=snapshot.period_end.isoformat(),
        total_revenue=str(total_revenue),
        segment_count=len(snapshot.segments),
        dominant_segment=dominant_segment,
        dominant_segment_pct=str(dominant_pct),
        hhi=str(hhi),
        concentration_level=concentration_level,
        segment_shares=tuple(shares),
        explanation=(
            f"HHI={hhi} ({concentration_level.lower()}). "
            f"Dominant segment: {dominant_segment} "
            f"at {dominant_pct}%."
        ),
    )


def compute_segment_trends(
    snapshots: Sequence[FinancialSnapshot],
) -> tuple[SegmentTrend, ...]:
    """
    Track how segment revenue shares evolve across periods.
    """

    ordered = _ordered_snapshots(snapshots)
    if len(ordered) < 2:
        return ()

    # Build per-segment share time series
    segment_timeseries: dict[str, list[tuple[str, Decimal | None]]] = {}

    for snap in ordered:
        period = snap.period_end.isoformat()
        total = snap.revenue

        for seg in snap.segments:
            if seg.segment_name not in segment_timeseries:
                segment_timeseries[seg.segment_name] = []

            if total is not None and total > 0 and seg.revenue is not None:
                share = (
                    (seg.revenue / total) * Decimal("100")
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                segment_timeseries[seg.segment_name].append(
                    (period, share)
                )
            else:
                segment_timeseries[seg.segment_name].append(
                    (period, None)
                )

    trends: list[SegmentTrend] = []

    for seg_name, ts in segment_timeseries.items():
        valid = [(p, s) for p, s in ts if s is not None]
        if len(valid) < 2:
            continue

        first_share = valid[0][1]
        last_share = valid[-1][1]
        change = last_share - first_share

        if change > Decimal("1"):
            direction = "INCREASING"
        elif change < Decimal("-1"):
            direction = "DECREASING"
        else:
            direction = "STABLE"

        trends.append(
            SegmentTrend(
                segment_name=seg_name,
                direction=direction,
                periods_analyzed=len(valid),
                first_period=valid[0][0],
                last_period=valid[-1][0],
                share_change=str(change.quantize(Decimal("0.01"))),
                explanation=(
                    f"Segment '{seg_name}' share "
                    f"{'increased' if direction == 'INCREASING' else 'decreased' if direction == 'DECREASING' else 'remained stable'} "
                    f"by {abs(change).quantize(Decimal('0.01'))}% "
                    f"over {len(valid)} periods."
                ),
            )
        )

    return tuple(trends)


def compute_business_quality_signals(
    snapshots: Sequence[FinancialSnapshot],
    symbol: str,
) -> tuple[BusinessQualitySignal, ...]:
    """
    Derive business quality signals from financial metrics.

    These are factual observations about scale, margin,
    cash generation, and growth — never investment advice.
    """

    ordered = _ordered_snapshots(snapshots)
    if not ordered:
        return ()

    signals: list[BusinessQualitySignal] = []
    latest = ordered[-1]

    # Scale signal
    if latest.revenue is not None:
        rev_b = latest.revenue / Decimal("1e9")
        if rev_b >= Decimal("1"):
            signals.append(
                BusinessQualitySignal(
                    signal_id=f"{symbol}_SCALE_REVENUE",
                    signal_type="SCALE",
                    direction="POSITIVE",
                    title="Revenue scale",
                    description=f"Annual revenue of {latest.revenue} indicates a large-scale operation.",
                    metric="revenue",
                    value=str(latest.revenue),
                )
            )

    # Margin signal
    if (
        latest.revenue is not None
        and latest.revenue > 0
        and latest.net_profit is not None
    ):
        margin = (
            (latest.net_profit / latest.revenue) * Decimal("100")
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if margin > Decimal("15"):
            direction = "POSITIVE"
        elif margin < Decimal("0"):
            direction = "NEGATIVE"
        else:
            direction = "NEUTRAL"

        signals.append(
            BusinessQualitySignal(
                signal_id=f"{symbol}_MARGIN",
                signal_type="MARGIN",
                direction=direction,
                title="Net profit margin",
                description=f"Net profit margin of {margin}%",
                metric="net_profit_margin",
                value=str(margin),
                threshold="15% positive threshold",
            )
        )

    # Cash generation signal
    if (
        latest.operating_cash_flow is not None
        and latest.net_profit is not None
        and latest.net_profit > 0
    ):
        ocf_ratio = (
            latest.operating_cash_flow / latest.net_profit
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if ocf_ratio >= Decimal("1"):
            direction = "POSITIVE"
        elif ocf_ratio >= Decimal("0.5"):
            direction = "NEUTRAL"
        else:
            direction = "NEGATIVE"

        signals.append(
            BusinessQualitySignal(
                signal_id=f"{symbol}_CASH_GENERATION",
                signal_type="CASH_GENERATION",
                direction=direction,
                title="Cash generation quality",
                description=(
                    f"Operating cash flow is {ocf_ratio}x net profit."
                ),
                metric="ocf_to_profit",
                value=str(ocf_ratio),
                threshold="1.0x positive threshold",
            )
        )

    # Leverage signal
    if (
        latest.total_debt is not None
        and latest.shareholders_equity is not None
        and latest.shareholders_equity > 0
    ):
        debt_eq = (
            latest.total_debt / latest.shareholders_equity
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        if debt_eq > Decimal("2"):
            direction = "NEGATIVE"
        elif debt_eq > Decimal("1"):
            direction = "NEUTRAL"
        else:
            direction = "POSITIVE"

        signals.append(
            BusinessQualitySignal(
                signal_id=f"{symbol}_LEVERAGE",
                signal_type="LEVERAGE",
                direction=direction,
                title="Balance sheet leverage",
                description=f"Debt-to-equity ratio of {debt_eq}",
                metric="debt_to_equity",
                value=str(debt_eq),
                threshold="2.0x negative threshold",
            )
        )

    return tuple(signals)


def analyze_business(
    snapshots: Sequence[FinancialSnapshot],
    profile: BusinessProfile | None,
    symbol: str,
    as_of: datetime,
) -> BusinessAnalysisResult:
    """
    Run the full business analysis pipeline.

    Combines segment concentration, segment trends,
    and business quality signals into a single typed result.
    """

    ordered = _ordered_snapshots(snapshots)
    notes: list[str] = []
    available: list[str] = []
    missing: list[str] = []

    if not ordered:
        notes.append("No financial data available for business analysis.")

        return BusinessAnalysisResult(
            symbol=symbol,
            as_of=as_of.isoformat(),
            has_profile=profile is not None,
            sector=profile.sector if profile else None,
            industry=profile.industry if profile else None,
            country=profile.country if profile else None,
            employees=profile.full_time_employees if profile else None,
            missing_analyses=(
                "segment_concentration",
                "segment_trends",
                "quality_signals",
            ),
        )

    # Profile data
    has_profile = profile is not None and (
        profile.has_sector or profile.has_industry
    )

    # Segment concentration (latest period)
    concentrations: tuple[SegmentConcentration, ...] = ()
    if any(s.segments for s in ordered):
        latest = ordered[-1]
        concentrations = (compute_segment_concentration(latest),)
        available.append("segment_concentration")
    else:
        missing.append("segment_concentration")
        notes.append("No segment data available in any period.")

    # Segment trends
    seg_trends: tuple[SegmentTrend, ...] = ()
    if len(ordered) >= 2:
        seg_trends = compute_segment_trends(ordered)
        if seg_trends:
            available.append("segment_trends")
        else:
            missing.append("segment_trends")
            notes.append("Insufficient segment data for trend analysis.")
    else:
        missing.append("segment_trends")
        notes.append("Segment trends require >= 2 periods.")

    # Business quality signals
    quality = compute_business_quality_signals(ordered, symbol)
    if quality:
        available.append("quality_signals")
    else:
        missing.append("quality_signals")
        notes.append("No quality signals derivable from available metrics.")

    # Coverage
    coverage: dict[str, int] = {}
    for s in ordered:
        p = s.period_end.isoformat()
        if s.segments:
            coverage[p] = len(s.segments)

    return BusinessAnalysisResult(
        symbol=symbol,
        as_of=as_of.isoformat(),
        has_profile=has_profile,
        sector=profile.sector if profile else None,
        industry=profile.industry if profile else None,
        country=profile.country if profile else None,
        employees=profile.full_time_employees if profile else None,
        segment_concentrations=concentrations,
        segment_trends=seg_trends,
        quality_signals=quality,
        coverage=coverage,
        notes=tuple(notes),
        available_analyses=tuple(available),
        missing_analyses=tuple(missing),
    )
