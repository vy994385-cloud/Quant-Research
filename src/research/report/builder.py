from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from src.research.features.models import (
    FeatureStatus,
    FeatureValue,
)
from src.research.features.financial_trends import (
    FinancialTrendSummary,
)
from src.research.report.models import (
    ResearchConclusion,
    ResearchEvidence,
    ResearchReport,
)
from src.research.signals.models import (
    ResearchSignal,
    SignalDirection,
    SignalSeverity,
)


_SEVERITY_WEIGHT = {
    SignalSeverity.INFO: 1,
    SignalSeverity.LOW: 2,
    SignalSeverity.MEDIUM: 3,
    SignalSeverity.HIGH: 4,
    SignalSeverity.CRITICAL: 5,
}


def _validate_as_of(as_of: datetime) -> None:
    if as_of.tzinfo is None:
        raise ValueError(
            "as_of must be timezone-aware"
        )


def _usable_features(
    features: list[FeatureValue],
    *,
    as_of: datetime,
) -> list[FeatureValue]:
    usable: list[FeatureValue] = []

    for feature in features:
        if feature.status != FeatureStatus.VALID:
            continue

        if feature.value is None:
            continue

        if feature.observation_at > feature.calculated_at:
            continue

        if feature.observation_at > as_of:
            continue

        if feature.calculated_at > as_of:
            continue

        usable.append(feature)

    return usable


def _confidence(
    features: list[FeatureValue],
    signals: list[ResearchSignal],
) -> Decimal:
    values: list[Decimal] = []

    values.extend(
        Decimal(str(feature.confidence))
        for feature in features
    )

    values.extend(
        signal.confidence
        for signal in signals
    )

    if not values:
        return Decimal("0")

    return sum(values, Decimal("0")) / Decimal(len(values))


def _conclusion(
    signals: list[ResearchSignal],
) -> ResearchConclusion:
    if not signals:
        return ResearchConclusion.INSUFFICIENT_EVIDENCE

    positive = Decimal("0")
    negative = Decimal("0")

    for signal in signals:
        weight = Decimal(
            _SEVERITY_WEIGHT[signal.severity]
        ) * signal.confidence

        if signal.direction == SignalDirection.POSITIVE:
            positive += weight

        elif signal.direction == SignalDirection.NEGATIVE:
            negative += weight

    if positive == 0 and negative == 0:
        return ResearchConclusion.NEUTRAL

    if positive > negative * Decimal("1.25"):
        return ResearchConclusion.POSITIVE

    if negative > positive * Decimal("1.25"):
        return ResearchConclusion.NEGATIVE

    return ResearchConclusion.MIXED


def _thesis(
    *,
    symbol: str,
    conclusion: ResearchConclusion,
    features: list[FeatureValue],
    signals: list[ResearchSignal],
) -> str:
    if not signals:
        return (
            f"{symbol} does not have enough validated "
            "point-in-time evidence to form a research conclusion."
        )

    positive = [
        signal for signal in signals
        if signal.direction == SignalDirection.POSITIVE
    ]

    negative = [
        signal for signal in signals
        if signal.direction == SignalDirection.NEGATIVE
    ]

    if conclusion == ResearchConclusion.POSITIVE:
        return (
            f"{symbol} shows a predominantly positive research "
            f"profile across the available evidence, with "
            f"{len(positive)} positive signal(s) versus "
            f"{len(negative)} negative signal(s)."
        )

    if conclusion == ResearchConclusion.NEGATIVE:
        return (
            f"{symbol} shows a predominantly negative research "
            f"profile across the available evidence, with "
            f"{len(negative)} negative signal(s) versus "
            f"{len(positive)} positive signal(s)."
        )

    if conclusion == ResearchConclusion.MIXED:
        return (
            f"{symbol} presents mixed research evidence. "
            f"The available dataset contains {len(positive)} "
            f"positive and {len(negative)} negative signal(s)."
        )

    return (
        f"{symbol} has validated research evidence, but the "
        "available signals do not establish a strong directional "
        "conclusion."
    )


