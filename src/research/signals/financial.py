from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from src.research.features.financial_trends import (
    FinancialTrendSummary,
)
from src.research.features.models import (
    FeatureStatus,
    FeatureValue,
)
from src.research.signals.models import (
    ResearchSignal,
    SignalDirection,
    SignalSeverity,
)


def _confidence(feature: FeatureValue) -> Decimal:
    return Decimal(str(feature.confidence))


def _base_signal(
    *,
    feature: FeatureValue,
    signal_id: str,
    direction: SignalDirection,
    severity: SignalSeverity,
    title: str,
    explanation: str,
) -> ResearchSignal:
    return ResearchSignal(
        signal_id=signal_id,
        category="FINANCIAL",
        direction=direction,
        severity=severity,
        confidence=_confidence(feature),
        title=title,
        explanation=explanation,
        symbol=feature.symbol,
        observation_at=feature.observation_at,
        supporting_features=(feature.feature_id,),
    )


def signals_from_features(
    features: list[FeatureValue],
    *,
    as_of: datetime | None = None,
) -> list[ResearchSignal]:
    """
    Convert valid point-in-time financial features into
    deterministic research signals.
    """

    if as_of is not None and as_of.tzinfo is None:
        raise ValueError(
            "as_of must be timezone-aware"
        )

    signals: list[ResearchSignal] = []

    for feature in features:
        if feature.status != FeatureStatus.VALID:
            continue

        if feature.value is None:
            continue

        if feature.observation_at > feature.calculated_at:
            continue

        if as_of is not None:
            if feature.observation_at > as_of:
                continue

            if feature.calculated_at > as_of:
                continue

        if feature.feature_id == "revenue_growth":
            if feature.value > 0:
                signals.append(
                    _base_signal(
                        feature=feature,
                        signal_id="FIN_REVENUE_GROWTH",
                        direction=SignalDirection.POSITIVE,
                        severity=SignalSeverity.INFO,
                        title="Revenue growth",
                        explanation=(
                            f"Revenue increased by "
                            f"{feature.value}%."
                        ),
                    )
                )

            elif feature.value < 0:
                signals.append(
                    _base_signal(
                        feature=feature,
                        signal_id="FIN_REVENUE_CONTRACTION",
                        direction=SignalDirection.NEGATIVE,
                        severity=SignalSeverity.MEDIUM,
                        title="Revenue contraction",
                        explanation=(
                            f"Revenue declined by "
                            f"{abs(feature.value)}%."
                        ),
                    )
                )

        elif feature.feature_id == "net_profit_margin":
            if feature.value > 0:
                signals.append(
                    _base_signal(
                        feature=feature,
                        signal_id="FIN_NET_MARGIN",
                        direction=SignalDirection.POSITIVE,
                        severity=SignalSeverity.INFO,
                        title="Positive net profit margin",
                        explanation=(
                            f"Net profit margin was "
                            f"{feature.value}%."
                        ),
                    )
                )

            elif feature.value < 0:
                signals.append(
                    _base_signal(
                        feature=feature,
                        signal_id="FIN_NEGATIVE_NET_MARGIN",
                        direction=SignalDirection.NEGATIVE,
                        severity=SignalSeverity.MEDIUM,
                        title="Negative net profit margin",
                        explanation=(
                            f"Net profit margin was "
                            f"{feature.value}%."
                        ),
                    )
                )

        elif feature.feature_id == "operating_cash_flow_margin":
            if feature.value > 0:
                signals.append(
                    _base_signal(
                        feature=feature,
                        signal_id="FIN_OPERATING_CASH_FLOW",
                        direction=SignalDirection.POSITIVE,
                        severity=SignalSeverity.INFO,
                        title="Positive operating cash flow",
                        explanation=(
                            "Operating cash flow remained positive "
                            f"at {feature.value}% of revenue."
                        ),
                    )
                )

            elif feature.value < 0:
                signals.append(
                    _base_signal(
                        feature=feature,
                        signal_id="FIN_NEGATIVE_OPERATING_CASH_FLOW",
                        direction=SignalDirection.NEGATIVE,
                        severity=SignalSeverity.MEDIUM,
                        title="Negative operating cash flow",
                        explanation=(
                            "Operating cash flow was negative "
                            f"at {feature.value}% of revenue."
                        ),
                    )
                )

        elif feature.feature_id == "debt_to_revenue":
            if feature.value >= 1.0:
                signals.append(
                    _base_signal(
                        feature=feature,
                        signal_id="FIN_HIGH_DEBT",
                        direction=SignalDirection.NEGATIVE,
                        severity=SignalSeverity.MEDIUM,
                        title="High debt relative to revenue",
                        explanation=(
                            f"Debt-to-revenue ratio was "
                            f"{feature.value}."
                        ),
                    )
                )

        elif feature.feature_id == "cash_to_debt":
            if feature.value >= 1.0:
                signals.append(
                    _base_signal(
                        feature=feature,
                        signal_id="FIN_CASH_DEBT_COVERAGE",
                        direction=SignalDirection.POSITIVE,
                        severity=SignalSeverity.INFO,
                        title="Strong cash debt coverage",
                        explanation=(
                            f"Cash-to-debt ratio was "
                            f"{feature.value}."
                        ),
                    )
                )

        elif feature.feature_id == "receivables_to_revenue":
            if feature.value >= 30.0:
                signals.append(
                    _base_signal(
                        feature=feature,
                        signal_id="FIN_ELEVATED_RECEIVABLES",
                        direction=SignalDirection.NEGATIVE,
                        severity=SignalSeverity.LOW,
                        title="Elevated receivables",
                        explanation=(
                            f"Receivables represented "
                            f"{feature.value}% of revenue."
                        ),
                    )
                )

    return signals


