from datetime import date, datetime, timezone

from src.data.ingestion.anomalies import (
    AnomalySeverity,
    MarketAnomaly,
)
from src.data.ingestion.provenance import (
    DataProvenance,
    ReviewStatus,
    SourceType,
)
from src.data.ingestion.review import (
    ReviewDecision,
    review_ingestion,
)
from src.data.models import PriceBar


def make_bar(close="100"):
    return PriceBar(
        symbol="TEST",
        trading_date=date(2026, 8, 7),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1000,
    )


def make_provenance(
    status=ReviewStatus.ACCEPT,
    tier=1,
):
    return DataProvenance(
        provider_name="Example Exchange",
        source_type=SourceType.EXCHANGE,
        retrieved_at=datetime.now(timezone.utc),
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 7),
        reliability_tier=tier,
        review_status=status,
    )


def test_clean_data_is_accepted():

    result = review_ingestion(
        symbol="TEST",
        bars=[make_bar()],
        provenance=make_provenance(),
        anomalies=[],
    )

    assert result.decision == ReviewDecision.ACCEPT
    assert result.anomaly_count == 0
    assert result.provenance_quality
    assert result.records_received == 1
    assert result.records_accepted == 1
    assert result.records_rejected == 0


def test_unreviewed_source_requires_review():

    result = review_ingestion(
        symbol="TEST",
        bars=[make_bar()],
        provenance=make_provenance(
            ReviewStatus.NEEDS_REVIEW
        ),
        anomalies=[],
    )

    assert result.decision == ReviewDecision.NEEDS_REVIEW

    assert any(
        reason.code == "PROVENANCE_UNREVIEWED"
        for reason in result.reasons
    )


def test_rejected_source_rejects_ingestion():

    result = review_ingestion(
        symbol="TEST",
        bars=[make_bar()],
        provenance=make_provenance(
            ReviewStatus.REJECT
        ),
        anomalies=[],
    )

    assert result.decision == ReviewDecision.REJECT

    assert any(
        reason.code == "PROVENANCE_REJECTED"
        for reason in result.reasons
    )


def test_anomaly_requires_review():

    anomaly = MarketAnomaly(
        symbol="TEST",
        trading_date=date(2026, 8, 7),
        code="EXTREME_PRICE_MOVE",
        message="Large price movement detected.",
        severity=AnomalySeverity.CRITICAL,
        value=25,
    )

    result = review_ingestion(
        symbol="TEST",
        bars=[make_bar()],
        provenance=make_provenance(),
        anomalies=[anomaly],
    )

    assert result.decision == ReviewDecision.NEEDS_REVIEW
    assert result.anomaly_count == 1

    assert any(
        reason.code == "EXTREME_PRICE_MOVE"
        for reason in result.reasons
    )


def test_validation_error_rejects_data():

    result = review_ingestion(
        symbol="TEST",
        bars=[make_bar()],
        provenance=make_provenance(),
        anomalies=[],
        validation_errors=[
            "Duplicate trading date detected."
        ],
    )

    assert result.decision == ReviewDecision.REJECT

    assert any(
        reason.code == "VALIDATION_ERROR"
        for reason in result.reasons
    )


def test_multiple_reasons_are_preserved():

    anomaly = MarketAnomaly(
        symbol="TEST",
        trading_date=date(2026, 8, 7),
        code="VOLUME_SPIKE",
        message="Volume spike detected.",
        severity=AnomalySeverity.WARNING,
        value=5000,
    )

    result = review_ingestion(
        symbol="TEST",
        bars=[make_bar()],
        provenance=make_provenance(
            ReviewStatus.NEEDS_REVIEW
        ),
        anomalies=[anomaly],
    )

    assert result.decision == ReviewDecision.NEEDS_REVIEW
    assert len(result.reasons) == 2


def test_review_result_is_not_a_trade_signal():

    result = review_ingestion(
        symbol="TEST",
        bars=[make_bar()],
        provenance=make_provenance(),
        anomalies=[],
    )

    assert result.is_trade_signal is False
