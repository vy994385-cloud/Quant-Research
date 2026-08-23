"""
Tests for the research expansion integration.

Verifies that the new modules (cash-flow quality, balance-sheet
deep, research gaps, cross-domain) are properly wired into
the research orchestration and API serialization pipeline.
"""

from __future__ import annotations

import pytest
from datetime import datetime, date, timezone
from decimal import Decimal

from src.data.company.financials import FinancialSnapshot
from src.analysis.deep_fundamental import analyze_deep_fundamentals
from src.analysis.cash_flow_quality import (
    CashFlowQualityResult,
    analyze_cash_flow_quality,
)
from src.analysis.balance_sheet_deep import (
    BalanceSheetDeepResult,
    analyze_balance_sheet_deep,
)
from src.analysis.research_gaps import ResearchGapResult, analyze_research_gaps
from src.analysis.cross_domain_observations import (
    CrossDomainResult,
    analyze_cross_domain,
)
from src.research.company_intel.models import CompanyIntelligenceSnapshot
from src.api.contracts import (
    ContractCashFlowQuality,
    ContractBalanceSheetDeep,
    ContractResearchGaps,
    ContractCrossDomain,
)


@pytest.fixture
def two_period_snapshots():
    """Two-period financial snapshots for testing."""
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
            available_at=datetime(2025, 6, 15, tzinfo=timezone.utc),
        ),
    ]


class TestDeepFundamentalIntegration:
    """Test that DeepFundamentalResult includes new fields."""

    def test_deep_fundamental_has_cash_flow_quality(self, two_period_snapshots):
        result = analyze_deep_fundamentals(
            two_period_snapshots,
            "TEST",
            datetime(2025, 12, 1, tzinfo=timezone.utc),
        )

        assert result.cash_flow_quality is not None
        assert isinstance(result.cash_flow_quality, CashFlowQualityResult)
        assert result.cash_flow_quality.observation_count > 0
        assert result.cash_flow_quality.direction in (
            "IMPROVING",
            "DETERIORATING",
            "STABLE",
            "UNKNOWN",
        )

    def test_deep_fundamental_has_balance_sheet_deep(self, two_period_snapshots):
        result = analyze_deep_fundamentals(
            two_period_snapshots,
            "TEST",
            datetime(2025, 12, 1, tzinfo=timezone.utc),
        )

        assert result.balance_sheet_deep is not None
        assert isinstance(result.balance_sheet_deep, BalanceSheetDeepResult)
        assert result.balance_sheet_deep.observation_count > 0
        assert result.balance_sheet_deep.direction in (
            "IMPROVING",
            "DETERIORATING",
            "STABLE",
            "UNKNOWN",
        )

    def test_deep_fundamental_available_analyses_includes_new(self, two_period_snapshots):
        result = analyze_deep_fundamentals(
            two_period_snapshots,
            "TEST",
            datetime(2025, 12, 1, tzinfo=timezone.utc),
        )

        assert "cash_flow_quality" in result.available_analyses
        assert "balance_sheet_deep" in result.available_analyses

    def test_deep_fundamental_empty_snapshots(self):
        result = analyze_deep_fundamentals(
            [],
            "TEST",
            datetime(2025, 12, 1, tzinfo=timezone.utc),
        )

        assert result.cash_flow_quality is None
        assert result.balance_sheet_deep is None
        assert "cash_flow_quality" in result.missing_analyses
        assert "balance_sheet_deep" in result.missing_analyses


class TestCompanyIntelligenceSnapshotIntegration:
    """Test that CompanyIntelligenceSnapshot includes new fields."""

    def test_snapshot_has_new_fields(self):
        snapshot = CompanyIntelligenceSnapshot(
            company="TEST",
            as_of=datetime(2025, 12, 1, tzinfo=timezone.utc),
            captured_at=datetime(2025, 12, 1, tzinfo=timezone.utc),
            item_count=0,
        )

        assert hasattr(snapshot, "cash_flow_quality")
        assert hasattr(snapshot, "balance_sheet_deep")
        assert hasattr(snapshot, "research_gaps")
        assert hasattr(snapshot, "cross_domain")
        assert snapshot.cash_flow_quality is None
        assert snapshot.balance_sheet_deep is None
        assert snapshot.research_gaps is None
        assert snapshot.cross_domain is None


class TestAPIContractIntegration:
    """Test that API contracts include new sections."""

    def test_contract_cash_flow_quality_model(self):
        contract = ContractCashFlowQuality(
            symbol="TEST",
            as_of="2025-12-01T00:00:00Z",
            direction="IMPROVING",
            observation_count=3,
            observations=[],
            notes=[],
        )

        assert contract.symbol == "TEST"
        assert contract.direction == "IMPROVING"
        assert contract.observation_count == 3

    def test_contract_balance_sheet_deep_model(self):
        contract = ContractBalanceSheetDeep(
            symbol="TEST",
            as_of="2025-12-01T00:00:00Z",
            direction="STABLE",
            observation_count=2,
            observations=[],
            notes=[],
        )

        assert contract.symbol == "TEST"
        assert contract.direction == "STABLE"
        assert contract.observation_count == 2

    def test_contract_research_gaps_model(self):
        contract = ContractResearchGaps(
            symbol="TEST",
            as_of="2025-12-01T00:00:00Z",
            gap_count=1,
            gaps=[],
            coverage_score="MEDIUM",
            notes=[],
        )

        assert contract.symbol == "TEST"
        assert contract.gap_count == 1
        assert contract.coverage_score == "MEDIUM"

    def test_contract_cross_domain_model(self):
        contract = ContractCrossDomain(
            symbol="TEST",
            as_of="2025-12-01T00:00:00Z",
            observation_count=2,
            observations=[],
            notes=[],
        )

        assert contract.symbol == "TEST"
        assert contract.observation_count == 2


