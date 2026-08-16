from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from src.data.company.financials import (
    FinancialSnapshot,
    SegmentResult,
)
from src.research.company_intel import (
    build_financial_intelligence,
    derived_metric_items,
    financial_periods_from_snapshots,
    financial_periods_to_items,
)
from src.research.company_intel.semantics import (
    ConsolidationScope,
    FinancialStatementType,
    ReportingPeriodType,
    SemanticCategory,
)

from .conftest import AS_OF, make_item, ts


def _snapshot(
    *,
    symbol: str = "TCS",
    period_end: date,
    revenue: str | None = "100",
    operating_profit: str | None = "20",
    net_profit: str | None = "20",
    operating_cash_flow: str | None = "25",
    total_assets: str | None = "500",
    available_at: datetime | None = AS_OF,
    period_type: str | None = None,
    consolidation: str | None = None,
) -> FinancialSnapshot:
    kwargs: dict = {
        "symbol": symbol,
        "period_end": period_end,
        "revenue": revenue,
        "operating_profit": operating_profit,
        "net_profit": net_profit,
        "operating_cash_flow": operating_cash_flow,
        "total_assets": total_assets,
        "available_at": available_at,
    }

    if period_type is not None:
        kwargs["period_type"] = period_type
    if consolidation is not None:
        kwargs["consolidation"] = consolidation

    return FinancialSnapshot(**kwargs)


def test_annual_period_inference_from_recorded_fixture():
    ends = [
        date(2023, 3, 31),
        date(2024, 3, 31),
        date(2025, 3, 31),
        date(2026, 3, 31),
    ]

    snapshots = [
        _snapshot(period_end=end)
        for end in ends
    ]

    periods = financial_periods_from_snapshots(
        snapshots,
        as_of=AS_OF,
    )

    assert len(periods) == 4
    assert all(
        period.period_type == ReportingPeriodType.ANNUAL
        for period in periods
    )
    assert periods[0].metrics["revenue"] is not None


def test_quarterly_period_inference():
    snapshots = [
        _snapshot(
            period_end=date(2025, 6, 30),
            available_at=ts(2025, 7, 15),
        ),
        _snapshot(
            period_end=date(2025, 9, 30),
            available_at=ts(2025, 10, 15),
        ),
        _snapshot(
            period_end=date(2025, 12, 31),
            available_at=ts(2026, 1, 15),
        ),
        _snapshot(
            period_end=date(2026, 3, 31),
            available_at=ts(2026, 4, 15),
        ),
    ]

    periods = financial_periods_from_snapshots(
        snapshots,
        as_of=AS_OF,
    )

    assert len(periods) == 4
    assert all(
        period.period_type == ReportingPeriodType.QUARTERLY
        for period in periods
    )


def test_explicit_period_type_wins_over_inference():
    snapshots = [
        _snapshot(
            period_end=date(2026, 3, 31),
            period_type="ANNUAL",
        ),
        _snapshot(
            period_end=date(2025, 3, 31),
            period_type="ANNUAL",
        ),
    ]

    periods = financial_periods_from_snapshots(
        snapshots,
        as_of=AS_OF,
    )

    assert all(
        period.period_type == ReportingPeriodType.ANNUAL
        for period in periods
    )


def test_consolidation_scope_is_preserved():
    snapshots = [
        _snapshot(
            period_end=date(2026, 3, 31),
            period_type="ANNUAL",
            consolidation="CONSOLIDATED",
        ),
        _snapshot(
            period_end=date(2026, 3, 31),
            period_type="ANNUAL",
            consolidation="STANDALONE",
        ),
    ]

    periods = financial_periods_from_snapshots(
        snapshots,
        as_of=AS_OF,
    )

    assert len(periods) == 2

    scopes = {period.consolidation for period in periods}

    assert scopes == {
        ConsolidationScope.CONSOLIDATED,
        ConsolidationScope.STANDALONE,
    }


