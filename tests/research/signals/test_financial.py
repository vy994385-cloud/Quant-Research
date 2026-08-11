from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.research.features.models import (
    FeatureStatus,
    FeatureValue,
)
from src.research.features.financial_trends import (
    FinancialTrendSummary,
)
from src.research.signals.financial import (
    signals_from_features,
    signals_from_trend_summaries,
)
from src.research.signals.models import (
    ResearchSignal,
    SignalDirection,
    SignalSeverity,
)


AS_OF = datetime(
    2026,
    8,
    10,
    12,
    0,
    tzinfo=timezone.utc,
)


def feature(
    feature_id: str,
    value: float,
    *,
    symbol: str = "TEST",
) -> FeatureValue:
    return FeatureValue(
        feature_id=feature_id,
        feature_version="1.0",
        symbol=symbol,
        value=value,
        unit="percent",
        observation_at=AS_OF,
        calculated_at=AS_OF,
    )


def test_revenue_growth_creates_positive_signal():
    signals = signals_from_features(
        [feature("revenue_growth", 25.0)]
    )

    assert len(signals) == 1

    signal = signals[0]

    assert signal.signal_id == "FIN_REVENUE_GROWTH"
    assert signal.direction == SignalDirection.POSITIVE
    assert signal.severity == SignalSeverity.INFO
    assert signal.symbol == "TEST"
    assert signal.supporting_features == (
        "revenue_growth",
    )


def test_revenue_contraction_creates_negative_signal():
    signals = signals_from_features(
        [feature("revenue_growth", -15.0)]
    )

    assert len(signals) == 1

    assert signals[0].signal_id == (
        "FIN_REVENUE_CONTRACTION"
    )

    assert signals[0].direction == (
        SignalDirection.NEGATIVE
    )


def test_healthy_margin_creates_positive_signal():
    signals = signals_from_features(
        [feature("net_profit_margin", 20.0)]
    )

    assert signals[0].signal_id == "FIN_NET_MARGIN"


def test_negative_margin_creates_negative_signal():
    signals = signals_from_features(
        [feature("net_profit_margin", -5.0)]
    )

    assert signals[0].direction == (
        SignalDirection.NEGATIVE
    )


def test_strong_cash_generation_creates_signal():
    signals = signals_from_features(
        [feature("operating_cash_flow_margin", 18.0)]
    )

    assert signals[0].signal_id == (
        "FIN_OPERATING_CASH_FLOW"
    )


def test_negative_cash_flow_creates_signal():
    signals = signals_from_features(
        [feature("operating_cash_flow_margin", -2.0)]
    )

    assert signals[0].direction == (
        SignalDirection.NEGATIVE
    )


def test_high_debt_creates_risk_signal():
    signals = signals_from_features(
        [
            FeatureValue(
                feature_id="debt_to_revenue",
                feature_version="1.0",
                symbol="TEST",
                value=1.5,
                unit="ratio",
                observation_at=AS_OF,
                calculated_at=AS_OF,
            )
        ]
    )

    assert signals[0].signal_id == "FIN_HIGH_DEBT"
    assert signals[0].category == "FINANCIAL"


def test_strong_cash_to_debt_creates_positive_signal():
    signals = signals_from_features(
        [
            FeatureValue(
                feature_id="cash_to_debt",
                feature_version="1.0",
                symbol="TEST",
                value=1.2,
                unit="ratio",
                observation_at=AS_OF,
                calculated_at=AS_OF,
            )
        ]
    )

    assert signals[0].signal_id == (
        "FIN_CASH_DEBT_COVERAGE"
    )


def test_elevated_receivables_creates_screening_signal():
    signals = signals_from_features(
        [
            FeatureValue(
                feature_id="receivables_to_revenue",
                feature_version="1.0",
                symbol="TEST",
                value=35.0,
                unit="percent",
                observation_at=AS_OF,
                calculated_at=AS_OF,
            )
        ]
    )

    assert signals[0].signal_id == (
        "FIN_ELEVATED_RECEIVABLES"
    )


