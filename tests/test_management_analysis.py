"""Tests for management analysis engine."""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.analysis.management_analysis import (
    CapitalAllocationSignal,
    ManagementAnalysisResult,
    ManagementChangePattern,
    analyze_management,
    compute_capital_allocation_signals,
    compute_management_patterns,
)
from src.data.company.financials import FinancialSnapshot
from src.data.company.management import ManagementChange


_AS_OF = datetime(2024, 6, 15, tzinfo=timezone.utc)


def _change(
    effective_date: date,
    person: str = "John Doe",
    role: str = "CEO",
    change_type: str = "Appointment",
) -> ManagementChange:
    return ManagementChange(
        symbol="TEST",
        person_name=person,
        role=role,
        change_type=change_type,
        effective_date=effective_date,
    )


def _snap(
    period_end: date,
    total_debt: Decimal | None = None,
    cash: Decimal | None = None,
    free_cash_flow: Decimal | None = None,
) -> FinancialSnapshot:
    return FinancialSnapshot(
        symbol="TEST",
        period_end=period_end,
        total_debt=total_debt,
        cash_and_equivalents=cash,
        free_cash_flow=free_cash_flow,
    )


# ---------------------------------------------------------------------------
# Empty / insufficient data
# ---------------------------------------------------------------------------


class TestInsufficientData:
    def test_empty_changes(self):
        result = analyze_management([], [], "TEST", _AS_OF)
        assert result.symbol == "TEST"
        assert result.change_count == 0
        assert "management_patterns" in result.missing_analyses

    def test_insufficient_snapshots(self):
        snap = _snap(date(2024, 1, 1))
        result = analyze_management([], [snap], "TEST", _AS_OF)
        assert "capital_allocation" in result.missing_analyses


# ---------------------------------------------------------------------------
# Management patterns
# ---------------------------------------------------------------------------


class TestManagementPatterns:
    def test_no_patterns(self):
        changes = [_change(date(2024, 1, 1))]
        result = compute_management_patterns(changes, "TEST")
        assert result == ()

    def test_elevated_departures(self):
        changes = [
            _change(date(2024, 1, 1), role="CEO", change_type="Resignation"),
            _change(date(2024, 2, 1), role="CFO", change_type="Resignation"),
            _change(date(2024, 3, 1), role="CTO", change_type="Resignation"),
        ]
        result = compute_management_patterns(changes, "TEST")
        assert len(result) == 1
        assert result[0].pattern_type == "ELEVATED_DEPARTURES"
        assert result[0].change_count == 3

    def test_role_churn(self):
        changes = [
            _change(date(2024, 1, 1), role="CEO", change_type="Resignation"),
            _change(date(2024, 2, 1), role="CEO", change_type="Appointment"),
            _change(date(2024, 3, 1), role="CEO", change_type="Resignation"),
            _change(date(2024, 4, 1), role="CEO", change_type="Appointment"),
        ]
        result = compute_management_patterns(changes, "TEST")
        role_churn = [p for p in result if p.pattern_type == "ROLE_CHURN"]
        assert len(role_churn) == 1
        assert role_churn[0].change_count == 4


# ---------------------------------------------------------------------------
# Capital allocation signals
# ---------------------------------------------------------------------------


class TestCapitalAllocationSignals:
    def test_insufficient_snapshots(self):
        result = compute_capital_allocation_signals([], "TEST")
        assert result == ()

    def test_debt_reduction(self):
        snap1 = _snap(date(2023, 1, 1), total_debt=Decimal("1000"))
        snap2 = _snap(date(2024, 1, 1), total_debt=Decimal("500"))
        result = compute_capital_allocation_signals([snap1, snap2], "TEST")
        debt_signals = [s for s in result if s.signal_type == "DEBT_MANAGEMENT"]
        assert len(debt_signals) == 1
        assert debt_signals[0].direction == "POSITIVE"

    def test_significant_debt_increase(self):
        snap1 = _snap(date(2023, 1, 1), total_debt=Decimal("100"))
        snap2 = _snap(date(2024, 1, 1), total_debt=Decimal("150"))
        result = compute_capital_allocation_signals([snap1, snap2], "TEST")
        debt_signals = [s for s in result if s.signal_type == "DEBT_MANAGEMENT"]
        assert len(debt_signals) == 1
        assert debt_signals[0].direction == "NEGATIVE"

    def test_cash_accumulation(self):
        snap1 = _snap(date(2023, 1, 1), cash=Decimal("100"))
        snap2 = _snap(date(2024, 1, 1), cash=Decimal("150"))
        result = compute_capital_allocation_signals([snap1, snap2], "TEST")
        cash_signals = [s for s in result if s.signal_type == "CASH_MANAGEMENT"]
        assert len(cash_signals) == 1
        assert cash_signals[0].direction == "POSITIVE"

    def test_positive_fcf(self):
        snap1 = _snap(date(2023, 1, 1))
        snap2 = _snap(date(2024, 1, 1), free_cash_flow=Decimal("100"))
        result = compute_capital_allocation_signals([snap1, snap2], "TEST")
        fcf_signals = [s for s in result if s.signal_type == "CASH_GENERATION"]
        assert len(fcf_signals) == 1
        assert fcf_signals[0].direction == "POSITIVE"


# ---------------------------------------------------------------------------
# Full analysis
# ---------------------------------------------------------------------------


class TestFullAnalysis:
    def test_with_data(self):
        changes = [
            _change(date(2024, 1, 1)),
            _change(date(2024, 2, 1)),
        ]
        snap1 = _snap(date(2023, 1, 1), total_debt=Decimal("1000"))
        snap2 = _snap(date(2024, 1, 1), total_debt=Decimal("500"))
        result = analyze_management(changes, [snap1, snap2], "TEST", _AS_OF)
        assert result.change_count == 2
        assert "management_patterns" in result.available_analyses
        assert "capital_allocation" in result.available_analyses

    def test_forbids_extra_fields(self):
        result = analyze_management([], [], "TEST", _AS_OF)
        assert result.symbol == "TEST"
