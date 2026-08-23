"""
F6 — Research Product Expansion serializers.

Serialization functions that convert recorded research results,
intelligence items, and F6 analysis models into the API contract
dictionaries consumed by ``f6_router`` (and re-exported through
``src.api.serializers``).

All functions project already-produced research output only:
they never invent scores, evidence, timing, or recommendations.
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal, InvalidOperation
from typing import Any

from src.analysis.industry_context import build_industry_context
from src.api.query_utils import utc_iso as _utc_iso
from src.data.company.business_profile import BusinessProfile
from src.data.company.financials import FinancialSnapshot
from src.tracking.engine import build_tracking_result
from src.tracking.models import CompanyTrackingResult


# ── shared helpers ───────────────────────────────────────────────


def _company_envelope(
    result,
    company_name: str | None,
) -> dict:
    """Canonical company envelope shared by all F6 serializers."""

    return {
        "symbol": result.company,
        "company_name": company_name,
        "sector": result.sector,
        "as_of": _utc_iso(result.as_of),
    }


def _enum_str(value: Any) -> str:
    """Render a str-enum (or plain string) as its canonical value."""

    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _iso_date(value: Any) -> str | None:
    """Render a date/datetime as its calendar-date string, else None."""

    if value is None:
        return None
    return value.date().isoformat() if hasattr(value, "date") else str(value)


# ── chart data ───────────────────────────────────────────────────


def _chart_data_point(pt) -> dict:
    return {
        "period_end": pt.period_end,
        "value": pt.value,
        "available": pt.available,
        "as_of": pt.as_of,
        "source": pt.source,
    }


def _chart_series(series) -> dict:
    return {
        "metric": series.metric,
        "label": series.label,
        "unit": _enum_str(series.unit),
        "category": _enum_str(series.category),
        "currency": series.currency,
        "data_points": [
            _chart_data_point(pt)
            for pt in series.data_points
        ],
        "period_count": series.period_count,
        "available_count": series.available_count,
        "missing_count": series.missing_count,
        "source": series.source,
    }


def _chart_data_dict(chart_data) -> dict:
    """Shared ChartDataSet serialization used by both entry points."""

    return {
        "symbol": chart_data.symbol,
        "as_of": _utc_iso(chart_data.as_of),
        "series": [
            _chart_series(s)
            for s in chart_data.series
        ],
        "categories": [
            _enum_str(c)
            for c in chart_data.categories
        ],
        "total_metrics": chart_data.total_metrics,
        "total_data_points": chart_data.total_data_points,
        "notes": list(chart_data.notes),
    }


def chart_data_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """
    Serialize chart data carried by an intelligence snapshot.

    The recorded pipeline does not attach a chart dataset to the
    snapshot itself; the router builds one from financial periods and
    serializes it via :func:`chart_data_from_model`. This entry point
    therefore yields ``chart_data: null`` unless a snapshot explicitly
    carries a compatible dataset.
    """

    intelligence = getattr(result, "intelligence", None)
    chart_data = None

    if (
        intelligence is not None
        and hasattr(intelligence, "chart_data")
        and intelligence.chart_data is not None
    ):
        chart_data = _chart_data_dict(intelligence.chart_data)

    return {
        "company": _company_envelope(result, company_name),
        "chart_data": chart_data,
    }


def chart_data_from_model(chart_data) -> dict:
    """Serialize a ChartDataSet built by the router."""
    return _chart_data_dict(chart_data)


def company_info_dict(
    result,
    company_name: str | None,
) -> dict:
    """Standardized company info dict for router responses."""

    return {
        "symbol": result.company,
        "company_name": company_name,
        "sector": result.sector,
        "as_of": _utc_iso(result.as_of),
    }


# ── company news ─────────────────────────────────────────────────


def _news_source_field(item, field: str) -> str:
    source = getattr(item, "source", None)
    if source is None:
        return ""
    value = getattr(source, field, None)
    return str(value) if value is not None else ""


def _news_category(item) -> str:
    category = getattr(item, "intel_category", None)
    if category is not None:
        return _enum_str(category)
    return _enum_str(getattr(item, "kind", ""))


def _news_item_dict(item) -> dict:
    return {
        "news_id": item.item_id,
        "symbol": item.symbol,
        "headline": item.title,
        "summary": item.description or "",
        "category": _news_category(item),
        "direction": _enum_str(item.direction),
        "source_name": _news_source_field(item, "source_name"),
        "source_url": _news_source_field(item, "source_url"),
        "source_type": _news_source_field(item, "source_type"),
        "published_at": _utc_iso(item.published_at),
        "available_at": _utc_iso(item.available_at),
        "event_date": _iso_date(item.effective_at),
        "related_metrics": [],
        "evidence_refs": [],
        "as_of": None,
        "provenance_id": item.provenance_id,
    }


def _news_result_dict(
    items,
    *,
    symbol: str,
    as_of: Any,
) -> dict:
    serialized = [
        _news_item_dict(item)
        for item in items
    ]
    serialized.sort(key=lambda i: i["news_id"])

    category_counts = dict(
        sorted(Counter(i["category"] for i in serialized).items())
    )
    source_names = sorted(
        {
            i["source_name"]
            for i in serialized
            if i["source_name"]
        }
    )

    return {
        "symbol": symbol,
        "as_of": _utc_iso(as_of),
        "items": serialized,
        "item_count": len(serialized),
        "category_counts": category_counts,
        "source_count": len(source_names),
        "source_names": source_names,
        "notes": [],
    }


def _business_events(intel):
    if intel is None:
        return ()
    return tuple(getattr(intel, "business_events", ()) or ())


def news_from_items(
    result,
    company_name: str | None,
) -> dict:
    """Serialize the company news feed from intelligence events."""

    intel = getattr(result, "intelligence", None)

    news = None
    if intel is not None:
        news = _news_result_dict(
            _business_events(intel),
            symbol=result.company,
            as_of=result.as_of,
        )

    return {
        "company": _company_envelope(result, company_name),
        "news": news,
    }


def news_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize the company news feed for a company."""
    return news_from_items(result, company_name)


