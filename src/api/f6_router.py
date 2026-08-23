"""
F6 — Research Product Expansion router.

Exposes chart data, company news, corporate actions, industry context,
and tracking endpoints. Data is computed from the recorded research
result at the router level.

All endpoints are:
- PIT-safe (as_of parameter honored)
- Deterministic (same input → same output)
- Evidence-backed (no invented data)
- No scores, rankings, recommendations, or trading signals
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Query

from src.api.errors import (
    InvalidAsOfError,
    UnknownCompanyError,
)
from src.api.f6_contracts import (
    CompanyChartDataContract,
    CompanyCorporateActionsContract,
    CompanyIndustryContextContract,
    CompanyNewsContract,
    CompanyTrackingContract,
)
from src.api.f6_serializers import (
    chart_data_from_model,
    company_info_dict,
    corporate_actions_from_items,
    industry_context_from_model,
    news_from_items,
    tracking_from_model,
)
from src.api.query_utils import parse_as_of
from src.api.recorded_research import RecordedCompanyResearchService
from src.analysis.chart_data import (
    ChartDataSet,
    ChartDataPoint,
    ChartMetricCategory,
    ChartSeries,
    ChartUnit,
    build_chart_data,
)
from src.analysis.industry_context import (
    IndustryContextResult,
    build_industry_context,
)
from src.data.company.business_profile import BusinessProfile
from src.data.company.financials import FinancialSnapshot
from src.tracking.engine import build_tracking_result
from src.tracking.models import CompanyTrackingResult


def _period_to_snapshot(period) -> FinancialSnapshot | None:
    """Convert a FinancialPeriod to a FinancialSnapshot for chart data."""

    metrics = period.metrics

    def _get(name: str) -> Decimal | None:
        v = metrics.get(name)
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        try:
            return Decimal(str(v))
        except (InvalidOperation, ValueError):
            return None

    return FinancialSnapshot(
        symbol=period.symbol,
        period_end=period.period_end,
        period_start=period.period_start,
        published_at=period.published_at,
        available_at=period.available_at,
        effective_at=period.effective_at,
        source_name=period.source_name,
        source_type=period.source_type,
        source_url=period.source_url,
        revenue=_get("revenue"),
        operating_profit=_get("operating_profit"),
        net_profit=_get("net_profit"),
        operating_cash_flow=_get("operating_cash_flow"),
        free_cash_flow=_get("free_cash_flow"),
        total_assets=_get("total_assets"),
        total_debt=_get("total_debt"),
        cash_and_equivalents=_get("cash_and_equivalents"),
        receivables=_get("receivables"),
        payables=_get("payables"),
        total_equity=_get("total_equity"),
        shareholders_equity=_get("shareholders_equity"),
        current_assets=_get("current_assets"),
        current_liabilities=_get("current_liabilities"),
        inventory=_get("inventory"),
    )


def create_f6_router(
    *,
    service: RecordedCompanyResearchService | None = None,
) -> APIRouter:
    """Build the F6 research expansion router."""

    service = service or RecordedCompanyResearchService()

    router = APIRouter(
        prefix="/api/v1",
        tags=["f6 research expansion"],
    )

    def _run(symbol: str, as_of_str: str | None):
        normalized = service.validate_company(symbol)
        captured_at = parse_as_of(as_of_str)
        return service.run(normalized, as_of=captured_at)

    @router.get(
        "/companies/{symbol}/chart-data",
        response_model=CompanyChartDataContract,
    )
    def company_chart_data(
        symbol: str,
        as_of: str | None = Query(default=None),
    ) -> dict:
        result = _run(symbol, as_of)
        intel = result.intelligence

        chart_data = None

        if (
            intel is not None
            and intel.financial_intelligence is not None
        ):
            fi = intel.financial_intelligence
            snapshots = []
            for period in fi.periods:
                snap = _period_to_snapshot(period)
                if snap is not None:
                    snapshots.append(snap)

            if snapshots:
                snapshots.sort(key=lambda s: s.period_end)
                chart_data = build_chart_data(
                    snapshots,
                    symbol=result.company,
                    as_of=result.as_of,
                )

        if chart_data is None:
            chart_data = ChartDataSet(
                symbol=result.company,
                as_of=result.as_of.isoformat(),
                notes=(
                    "No financial period data available "
                    "for chart generation.",
                ),
            )

        return {
            "company": company_info_dict(
                result,
                service.company_name(result.company),
            ),
            "chart_data": chart_data_from_model(chart_data),
        }

    @router.get(
        "/companies/{symbol}/news",
        response_model=CompanyNewsContract,
    )
    def company_news(
        symbol: str,
        as_of: str | None = Query(default=None),
    ) -> dict:
        result = _run(symbol, as_of)
        return news_from_items(
            result,
            service.company_name(result.company),
        )

    @router.get(
        "/companies/{symbol}/corporate-actions",
        response_model=CompanyCorporateActionsContract,
    )
    def company_corporate_actions(
        symbol: str,
        as_of: str | None = Query(default=None),
    ) -> dict:
        result = _run(symbol, as_of)
        return corporate_actions_from_items(
            result,
            service.company_name(result.company),
        )

    @router.get(
        "/companies/{symbol}/industry-context",
        response_model=CompanyIndustryContextContract,
    )
    def company_industry_context(
        symbol: str,
        as_of: str | None = Query(default=None),
    ) -> dict:
        result = _run(symbol, as_of)

        profile = BusinessProfile(
            symbol=result.company,
            sector=result.sector,
        )

        ic = build_industry_context(profile, result.company)

        return industry_context_from_model(
            result,
            ic,
            service.company_name(result.company),
        )

    @router.get(
        "/companies/{symbol}/tracking",
        response_model=CompanyTrackingContract,
    )
    def company_tracking(
        symbol: str,
        as_of: str | None = Query(default=None),
    ) -> dict:
        result = _run(symbol, as_of)
        intel = result.intelligence

        tracking = None

        if (
            intel is not None
            and intel.financial_intelligence is not None
        ):
            fi = intel.financial_intelligence
            snapshots = []
            for period in fi.periods:
                snap = _period_to_snapshot(period)
                if snap is not None:
                    snapshots.append(snap)

            if snapshots:
                snapshots.sort(key=lambda s: s.period_end)
                tracking = build_tracking_result(
                    snapshots, result.company, result.as_of
                )

        if tracking is None:
            tracking = CompanyTrackingResult(
                symbol=result.company,
                as_of=result.as_of,
                notes=(
                    "No financial data available "
                    "for tracking.",
                ),
            )

        return tracking_from_model(
            result,
            tracking,
            service.company_name(result.company),
        )

    return router


__all__ = ["create_f6_router"]
