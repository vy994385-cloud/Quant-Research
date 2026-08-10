from decimal import Decimal

import pytest

from src.analysis.benchmarking import BenchmarkResult
from src.analysis.company_report import build_company_report
from src.analysis.financial_anomalies import FinancialAnomaly
from src.analysis.financial_trends import FinancialTrend
from src.analysis.future_intelligence import (
    FutureTechnologyArea,
    FutureTechnologySignal,
    InnovationEvidenceStrength,
    InnovationSignalDirection,
    build_future_technology_profile,
)
from src.analysis.risk_signals import RiskSignal


def test_build_company_report():

    anomaly = FinancialAnomaly(
        metric="receivables",
        current_change=Decimal("50"),
        comparison_change=Decimal("10"),
        severity="MEDIUM",
        explanation="Receivables increased faster than revenue.",
    )

    trend = FinancialTrend(
        metric="revenue",
        direction="INCREASING",
        observations=3,
        average_change=Decimal("10"),
        explanation="Revenue increased consistently.",
    )

    benchmark = BenchmarkResult(
        metric="receivables",
        company_value=Decimal("300"),
        peer_median=Decimal("100"),
        percentile=Decimal("95"),
        relative_to_peers="ABOVE_PEER_MEDIAN",
    )

    signal = RiskSignal(
        signal_id="TEST_001",
        category="FINANCIAL",
        severity="MEDIUM",
        confidence=Decimal("0.70"),
        title="Unusual receivables movement",
        explanation="Receivables increased faster than revenue.",
        supporting_metrics=("receivables",),
    )

    report = build_company_report(
        symbol="TEST",
        anomalies=[anomaly],
        trends=[trend],
        benchmarks=[benchmark],
        risk_signals=[signal],
        available_data_points=8,
        expected_data_points=10,
    )

    assert report.symbol == "TEST"

    assert len(report.anomalies) == 1
    assert len(report.trends) == 1
    assert len(report.benchmarks) == 1
    assert len(report.risk_signals) == 1

    assert len(report.strengths) == 1
    assert len(report.risks) == 1

    assert report.confidence == Decimal("0.8")

    assert report.has_future_intelligence is False
    assert report.future_readiness == Decimal("50")
    assert report.ai_participation == Decimal("0")
    assert report.innovation_execution == Decimal("50")
    assert report.technology_diversification == Decimal("0")


def test_report_records_missing_context():

    report = build_company_report(
        symbol="TEST",
        anomalies=[],
        trends=[],
        benchmarks=[],
        risk_signals=[],
        available_data_points=2,
        expected_data_points=10,
    )

    assert report.confidence == Decimal("0.2")

    assert len(report.unknowns) == 4

    assert any(
        "Peer comparison" in unknown
        for unknown in report.unknowns
    )

    assert any(
        "Future-technology intelligence" in unknown
        for unknown in report.unknowns
    )


def test_future_intelligence_is_attached_to_report():

    signal = FutureTechnologySignal(
        code="AI_DEPLOYMENT",
        title="AI deployment",
        description="AI system deployed into production.",
        technology_area=(
            FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE
        ),
        direction=InnovationSignalDirection.POSITIVE,
        materiality=5,
        confidence=Decimal("0.95"),
        evidence_strength=(
            InnovationEvidenceStrength.VERIFIED
        ),
        technology_relevance=Decimal("95"),
        execution_strength=Decimal("95"),
        commercialization_strength=Decimal("90"),
        strategic_importance=Decimal("95"),
    )

    profile = build_future_technology_profile(
        "TEST",
        sector="SOFTWARE",
        signals=[signal],
    )

    report = build_company_report(
        symbol="TEST",
        anomalies=[],
        trends=[],
        benchmarks=[],
        risk_signals=[],
        available_data_points=10,
        expected_data_points=10,
        future_technology=profile,
    )

    assert report.has_future_intelligence is True
    assert report.future_technology is profile

    assert report.future_signal_count == 1
    assert report.future_technology_area_count == 1

    assert report.future_readiness > Decimal("50")
    assert report.ai_participation > Decimal("0")
    assert report.innovation_execution > Decimal("0")
    assert report.technology_diversification == Decimal("65")


def test_future_intelligence_requires_matching_symbol():

    profile = build_future_technology_profile(
        "OTHER",
        signals=[],
    )

    with pytest.raises(
        ValueError,
        match="future technology symbol",
    ):
        build_company_report(
            symbol="TEST",
            anomalies=[],
            trends=[],
            benchmarks=[],
            risk_signals=[],
            available_data_points=1,
            expected_data_points=1,
            future_technology=profile,
        )


def test_future_intelligence_does_not_change_confidence():

    profile = build_future_technology_profile(
        "TEST",
        signals=[],
    )

    report = build_company_report(
        symbol="TEST",
        anomalies=[],
        trends=[],
        benchmarks=[],
        risk_signals=[],
        available_data_points=7,
        expected_data_points=10,
        future_technology=profile,
    )

    assert report.confidence == Decimal("0.7")


def test_no_future_signals_are_not_automatically_negative():

    profile = build_future_technology_profile(
        "TEST",
        signals=[],
    )

    report = build_company_report(
        symbol="TEST",
        anomalies=[],
        trends=[],
        benchmarks=[],
        risk_signals=[],
        available_data_points=10,
        expected_data_points=10,
        future_technology=profile,
    )

    assert report.future_readiness == Decimal("50")
    assert report.ai_participation == Decimal("0")
    assert report.innovation_execution == Decimal("50")
    assert report.technology_diversification == Decimal("0")