# ── corporate actions ────────────────────────────────────────────


_ACTION_CATEGORY = "CORPORATE_ACTION"


def _is_corporate_action(item) -> bool:
    category = getattr(item, "intel_category", None)
    return (
        category is not None
        and _enum_str(category) == _ACTION_CATEGORY
    )


def _action_item_dict(item) -> dict:
    event_type = getattr(item, "event_type", None)

    action_type = (
        _enum_str(event_type)
        if event_type is not None
        else _ACTION_CATEGORY
    )

    return {
        "action_id": item.item_id,
        "symbol": item.symbol,
        "action_type": action_type,
        "title": item.title,
        "description": item.description or "",
        # The intelligence stream carries publication/effective
        # timestamps; record dates have no analog and stay null.
        "announcement_date": _iso_date(item.published_at),
        "effective_date": _iso_date(item.effective_at),
        "record_date": None,
        "value": None,
        "ratio": None,
        "source_name": _news_source_field(item, "source_name"),
        "source_url": _news_source_field(item, "source_url"),
        "provenance_id": item.provenance_id,
        "published_at": _utc_iso(item.published_at),
        "available_at": _utc_iso(item.available_at),
        "as_of": None,
    }


def _actions_result_dict(
    items,
    *,
    symbol: str,
    as_of: Any,
) -> dict:
    actions = [item for item in items if _is_corporate_action(item)]

    serialized = [
        _action_item_dict(item)
        for item in actions
    ]
    serialized.sort(key=lambda i: i["action_id"])

    type_counts = dict(
        sorted(Counter(i["action_type"] for i in serialized).items())
    )
    source_names = sorted(
        {
            i["source_name"]
            for i in serialized
            if i["source_name"]
        }
    )

    return {
        "symbol": symbol,
        "as_of": _utc_iso(as_of),
        "items": serialized,
        "item_count": len(serialized),
        "type_counts": type_counts,
        "source_count": len(source_names),
        "notes": [],
    }


def corporate_actions_from_items(
    result,
    company_name: str | None,
) -> dict:
    """Serialize corporate actions extracted from intelligence events."""

    intel = getattr(result, "intelligence", None)

    actions = None
    if intel is not None:
        actions = _actions_result_dict(
            _business_events(intel),
            symbol=result.company,
            as_of=result.as_of,
        )

    return {
        "company": _company_envelope(result, company_name),
        "corporate_actions": actions,
    }


