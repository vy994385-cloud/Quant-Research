"""Tests for competitive analysis engine."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.analysis.competitive_analysis import (
    CompetitiveAnalysisResult,
    CompetitiveMetric,
    CompetitiveSignal,
    analyze_competitive,
    compute_competitive_signals,
    compute_financial_metric_comparison,
)
from src.data.company.financials import FinancialSnapshot


_AS_OF = datetime(2024, 6, 15, tzinfo=timezone.utc)


def _snap(
    period_end: date,
    revenue: Decimal | None = None,
    net_profit: Decimal | None = None,
    total_debt: Decimal | None = None,
    total_assets: Decimal | None = None,
    shareholders_equity: Decimal | None = None,
    operating_profit: Decimal | None = None,
) -> FinancialSnapshot:
    return FinancialSnapshot(
        symbol="TEST",
        period_end=period_end,
        revenue=revenue,
        net_profit=net_profit,
        total_debt=total_debt,
        total_assets=total_assets,
        shareholders_equity=shareholders_equity,
        operating_profit=operating_profit,
    )


# ---------------------------------------------------------------------------
# Empty / insufficient data
# ---------------------------------------------------------------------------


class TestInsufficientData:
    def test_no_peers(self):
        company = _snap(date(2024, 1, 1), revenue=Decimal("1000"))
        result = analyze_competitive(company, [], "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert result.has_peer_data is False
        assert result.peer_count == 0
        assert "peer_comparison" in result.missing_analyses

    def test_company_metric_missing(self):
        company = _snap(date(2024, 1, 1))
        peers = [_snap(date(2024, 1, 1), revenue=Decimal("500"))]
        result = analyze_competitive(company, peers, "TEST", _AS_OF)
        assert result.has_peer_data is True
        assert len(result.metrics) == 0


# ---------------------------------------------------------------------------
# Metric comparison
# ---------------------------------------------------------------------------


class TestMetricComparison:
    def test_above_peers(self):
        company = _snap(date(2024, 1, 1), revenue=Decimal("1000"))
        peers = [
            _snap(date(2024, 1, 1), revenue=Decimal("200")),
            _snap(date(2024, 1, 1), revenue=Decimal("300")),
        ]
        result = compute_financial_metric_comparison(
            company, peers, "revenue"
        )
        assert result is not None
        assert result.position == "ABOVE_PEERS"
        assert result.company_value == "1000"
        assert result.percentile == "100.00"

    def test_below_peers(self):
        company = _snap(date(2024, 1, 1), revenue=Decimal("100"))
        peers = [
            _snap(date(2024, 1, 1), revenue=Decimal("500")),
            _snap(date(2024, 1, 1), revenue=Decimal("1000")),
        ]
        result = compute_financial_metric_comparison(
            company, peers, "revenue"
        )
        assert result is not None
        assert result.position == "BELOW_PEERS"
        # company=100, peers=[500, 1000]: 0 peers <= 100, percentile=0.00
        assert result.percentile == "0.00"

    def test_no_peers_for_metric(self):
        company = _snap(date(2024, 1, 1), revenue=Decimal("1000"))
        peers = [_snap(date(2024, 1, 1))]
        result = compute_financial_metric_comparison(
            company, peers, "revenue"
        )
        assert result is not None
        assert result.position == "NO_PEERS"

    def test_company_metric_none(self):
        company = _snap(date(2024, 1, 1))
        peers = [_snap(date(2024, 1, 1), revenue=Decimal("500"))]
        result = compute_financial_metric_comparison(
            company, peers, "revenue"
        )
        assert result is None


# ---------------------------------------------------------------------------
# Competitive signals
# ---------------------------------------------------------------------------


class TestCompetitiveSignals:
    def test_positive_signal(self):
        metrics = (
            CompetitiveMetric(
                metric="revenue",
                company_value="1000",
                peer_median="500",
                percentile="100.00",
                position="ABOVE_PEERS",
            ),
        )
        signals = compute_competitive_signals(metrics, "TEST")
        assert len(signals) == 1
        assert signals[0].direction == "POSITIVE"
        assert signals[0].metric == "revenue"

    def test_negative_signal(self):
        metrics = (
            CompetitiveMetric(
                metric="revenue",
                company_value="100",
                peer_median="500",
                percentile="33.33",
                position="BELOW_PEERS",
            ),
        )
        signals = compute_competitive_signals(metrics, "TEST")
        assert len(signals) == 1
        assert signals[0].direction == "NEGATIVE"

    def test_no_signal_for_inline(self):
        metrics = (
            CompetitiveMetric(
                metric="revenue",
                company_value="500",
                peer_median="500",
                percentile="50.00",
                position="INLINE_WITH_PEERS",
            ),
        )
        signals = compute_competitive_signals(metrics, "TEST")
        assert len(signals) == 0


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------


class TestFullAnalysis:
    def test_with_peers(self):
        company = _snap(
            date(2024, 1, 1),
            revenue=Decimal("1000"),
            net_profit=Decimal("200"),
        )
        peers = [
            _snap(date(2024, 1, 1), revenue=Decimal("500"), net_profit=Decimal("100")),
            _snap(date(2024, 1, 1), revenue=Decimal("300"), net_profit=Decimal("50")),
        ]
        result = analyze_competitive(company, peers, "TEST", _AS_OF)
        assert result.has_peer_data is True
        assert result.peer_count == 2
        assert len(result.metrics) > 0
        assert "peer_comparison" in result.available_analyses

    def test_forbids_extra_fields(self):
        company = _snap(date(2024, 1, 1), revenue=Decimal("1000"))
        result = analyze_competitive(company, [], "TEST", _AS_OF)
        assert result.symbol == "TEST"
