"""
Structured side-by-side company comparison.

Builds one deterministic comparison table from existing recorded
research results. Every cell either carries a recorded value with
its unit or an explicit unavailable null:

- profile: name / sector;
- financial history: reported metrics aligned by period end;
- derived metrics: latest deep-financial ratios with their units;
- events: recorded business-event and corporate-action counts;
- evidence: recorded evidence and technology-evidence counts;
- coverage: source freshness and research-gap state counts;
- sources: provenance completeness;
- observations: recorded research observations per company;
- conflicts: conflict summary per company;
- PIT consistency: shared vs mixed as_of disclosure.

There are deliberately NO winner/loser, score, or ranking fields:
the table states facts side by side and nothing else.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

_CATEGORY_ORDER = {
    "PROFILE": 0,
    "FINANCIALS": 1,
    "DERIVED": 2,
    "EVENTS": 3,
    "EVIDENCE": 4,
    "OBSERVATIONS": 5,
    "CONFLICTS": 6,
    "COVERAGE": 7,
    "SOURCES": 8,
    "PIT": 9,
}

_FINANCIAL_METRICS = (
    ("revenue", "Revenue"),
    ("net_profit", "Net profit"),
    ("operating_profit", "Operating profit"),
    ("total_assets", "Total assets"),
    ("total_debt", "Total debt"),
    ("operating_cash_flow", "Operating cash flow"),
)

_DERIVED_METRICS = (
    ("operating_margin", "Operating margin"),
    ("net_margin", "Net margin"),
    ("cash_conversion", "Cash conversion"),
    ("return_on_assets", "Return on assets"),
)

_MAX_ALIGNED_PERIODS = 3

_RECENT_EVENT_WINDOW_DAYS = 365


def _require_aware(as_of: datetime) -> None:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")


class ComparisonCell(BaseModel):
    """One symbol's value for one compared metric."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    value: str | None = None
    available: bool = False
    unit: str | None = None
    source: str | None = None
    provenance: tuple[str, ...] = ()


class ComparisonRow(BaseModel):
    """One compared metric across all requested companies."""

    model_config = ConfigDict(extra="forbid")

    metric: str = Field(min_length=1)
    label: str = Field(min_length=1)
    category: str = Field(min_length=1)

    # For FINANCIALS rows: the period end being compared.
    period_end: str | None = None

    cells: tuple[ComparisonCell, ...] = ()


class ComparisonCompany(BaseModel):
    """Header facts for one compared company."""

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)
    company_name: str | None = None
    sector: str | None = None


class CompanyComparison(BaseModel):
    """Deterministic side-by-side comparison of two or more companies."""

    model_config = ConfigDict(extra="forbid")

    comparison_context: str = "side_by_side"
    shared_as_of: datetime | None = None
    mixed_as_of_warning: str | None = None

    as_of: datetime
    companies: tuple[ComparisonCompany, ...] = ()
    rows: tuple[ComparisonRow, ...] = ()
    row_count: int = Field(ge=0)

    coverage_summary: dict[str, dict[str, int]] = Field(default_factory=dict)
    conflict_summary: dict[str, int] = Field(default_factory=dict)

    notes: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------


def _cells_for(
    symbols: tuple[str, ...],
    value_by_symbol: dict[str, tuple[str | None, str | None]],
) -> tuple[ComparisonCell, ...]:
    cells = []
    for symbol in symbols:
        value, unit = value_by_symbol.get(symbol, (None, None))
        cells.append(
            ComparisonCell(
                symbol=symbol,
                value=value,
                available=value is not None,
                unit=unit if value is not None else None,
            )
        )
    return tuple(cells)


def _financial_rows(
    results_by_symbol,
    symbols: tuple[str, ...],
) -> list[ComparisonRow]:
    # Collect period-end-aligned metrics across companies.
    metric_values: dict[tuple[str, str], dict[str, object]] = {}
    period_labels: dict[str, str] = {}

    for symbol, result in results_by_symbol.items():
        intel = result.intelligence
        fi = (
            intel.financial_intelligence
            if intel is not None
            else None
        )
        if fi is None:
            continue

        for period in fi.periods:
            key = period.period_end.isoformat()
            period_labels.setdefault(key, key)
            for metric, _ in _FINANCIAL_METRICS:
                value = period.metrics.get(metric)
                if value is not None:
                    metric_values.setdefault((metric, key), {})[
                        symbol
                    ] = value

    aligned_periods = sorted(period_labels)[
        -_MAX_ALIGNED_PERIODS:
    ]

    rows: list[ComparisonRow] = []
    for period_key in aligned_periods:
        for metric, label in _FINANCIAL_METRICS:
            by_symbol = metric_values.get((metric, period_key), {})
            serialized = {
                symbol: (str(value), "INR")
                for symbol, value in by_symbol.items()
            }
            rows.append(
                ComparisonRow(
                    metric=f"{metric}@{period_key}",
                    label=label,
                    category="FINANCIALS",
                    period_end=period_key,
                    cells=_cells_for(
                        symbols, serialized
                    ),
                )
            )

    return rows