def test_statements_split_by_statement_type():
    periods = financial_periods_from_snapshots(
        [_snapshot(period_end=date(2026, 3, 31))],
        as_of=AS_OF,
    )

    statements = periods[0].statements

    types = {statement.statement_type for statement in statements}

    assert FinancialStatementType.INCOME_STATEMENT in types
    assert FinancialStatementType.BALANCE_SHEET in types
    assert FinancialStatementType.CASH_FLOW_STATEMENT in types


def test_future_period_end_is_excluded():
    snapshots = [
        _snapshot(
            period_end=date(2026, 12, 31),
            available_at=ts(2027, 1, 15),
        ),
        _snapshot(period_end=date(2026, 3, 31)),
    ]

    periods = financial_periods_from_snapshots(
        snapshots,
        as_of=AS_OF,
    )

    assert len(periods) == 1
    assert periods[0].period_end == date(2026, 3, 31)


def test_snapshot_available_after_as_of_is_excluded():
    snapshots = [
        _snapshot(
            period_end=date(2026, 6, 30),
            available_at=ts(2026, 9, 1),
        ),
    ]

    periods = financial_periods_from_snapshots(
        snapshots,
        as_of=AS_OF,
    )

    assert periods == ()


def test_default_available_at_applies_when_missing():
    snapshots = [
        _snapshot(
            period_end=date(2026, 3, 31),
            available_at=None,
        ),
    ]

    periods = financial_periods_from_snapshots(
        snapshots,
        as_of=AS_OF,
        default_available_at=ts(2026, 4, 1),
    )

    assert len(periods) == 1
    assert periods[0].available_at == ts(2026, 4, 1)


def test_build_financial_intelligence_counts_and_coverage():
    snapshots = [
        _snapshot(
            period_end=date(2025, 3, 31),
            period_type="ANNUAL",
        ),
        _snapshot(
            period_end=date(2026, 3, 31),
            period_type="ANNUAL",
        ),
    ]

    periods = financial_periods_from_snapshots(
        snapshots,
        as_of=AS_OF,
    )

    summary = build_financial_intelligence(
        "TCS",
        periods,
        as_of=AS_OF,
    )

    assert summary.period_count == 2
    assert summary.annual_count == 2
    assert summary.quarterly_count == 0
    assert summary.latest_period_end == date(2026, 3, 31)
    assert summary.earliest_period_end == date(2025, 3, 31)
    assert summary.coverage["revenue"] == 2
    assert summary.coverage["total_assets"] == 2


def test_build_financial_intelligence_mixed_period_note():
    snapshots = [
        _snapshot(
            period_end=date(2026, 3, 31),
            period_type="ANNUAL",
        ),
        _snapshot(
            period_end=date(2026, 6, 30),
            period_type="QUARTERLY",
            available_at=ts(2026, 7, 15),
        ),
    ]

    periods = financial_periods_from_snapshots(
        snapshots,
        as_of=AS_OF,
    )

    summary = build_financial_intelligence(
        "TCS",
        periods,
        as_of=AS_OF,
    )

    assert any(
        "Quarterly and annual" in note
        for note in summary.notes
    )


def test_mixed_consolidation_note():
    snapshots = [
        _snapshot(
            period_end=date(2026, 3, 31),
            period_type="ANNUAL",
            consolidation="CONSOLIDATED",
        ),
        _snapshot(
            period_end=date(2026, 3, 31),
            period_type="ANNUAL",
            consolidation="STANDALONE",
        ),
    ]

    periods = financial_periods_from_snapshots(
        snapshots,
        as_of=AS_OF,
    )

    summary = build_financial_intelligence(
        "TCS",
        periods,
        as_of=AS_OF,
    )

    assert any(
        "consolidated and standalone" in note
        for note in summary.notes
    )


def test_financial_periods_to_items_are_facts():
    periods = financial_periods_from_snapshots(
        [_snapshot(period_end=date(2026, 3, 31))],
        as_of=AS_OF,
    )

    items = financial_periods_to_items(
        periods,
        as_of=AS_OF,
    )

    assert len(items) == 1
    assert items[0].semantic_category == SemanticCategory.FACT
    assert items[0].verification_status.value == "CONFIRMED"


