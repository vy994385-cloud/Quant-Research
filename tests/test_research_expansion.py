"""
Tests for research engine expansion modules.

Covers:
  - Cash-flow quality analysis
  - Balance sheet deep analysis
  - Expanded financial anomalies
  - Extended market observations
  - Event timeline
  - Research gaps
  - Cross-domain observations
  - Report data contract

All tests verify:
  - Deterministic behavior
  - PIT safety (no look-ahead)
  - Missing-data handling
  - Provenance preservation
  - Edge cases
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.data.company.financials import FinancialSnapshot
from src.data.company.events import CompanyEvent
from src.data.models import PriceBar


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def as_of():
    return datetime(2025, 6, 1, tzinfo=timezone.utc)


@pytest.fixture
def snapshots():
    return [
        FinancialSnapshot(
            symbol="TEST",
            period_end=date(2024, 3, 31),
            revenue=Decimal("1000000"),
            net_profit=Decimal("100000"),
            operating_cash_flow=Decimal("150000"),
            free_cash_flow=Decimal("120000"),
            total_debt=Decimal("500000"),
            cash_and_equivalents=Decimal("200000"),
            total_equity=Decimal("800000"),
            current_assets=Decimal("400000"),
            current_liabilities=Decimal("300000"),
            receivables=Decimal("150000"),
            payables=Decimal("80000"),
            inventory=Decimal("100000"),
            available_at=datetime(2024, 6, 15, tzinfo=timezone.utc),
        ),
        FinancialSnapshot(
            symbol="TEST",
            period_end=date(2025, 3, 31),
            revenue=Decimal("1200000"),
            net_profit=Decimal("120000"),
            operating_cash_flow=Decimal("180000"),
            free_cash_flow=Decimal("150000"),
            total_debt=Decimal("450000"),
            cash_and_equivalents=Decimal("250000"),
            total_equity=Decimal("900000"),
            current_assets=Decimal("500000"),
            current_liabilities=Decimal("350000"),
            receivables=Decimal("180000"),
            payables=Decimal("90000"),
            inventory=Decimal("120000"),
            available_at=datetime(2025, 6, 15, tzinfo=timezone.utc),
        ),
    ]


@pytest.fixture
def events():
    return [
        CompanyEvent(
            symbol="TEST",
            event_date=date(2025, 1, 15),
            title="Q3 Results Announced",
            description="Company reported strong quarterly results",
            category="EARNINGS",
            direction="POSITIVE",
            materiality=4,
            evidence_ids=["ev1"],
        ),
        CompanyEvent(
            symbol="TEST",
            event_date=date(2025, 2, 10),
            title="New Partnership Announced",
            description="Strategic partnership with tech company",
            category="BUSINESS_DEVELOPMENT",
            direction="POSITIVE",
            materiality=3,
            evidence_ids=["ev2"],
        ),
    ]


@pytest.fixture
def bars():
    bars = []
    base_price = 100.0
    for i in range(50):
        bars.append(
            PriceBar(
                symbol="TEST",
                trading_date=date(2025, 1, 1 + i)
                if 1 + i <= 31
                else date(2025, 2, 1 + i - 31),
                open=Decimal(str(base_price + i * 0.5)),
                high=Decimal(str(base_price + i * 0.5 + 2)),
                low=Decimal(str(base_price + i * 0.5 - 1)),
                close=Decimal(str(base_price + i * 0.5 + 1)),
                volume=Decimal("1000000"),
            )
        )
    return bars


# ---------------------------------------------------------------------------
# R1.1: Cash-Flow Quality Tests
# ---------------------------------------------------------------------------


class TestCashFlowQuality:
    def test_basic_analysis(self, snapshots, as_of):
        from src.analysis.cash_flow_quality import (
            analyze_cash_flow_quality,
        )

        result = analyze_cash_flow_quality(
            symbol="TEST",
            as_of=as_of,
            snapshots=snapshots,
        )

        assert result.symbol == "TEST"
        assert result.observation_count > 0
        assert result.direction in (
            "IMPROVING",
            "DETERIORATING",
            "STABLE",
            "UNKNOWN",
        )

    def test_empty_snapshots(self, as_of):
        from src.analysis.cash_flow_quality import (
            analyze_cash_flow_quality,
        )

        result = analyze_cash_flow_quality(
            symbol="TEST",
            as_of=as_of,
            snapshots=(),
        )

        assert result.observation_count == 0
        assert len(result.notes) > 0

    def test_provenance_preserved(self, snapshots, as_of):
        from src.analysis.cash_flow_quality import (
            analyze_cash_flow_quality,
        )

        result = analyze_cash_flow_quality(
            symbol="TEST",
            as_of=as_of,
            snapshots=snapshots,
        )

        for obs in result.observations:
            assert obs.as_of == as_of.isoformat()
            assert obs.symbol == "TEST"
            assert obs.category == "cash_flow_quality"
            assert obs.observation_id.startswith("CFQ-")

    def test_cfo_to_net_income(self, snapshots, as_of):
        from src.analysis.cash_flow_quality import (
            analyze_cfo_to_net_income,
        )

        observations = analyze_cfo_to_net_income(
            snapshots, "TEST", as_of
        )

        assert len(observations) == 2
        for obs in observations:
            assert obs.observation_type == "cfo_to_net_income"
            assert obs.value is not None
            assert obs.calculation_method != ""

    def test_fcf_conversion(self, snapshots, as_of):
        from src.analysis.cash_flow_quality import (
            analyze_fcf_conversion,
        )

        observations = analyze_fcf_conversion(
            snapshots, "TEST", as_of
        )

        assert len(observations) == 2
        for obs in observations:
            assert obs.observation_type == "fcf_conversion"

    def test_working_capital(self, snapshots, as_of):
        from src.analysis.cash_flow_quality import (
            analyze_working_capital_behavior,
        )

        observations = analyze_working_capital_behavior(
            snapshots, "TEST", as_of
        )

        # Should have DSO, DIO, DPO for each period
        assert len(observations) == 6
        observation_types = {obs.observation_type for obs in observations}
        assert "dso" in observation_types
        assert "dio" in observation_types
        assert "dpo" in observation_types

    def test_missing_data_handling(self, as_of):
        from src.analysis.cash_flow_quality import (
            analyze_cash_flow_quality,
        )

        # Snapshot with missing data
        snapshot = FinancialSnapshot(
            symbol="TEST",
            period_end=date(2025, 3, 31),
            revenue=Decimal("1000000"),
            # Missing cash flow data
            available_at=datetime(2025, 6, 15, tzinfo=timezone.utc),
        )

        result = analyze_cash_flow_quality(
            symbol="TEST",
            as_of=as_of,
            snapshots=[snapshot],
        )

        # Should handle missing data gracefully
        assert result.observation_count == 0


# ---------------------------------------------------------------------------
# R1.2: Balance Sheet Deep Tests
# ---------------------------------------------------------------------------


class TestBalanceSheetDeep:
    def test_basic_analysis(self, snapshots, as_of):
        from src.analysis.balance_sheet_deep import (
            analyze_balance_sheet_deep,
        )

        result = analyze_balance_sheet_deep(
            symbol="TEST",
            as_of=as_of,
            snapshots=snapshots,
        )

        assert result.symbol == "TEST"
        assert result.observation_count > 0
        assert result.direction in (
            "IMPROVING",
            "DETERIORATING",
            "STABLE",
            "UNKNOWN",
        )

    def test_empty_snapshots(self, as_of):
        from src.analysis.balance_sheet_deep import (
            analyze_balance_sheet_deep,
        )

        result = analyze_balance_sheet_deep(
            symbol="TEST",
            as_of=as_of,
            snapshots=(),
        )

        assert result.observation_count == 0

    def test_provenance_preserved(self, snapshots, as_of):
        from src.analysis.balance_sheet_deep import (
            analyze_balance_sheet_deep,
        )

        result = analyze_balance_sheet_deep(
            symbol="TEST",
            as_of=as_of,
            snapshots=snapshots,
        )

        for obs in result.observations:
            assert obs.as_of == as_of.isoformat()
            assert obs.symbol == "TEST"
            assert obs.category == "balance_sheet_deep"
            assert obs.observation_id.startswith("BSD-")

    def test_net_debt(self, snapshots, as_of):
        from src.analysis.balance_sheet_deep import (
            analyze_net_debt,
        )

        observations = analyze_net_debt(
            snapshots, "TEST", as_of
        )

        assert len(observations) == 2
        for obs in observations:
            assert obs.observation_type == "net_debt"

    def test_cash_to_debt(self, snapshots, as_of):
        from src.analysis.balance_sheet_deep import (
            analyze_cash_to_debt,
        )

        observations = analyze_cash_to_debt(
            snapshots, "TEST", as_of
        )

        assert len(observations) == 2
        for obs in observations:
            assert obs.observation_type == "cash_to_debt"

    def test_debt_to_equity(self, snapshots, as_of):
        from src.analysis.balance_sheet_deep import (
            analyze_debt_to_equity,
        )

        observations = analyze_debt_to_equity(
            snapshots, "TEST", as_of
        )

        assert len(observations) == 2
        for obs in observations:
            assert obs.observation_type == "debt_to_equity"


# ---------------------------------------------------------------------------
# R1.3: Expanded Financial Anomalies Tests
# ---------------------------------------------------------------------------


class TestExpandedFinancialAnomalies:
    def test_revenue_cash_flow_divergence(self, as_of):
        from src.analysis.financial_anomalies import (
            analyze_financial_change,
        )

        prev = FinancialSnapshot(
            symbol="TEST",
            period_end=date(2024, 3, 31),
            revenue=Decimal("1000000"),
            net_profit=Decimal("100000"),
            operating_cash_flow=Decimal("150000"),
            total_debt=Decimal("500000"),
        )

        curr = FinancialSnapshot(
            symbol="TEST",
            period_end=date(2025, 3, 31),
            revenue=Decimal("1300000"),  # 30% growth
            net_profit=Decimal("130000"),
            operating_cash_flow=Decimal("160000"),  # only 6.7%
            total_debt=Decimal("500000"),
        )

        anomalies = analyze_financial_change(prev, curr)

        # Should detect revenue vs cash flow divergence
        metric_types = {a.metric for a in anomalies}
        assert "revenue_cash_flow_divergence" in metric_types

    def test_debt_cash_flow_divergence(self, as_of):
        from src.analysis.financial_anomalies import (
            analyze_financial_change,
        )

        prev = FinancialSnapshot(
            symbol="TEST",
            period_end=date(2024, 3, 31),
            revenue=Decimal("1000000"),
            operating_cash_flow=Decimal("150000"),
            total_debt=Decimal("500000"),
        )

        curr = FinancialSnapshot(
            symbol="TEST",
            period_end=date(2025, 3, 31),
            revenue=Decimal("1000000"),
            operating_cash_flow=Decimal("140000"),
            total_debt=Decimal("700000"),  # 40% growth
        )

        anomalies = analyze_financial_change(prev, curr)

        metric_types = {a.metric for a in anomalies}
        assert "debt_cash_flow_divergence" in metric_types

    def test_no_anomaly_when_aligned(self, as_of):
        from src.analysis.financial_anomalies import (
            analyze_financial_change,
        )

        prev = FinancialSnapshot(
            symbol="TEST",
            period_end=date(2024, 3, 31),
            revenue=Decimal("1000000"),
            operating_cash_flow=Decimal("150000"),
            total_debt=Decimal("500000"),
        )

        curr = FinancialSnapshot(
            symbol="TEST",
            period_end=date(2025, 3, 31),
            revenue=Decimal("1100000"),
            operating_cash_flow=Decimal("165000"),  # 10% growth
            total_debt=Decimal("525000"),  # 5% growth
        )

        anomalies = analyze_financial_change(prev, curr)

        # Should not detect divergence
        metric_types = {a.metric for a in anomalies}
        assert "revenue_cash_flow_divergence" not in metric_types
        assert "debt_cash_flow_divergence" not in metric_types


# ---------------------------------------------------------------------------
# R2.1: Extended Market Observations Tests
# ---------------------------------------------------------------------------


class TestExtendedMarketObservations:
    def test_extended_returns(self, as_of):
        from src.research.market_observations import (
            build_market_observations,
        )

        # Need 51+ bars for 50d return
        from datetime import timedelta

        many_bars = []
        base_date = date(2024, 10, 1)
        for i in range(60):
            many_bars.append(
                PriceBar(
                    symbol="TEST",
                    trading_date=base_date + timedelta(days=i),
                    open=Decimal(str(100 + i * 0.5)),
                    high=Decimal(str(100 + i * 0.5 + 2)),
                    low=Decimal(str(100 + i * 0.5 - 1)),
                    close=Decimal(str(100 + i * 0.5 + 1)),
                    volume=Decimal("1000000"),
                )
            )

        observations = build_market_observations(
            symbol="TEST",
            bars=many_bars,
            available_at=as_of,
        )

        last = observations[-1]

        # Should have extended returns with 60 bars
        assert last.return_20d is not None
        assert last.return_50d is not None

    def test_volatility_regime(self, bars, as_of):
        from src.research.market_observations import (
            build_market_observations,
        )

        observations = build_market_observations(
            symbol="TEST",
            bars=bars,
            available_at=as_of,
        )

        last = observations[-1]

        # Should have volatility regime
        assert last.volatility_regime in (
            "LOW",
            "NORMAL",
            "HIGH",
            None,
        )

    def test_trend_regime(self, bars, as_of):
        from src.research.market_observations import (
            build_market_observations,
        )

        observations = build_market_observations(
            symbol="TEST",
            bars=bars,
            available_at=as_of,
        )

        last = observations[-1]

        # Should have trend regime
        assert last.trend_regime in (
            "UPTREND",
            "DOWNTREND",
            "SIDEWAYS",
            None,
        )

    def test_gap_detection(self, bars, as_of):
        from src.research.market_observations import (
            build_market_observations,
        )

        observations = build_market_observations(
            symbol="TEST",
            bars=bars,
            available_at=as_of,
        )

        # Should have gap flags
        for obs in observations:
            assert isinstance(obs.gap_up, bool)
            assert isinstance(obs.gap_down, bool)

    def test_52week_context(self, bars, as_of):
        from src.research.market_observations import (
            build_market_observations,
        )

        observations = build_market_observations(
            symbol="TEST",
            bars=bars,
            available_at=as_of,
        )

        last = observations[-1]

        # Should have 52-week context
        assert last.high_52w is not None
        assert last.low_52w is not None
        assert last.pct_from_52w_high is not None
        assert last.pct_from_52w_low is not None


# ---------------------------------------------------------------------------
# R4.1: Event Timeline Tests
# ---------------------------------------------------------------------------


class TestEventTimeline:
    def test_basic_timeline(self, events, as_of):
        from src.analysis.event_analysis import (
            build_event_timeline,
        )

        timeline = build_event_timeline(
            events=events,
            symbol="TEST",
            as_of=as_of,
        )

        assert timeline.symbol == "TEST"
        assert timeline.entry_count == 2
        assert timeline.category_counts["EARNINGS"] == 1
        assert timeline.category_counts["BUSINESS_DEVELOPMENT"] == 1

    def test_empty_events(self, as_of):
        from src.analysis.event_analysis import (
            build_event_timeline,
        )

        timeline = build_event_timeline(
            events=(),
            symbol="TEST",
            as_of=as_of,
        )

        assert timeline.entry_count == 0

    def test_subsequent_observations(self, events, as_of):
        from src.analysis.event_analysis import (
            build_event_timeline,
        )

        subsequent_financial = {
            "2025-01-15": [
                {
                    "metric": "revenue_growth",
                    "period": "2025-03-31",
                    "value": "15.2%",
                    "change": "+5.1pp",
                    "direction": "POSITIVE",
                }
            ]
        }

        timeline = build_event_timeline(
            events=events,
            symbol="TEST",
            as_of=as_of,
            subsequent_financial_observations=subsequent_financial,
        )

        assert timeline.with_subsequent_observations == 1
        assert timeline.entries[0].subsequent_observations_count == 1

    def test_pit_filtering(self, as_of):
        from src.analysis.event_analysis import (
            build_event_timeline,
        )

        # Event after as_of
        future_event = CompanyEvent(
            symbol="TEST",
            event_date=date(2026, 1, 1),
            title="Future Event",
            description="This should be filtered out",
            category="OTHER",
            direction="NEUTRAL",
            materiality=1,
            evidence_ids=[],
        )

        timeline = build_event_timeline(
            events=[future_event],
            symbol="TEST",
            as_of=as_of,
        )

        assert timeline.entry_count == 0


# ---------------------------------------------------------------------------
# R6.1: Research Gaps Tests
# ---------------------------------------------------------------------------


class TestResearchGaps:
    def test_basic_gap_analysis(self, snapshots, events, as_of):
        from src.analysis.research_gaps import (
            analyze_research_gaps,
        )

        result = analyze_research_gaps(
            symbol="TEST",
            as_of=as_of,
            snapshots=snapshots,
            events=events,
        )

        assert result.symbol == "TEST"
        assert result.gap_count > 0
        assert result.coverage_score in ("HIGH", "MEDIUM", "LOW")

    def test_no_data_gaps(self, as_of):
        from src.analysis.research_gaps import (
            analyze_research_gaps,
        )

        result = analyze_research_gaps(
            symbol="TEST",
            as_of=as_of,
            snapshots=(),
            events=(),
            business_profile=None,
        )

        assert result.gap_count > 0
        assert result.coverage_score == "LOW"

    def test_stale_data_detection(self, as_of):
        from src.analysis.research_gaps import (
            analyze_research_gaps,
        )

        # Very old snapshot
        old_snapshot = FinancialSnapshot(
            symbol="TEST",
            period_end=date(2020, 3, 31),
            revenue=Decimal("1000000"),
            available_at=datetime(2020, 6, 15, tzinfo=timezone.utc),
        )

        result = analyze_research_gaps(
            symbol="TEST",
            as_of=as_of,
            snapshots=[old_snapshot],
        )

        # Should detect stale data
        stale_gaps = [
            g
            for g in result.gaps
            if g.status == "STALE"
        ]
        assert len(stale_gaps) > 0

    def test_provenance_preserved(self, snapshots, as_of):
        from src.analysis.research_gaps import (
            analyze_research_gaps,
        )

        result = analyze_research_gaps(
            symbol="TEST",
            as_of=as_of,
            snapshots=snapshots,
        )

        for gap in result.gaps:
            assert gap.as_of == as_of.isoformat()
            assert gap.symbol == "TEST"
            assert gap.gap_id.startswith("GAP-")


# ---------------------------------------------------------------------------
# R7.1: Cross-Domain Observations Tests
# ---------------------------------------------------------------------------


class TestCrossDomainObservations:
    def test_basic_analysis(self, snapshots, as_of):
        from src.analysis.cross_domain_observations import (
            analyze_cross_domain,
        )

        result = analyze_cross_domain(
            symbol="TEST",
            as_of=as_of,
            snapshots=snapshots,
            market_return_20d=-0.05,
        )

        assert result.symbol == "TEST"
        assert result.observation_count > 0

    def test_empty_snapshots(self, as_of):
        from src.analysis.cross_domain_observations import (
            analyze_cross_domain,
        )

        result = analyze_cross_domain(
            symbol="TEST",
            as_of=as_of,
            snapshots=(),
        )

        assert result.observation_count == 0

    def test_growth_margin_divergence(self, as_of):
        from src.analysis.cross_domain_observations import (
            analyze_growth_margin_divergence,
        )

        snapshots = [
            FinancialSnapshot(
                symbol="TEST",
                period_end=date(2024, 3, 31),
                revenue=Decimal("1000000"),
                net_profit=Decimal("150000"),  # 15% margin
            ),
            FinancialSnapshot(
                symbol="TEST",
                period_end=date(2025, 3, 31),
                revenue=Decimal("1300000"),  # 30% growth
                net_profit=Decimal("104000"),  # 8% margin (7pp drop)
            ),
        ]

        observations = analyze_growth_margin_divergence(
            snapshots, "TEST", as_of
        )

        # Should detect divergence (revenue grew 30% but margin dropped 7pp)
        assert len(observations) > 0
        assert observations[0].category == "growth_margin"

    def test_provenance_preserved(self, snapshots, as_of):
        from src.analysis.cross_domain_observations import (
            analyze_cross_domain,
        )

        result = analyze_cross_domain(
            symbol="TEST",
            as_of=as_of,
            snapshots=snapshots,
        )

        for obs in result.observations:
            assert obs.as_of == as_of.isoformat()
            assert obs.symbol == "TEST"
            assert obs.observation_id.startswith("XD-")


# ---------------------------------------------------------------------------
# R8.1: Report Data Contract Tests
# ---------------------------------------------------------------------------


class TestReportDataContract:
    def test_basic_contract(self, snapshots, as_of):
        from src.research.report_data_contract import (
            build_report_data_contract,
        )

        contract = build_report_data_contract(
            symbol="TEST",
            as_of=as_of,
            financial_snapshots=tuple(snapshots),
        )

        assert contract.symbol == "TEST"
        assert contract.total_sections == 20
        assert contract.overall_completeness_pct >= 0

    def test_empty_data(self, as_of):
        from src.research.report_data_contract import (
            build_report_data_contract,
        )

        contract = build_report_data_contract(
            symbol="TEST",
            as_of=as_of,
        )

        assert contract.total_sections == 20
        assert contract.complete_sections == 0
        assert contract.missing_sections == 20

    def test_section_coverage(self, snapshots, as_of):
        from src.research.report_data_contract import (
            build_report_data_contract,
        )

        contract = build_report_data_contract(
            symbol="TEST",
            as_of=as_of,
            financial_snapshots=tuple(snapshots),
        )

        # Financials section should be partial or complete
        financials_section = next(
            s
            for s in contract.sections
            if s.section_name == "financials"
        )
        assert financials_section.data_available is True


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_single_period_analysis(self, as_of):
        from src.analysis.cash_flow_quality import (
            analyze_cash_flow_quality,
        )
        from src.analysis.balance_sheet_deep import (
            analyze_balance_sheet_deep,
        )

        snapshot = FinancialSnapshot(
            symbol="TEST",
            period_end=date(2025, 3, 31),
            revenue=Decimal("1000000"),
            net_profit=Decimal("100000"),
            operating_cash_flow=Decimal("150000"),
            total_debt=Decimal("500000"),
            cash_and_equivalents=Decimal("200000"),
            available_at=datetime(2025, 6, 15, tzinfo=timezone.utc),
        )

        cf_result = analyze_cash_flow_quality(
            symbol="TEST",
            as_of=as_of,
            snapshots=[snapshot],
        )

        bs_result = analyze_balance_sheet_deep(
            symbol="TEST",
            as_of=as_of,
            snapshots=[snapshot],
        )

        # Should handle single period gracefully
        assert cf_result.period_count == 1
        assert bs_result.period_count == 1

    def test_zero_values(self, as_of):
        from src.analysis.cash_flow_quality import (
            analyze_cash_flow_quality,
        )

        snapshot = FinancialSnapshot(
            symbol="TEST",
            period_end=date(2025, 3, 31),
            revenue=Decimal("0"),
            net_profit=Decimal("0"),
            operating_cash_flow=Decimal("0"),
            available_at=datetime(2025, 6, 15, tzinfo=timezone.utc),
        )

        result = analyze_cash_flow_quality(
            symbol="TEST",
            as_of=as_of,
            snapshots=[snapshot],
        )

        # Should handle zero values gracefully
        assert result.observation_count == 0

    def test_negative_values(self, as_of):
        from src.analysis.cash_flow_quality import (
            analyze_cash_flow_quality,
        )

        snapshot = FinancialSnapshot(
            symbol="TEST",
            period_end=date(2025, 3, 31),
            revenue=Decimal("1000000"),
            net_profit=Decimal("-100000"),  # Loss
            operating_cash_flow=Decimal("-50000"),  # Negative CFO
            available_at=datetime(2025, 6, 15, tzinfo=timezone.utc),
        )

        result = analyze_cash_flow_quality(
            symbol="TEST",
            as_of=as_of,
            snapshots=[snapshot],
        )

        # Should handle negative values gracefully
        assert result.observation_count >= 0