def _derived_rows(
    results_by_symbol,
    symbols: tuple[str, ...],
) -> list[ComparisonRow]:
    rows: list[ComparisonRow] = []

    for metric, label in _DERIVED_METRICS:
        by_symbol: dict[str, tuple[str, str]] = {}

        for symbol, result in results_by_symbol.items():
            intel = result.intelligence
            insights = (
                intel.deep_financial_insights
                if intel is not None
                else None
            )
            if insights is None:
                continue

            best = None
            for observation in insights.observations:
                if observation.metric != metric:
                    continue
                if (
                    getattr(observation, "observation_type", None)
                    is not None
                    and getattr(observation.observation_type, "value", "")
                    == "UNAVAILABLE"
                ):
                    continue
                if observation.value is None:
                    continue
                if best is None or (
                    observation.period_end,
                    observation.observation_id,
                ) > (best.period_end, best.observation_id):
                    best = observation

            if best is not None:
                by_symbol[symbol] = (
                    str(best.value),
                    best.unit or "FRACTION",
                )

        rows.append(
            ComparisonRow(
                metric=metric,
                label=f"{label} (latest)",
                category="DERIVED",
                cells=_cells_for(symbols, by_symbol),
            )
        )

    return rows


def _fact_rows(
    results_by_symbol,
    as_of: datetime,
    symbols: tuple[str, ...],
) -> list[ComparisonRow]:
    rows: list[ComparisonRow] = []

    event_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}
    evidence_counts: dict[str, int] = {}
    tech_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    stale_counts: dict[str, int] = {}
    provenance_counts: dict[str, int] = {}
    gap_counts: dict[str, dict[str, int]] = {}
    coverage_counts: dict[str, int] = {}
    missing_category_counts: dict[str, int] = {}
    conflict_counts: dict[str, int] = {}
    freshness_stamps: dict[str, str | None] = {}

    cutoff = as_of.timestamp() - _RECENT_EVENT_WINDOW_DAYS * 86400

    for symbol, result in results_by_symbol.items():
        intel = result.intelligence
        items = list(intel.items) if intel is not None else []

        event_counts[symbol] = sum(
            1 for i in items if i.kind.value == "BUSINESS_EVENT"
        )
        action_counts[symbol] = sum(
            1
            for i in items
            if i.intel_category is not None
            and i.intel_category.value == "CORPORATE_ACTION"
        )

        evidence_counts[symbol] = len(result.evidence_items or ())
        tech_counts[symbol] = sum(
            1
            for e in result.evidence_items or ()
            if e.evidence_type.value == "FUTURE_TECHNOLOGY"
        )

        statuses = list(intel.source_statuses) if intel else []
        source_counts[symbol] = len(statuses)
        stale_counts[symbol] = sum(1 for s in statuses if s.stale)
        provenance_counts[symbol] = sum(
            1 for s in statuses if s.provenance_completeness
        )

        gaps = intel.research_gaps if intel is not None else None
        per_status: dict[str, int] = {}
        if gaps is not None:
            for gap in gaps.gaps:
                per_status[gap.status] = (
                    per_status.get(gap.status, 0) + 1
                )
        gap_counts[symbol] = per_status

        status = intel.status if intel is not None else None
        coverage_counts[symbol] = (
            status.coverage.item_count if status else 0
        )
        missing_category_counts[symbol] = (
            len(status.coverage.missing_categories) if status else 0
        )
        conflict_counts[symbol] = (
            status.quality.conflict_count if status else 0
        )
        newest = max(
            (
                i.published_at
                for i in items
                if i.published_at is not None
            ),
            default=None,
        )
        freshness_stamps[symbol] = (
            newest.isoformat() if newest is not None else None
        )

    def simple_row(metric, label, category, counts):
        return ComparisonRow(
            metric=metric,
            label=label,
            category=category,
            cells=_cells_for(
                symbols,
                {
                    s: (str(counts.get(s, 0)), "count")
                    for s in symbols
                    if s in counts
                },
            ),
        )

    rows.append(simple_row("business_events", "Business events recorded", "EVENTS", event_counts))
    rows.append(simple_row("corporate_actions", "Corporate actions recorded", "EVENTS", action_counts))
    rows.append(simple_row("evidence_items", "Evidence items", "EVIDENCE", evidence_counts))
    rows.append(simple_row("technology_evidence", "Technology evidence items", "EVIDENCE", tech_counts))
    rows.append(simple_row("sources", "Research sources", "COVERAGE", source_counts))
    rows.append(simple_row("stale_sources", "Stale sources", "COVERAGE", stale_counts))
    rows.append(simple_row("coverage_items", "Recorded coverage items", "COVERAGE", coverage_counts))
    rows.append(simple_row("missing_categories", "Missing research categories", "COVERAGE", missing_category_counts))
    rows.append(simple_row("conflicts_recorded", "Conflicting evidence pairs recorded", "EVIDENCE", conflict_counts))
    rows.append(simple_row("provenance_complete_sources", "Sources with complete provenance", "SOURCES", provenance_counts))

    # Freshness fact: newest published intel timestamp per company.
    rows.append(
        ComparisonRow(
            metric="newest_intel_published_at",
            label="Newest intelligence published at (UTC)",
            category="COVERAGE",
            cells=tuple(
                ComparisonCell(
                    symbol=s,
                    value=freshness_stamps.get(s),
                    available=freshness_stamps.get(s) is not None,
                )
                for s in symbols
            ),
        )
    )

    all_statuses = sorted(
        {status for per in gap_counts.values() for status in per}
    )
    for status in all_statuses:
        rows.append(
            ComparisonRow(
                metric=f"research_gaps_{status.lower()}",
                label=f"Research gaps ({status.lower()})",
                category="COVERAGE",
                cells=_cells_for(
                    symbols,
                    {
                        s: (
                            str(per.get(status, 0)),
                            "count",
                        )
                        for s, per in gap_counts.items()
                    },
                ),
            )
        )

    return rows