class TestSerializerIntegration:
    """Test that serializers include new fields."""

    def test_research_contract_serializer_includes_new_fields(self):
        from src.api.serializers import (
            cash_flow_quality_contract,
            balance_sheet_deep_contract,
            research_gaps_contract,
            cross_domain_contract,
        )

        # Verify all serializer functions exist and are callable
        assert callable(cash_flow_quality_contract)
        assert callable(balance_sheet_deep_contract)
        assert callable(research_gaps_contract)
        assert callable(cross_domain_contract)


class TestObservationProvenance:
    """Test that observations from new modules carry provenance."""

    def test_cash_flow_observation_has_provenance(self, two_period_snapshots):
        result = analyze_cash_flow_quality(
            symbol="TEST",
            as_of=datetime(2025, 12, 1, tzinfo=timezone.utc),
            snapshots=two_period_snapshots,
        )

        assert result.observation_count > 0
        for obs in result.observations:
            assert hasattr(obs, "observation_id")
            assert hasattr(obs, "symbol")
            assert hasattr(obs, "observation_type")
            assert hasattr(obs, "explanation")
            assert hasattr(obs, "as_of")
            assert obs.symbol == "TEST"

    def test_balance_sheet_observation_has_provenance(self, two_period_snapshots):
        result = analyze_balance_sheet_deep(
            symbol="TEST",
            as_of=datetime(2025, 12, 1, tzinfo=timezone.utc),
            snapshots=two_period_snapshots,
        )

        assert result.observation_count > 0
        for obs in result.observations:
            assert hasattr(obs, "observation_id")
            assert hasattr(obs, "symbol")
            assert hasattr(obs, "observation_type")
            assert hasattr(obs, "explanation")
            assert hasattr(obs, "as_of")
            assert obs.symbol == "TEST"

    def test_research_gap_has_provenance(self, two_period_snapshots):
        result = analyze_research_gaps(
            symbol="TEST",
            as_of=datetime(2025, 12, 1, tzinfo=timezone.utc),
            snapshots=two_period_snapshots,
        )

        for gap in result.gaps:
            assert hasattr(gap, "gap_id")
            assert hasattr(gap, "symbol")
            assert hasattr(gap, "category")
            assert hasattr(gap, "gap")
            assert hasattr(gap, "as_of")
            assert gap.symbol == "TEST"

    def test_cross_domain_observation_has_provenance(self, two_period_snapshots):
        result = analyze_cross_domain(
            symbol="TEST",
            as_of=datetime(2025, 12, 1, tzinfo=timezone.utc),
            snapshots=two_period_snapshots,
        )

        for obs in result.observations:
            assert hasattr(obs, "observation_id")
            assert hasattr(obs, "symbol")
            assert hasattr(obs, "label")
            assert hasattr(obs, "description")
            assert hasattr(obs, "as_of")
            assert obs.symbol == "TEST"


class TestEndToEndIntegration:
    """End-to-end test of the integration pipeline."""

    def test_full_pipeline(self, two_period_snapshots):
        """Test that the full pipeline produces valid results."""
        from src.analysis.deep_fundamental import (
            analyze_deep_fundamentals,
        )

        as_of = datetime(2025, 12, 1, tzinfo=timezone.utc)

        # Run deep fundamental analysis
        deep_result = analyze_deep_fundamentals(
            two_period_snapshots,
            "TEST",
            as_of,
        )

        # Verify new fields are populated
        assert deep_result.cash_flow_quality is not None
        assert deep_result.balance_sheet_deep is not None

        # Verify cash flow quality result
        cfq = deep_result.cash_flow_quality
        assert cfq.symbol == "TEST"
        assert cfq.observation_count > 0
        assert cfq.direction in ("IMPROVING", "DETERIORATING", "STABLE", "UNKNOWN")

        # Verify balance sheet deep result
        bsd = deep_result.balance_sheet_deep
        assert bsd.symbol == "TEST"
        assert bsd.observation_count > 0
        assert bsd.direction in ("IMPROVING", "DETERIORATING", "STABLE", "UNKNOWN")

        # Verify all observations have required fields
        for obs in cfq.observations:
            assert obs.observation_id
            assert obs.symbol == "TEST"
            assert obs.observation_type
            assert obs.explanation
            assert obs.as_of

        for obs in bsd.observations:
            assert obs.observation_id
            assert obs.symbol == "TEST"
            assert obs.observation_type
            assert obs.explanation
            assert obs.as_of
