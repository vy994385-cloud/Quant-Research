from decimal import Decimal

from src.analysis.benchmarking import BenchmarkResult
from src.analysis.company_report import build_company_report
from src.analysis.financial_anomalies import FinancialAnomaly
from src.analysis.financial_trends import FinancialTrend
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

    assert len(report.unknowns) == 3

    assert any(
        "Peer comparison" in unknown
        for unknown in report.unknowns
    )