def build_company_comparison(
    results,
    *,
    as_of: datetime,
    company_names: dict[str, str] | None = None,
) -> CompanyComparison:
    """
    Build the canonical side-by-side comparison.

    results: iterable of recorded research results (at least two).
    """

    _require_aware(as_of)

    results_by_symbol: dict[str, object] = {}
    sectors: dict[str, str | None] = {}
    for result in results:
        symbol = result.company.strip().upper()
        if symbol in results_by_symbol:
            raise ValueError(f"duplicate symbol in comparison: {symbol}")
        results_by_symbol[symbol] = result
        sectors[symbol] = getattr(result, "sector", None)

    if len(results_by_symbol) < 2:
        raise ValueError(
            "comparison requires at least two distinct companies"
        )

    symbols = tuple(sorted(results_by_symbol))

    companies = tuple(
        ComparisonCompany(
            symbol=symbol,
            company_name=(
                company_names.get(symbol)
                if company_names
                else None
            ),
            sector=sectors.get(symbol),
        )
        for symbol in symbols
    )

    profile_rows = [
        ComparisonRow(
            metric="sector",
            label="Sector",
            category="PROFILE",
            cells=tuple(
                ComparisonCell(
                    symbol=s,
                    value=sectors.get(s),
                    available=bool(sectors.get(s)),
                )
                for s in symbols
            ),
        )
    ]

    rows = (
        profile_rows
        + _financial_rows(results_by_symbol, symbols)
        + _derived_rows(results_by_symbol, symbols)
        + _fact_rows(results_by_symbol, as_of, symbols)
    )

    rows.sort(key=lambda r: (_CATEGORY_ORDER.get(r.category, 99), r.metric))

    # Coverage summary per company.
    coverage_summary: dict[str, dict[str, int]] = {}
    conflict_summary: dict[str, int] = {}
    for symbol, result in results_by_symbol.items():
        intel = result.intelligence
        status = intel.status if intel is not None else None
        if status is not None:
            coverage_summary[symbol] = dict(sorted(status.coverage.by_kind.items())) if hasattr(status.coverage, 'by_kind') else {}
        else:
            coverage_summary[symbol] = {}
        conflict_summary[symbol] = (
            status.quality.conflict_count if status is not None and hasattr(status, 'quality') else 0
        )

    # Determine PIT consistency.
    mismatched = sorted(
        symbol
        for symbol, result in results_by_symbol.items()
        if result.as_of != as_of
    )
    shared_as_of = as_of if not mismatched else None
    mixed_as_of_warning = None
    if mismatched:
        mixed_as_of_warning = (
            "Point-in-time notice: recorded state for "
            + ", ".join(mismatched)
            + " was captured at an earlier as_of than the comparison "
            "timestamp; cells for those companies reflect their own "
            "recorded as_of."
        )

    notes = [
        "Comparison states recorded facts side by side. It does not "
        "judge, rate, or advise.",
        "Missing cells are genuinely unavailable in the recorded "
        "data at as_of.",
    ]

    if mismatched:
        notes.append(mixed_as_of_warning)
    else:
        notes.append(
            "All compared states were captured at the same point in "
            "time (as_of), so columns are directly comparable."
        )

    return CompanyComparison(
        comparison_context="side_by_side",
        shared_as_of=shared_as_of,
        mixed_as_of_warning=mixed_as_of_warning,
        as_of=as_of,
        companies=companies,
        rows=tuple(rows),
        row_count=len(rows),
        coverage_summary=dict(sorted(coverage_summary.items())),
        conflict_summary=dict(sorted(conflict_summary.items())),
        notes=tuple(notes),
    )


__all__ = [
    "ComparisonCell",
    "ComparisonCompany",
    "ComparisonRow",
    "CompanyComparison",
    "build_company_comparison",
]