def corporate_actions_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize corporate actions for a company."""
    return corporate_actions_from_items(result, company_name)


# ── industry context ─────────────────────────────────────────────


def _industry_context_dict(ic) -> dict:
    return {
        "symbol": ic.symbol,
        "sector": ic.sector,
        "industry": ic.industry,
        "country": ic.country,
        "characteristics": [
            {
                "name": c.name,
                "description": c.description,
                "relevance": c.relevance,
            }
            for c in ic.characteristics
        ],
        "relevant_metrics": list(ic.relevant_metrics),
        "research_questions": [
            {
                "question": q.question,
                "category": q.category,
                "priority": q.priority,
            }
            for q in ic.research_questions
        ],
        "relevant_technology_areas": list(ic.relevant_technology_areas),
        "industry_risks": list(ic.industry_risks),
        "company_context": list(ic.company_context),
        "notes": list(ic.notes),
    }


def industry_context_from_model(
    result,
    ic,
    company_name: str | None,
) -> dict:
    """Serialize a pre-built IndustryContextResult."""

    return {
        "company": _company_envelope(result, company_name),
        "industry_context": _industry_context_dict(ic),
    }


def industry_context_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Build and serialize industry context for a company."""

    profile = BusinessProfile(
        symbol=result.company,
        sector=result.sector,
    )
    ic = build_industry_context(profile, result.company)

    return industry_context_from_model(result, ic, company_name)


# ── financial change tracking ────────────────────────────────────


def _period_to_snapshot(period) -> FinancialSnapshot | None:
    """Convert a FinancialPeriod to a FinancialSnapshot for analysis."""

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


def _financial_snapshots(intel) -> list[FinancialSnapshot]:
    """Extract deterministic period snapshots from an intelligence."""

    if intel is None:
        return []

    fi = getattr(intel, "financial_intelligence", None)
    if fi is None:
        return []

    snapshots: list[FinancialSnapshot] = []
    for period in fi.periods:
        snap = _period_to_snapshot(period)
        if snap is not None:
            snapshots.append(snap)

    snapshots.sort(key=lambda s: s.period_end)
    return snapshots


def _tracking_change_dict(change) -> dict:
    return {
        "change_id": change.change_id,
        "symbol": change.symbol,
        "domain": _enum_str(change.domain),
        "severity": _enum_str(change.severity),
        "title": change.title,
        "description": change.description,
        "previous_value": change.previous_value,
        "current_value": change.current_value,
        "change_date": _iso_date(change.change_date),
        "evidence_refs": list(change.evidence_refs),
        "source_names": list(change.source_names),
        "as_of": _utc_iso(change.as_of),
    }


def _tracking_dict(tracking) -> dict:
    return {
        "symbol": tracking.symbol,
        "as_of": _utc_iso(tracking.as_of),
        "changes": [
            _tracking_change_dict(c)
            for c in tracking.changes
        ],
        "change_count": tracking.change_count,
        "domain_counts": dict(tracking.domain_counts),
        "significant_count": tracking.significant_count,
        "notable_count": tracking.notable_count,
        "notes": list(tracking.notes),
    }


def tracking_from_model(
    result,
    tracking,
    company_name: str | None,
) -> dict:
    """Serialize a pre-built CompanyTrackingResult."""

    return {
        "company": _company_envelope(result, company_name),
        "tracking": _tracking_dict(tracking),
    }


def tracking_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Build and serialize financial change tracking for a company."""

    intel = getattr(result, "intelligence", None)
    snapshots = _financial_snapshots(intel)

    if snapshots:
        tracking = build_tracking_result(
            snapshots, result.company, result.as_of
        )
    else:
        tracking = CompanyTrackingResult(
            symbol=result.company,
            as_of=result.as_of,
            notes=(
                "No financial data available "
                "for tracking.",
            ),
        )

    return tracking_from_model(result, tracking, company_name)


__all__ = [
    "chart_data_contract",
    "chart_data_from_model",
    "company_info_dict",
    "corporate_actions_contract",
    "corporate_actions_from_items",
    "industry_context_contract",
    "industry_context_from_model",
    "news_contract",
    "news_from_items",
    "tracking_contract",
    "tracking_from_model",
]
