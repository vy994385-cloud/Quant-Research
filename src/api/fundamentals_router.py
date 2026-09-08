"""
Financial history API routes.

Exposes the raw financial research data through a typed contract.
Period-by-period metrics, calculated ratios, coverage, and provenance.

Phase 1B extends this with a deep fundamentals endpoint providing:
- Multi-period trajectories (CAGR, growth, margin, leverage)
- Earnings quality analysis
- Balance-sheet quality analysis
- Fundamental anomaly detection
- Unified research observations with provenance/PIT metadata
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Query

from src.analysis.financial_ratios import (
    accruals_ratio,
    cash_conversion_ratio,
    current_ratio,
    debt_to_revenue,
    free_cash_flow_margin,
    net_profit_margin,
    operating_cash_flow_margin,
    return_on_capital_employed,
    return_on_equity,
    revenue_growth,
    working_capital,
)
from src.api.contracts import (
    CompanyDeepFundamentalContract,
    CompanyFinancialHistoryContract,
    ContractBalanceSheetQualityObservation,
    ContractCashDebtChange,
    ContractCashProfitComparison,
    ContractDeepFundamentalResult,
    ContractDebtGrowthComparison,
    ContractEarningsQualityObservation,
    ContractEquityChange,
    ContractFundamentalObservation,
    ContractFundamentalObservationSet,
    ContractFinancialHistory,
    ContractFinancialMetric,
    ContractFinancialPeriodDetail,
    ContractFinancialRatio,
    ContractGrowthDivergence,
    ContractLeverageTrajectory,
    ContractLiquidityChange,
    ContractMarginTrajectory,
    ContractPeriodGrowthRate,
    ContractSignal,
    ContractTrajectoryAnalysis,
    ContractWorkingCapitalChange,
)
from src.api.query_utils import company_identity, parse_as_of, utc_iso
from src.data.company.financials import FinancialSnapshot
from src.data.providers.yahoo_financials import (
    YahooFinanceFinancialProvider,
)


RAW_METRICS = [
    "revenue",
    "net_profit",
    "operating_profit",
    "operating_cash_flow",
    "free_cash_flow",
    "total_assets",
    "total_debt",
    "cash_and_equivalents",
    "receivables",
    "payables",
    "total_equity",
    "current_assets",
    "current_liabilities",
    "inventory",
    "shareholders_equity",
]

CALCULATED_RATIOS = [
    "net_profit_margin",
    "operating_cash_flow_margin",
    "free_cash_flow_margin",
    "revenue_growth",
    "debt_to_revenue",
    "cash_conversion_ratio",
    "return_on_equity",
    "return_on_capital_employed",
    "working_capital",
    "current_ratio",
    "accruals_ratio",
]


def _serialize_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _metric_observation(
    snapshot: FinancialSnapshot,
    metric: str,
) -> ContractFinancialMetric:
    value = getattr(snapshot, metric, None)
    available = value is not None

    as_of = None
    if snapshot.available_at is not None:
        as_of = utc_iso(snapshot.available_at)
    elif snapshot.published_at is not None:
        as_of = utc_iso(snapshot.published_at)

    return ContractFinancialMetric(
        metric=metric,
        value=_serialize_decimal(value),
        available=available,
        source=snapshot.source_name,
        as_of=as_of,
    )


def _ratio_observation(
    snapshot: FinancialSnapshot,
    ratio_name: str,
    numerator_metric: str | None,
    denominator_metric: str | None,
    explanation: str,
    ratio_fn,
) -> ContractFinancialRatio:
    value = ratio_fn(snapshot)
    available = value is not None

    return ContractFinancialRatio(
        ratio=ratio_name,
        value=_serialize_decimal(value),
        available=available,
        numerator_metric=numerator_metric,
        denominator_metric=denominator_metric,
        explanation=explanation,
    )


def _build_ratios(
    snapshot: FinancialSnapshot,
) -> list[ContractFinancialRatio]:
    ratios: list[ContractFinancialRatio] = []

    ratio_defs = [
        (
            "net_profit_margin",
            "net_profit",
            "revenue",
            "Net profit as percentage of revenue",
            net_profit_margin,
        ),
        (
            "operating_cash_flow_margin",
            "operating_cash_flow",
            "revenue",
            "Operating cash flow as percentage of revenue",
            operating_cash_flow_margin,
        ),
        (
            "free_cash_flow_margin",
            "free_cash_flow",
            "revenue",
            "Free cash flow as percentage of revenue",
            free_cash_flow_margin,
        ),
        (
            "revenue_growth",
            None,
            None,
            "Year-over-year revenue growth percentage",
            lambda s: revenue_growth(s, s),
        ),
        (
            "debt_to_revenue",
            "total_debt",
            "revenue",
            "Total debt relative to revenue",
            debt_to_revenue,
        ),
        (
            "cash_conversion_ratio",
            "operating_cash_flow",
            "net_profit",
            "Operating cash flow as percentage of net profit",
            cash_conversion_ratio,
        ),
        (
            "return_on_equity",
            "net_profit",
            "shareholders_equity",
            "Net profit as percentage of shareholders equity",
            return_on_equity,
        ),
        (
            "return_on_capital_employed",
            "operating_profit",
            None,
            "Operating profit as percentage of capital employed",
            return_on_capital_employed,
        ),
        (
            "working_capital",
            "current_assets",
            "current_liabilities",
            "Current assets minus current liabilities",
            working_capital,
        ),
        (
            "current_ratio",
            "current_assets",
            "current_liabilities",
            "Current assets divided by current liabilities",
            current_ratio,
        ),
        (
            "accruals_ratio",
            "net_profit",
            "operating_cash_flow",
            "Accruals as percentage of total assets",
            accruals_ratio,
        ),
    ]

    for (
        name,
        num,
        den,
        explanation,
        fn,
    ) in ratio_defs:
        ratios.append(
            _ratio_observation(
                snapshot,
                name,
                num,
                den,
                explanation,
                fn,
            )
        )

    return ratios


def build_financial_history(
    snapshots: list[FinancialSnapshot],
    symbol: str,
    as_of: datetime,
) -> ContractFinancialHistory:
    """Build a typed financial history contract from raw snapshots."""

    period_details: list[ContractFinancialPeriodDetail] = []

    available_metrics: set[str] = set()
    available_ratios: set[str] = set()

    for idx, snapshot in enumerate(snapshots):
        metrics = [
            _metric_observation(snapshot, m)
            for m in RAW_METRICS
        ]

        ratios = _build_ratios(snapshot)

        period_id = (
            f"{symbol}-{snapshot.period_end.isoformat()}"
        )

        period_details.append(
            ContractFinancialPeriodDetail(
                period_id=period_id,
                symbol=symbol,
                period_end=snapshot.period_end.isoformat(),
                period_type=snapshot.period_type,
                consolidation=snapshot.consolidation,
                published_at=utc_iso(snapshot.published_at),
                available_at=utc_iso(snapshot.available_at),
                effective_at=utc_iso(snapshot.effective_at),
                source_name=snapshot.source_name,
                source_type=snapshot.source_type,
                source_url=snapshot.source_url,
                currency=snapshot.currency,
                metrics=metrics,
                ratios=ratios,
            )
        )

        for m in metrics:
            if m.available:
                available_metrics.add(m.metric)

        for r in ratios:
            if r.available:
                available_ratios.add(r.ratio)

    all_metrics_set = set(RAW_METRICS)
    all_ratios_set = set(CALCULATED_RATIOS)

    missing_metrics = sorted(
        all_metrics_set - available_metrics
    )
    missing_ratios = sorted(
        all_ratios_set - available_ratios
    )

    coverage: dict[str, int] = {}
    for m in RAW_METRICS:
        count = sum(
            1
            for p in period_details
            for obs in p.metrics
            if obs.metric == m and obs.available
        )
        if count > 0:
            coverage[m] = count

    for r in CALCULATED_RATIOS:
        count = sum(
            1
            for p in period_details
            for obs in p.ratios
            if obs.ratio == r and obs.available
        )
        if count > 0:
            coverage[r] = count

    notes: list[str] = []

    if not snapshots:
        notes.append(
            "No financial data available for this company."
        )

    if missing_metrics:
        notes.append(
            f"Missing raw metrics: {', '.join(missing_metrics)}"
        )

    if missing_ratios:
        notes.append(
            f"Missing calculated ratios: {', '.join(missing_ratios)}"
        )

    return ContractFinancialHistory(
        symbol=symbol,
        as_of=utc_iso(as_of),
        period_count=len(period_details),
        periods=period_details,
        available_metrics=sorted(available_metrics),
        missing_metrics=missing_metrics,
        available_ratios=sorted(available_ratios),
        missing_ratios=missing_ratios,
        coverage=coverage,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Phase 1B: Deep Fundamental Research serialization
# ---------------------------------------------------------------------------


def _serialize_trajectory(traj) -> ContractTrajectoryAnalysis:
    """Convert a TrajectoryAnalysis dataclass to API contract."""
    growth_rates = [
        ContractPeriodGrowthRate(
            from_period=gr.from_period,
            to_period=gr.to_period,
            previous_value=gr.previous_value,
            current_value=gr.current_value,
            growth_rate=gr.growth_rate,
            metric=gr.metric,
        )
        for gr in traj.growth_rates
    ]

    return ContractTrajectoryAnalysis(
        metric=traj.metric,
        symbol=traj.symbol,
        period_count=traj.period_count,
        first_period=traj.first_period,
        last_period=traj.last_period,
        first_value=traj.first_value,
        last_value=traj.last_value,
        cagr=traj.cagr,
        total_change=traj.total_change,
        total_change_pct=traj.total_change_pct,
        growth_rates=growth_rates,
        direction=traj.direction,
        acceleration=traj.acceleration,
        persistence_pct=traj.persistence_pct,
        average_growth_rate=traj.average_growth_rate,
        min_growth_rate=traj.min_growth_rate,
        max_growth_rate=traj.max_growth_rate,
        explanation=traj.explanation,
    )


def _serialize_margin_trajectory(
    mt,
) -> ContractMarginTrajectory:
    """Convert a MarginTrajectory dataclass to API contract."""
    values = [[p, v] for p, v in mt.values]

    return ContractMarginTrajectory(
        margin_name=mt.margin_name,
        symbol=mt.symbol,
        period_count=mt.period_count,
        first_period=mt.first_period,
        last_period=mt.last_period,
        first_value=mt.first_value,
        last_value=mt.last_value,
        total_change_pp=mt.total_change_pp,
        direction=mt.direction,
        persistent=mt.persistent,
        values=values,
        explanation=mt.explanation,
    )


def _serialize_leverage_trajectory(
    lt,
) -> ContractLeverageTrajectory:
    """Convert a LeverageTrajectory dataclass to API contract."""
    values = [[p, v] for p, v in lt.values]

    return ContractLeverageTrajectory(
        metric=lt.metric,
        symbol=lt.symbol,
        period_count=lt.period_count,
        first_period=lt.first_period,
        last_period=lt.last_period,
        first_value=lt.first_value,
        last_value=lt.last_value,
        direction=lt.direction,
        elevated=lt.elevated,
        peak_value=lt.peak_value,
        trough_value=lt.trough_value,
        values=values,
        explanation=lt.explanation,
    )


def _serialize_cash_profit_comparison(
    cpc,
) -> ContractCashProfitComparison:
    return ContractCashProfitComparison(
        period=cpc.period,
        net_profit=cpc.net_profit,
        operating_cash_flow=cpc.operating_cash_flow,
        free_cash_flow=cpc.free_cash_flow,
        ocf_to_profit_ratio=cpc.ocf_to_profit_ratio,
        fcf_to_profit_ratio=cpc.fcf_to_profit_ratio,
        ocf_exceeds_profit=cpc.ocf_exceeds_profit,
        fcf_exceeds_profit=cpc.fcf_exceeds_profit,
        explanation=cpc.explanation,
    )


def _serialize_growth_divergence(
    gd,
) -> ContractGrowthDivergence:
    return ContractGrowthDivergence(
        period=gd.period,
        metric=gd.metric,
        metric_growth_rate=gd.metric_growth_rate,
        revenue_growth_rate=gd.revenue_growth_rate,
        divergence_pp=gd.divergence_pp,
        flagged=gd.flagged,
        explanation=gd.explanation,
    )


def _serialize_earnings_quality(
    eq,
) -> ContractEarningsQualityObservation:
    return ContractEarningsQualityObservation(
        observation_type=eq.observation_type,
        symbol=eq.symbol,
        severity=eq.severity,
        periods_covered=eq.periods_covered,
        first_period=eq.first_period,
        last_period=eq.last_period,
        value=eq.value,
        metric=eq.metric,
        cash_profit_comparisons=[
            _serialize_cash_profit_comparison(c)
            for c in eq.cash_profit_comparisons
        ],
        growth_divergences=[
            _serialize_growth_divergence(g)
            for g in eq.growth_divergences
        ],
        persistent=eq.persistent,
        explanation=eq.explanation,
    )


def _serialize_debt_comparison(
    dc,
) -> ContractDebtGrowthComparison:
    return ContractDebtGrowthComparison(
        period=dc.period,
        debt_growth_rate=dc.debt_growth_rate,
        revenue_growth_rate=dc.revenue_growth_rate,
        divergence_pp=dc.divergence_pp,
        flagged=dc.flagged,
        explanation=dc.explanation,
    )


def _serialize_liquidity_change(
    lc,
) -> ContractLiquidityChange:
    return ContractLiquidityChange(
        from_period=lc.from_period,
        to_period=lc.to_period,
        previous_ratio=lc.previous_ratio,
        current_ratio=lc.current_ratio,
        change=lc.change,
        deteriorated=lc.deteriorated,
        explanation=lc.explanation,
    )


def _serialize_working_capital_change(
    wc,
) -> ContractWorkingCapitalChange:
    return ContractWorkingCapitalChange(
        from_period=wc.from_period,
        to_period=wc.to_period,
        previous_value=wc.previous_value,
        current_value=wc.current_value,
        change=wc.change,
        explanation=wc.explanation,
    )


def _serialize_cash_debt_change(
    cd,
) -> ContractCashDebtChange:
    return ContractCashDebtChange(
        from_period=cd.from_period,
        to_period=cd.to_period,
        previous_ratio=cd.previous_ratio,
        current_ratio=cd.current_ratio,
        change_pct=cd.change_pct,
        weakened=cd.weakened,
        explanation=cd.explanation,
    )


def _serialize_equity_change(
    ec,
) -> ContractEquityChange:
    return ContractEquityChange(
        from_period=ec.from_period,
        to_period=ec.to_period,
        previous_value=ec.previous_value,
        current_value=ec.current_value,
        change_pct=ec.change_pct,
        eroded=ec.eroded,
        explanation=ec.explanation,
    )


def _serialize_balance_sheet(
    bs,
) -> ContractBalanceSheetQualityObservation:
    return ContractBalanceSheetQualityObservation(
        observation_type=bs.observation_type,
        symbol=bs.symbol,
        severity=bs.severity,
        periods_covered=bs.periods_covered,
        first_period=bs.first_period,
        last_period=bs.last_period,
        debt_comparisons=[
            _serialize_debt_comparison(d)
            for d in bs.debt_comparisons
        ],
        liquidity_changes=[
            _serialize_liquidity_change(l)
            for l in bs.liquidity_changes
        ],
        working_capital_changes=[
            _serialize_working_capital_change(w)
            for w in bs.working_capital_changes
        ],
        cash_debt_changes=[
            _serialize_cash_debt_change(c)
            for c in bs.cash_debt_changes
        ],
        equity_changes=[
            _serialize_equity_change(e)
            for e in bs.equity_changes
        ],
        persistent=bs.persistent,
        explanation=bs.explanation,
    )


def _serialize_anomaly(
    anomaly,
    *,
    symbol: str,
    as_of: str,
) -> ContractSignal:
    """Convert a FinancialAnomaly to a ContractSignal."""
    return ContractSignal(
        signal_id=f"ANOM-{anomaly.metric}",
        category="fundamental_anomaly",
        direction="NEGATIVE",
        severity=anomaly.severity,
        # Anomalies are deterministic derived comparisons; no separate
        # confidence is computed, so none is reported.
        confidence=None,
        title=f"Fundamental anomaly: {anomaly.metric}",
        explanation=anomaly.explanation,
        symbol=symbol,
        observation_at=as_of,
    )


def _serialize_fundamental_observation(
    obs,
) -> ContractFundamentalObservation:
    return ContractFundamentalObservation(
        observation_id=obs.observation_id,
        symbol=obs.symbol,
        category=obs.category,
        observation_type=obs.observation_type,
        period=obs.period,
        metric=obs.metric,
        value=obs.value,
        previous_value=obs.previous_value,
        change=obs.change,
        change_pct=obs.change_pct,
        calculation_method=obs.calculation_method,
        source_name=obs.source_name,
        source_type=obs.source_type,
        source_url=obs.source_url,
        available_at=obs.available_at,
        as_of=obs.as_of,
        status=obs.status,
        direction=obs.direction,
        severity=obs.severity,
        explanation=obs.explanation,
        related_metrics=list(obs.related_metrics),
        supporting_data=obs.supporting_data,
    )


def _serialize_observation_set(
    obs_set,
) -> ContractFundamentalObservationSet:
    return ContractFundamentalObservationSet(
        symbol=obs_set.symbol,
        as_of=obs_set.as_of,
        trajectory_observations=[
            _serialize_fundamental_observation(o)
            for o in obs_set.trajectory_observations
        ],
        earnings_quality_observations=[
            _serialize_fundamental_observation(o)
            for o in obs_set.earnings_quality_observations
        ],
        balance_sheet_observations=[
            _serialize_fundamental_observation(o)
            for o in obs_set.balance_sheet_observations
        ],
        anomaly_observations=[
            _serialize_fundamental_observation(o)
            for o in obs_set.anomaly_observations
        ],
        total_count=obs_set.total_count,
        positive_count=obs_set.positive_count,
        negative_count=obs_set.negative_count,
        neutral_count=obs_set.neutral_count,
        coverage=obs_set.coverage,
        notes=obs_set.notes,
    )


def _serialize_deep_fundamental(
    result,
) -> ContractDeepFundamentalResult:
    """Convert a DeepFundamentalResult to API contract."""
    return ContractDeepFundamentalResult(
        symbol=result.symbol,
        as_of=result.as_of,
        period_count=result.period_count,
        first_period=result.first_period,
        last_period=result.last_period,
        trajectories=[
            _serialize_trajectory(t)
            for t in result.trajectories
        ],
        margin_trajectories=[
            _serialize_margin_trajectory(m)
            for m in result.margin_trajectories
        ],
        leverage_trajectories=[
            _serialize_leverage_trajectory(l)
            for l in result.leverage_trajectories
        ],
        earnings_quality_observations=[
            _serialize_earnings_quality(e)
            for e in result.earnings_quality_observations
        ],
        balance_sheet_observations=[
            _serialize_balance_sheet(b)
            for b in result.balance_sheet_observations
        ],
        anomalies=[
            _serialize_anomaly(a, symbol=result.symbol, as_of=result.as_of)
            for a in result.anomalies
        ],
        financial_trends=[],
        observation_set=(
            _serialize_observation_set(result.observation_set)
            if result.observation_set is not None
            else None
        ),
        available_analyses=list(result.available_analyses),
        missing_analyses=list(result.missing_analyses),
        notes=list(result.notes),
        positive_count=result.positive_count,
        negative_count=result.negative_count,
        neutral_count=result.neutral_count,
    )


def _fetch_snapshots(
    provider: YahooFinanceFinancialProvider,
    normalized: str,
    start_date: date,
    end_date: date,
) -> list[FinancialSnapshot]:
    """Fetch financial snapshots from the provider."""
    try:
        return provider.get_annual_financials(
            symbol=normalized,
            start_date=start_date,
            end_date=end_date,
        )
    except (RuntimeError, ValueError):
        return []


def _stamp_live_snapshots(
    snapshots: list[FinancialSnapshot],
    capture_time: datetime,
) -> list[FinancialSnapshot]:
    """Stamp a live provider retrieval time onto fetched snapshots.

    The Yahoo provider returns no archival timestamp, so its snapshots
    carry ``available_at=None`` and every PIT filter rejects them. The
    API boundary stamps the *actual retrieval instant* as
    ``available_at`` (only where the provider did not already supply
    one) so that:

    - a default (now) vantage uses the current snapshot set, and
    - an explicit historical ``as_of`` queried vantage still honestly
      rejects this live data, because it was retrieved after the
      requested point in time.

    The stamp is deliberately independent of the requested ``as_of``;
    stamping with the vantage itself would leak current data into a
    historical query. Snapshots are copied immutably; the underlying
    model is untouched.
    """
    return [
        snapshot.model_copy(
            update={
                "available_at": (
                    snapshot.available_at or capture_time
                )
            }
        )
        for snapshot in snapshots
    ]


def _parse_date_param(
    value: str | None,
    default: date,
) -> date:
    """Parse an optional date query parameter."""
    if not value:
        return default
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return default


def create_fundamentals_router(
    *,
    provider: YahooFinanceFinancialProvider | None = None,
) -> APIRouter:
    """
    Build the financial history API router.

    `provider` defaults to the Yahoo Finance provider.
    Tests inject a mock or stub provider.
    """

    provider = provider or YahooFinanceFinancialProvider()

    router = APIRouter(
        prefix="/api/v1",
        tags=["fundamentals"],
    )

    @router.get(
        "/companies/{symbol}/financial-history",
        response_model=CompanyFinancialHistoryContract,
    )
    def company_financial_history(
        symbol: str,
        as_of: str | None = Query(
            default=None,
            description=(
                "Optional point-in-time timestamp (ISO 8601, "
                "timezone-aware). Defaults to now."
            ),
        ),
        start_date: str | None = Query(
            default=None,
            description=(
                "Optional start date for financial data (YYYY-MM-DD). "
                "Defaults to 10 years ago."
            ),
        ),
        end_date: str | None = Query(
            default=None,
            description=(
                "Optional end date for financial data (YYYY-MM-DD). "
                "Defaults to today."
            ),
        ),
    ) -> dict:
        normalized = symbol.strip().upper()

        if not normalized:
            normalized = "DEMO"

        captured_at = parse_as_of(as_of)

        capture_time = datetime.now(timezone.utc)

        if captured_at is None:
            captured_at = capture_time

        today = date.today()

        parsed_end = _parse_date_param(end_date, today)
        parsed_start = _parse_date_param(
            start_date,
            date(today.year - 10, today.month, today.day),
        )

        snapshots = _fetch_snapshots(
            provider, normalized, parsed_start, parsed_end
        )

        history = build_financial_history(
            snapshots=_stamp_live_snapshots(
                snapshots, capture_time
            ),
            symbol=normalized,
            as_of=captured_at,
        )

        return {
            "company": company_identity(
                normalized,
                as_of=captured_at,
            ),
            "financial_history": history.model_dump(
                mode="json"
            ),
        }

    @router.get(
        "/companies/{symbol}/deep-fundamentals",
        response_model=CompanyDeepFundamentalContract,
    )
    def company_deep_fundamentals(
        symbol: str,
        as_of: str | None = Query(
            default=None,
            description=(
                "Optional point-in-time timestamp (ISO 8601, "
                "timezone-aware). Defaults to now."
            ),
        ),
        start_date: str | None = Query(
            default=None,
            description=(
                "Optional start date for financial data (YYYY-MM-DD). "
                "Defaults to 10 years ago."
            ),
        ),
        end_date: str | None = Query(
            default=None,
            description=(
                "Optional end date for financial data (YYYY-MM-DD). "
                "Defaults to today."
            ),
        ),
    ) -> dict:
        from src.analysis.deep_fundamental import (
            analyze_deep_fundamentals,
        )

        normalized = symbol.strip().upper()

        if not normalized:
            normalized = "DEMO"

        captured_at = parse_as_of(as_of)

        capture_time = datetime.now(timezone.utc)

        if captured_at is None:
            captured_at = capture_time

        today = date.today()

        parsed_end = _parse_date_param(end_date, today)
        parsed_start = _parse_date_param(
            start_date,
            date(today.year - 10, today.month, today.day),
        )

        snapshots = _fetch_snapshots(
            provider, normalized, parsed_start, parsed_end
        )

        result = analyze_deep_fundamentals(
            snapshots=_stamp_live_snapshots(
                snapshots, capture_time
            ),
            symbol=normalized,
            as_of=captured_at,
        )

        return {
            "company": company_identity(
                normalized,
                as_of=captured_at,
            ),
            "deep_fundamentals": _serialize_deep_fundamental(
                result
            ).model_dump(mode="json"),
        }

    return router


__all__ = [
    "CALCULATED_RATIOS",
    "RAW_METRICS",
    "build_financial_history",
    "create_fundamentals_router",
]
