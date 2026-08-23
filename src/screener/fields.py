"""
Real-data field registry for the screener capability.

Every field that is marked available is computed from existing
recorded research data (financial periods, evidence, intelligence,
research gaps, source statuses, and recorded market bars).

Fields with no real data source (for example ownership and industry,
which the recorded fixtures do not carry) are registered as
UNAVAILABLE and are never executable filters. No fake filter
definitions are exposed.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum

from src.analysis.technical_indicators import compute_technical_indicators


class ScreenerFieldCategory(str, Enum):
    """Categories of screener fields backed by real data."""

    FUNDAMENTALS = "FUNDAMENTALS"
    GROWTH = "GROWTH"
    PROFITABILITY = "PROFITABILITY"
    CASH_FLOW = "CASH_FLOW"
    BALANCE_SHEET = "BALANCE_SHEET"
    MARKET = "MARKET"
    TECHNICAL = "TECHNICAL"
    OWNERSHIP = "OWNERSHIP"
    EVENTS = "EVENTS"
    RESEARCH_COVERAGE = "RESEARCH_COVERAGE"
    EVIDENCE_FRESHNESS = "EVIDENCE_FRESHNESS"
    PIT_AVAILABILITY = "PIT_AVAILABILITY"
    RESEARCH_GAPS = "RESEARCH_GAPS"
    TECHNOLOGY_EVIDENCE = "TECHNOLOGY_EVIDENCE"
    BUSINESS_EVIDENCE = "BUSINESS_EVIDENCE"
    SECTOR = "SECTOR"
    INDUSTRY = "INDUSTRY"


@dataclass(frozen=True)
class FieldDefinition:
    """Definition of one screener field."""

    name: str
    category: ScreenerFieldCategory
    label: str
    description: str
    value_type: str  # "number" | "integer" | "string" | "boolean"
    unit: str | None
    available: bool = True
    availability_note: str | None = None


def _field(
    name: str,
    category: ScreenerFieldCategory,
    label: str,
    description: str,
    value_type: str = "number",
    unit: str | None = None,
) -> FieldDefinition:
    return FieldDefinition(
        name=name,
        category=category,
        label=label,
        description=description,
        value_type=value_type,
        unit=unit,
        available=True,
    )


def _unavailable_field(
    name: str,
    category: ScreenerFieldCategory,
    label: str,
    note: str,
) -> FieldDefinition:
    return FieldDefinition(
        name=name,
        category=category,
        label=label,
        description=note,
        value_type="number",
        unit=None,
        available=False,
        availability_note=note,
    )


FIELD_REGISTRY: dict[str, FieldDefinition] = {}


def _register(*definitions: FieldDefinition) -> None:
    for definition in definitions:
        if definition.name in FIELD_REGISTRY:
            raise ValueError(
                f"duplicate screener field: {definition.name}"
            )
        FIELD_REGISTRY[definition.name] = definition


# ── Fundamentals ─────────────────────────────────────────────────

_register(
    _field(
        "revenue_latest",
        ScreenerFieldCategory.FUNDAMENTALS,
        "Revenue (latest period)",
        "Reported revenue for the latest financial period.",
    ),
    _field(
        "net_profit_latest",
        ScreenerFieldCategory.FUNDAMENTALS,
        "Net profit (latest period)",
        "Reported net profit for the latest financial period.",
    ),
    _field(
        "operating_profit_latest",
        ScreenerFieldCategory.FUNDAMENTALS,
        "Operating profit (latest period)",
        "Reported operating profit for the latest financial period.",
    ),
    _field(
        "total_assets_latest",
        ScreenerFieldCategory.FUNDAMENTALS,
        "Total assets (latest period)",
        "Reported total assets for the latest financial period.",
    ),
)

# ── Growth ───────────────────────────────────────────────────────

_register(
    _field(
        "revenue_change_pct",
        ScreenerFieldCategory.GROWTH,
        "Revenue change %",
        (
            "Percentage revenue change between the two most recent "
            "comparable reporting periods."
        ),
        unit="percent",
    ),
    _field(
        "net_profit_change_pct",
        ScreenerFieldCategory.GROWTH,
        "Net profit change %",
        (
            "Percentage net-profit change between the two most recent "
            "comparable reporting periods."
        ),
        unit="percent",
    ),
)

# ── Profitability ────────────────────────────────────────────────

_register(
    _field(
        "net_margin_pct",
        ScreenerFieldCategory.PROFITABILITY,
        "Net margin %",
        "Net profit divided by revenue for the latest period.",
        unit="percent",
    ),
    _field(
        "operating_margin_pct",
        ScreenerFieldCategory.PROFITABILITY,
        "Operating margin %",
        "Operating profit divided by revenue for the latest period.",
        unit="percent",
    ),
)

# ── Cash flow ────────────────────────────────────────────────────

_register(
    _field(
        "operating_cash_flow_latest",
        ScreenerFieldCategory.CASH_FLOW,
        "Operating cash flow (latest period)",
        "Reported operating cash flow for the latest financial period.",
    ),
    _field(
        "free_cash_flow_latest",
        ScreenerFieldCategory.CASH_FLOW,
        "Free cash flow (latest period)",
        "Reported free cash flow for the latest financial period.",
    ),
)

# ── Balance sheet ────────────────────────────────────────────────

_register(
    _field(
        "total_debt_latest",
        ScreenerFieldCategory.BALANCE_SHEET,
        "Total debt (latest period)",
        "Reported total debt for the latest financial period.",
    ),
    _field(
        "cash_and_equivalents_latest",
        ScreenerFieldCategory.BALANCE_SHEET,
        "Cash and equivalents (latest period)",
        (
            "Reported cash and equivalents for the latest "
            "financial period."
        ),
    ),
    _field(
        "debt_to_equity_pct",
        ScreenerFieldCategory.BALANCE_SHEET,
        "Debt to equity %",
        "Total debt divided by total equity for the latest period.",
        unit="percent",
    ),
    _field(
        "current_ratio",
        ScreenerFieldCategory.BALANCE_SHEET,
        "Current ratio",
        (
            "Current assets divided by current liabilities for the "
            "latest period."
        ),
        unit="ratio",
    ),
)

# ── Market ───────────────────────────────────────────────────────

_register(
    _field(
        "close_latest",
        ScreenerFieldCategory.MARKET,
        "Latest close",
        "Most recent recorded closing price.",
    ),
    _field(
        "return_1y_pct",
        ScreenerFieldCategory.MARKET,
        "1-year return %",
        "Recorded price return over the last ~250 trading bars.",
        unit="percent",
    ),
    _field(
        "high_52w",
        ScreenerFieldCategory.MARKET,
        "52-week high",
        "Highest recorded close over the available window.",
    ),
    _field(
        "low_52w",
        ScreenerFieldCategory.MARKET,
        "52-week low",
        "Lowest recorded close over the available window.",
    ),
)

# ── Technical ────────────────────────────────────────────────────

_register(
    _field(
        "sma_50",
        ScreenerFieldCategory.TECHNICAL,
        "50-bar SMA",
        "Simple moving average of closes over 50 bars.",
    ),
    _field(
        "rsi_14",
        ScreenerFieldCategory.TECHNICAL,
        "RSI (14)",
        "Relative strength index over 14 bars.",
    ),
)

# ── Ownership / Industry: real data not present in the recorded ──
#    research path. Registered as unavailable on purpose.

_register(
    _unavailable_field(
        "promoter_ownership_pct",
        ScreenerFieldCategory.OWNERSHIP,
        "Promoter ownership %",
        (
            "Ownership data is not present in the recorded research "
            "fixtures; no live provider is wired to this path yet."
        ),
    ),
    _unavailable_field(
        "institutional_ownership_pct",
        ScreenerFieldCategory.OWNERSHIP,
        "Institutional ownership %",
        (
            "Ownership data is not present in the recorded research "
            "fixtures; no live provider is wired to this path yet."
        ),
    ),
    _unavailable_field(
        "industry",
        ScreenerFieldCategory.INDUSTRY,
        "Industry",
        (
            "Industry classification is not present in the recorded "
            "research fixtures; only sector is available today."
        ),
    ),
)

# ── Events ───────────────────────────────────────────────────────

_register(
    _field(
        "event_count_90d",
        ScreenerFieldCategory.EVENTS,
        "Company events (90d)",
        (
            "Business events published within 90 days before as_of "
            "in the recorded intelligence snapshot."
        ),
        value_type="integer",
    ),
    _field(
        "corporate_action_count_90d",
        ScreenerFieldCategory.EVENTS,
        "Corporate actions (90d)",
        (
            "Corporate-action items published within 90 days before "
            "as_of in the recorded intelligence snapshot."
        ),
        value_type="integer",
    ),
)

# ── Research coverage ────────────────────────────────────────────

_register(
    _field(
        "intel_item_count",
        ScreenerFieldCategory.RESEARCH_COVERAGE,
        "Intelligence items",
        "Total evidence-based intelligence items at as_of.",
        value_type="integer",
    ),
    _field(
        "financial_period_count",
        ScreenerFieldCategory.RESEARCH_COVERAGE,
        "Financial periods",
        "Number of recorded reporting periods.",
        value_type="integer",
    ),
    _field(
        "evidence_item_count",
        ScreenerFieldCategory.RESEARCH_COVERAGE,
        "Evidence items",
        "Number of canonical evidence items at as_of.",
        value_type="integer",
    ),
)

# ── Evidence freshness ───────────────────────────────────────────

_register(
    _field(
        "days_since_latest_published",
        ScreenerFieldCategory.EVIDENCE_FRESHNESS,
        "Days since latest disclosure",
        (
            "Days between the latest published disclosure and as_of; "
            "null when nothing has been published."
        ),
        value_type="integer",
    ),
    _field(
        "stale_source_count",
        ScreenerFieldCategory.EVIDENCE_FRESHNESS,
        "Stale sources",
        (
            "Number of sources whose latest disclosure is more than "
            "90 days old at as_of."
        ),
        value_type="integer",
    ),
)

# ── PIT availability ─────────────────────────────────────────────

_register(
    _field(
        "pit_checks_passed",
        ScreenerFieldCategory.PIT_AVAILABILITY,
        "PIT checks passed",
        "True when every recorded point-in-time check passed at as_of.",
        value_type="boolean",
    ),
    _field(
        "future_evidence_excluded",
        ScreenerFieldCategory.PIT_AVAILABILITY,
        "Future evidence excluded",
        (
            "Count of point-in-time exclusions applied at as_of "
            "(0 when the recorded path excluded nothing)."
        ),
        value_type="integer",
    ),
)

# ── Research gaps ────────────────────────────────────────────────

_register(
    _field(
        "gap_count",
        ScreenerFieldCategory.RESEARCH_GAPS,
        "Research gaps",
        "Total number of detected research gaps.",
        value_type="integer",
    ),
    _field(
        "unavailable_gap_count",
        ScreenerFieldCategory.RESEARCH_GAPS,
        "Unavailable data gaps",
        "Research gaps whose status is UNAVAILABLE.",
        value_type="integer",
    ),
    _field(
        "gap_coverage_score",
        ScreenerFieldCategory.RESEARCH_GAPS,
        "Gap coverage score",
        "Descriptive coverage of the research itself: HIGH/MEDIUM/LOW.",
        value_type="string",
    ),
)

# ── Technology / business evidence ───────────────────────────────

_register(
    _field(
        "technology_evidence_count",
        ScreenerFieldCategory.TECHNOLOGY_EVIDENCE,
        "Technology evidence items",
        (
            "Canonical evidence items classified as future-technology "
            "evidence."
        ),
        value_type="integer",
    ),
    _field(
        "business_evidence_count",
        ScreenerFieldCategory.BUSINESS_EVIDENCE,
        "Business event items",
        "Recorded business-event intelligence items at as_of.",
        value_type="integer",
    ),
)

# ── Sector ───────────────────────────────────────────────────────

_register(
    _field(
        "sector",
        ScreenerFieldCategory.SECTOR,
        "Sector",
        "Registered sector of the company.",
        value_type="string",
    ),
)


AVAILABLE_FIELDS: tuple[str, ...] = tuple(
    name
    for name, definition in FIELD_REGISTRY.items()
    if definition.available
)

UNAVAILABLE_FIELDS: tuple[str, ...] = tuple(
    name
    for name, definition in FIELD_REGISTRY.items()
    if not definition.available
)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def _metric_decimal(metrics: dict, key: str) -> Decimal | None:
    value = metrics.get(key)
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _pct(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100


def _ratio_pct(numerator: Decimal | None, denominator: Decimal | None):
    if numerator is None or denominator is None or denominator == 0:
        return None
    return (numerator / denominator) * 100


def _latest_comparable_periods(periods):
    """
    Pick the latest period and its previous comparable period.

    Comparability requires the same period_type + consolidation scope;
    quarterly figures are never compared against annual figures.
    """

    if not periods:
        return None, None

    series: dict[tuple[str, str], list] = {}
    for period in periods:
        key = (
            period.period_type.value,
            period.consolidation.value,
        )
        series.setdefault(key, []).append(period)

    best_key = None
    best_latest = None
    for key, group in series.items():
        latest = max(group, key=lambda p: p.period_end)
        if best_latest is None or latest.period_end > best_latest.period_end:
            best_latest = latest
            best_key = key

    if best_latest is None:
        return None, None

    group = series[best_key]
    older = [p for p in group if p.period_end < best_latest.period_end]

    previous = max(older, key=lambda p: p.period_end) if older else None
    return best_latest, previous


def extract_market_bars(result) -> list:
    """
    Reconstruct validated PriceBar objects from the recorded market
    ingestion archive records, ordered oldest -> newest.
    """

    from src.data.models import PriceBar

    bars: list[PriceBar] = []

    accepted = getattr(getattr(result, "market_ingestion", None), "accepted", None)
    if not accepted:
        return bars

    for record in accepted:
        payload = getattr(record, "payload", None)
        if not isinstance(payload, dict):
            continue

        try:
            bars.append(PriceBar(**payload))
        except Exception:
            continue

    bars.sort(key=lambda bar: bar.trading_date)
    return bars


def extract_company_fields(result, service=None) -> dict[str, object]:
    """
    Compute every registered field value for one recorded research
    result. Unavailable fields are returned as None.

    Values are Decimal / int / str / bool / None — never fabricated.
    """

    values: dict[str, object] = {
        name: None for name in FIELD_REGISTRY
    }

    # ── Financial fields ─────────────────────────────────────────
    intel = result.intelligence
    fi = intel.financial_intelligence if intel else None
    periods = list(fi.periods) if fi is not None else []

    latest, previous = _latest_comparable_periods(periods)

    if latest is not None:
        metrics = latest.metrics
        values["revenue_latest"] = _metric_decimal(metrics, "revenue")
        values["net_profit_latest"] = _metric_decimal(metrics, "net_profit")
        values["operating_profit_latest"] = _metric_decimal(
            metrics, "operating_profit"
        )
        values["total_assets_latest"] = _metric_decimal(
            metrics, "total_assets"
        )
        values["operating_cash_flow_latest"] = _metric_decimal(
            metrics, "operating_cash_flow"
        )
        values["free_cash_flow_latest"] = _metric_decimal(
            metrics, "free_cash_flow"
        )
        values["total_debt_latest"] = _metric_decimal(metrics, "total_debt")
        values["cash_and_equivalents_latest"] = _metric_decimal(
            metrics, "cash_and_equivalents"
        )

        revenue = values["revenue_latest"]
        values["net_margin_pct"] = _ratio_pct(
            values["net_profit_latest"], revenue
        )
        values["operating_margin_pct"] = _ratio_pct(
            values["operating_profit_latest"], revenue
        )

        equity = _metric_decimal(metrics, "total_equity")
        if equity is None:
            equity = _metric_decimal(metrics, "shareholders_equity")

        debt = values["total_debt_latest"]
        if debt is not None and equity is not None and equity != 0:
            values["debt_to_equity_pct"] = (debt / equity) * 100

        current_assets = _metric_decimal(metrics, "current_assets")
        current_liabilities = _metric_decimal(metrics, "current_liabilities")
        if (
            current_assets is not None
            and current_liabilities is not None
            and current_liabilities != 0
        ):
            values["current_ratio"] = current_assets / current_liabilities

        values["financial_period_count"] = len(periods)

    if latest is not None and previous is not None:
        revenue_growth = _pct(
            _metric_decimal(latest.metrics, "revenue") or Decimal(0),
            _metric_decimal(previous.metrics, "revenue") or Decimal(0),
        ) if (
            _metric_decimal(latest.metrics, "revenue") is not None
            and _metric_decimal(previous.metrics, "revenue") is not None
        ) else None
        profit_growth = _pct(
            _metric_decimal(latest.metrics, "net_profit") or Decimal(0),
            _metric_decimal(previous.metrics, "net_profit") or Decimal(0),
        ) if (
            _metric_decimal(latest.metrics, "net_profit") is not None
            and _metric_decimal(previous.metrics, "net_profit") is not None
        ) else None

        values["revenue_change_pct"] = revenue_growth
        values["net_profit_change_pct"] = profit_growth

    # ── Evidence / intelligence fields ───────────────────────────
    if intel is not None:
        items = intel.items
        values["intel_item_count"] = len(items)
        values["business_evidence_count"] = len(intel.business_events)

        cutoff = result.as_of
        window_days = 90
        event_count = 0
        action_count = 0
        for item in items:
            stamp = item.published_at or item.available_at
            if stamp is None:
                continue
            if (cutoff - stamp).days > window_days:
                continue
            if item.intel_category is not None and item.intel_category.value == "CORPORATE_ACTION":
                action_count += 1
            else:
                event_count += 1

        values["event_count_90d"] = event_count
        values["corporate_action_count_90d"] = action_count

        status = intel.status
        if status is not None:
            values["days_since_latest_published"] = (
                status.freshness.days_since_latest_published
            )

        values["stale_source_count"] = sum(
            1 for s in intel.source_statuses if s.stale
        )

        gaps = intel.research_gaps
        if gaps is not None:
            values["gap_count"] = gaps.gap_count
            values["unavailable_gap_count"] = gaps.status_counts.get(
                "UNAVAILABLE", 0
            )
            values["gap_coverage_score"] = gaps.coverage_score

    technology_count = sum(
        1
        for item in result.evidence_items
        if item.evidence_type.value == "FUTURE_TECHNOLOGY"
    ) if result.evidence_items else 0
    values["technology_evidence_count"] = technology_count
    values["evidence_item_count"] = (
        len(result.evidence_items) if result.evidence_items else 0
    )

    # ── PIT availability ─────────────────────────────────────────
    pit_checks = result.pit_checks or {}
    bool_checks = [
        value for value in pit_checks.values() if isinstance(value, bool)
    ]
    values["pit_checks_passed"] = all(bool_checks) if bool_checks else None
    values["future_evidence_excluded"] = int(
        pit_checks.get("pit_future_evidence_excluded", 0) or 0
    )

    # ── Market / technical fields ────────────────────────────────
    bars = extract_market_bars(result)
    if bars:
        technical = compute_technical_indicators(bars)
        latest_bar = bars[-1]
        values["close_latest"] = latest_bar.close
        values["return_1y_pct"] = technical.return_200d
        values["high_52w"] = technical.high_low.high_52w
        values["low_52w"] = technical.high_low.low_52w
        values["sma_50"] = technical.sma.sma_50
        values["rsi_14"] = technical.rsi.rsi_14

    # ── Identity fields ──────────────────────────────────────────
    if service is not None:
        values["sector"] = service.company_sector(result.company)

    return values


def field_values_contract_dict(values: dict[str, object]) -> dict[str, str | None]:
    """Serialize extracted values into API-safe strings (None stays null)."""

    serialized: dict[str, str | None] = {}

    for name in FIELD_REGISTRY:
        value = values.get(name)

        if value is None:
            serialized[name] = None
        elif isinstance(value, bool):
            serialized[name] = "true" if value else "false"
        elif isinstance(value, float):
            serialized[name] = str(Decimal(str(value)))
        else:
            serialized[name] = str(value)

    return serialized


__all__ = [
    "AVAILABLE_FIELDS",
    "FIELD_REGISTRY",
    "FieldDefinition",
    "ScreenerFieldCategory",
    "UNAVAILABLE_FIELDS",
    "extract_company_fields",
    "extract_market_bars",
    "field_values_contract_dict",
]