def _feature_evidence(
    features: list[FeatureValue],
) -> list[ResearchEvidence]:
    evidence: list[ResearchEvidence] = []

    for feature in features:
        evidence.append(
            ResearchEvidence(
                evidence_id=(
                    f"FEATURE_{feature.feature_id.upper()}"
                ),
                title=feature.feature_id.replace("_", " ").title(),
                explanation=(
                    f"{feature.feature_id} was measured at "
                    f"{feature.value} {feature.unit}."
                ),
                symbol=feature.symbol,
                observation_at=feature.observation_at,
                source_ids=feature.source_ids,
                provenance_ids=feature.provenance_ids,
                confidence=Decimal(
                    str(feature.confidence)
                ),
            )
        )

    return evidence


def _signal_evidence(
    signals: list[ResearchSignal],
) -> tuple[
    list[ResearchEvidence],
    list[ResearchEvidence],
]:
    positive: list[ResearchEvidence] = []
    negative: list[ResearchEvidence] = []

    for signal in signals:
        evidence = ResearchEvidence(
            evidence_id=f"SIGNAL_{signal.signal_id}",
            title=signal.title,
            explanation=signal.explanation,
            symbol=signal.symbol,
            observation_at=signal.observation_at,
            confidence=signal.confidence,
        )

        if signal.direction == SignalDirection.POSITIVE:
            positive.append(evidence)

        elif signal.direction == SignalDirection.NEGATIVE:
            negative.append(evidence)

    return positive, negative


def build_company_report(
    *,
    symbol: str,
    as_of: datetime,
    features: list[FeatureValue],
    signals: list[ResearchSignal] | None = None,
    trend_summaries: list[FinancialTrendSummary] | None = None,
) -> ResearchReport:
    """
    Build a deterministic point-in-time company research report.

    Signals supplied to this function are filtered so future
    observations/calculations cannot enter the report.
    """

    _validate_as_of(as_of)

    symbol = symbol.strip().upper()

    if not symbol:
        raise ValueError("symbol cannot be empty")

    usable = _usable_features(
        features,
        as_of=as_of,
    )

    filtered_signals: list[ResearchSignal] = []

    for signal in signals or []:
        if signal.symbol.upper() != symbol:
            continue

        if signal.observation_at > as_of:
            continue

        filtered_signals.append(signal)

    feature_ids = tuple(
        sorted(
            {
                feature.feature_id
                for feature in usable
            }
        )
    )

    positive_evidence = _feature_evidence(usable)
    signal_positive, signal_negative = _signal_evidence(
        filtered_signals
    )

    positive_evidence.extend(signal_positive)

    trend_summaries = trend_summaries or []

    for summary in trend_summaries:
        if summary.direction == "INCREASING":
            positive_evidence.append(
                ResearchEvidence(
                    evidence_id=(
                        f"TREND_{summary.metric.upper()}"
                    ),
                    title=f"Increasing {summary.metric}",
                    explanation=summary.explanation,
                    symbol=symbol,
                    observation_at=as_of,
                    confidence=Decimal("0.80"),
                )
            )

        elif summary.direction == "DECREASING":
            signal_negative.append(
                ResearchEvidence(
                    evidence_id=(
                        f"TREND_RISK_{summary.metric.upper()}"
                    ),
                    title=f"Deteriorating {summary.metric}",
                    explanation=summary.explanation,
                    symbol=symbol,
                    observation_at=as_of,
                    confidence=Decimal("0.80"),
                )
            )

    conclusion = _conclusion(filtered_signals)

    return ResearchReport(
        symbol=symbol,
        as_of=as_of,
        conclusion=conclusion,
        confidence=_confidence(
            usable,
            filtered_signals,
        ),
        thesis=_thesis(
            symbol=symbol,
            conclusion=conclusion,
            features=usable,
            signals=filtered_signals,
        ),
        features=feature_ids,
        signals=tuple(filtered_signals),
        positive_evidence=tuple(positive_evidence),
        negative_evidence=tuple(signal_negative),
        data_quality_notes=(
            (
                "Only VALID features whose observation and "
                "calculation timestamps are on or before the "
                "report as-of timestamp were included."
            ),
        ),
    )
