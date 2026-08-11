from datetime import datetime, timezone
from decimal import Decimal

from src.research.features.models import (
    FeatureValue,
)
from src.research.report.builder import (
    build_company_report,
)
from src.research.report.models import (
    ResearchConclusion,
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
    observation_at: datetime = AS_OF,
) -> FeatureValue:
    return FeatureValue(
        feature_id=feature_id,
        feature_version="1.0",
        symbol="TEST",
        value=value,
        unit="percent",
        observation_at=observation_at,
        calculated_at=observation_at,
        confidence=0.9,
    )


def signal(
    signal_id: str,
    direction: SignalDirection,
) -> ResearchSignal:
    return ResearchSignal(
        signal_id=signal_id,
        category="FINANCIAL",
        direction=direction,
        severity=SignalSeverity.MEDIUM,
        confidence=Decimal("0.9"),
        title=signal_id,
        explanation="Research evidence.",
        symbol="TEST",
        observation_at=AS_OF,
    )


def test_positive_report():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[
            feature("revenue_growth", 20.0),
        ],
        signals=[
            signal(
                "FIN_REVENUE_GROWTH",
                SignalDirection.POSITIVE,
            ),
        ],
    )

    assert report.symbol == "TEST"
    assert report.conclusion == ResearchConclusion.POSITIVE
    assert report.features == ("revenue_growth",)
    assert len(report.positive_evidence) >= 1
    assert report.confidence > Decimal("0")


def test_negative_report():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[
            feature("net_profit_margin", -5.0),
        ],
        signals=[
            signal(
                "FIN_NEGATIVE_NET_MARGIN",
                SignalDirection.NEGATIVE,
            ),
        ],
    )

    assert report.conclusion == ResearchConclusion.NEGATIVE
    assert len(report.negative_evidence) >= 1


def test_mixed_report():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[
            feature("revenue_growth", 20.0),
        ],
        signals=[
            signal(
                "FIN_REVENUE_GROWTH",
                SignalDirection.POSITIVE,
            ),
            signal(
                "FIN_HIGH_DEBT",
                SignalDirection.NEGATIVE,
            ),
        ],
    )

    assert report.conclusion == ResearchConclusion.MIXED


def test_future_feature_is_excluded():
    later = datetime(
        2026,
        8,
        11,
        12,
        0,
        tzinfo=timezone.utc,
    )

    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[
            feature(
                "revenue_growth",
                30.0,
                observation_at=later,
            ),
        ],
    )

    assert report.features == ()
    assert report.conclusion == (
        ResearchConclusion.INSUFFICIENT_EVIDENCE
    )


def test_future_signal_is_excluded():
    later = datetime(
        2026,
        8,
        11,
        12,
        0,
        tzinfo=timezone.utc,
    )

    future_signal = ResearchSignal(
        signal_id="FUTURE",
        category="FINANCIAL",
        direction=SignalDirection.POSITIVE,
        severity=SignalSeverity.INFO,
        confidence=Decimal("0.9"),
        title="Future",
        explanation="Future evidence.",
        symbol="TEST",
        observation_at=later,
    )

    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        signals=[future_signal],
    )

    assert report.signals == ()
    assert report.conclusion == (
        ResearchConclusion.INSUFFICIENT_EVIDENCE
    )


def test_other_symbol_is_excluded():
    other = ResearchSignal(
        signal_id="OTHER",
        category="FINANCIAL",
        direction=SignalDirection.POSITIVE,
        severity=SignalSeverity.INFO,
        confidence=Decimal("0.9"),
        title="Other",
        explanation="Other company.",
        symbol="OTHER",
        observation_at=AS_OF,
    )

    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        signals=[other],
    )

    assert report.signals == ()
    assert report.conclusion == (
        ResearchConclusion.INSUFFICIENT_EVIDENCE
    )