def test_invalid_feature_is_ignored():
    invalid = FeatureValue(
        feature_id="revenue_growth",
        feature_version="1.0",
        symbol="TEST",
        value=None,
        unit="percent",
        observation_at=AS_OF,
        calculated_at=AS_OF,
        status=FeatureStatus.MISSING,
    )

    assert signals_from_features([invalid]) == []


def test_low_quality_feature_does_not_create_signal():
    low_confidence = FeatureValue(
        feature_id="revenue_growth",
        feature_version="1.0",
        symbol="TEST",
        value=30.0,
        unit="percent",
        observation_at=AS_OF,
        calculated_at=AS_OF,
        confidence=0.2,
    )

    signals = signals_from_features(
        [low_confidence]
    )

    assert len(signals) == 1
    assert signals[0].confidence == Decimal("0.2")


def test_pit_unsafe_feature_is_ignored():
    later = datetime(
        2026,
        8,
        11,
        12,
        0,
        tzinfo=timezone.utc,
    )

    unsafe = FeatureValue(
        feature_id="revenue_growth",
        feature_version="1.0",
        symbol="TEST",
        value=30.0,
        unit="percent",
        observation_at=later,
        calculated_at=later,
    )

    assert signals_from_features(
    [unsafe],
    as_of=AS_OF,
) == []


def test_trend_summary_creates_positive_signal():
    summary = FinancialTrendSummary(
        metric="revenue",
        direction="INCREASING",
        observations=4,
        average_change=Decimal("12"),
        positive_periods=3,
        negative_periods=0,
        stable_periods=0,
        consistency=Decimal("100"),
        explanation="Revenue increased consistently.",
    )

    signals = signals_from_trend_summaries(
        [summary],
        symbol="TEST",
        observation_at=AS_OF,
    )

    assert len(signals) == 1
    assert signals[0].direction == SignalDirection.POSITIVE
    assert signals[0].category == "FINANCIAL_TREND"


def test_deteriorating_profit_trend_creates_negative_signal():
    summary = FinancialTrendSummary(
        metric="net_profit",
        direction="DECREASING",
        observations=4,
        average_change=Decimal("-10"),
        positive_periods=0,
        negative_periods=3,
        stable_periods=0,
        consistency=Decimal("100"),
        explanation="Profit declined consistently.",
    )

    signals = signals_from_trend_summaries(
        [summary],
        symbol="TEST",
        observation_at=AS_OF,
    )

    assert signals[0].direction == (
        SignalDirection.NEGATIVE
    )


def test_rising_debt_creates_risk_signal():
    summary = FinancialTrendSummary(
        metric="total_debt",
        direction="INCREASING",
        observations=4,
        average_change=Decimal("15"),
        positive_periods=3,
        negative_periods=0,
        stable_periods=0,
        consistency=Decimal("100"),
        explanation="Debt increased consistently.",
    )

    signals = signals_from_trend_summaries(
        [summary],
        symbol="TEST",
        observation_at=AS_OF,
    )

    assert len(signals) == 1
    assert signals[0].signal_id == (
        "TREND_RISK_TOTAL_DEBT"
    )
    assert signals[0].direction == (
        SignalDirection.NEGATIVE
    )


def test_research_signal_rejects_naive_timestamp():
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        ResearchSignal(
            signal_id="TEST",
            category="FINANCIAL",
            direction=SignalDirection.POSITIVE,
            severity=SignalSeverity.INFO,
            confidence=Decimal("0.8"),
            title="Test signal",
            explanation="Test explanation",
            symbol="TEST",
            observation_at=datetime(
                2026,
                8,
                10,
                12,
            ),
        )


def test_research_signal_normalizes_identity():
    signal = ResearchSignal(
        signal_id=" revenue_growth ",
        category=" financial ",
        direction=SignalDirection.POSITIVE,
        severity=SignalSeverity.INFO,
        confidence=Decimal("0.8"),
        title="Test signal",
        explanation="Test explanation",
        symbol=" test ",
        observation_at=AS_OF,
        supporting_features=(
            "Revenue_Growth",
            "revenue_growth",
        ),
    )

    assert signal.signal_id == "REVENUE_GROWTH"
    assert signal.category == "FINANCIAL"
    assert signal.symbol == "TEST"
    assert signal.supporting_features == (
        "revenue_growth",
    )
