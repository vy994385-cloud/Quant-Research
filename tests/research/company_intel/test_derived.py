"""Tests for derived hidden information, including financial divergence detections."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.research.company_intel.derived import (
    _debt_cash_changes,
    _margin_acceleration,
    _profit_cashflow_divergence,
    _revenue_receivables_divergence,
    _trajectory_changes,
    _working_capital_shifts,
    build_hidden_information,
)
from src.research.company_intel.models import (
    CorporateIntelItem,
    DeepFinancialInsights,
    DerivedObservation,
    FinancialPeriod,
    HiddenInformationInsights,
    SourceRef,
)
from src.research.company_intel.semantics import (
    IntelDirection,
    IntelKind,
    ReportingPeriodType,
    SemanticCategory,
    VerificationStatus,
)

_AWARE = timezone.utc


def _fp(
    symbol: str,
    period_end: date,
    metrics: dict[str, Decimal],
    period_type: ReportingPeriodType = ReportingPeriodType.QUARTERLY,
) -> FinancialPeriod:
    return FinancialPeriod(
        period_id=f"{symbol}:{period_end.isoformat()}",
        symbol=symbol,
        period_end=period_end,
        period_type=period_type,
        metrics=metrics,
    )


AS_OF = datetime(2026, 8, 10, tzinfo=_AWARE)


class TestRevenueReceivablesDivergence:
    def test_detects_faster_receivables_growth(self):
        periods = (
            _fp(
                "TCS",
                date(2025, 3, 31),
                {"revenue": Decimal("100"), "receivables": Decimal("20")},
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {
                    "revenue": Decimal("110"),
                    "receivables": Decimal("30"),
                },
            ),
        )
        obs = _revenue_receivables_divergence(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert len(obs) == 1
        assert obs[0].severity == "WARN"
        assert "receivables" in obs[0].label.lower()

    def test_no_divergence_when_proportional(self):
        periods = (
            _fp(
                "TCS",
                date(2025, 3, 31),
                {"revenue": Decimal("100"), "receivables": Decimal("20")},
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {
                    "revenue": Decimal("120"),
                    "receivables": Decimal("24"),
                },
            ),
        )
        obs = _revenue_receivables_divergence(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert len(obs) == 0

    def test_empty_with_insufficient_periods(self):
        obs = _revenue_receivables_divergence(
            (_fp("TCS", date(2025, 3, 31), {"revenue": Decimal("100")}),),
            symbol="TCS",
            as_of=AS_OF,
        )
        assert len(obs) == 0


class TestProfitCashflowDivergence:
    def test_detects_profit_up_cashflow_down(self):
        periods = (
            _fp(
                "TCS",
                date(2025, 3, 31),
                {
                    "net_profit": Decimal("50"),
                    "operating_cash_flow": Decimal("60"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {
                    "net_profit": Decimal("60"),
                    "operating_cash_flow": Decimal("40"),
                },
            ),
        )
        obs = _profit_cashflow_divergence(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert len(obs) == 1
        assert obs[0].severity == "WARN"
        assert "cash flow" in obs[0].label.lower()

    def test_no_divergence_when_both_rise(self):
        periods = (
            _fp(
                "TCS",
                date(2025, 3, 31),
                {
                    "net_profit": Decimal("50"),
                    "operating_cash_flow": Decimal("60"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {
                    "net_profit": Decimal("55"),
                    "operating_cash_flow": Decimal("65"),
                },
            ),
        )
        obs = _profit_cashflow_divergence(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert len(obs) == 0


class TestMarginAcceleration:
    def test_detects_upward_acceleration(self):
        periods = (
            _fp(
                "TCS",
                date(2024, 12, 31),
                {
                    "revenue": Decimal("100"),
                    "operating_profit": Decimal("10"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 3, 31),
                {
                    "revenue": Decimal("100"),
                    "operating_profit": Decimal("15"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {
                    "revenue": Decimal("100"),
                    "operating_profit": Decimal("25"),
                },
            ),
        )
        obs = _margin_acceleration(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert len(obs) == 1
        assert obs[0].severity == "INFO"
        assert "upward" in obs[0].label.lower()

    def test_detects_downward_acceleration(self):
        periods = (
            _fp(
                "TCS",
                date(2024, 12, 31),
                {
                    "revenue": Decimal("100"),
                    "operating_profit": Decimal("25"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 3, 31),
                {
                    "revenue": Decimal("100"),
                    "operating_profit": Decimal("15"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {
                    "revenue": Decimal("100"),
                    "operating_profit": Decimal("0"),
                },
            ),
        )
        obs = _margin_acceleration(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert len(obs) == 1
        assert obs[0].severity == "WARN"
        assert "downward" in obs[0].label.lower()

    def test_no_acceleration_with_linear_margins(self):
        periods = (
            _fp(
                "TCS",
                date(2024, 12, 31),
                {
                    "revenue": Decimal("100"),
                    "operating_profit": Decimal("10"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 3, 31),
                {
                    "revenue": Decimal("100"),
                    "operating_profit": Decimal("15"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {
                    "revenue": Decimal("100"),
                    "operating_profit": Decimal("20"),
                },
            ),
        )
        obs = _margin_acceleration(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert len(obs) == 0


class TestDebtCashChanges:
    def test_detects_both_rising(self):
        periods = (
            _fp(
                "TCS",
                date(2025, 3, 31),
                {
                    "total_debt": Decimal("100"),
                    "cash_and_equivalents": Decimal("50"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {
                    "total_debt": Decimal("120"),
                    "cash_and_equivalents": Decimal("65"),
                },
            ),
        )
        obs = _debt_cash_changes(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert any("debt and cash rising" in o.label.lower() for o in obs)

    def test_detects_debt_up_cash_down(self):
        periods = (
            _fp(
                "TCS",
                date(2025, 3, 31),
                {
                    "total_debt": Decimal("100"),
                    "cash_and_equivalents": Decimal("50"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {
                    "total_debt": Decimal("120"),
                    "cash_and_equivalents": Decimal("40"),
                },
            ),
        )
        obs = _debt_cash_changes(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert any("declining" in o.label.lower() for o in obs)


class TestWorkingCapitalShifts:
    def test_detects_expansion(self):
        periods = (
            _fp(
                "TCS",
                date(2025, 3, 31),
                {
                    "receivables": Decimal("100"),
                    "payables": Decimal("80"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {
                    "receivables": Decimal("150"),
                    "payables": Decimal("80"),
                },
            ),
        )
        obs = _working_capital_shifts(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert len(obs) == 1
        assert "expanded" in obs[0].label.lower()

    def test_no_shift_when_proportional(self):
        periods = (
            _fp(
                "TCS",
                date(2025, 3, 31),
                {
                    "receivables": Decimal("100"),
                    "payables": Decimal("80"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {
                    "receivables": Decimal("110"),
                    "payables": Decimal("88"),
                },
            ),
        )
        obs = _working_capital_shifts(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert len(obs) == 0


class TestTrajectoryChanges:
    def test_detects_revenue_reversal_to_growth(self):
        periods = (
            _fp(
                "TCS",
                date(2024, 12, 31),
                {"revenue": Decimal("100")},
            ),
            _fp(
                "TCS",
                date(2025, 3, 31),
                {"revenue": Decimal("80")},
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {"revenue": Decimal("90")},
            ),
        )
        obs = _trajectory_changes(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert len(obs) == 1
        assert "growth" in obs[0].label.lower()

    def test_detects_revenue_reversal_to_decline(self):
        periods = (
            _fp(
                "TCS",
                date(2024, 12, 31),
                {"revenue": Decimal("80")},
            ),
            _fp(
                "TCS",
                date(2025, 3, 31),
                {"revenue": Decimal("100")},
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {"revenue": Decimal("90")},
            ),
        )
        obs = _trajectory_changes(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert len(obs) == 1
        assert "decline" in obs[0].label.lower()

    def test_no_reversal_with_monotonic_trend(self):
        periods = (
            _fp(
                "TCS",
                date(2024, 12, 31),
                {"revenue": Decimal("80")},
            ),
            _fp(
                "TCS",
                date(2025, 3, 31),
                {"revenue": Decimal("90")},
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {"revenue": Decimal("100")},
            ),
        )
        obs = _trajectory_changes(
            periods, symbol="TCS", as_of=AS_OF
        )
        assert len(obs) == 0


class TestBuildHiddenInformationIntegration:
    def test_financial_periods_fed_through(self):
        periods = (
            _fp(
                "TCS",
                date(2024, 12, 31),
                {"revenue": Decimal("100"), "receivables": Decimal("10")},
            ),
            _fp(
                "TCS",
                date(2025, 3, 31),
                {
                    "revenue": Decimal("110"),
                    "receivables": Decimal("30"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {
                    "revenue": Decimal("120"),
                    "receivables": Decimal("60"),
                },
            ),
        )
        result = build_hidden_information(
            (),
            symbol="TCS",
            as_of=AS_OF,
            deep_financial_insights=None,
            financial_periods=periods,
        )
        assert isinstance(result, HiddenInformationInsights)
        labels = [o.label for o in result.observations]
        assert any("receivables" in l.lower() for l in labels)

    def test_severity_field_present(self):
        periods = (
            _fp(
                "TCS",
                date(2024, 12, 31),
                {
                    "revenue": Decimal("100"),
                    "operating_profit": Decimal("10"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 3, 31),
                {
                    "revenue": Decimal("100"),
                    "operating_profit": Decimal("15"),
                },
            ),
            _fp(
                "TCS",
                date(2025, 6, 30),
                {
                    "revenue": Decimal("100"),
                    "operating_profit": Decimal("25"),
                },
            ),
        )
        result = build_hidden_information(
            (),
            symbol="TCS",
            as_of=AS_OF,
            deep_financial_insights=None,
            financial_periods=periods,
        )
        for obs in result.observations:
            assert hasattr(obs, "severity")
            assert obs.severity in ("INFO", "WARN", "ALERT")

    def test_no_financial_periods_yields_no_financial_divergences(self):
        result = build_hidden_information(
            (),
            symbol="TCS",
            as_of=AS_OF,
            deep_financial_insights=None,
        )
        assert isinstance(result, HiddenInformationInsights)
        assert len(result.observations) == 0