def signals_from_trend_summaries(
    summaries: list[FinancialTrendSummary],
    *,
    symbol: str,
    observation_at: datetime,
) -> list[ResearchSignal]:
    """
    Convert multi-period financial trend summaries into signals.
    """

    if observation_at.tzinfo is None:
        raise ValueError(
            "observation_at must be timezone-aware"
        )

    signals: list[ResearchSignal] = []

    for summary in summaries:
        metric = summary.metric
        direction = summary.direction

        if direction == "INCREASING":
            if metric == "total_debt":
                signals.append(
                    ResearchSignal(
                        signal_id="TREND_RISK_TOTAL_DEBT",
                        category="FINANCIAL_TREND",
                        direction=SignalDirection.NEGATIVE,
                        severity=SignalSeverity.MEDIUM,
                        confidence=Decimal("0.80"),
                        title="Rising debt trend",
                        explanation=summary.explanation,
                        symbol=symbol,
                        observation_at=observation_at,
                        supporting_features=(metric,),
                    )
                )
            else:
                signals.append(
                    ResearchSignal(
                        signal_id=f"TREND_{metric.upper()}",
                        category="FINANCIAL_TREND",
                        direction=SignalDirection.POSITIVE,
                        severity=SignalSeverity.INFO,
                        confidence=Decimal("0.80"),
                        title=f"Increasing {metric}",
                        explanation=summary.explanation,
                        symbol=symbol,
                        observation_at=observation_at,
                        supporting_features=(metric,),
                    )
                )

        elif direction == "DECREASING":
            signals.append(
                ResearchSignal(
                    signal_id=f"TREND_RISK_{metric.upper()}",
                    category="FINANCIAL_TREND",
                    direction=SignalDirection.NEGATIVE,
                    severity=SignalSeverity.MEDIUM,
                    confidence=Decimal("0.80"),
                    title=f"Deteriorating {metric}",
                    explanation=summary.explanation,
                    symbol=symbol,
                    observation_at=observation_at,
                    supporting_features=(metric,),
                )
            )

    return signals