def test_derived_metric_items_are_derived_metrics():
    periods = financial_periods_from_snapshots(
        [_snapshot(period_end=date(2026, 3, 31))],
        as_of=AS_OF,
    )

    items = derived_metric_items(
        periods,
        as_of=AS_OF,
    )

    assert len(items) == 2

    for item in items:
        assert (
            item.semantic_category
            == SemanticCategory.DERIVED_METRIC
        )

    margin = [
        item
        for item in items
        if "margin" in item.item_id
    ][0]

    assert "operating margin" in margin.title
    assert "0.2" in margin.description


def test_segments_and_subsidiaries_are_preserved():
    snapshot = _snapshot(period_end=date(2026, 3, 31)).model_copy(
        update={
            "segments": (
                SegmentResult(
                    segment_name="Banking",
                    revenue=Decimal("50"),
                    profit=Decimal("10"),
                ),
                SegmentResult(
                    segment_name="Software",
                    revenue=Decimal("50"),
                    profit=Decimal("10"),
                ),
            ),
            "subsidiaries": ("tcs-digital",),
        }
    )

    periods = financial_periods_from_snapshots(
        [snapshot],
        as_of=AS_OF,
    )

    period = periods[0]

    assert len(period.segments) == 2
    assert period.segments[0].segment_name == "Banking"
    assert period.subsidiaries == ("tcs-digital",)

    statements = period.statements

    assert all(
        statement.subsidiaries == ("tcs-digital",)
        for statement in statements
    )

    income = [
        statement
        for statement in statements
        if statement.statement_type
        == FinancialStatementType.INCOME_STATEMENT
    ][0]

    assert len(income.segments) == 2


def test_effective_at_is_carried_to_period_and_statements():
    snapshot = _snapshot(
        period_end=date(2026, 3, 31),
        period_type="ANNUAL",
    ).model_copy(
        update={
            "published_at": ts(2026, 4, 30),
            "effective_at": ts(2026, 3, 31),
        }
    )

    periods = financial_periods_from_snapshots(
        [snapshot],
        as_of=AS_OF,
    )

    period = periods[0]

    assert period.published_at == ts(2026, 4, 30)
    assert period.effective_at == ts(2026, 3, 31)

    assert all(
        statement.effective_at == ts(2026, 3, 31)
        for statement in period.statements
    )


def test_extra_line_items_are_bucketed_by_statement_type():
    snapshot = _snapshot(period_end=date(2026, 3, 31)).model_copy(
        update={
            "items": {
                "gross_profit": Decimal("40"),
                "inventory": Decimal("60"),
                "capex": Decimal("5"),
                "mystery_metric": Decimal("7"),
            }
        }
    )

    periods = financial_periods_from_snapshots(
        [snapshot],
        as_of=AS_OF,
    )

    statements = periods[0].statements

    buckets = {
        statement.statement_type: statement
        for statement in statements
    }

    assert "gross_profit" in buckets[
        FinancialStatementType.INCOME_STATEMENT
    ].items
    assert "inventory" in buckets[
        FinancialStatementType.BALANCE_SHEET
    ].items
    assert "capex" in buckets[
        FinancialStatementType.CASH_FLOW_STATEMENT
    ].items

    other = buckets[FinancialStatementType.OTHER]

    assert "mystery_metric" in other.items
    assert other.statement_id.endswith("-OT")


def test_financial_intelligence_counts_segments_and_subsidiaries():
    snapshot = _snapshot(period_end=date(2026, 3, 31)).model_copy(
        update={
            "segments": (
                SegmentResult(
                    segment_name="Banking",
                    revenue=Decimal("50"),
                ),
            ),
            "subsidiaries": ("tcs-digital",),
        }
    )

    periods = financial_periods_from_snapshots(
        [snapshot],
        as_of=AS_OF,
    )

    summary = build_financial_intelligence(
        "TCS",
        periods,
        as_of=AS_OF,
    )

    assert summary.statement_count == 1
    assert summary.segment_count == 1
    assert summary.subsidiary_count == 1
    assert any(
        "Business-segment detail" in note
        for note in summary.notes
    )
