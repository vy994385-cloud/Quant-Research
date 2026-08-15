from __future__ import annotations

from datetime import datetime, time, timezone
from decimal import Decimal

from src.research.features.models import (
    FeatureStatus,
    FeatureValue,
)
from src.research.features.financial_trends import (
    FinancialTrendSummary,
)
from src.research.report.models import (
    CompanyIntelligenceReport,
    ResearchConclusion,
    ResearchEvidence,
    ResearchReport,
)
from src.research.intelligence import build_research_intelligence
from src.data.company.financials import FinancialSnapshot
from src.features.market_snapshot import MarketFeatureSnapshot
from src.research.signals.models import (
    ResearchSignal,
    SignalDirection,
    SignalSeverity,
)

from src.research.synthesis.models import (
    EvidenceDirection,
    EvidenceItem,
    EvidenceReliability,
    EvidenceType,
)
from src.research.synthesis.evidence import (
    synthesize_evidence,
)


from src.research.narrative.engine import (
    build_evidence_narrative,
)

from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
    EvidenceReference,
    IntelligenceDirection,
    IntelligenceSignal,
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
        raise ValueError("as_of must be timezone-aware")


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


def _trend_signals(
    summaries: list[FinancialTrendSummary],
    *,
    symbol: str,
    as_of: datetime,
) -> list[ResearchSignal]:
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
                        observation_at=as_of,
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
                        observation_at=as_of,
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
                    observation_at=as_of,
                    supporting_features=(metric,),
                )
            )

    return signals


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
        weight = (
            Decimal(_SEVERITY_WEIGHT[signal.severity])
            * signal.confidence
        )

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


def _feature_evidence(
    features: list[FeatureValue],
    *,
    symbol: str,
) -> list[ResearchEvidence]:
    evidence: list[ResearchEvidence] = []

    for feature in features:
        evidence.append(
            ResearchEvidence(
                evidence_id=f"FEATURE_{feature.feature_id}",
                title=f"Validated feature: {feature.feature_id}",
                explanation=(
                    f"Feature {feature.feature_id} is available "
                    "as validated point-in-time research evidence."
                ),
                symbol=symbol,
                observation_at=feature.observation_at,
                confidence=Decimal(str(feature.confidence)),
                source_ids=tuple(feature.source_ids),
                provenance_ids=tuple(feature.provenance_ids),
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
            source_ids=(),
            provenance_ids=(),
        )

        if signal.direction == SignalDirection.POSITIVE:
            positive.append(evidence)

        elif signal.direction == SignalDirection.NEGATIVE:
            negative.append(evidence)

    return positive, negative


def _research_evidence_items(
    *,
    positive: list[ResearchEvidence],
    negative: list[ResearchEvidence],
    as_of: datetime,
) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []

    for evidence in positive:
        items.append(
            EvidenceItem(
                evidence_id=evidence.evidence_id,
                symbol=evidence.symbol,
                evidence_type=EvidenceType.FEATURE,
                title=evidence.title,
                explanation=evidence.explanation,
                direction=EvidenceDirection.POSITIVE,
                confidence=evidence.confidence,
                reliability=EvidenceReliability.UNKNOWN,
                observation_at=evidence.observation_at,
                source_ids=evidence.source_ids,
                provenance_ids=evidence.provenance_ids,
            )
        )

    for evidence in negative:
        items.append(
            EvidenceItem(
                evidence_id=evidence.evidence_id,
                symbol=evidence.symbol,
                evidence_type=EvidenceType.SIGNAL,
                title=evidence.title,
                explanation=evidence.explanation,
                direction=EvidenceDirection.NEGATIVE,
                confidence=evidence.confidence,
                reliability=EvidenceReliability.UNKNOWN,
                observation_at=evidence.observation_at,
                source_ids=evidence.source_ids,
                provenance_ids=evidence.provenance_ids,
            )
        )

    return [
        item
        for item in items
        if item.observation_at <= as_of
    ]


def _intelligence_reliability(
    reference: EvidenceReference,
) -> EvidenceReliability:
    """
    Map company-intelligence source quality into the
    normalized evidence reliability contract.

    The mapping is deliberately conservative.
    """
    if reference.source_type.upper() == "REGULATORY":
        return EvidenceReliability.REGULATORY

    if reference.source_type.upper() == "AUDITED":
        return EvidenceReliability.AUDITED

    if reference.reliability_tier == 1:
        return EvidenceReliability.PRIMARY

    if reference.reliability_tier == 2:
        return EvidenceReliability.PRIMARY

    if reference.reliability_tier == 3:
        return EvidenceReliability.SECONDARY

    if reference.reliability_tier == 4:
        return EvidenceReliability.TERTIARY

    return EvidenceReliability.UNKNOWN


def _intelligence_observation_at(
    snapshot: CompanyResearchSnapshot,
) -> datetime:
    """
    Convert the intelligence snapshot's date-level observation
    into the normalized timezone-aware evidence timestamp.

    We intentionally use the beginning of the stated observation
    date rather than inventing an intraday timestamp.
    """
    return datetime.combine(
        snapshot.as_of_date,
        time.min,
        tzinfo=timezone.utc,
    )


def _company_intelligence_evidence_items(
    snapshot: CompanyResearchSnapshot | None,
    *,
    symbol: str,
    as_of: datetime,
) -> list[EvidenceItem]:
    """
    Convert validated company-intelligence observations into
    normalized point-in-time EvidenceItems.

    Future intelligence is excluded before synthesis.
    """
    if snapshot is None:
        return []

    if snapshot.symbol.strip().upper() != symbol:
        return []

    observation_at = _intelligence_observation_at(snapshot)

    if observation_at > as_of:
        return []

    items: list[EvidenceItem] = []

    for signal in snapshot.signals:
        if signal.direction == IntelligenceDirection.POSITIVE:
            direction = EvidenceDirection.POSITIVE
        elif signal.direction == IntelligenceDirection.NEGATIVE:
            direction = EvidenceDirection.NEGATIVE
        elif signal.direction == IntelligenceDirection.NEUTRAL:
            direction = EvidenceDirection.NEUTRAL
        else:
            direction = EvidenceDirection.MIXED

        references = signal.evidence

        if references:
            for index, reference in enumerate(references):
                evidence_id = (
                    f"INTELLIGENCE_{signal.code}_{index}"
                )

                items.append(
                    EvidenceItem(
                        evidence_id=evidence_id,
                        symbol=symbol,
                        evidence_type=(
                            EvidenceType.COMPANY_INTELLIGENCE
                        ),
                        title=signal.title,
                        explanation=signal.description,
                        direction=direction,
                        confidence=signal.confidence,
                        reliability=(
                            _intelligence_reliability(reference)
                        ),
                        observation_at=observation_at,
                        source_ids=(
                            (reference.reference,)
                            if reference.reference
                            else ()
                        ),
                        provenance_ids=(),
                    )
                )

        else:
            items.append(
                EvidenceItem(
                    evidence_id=(
                        f"INTELLIGENCE_{signal.code}"
                    ),
                    symbol=symbol,
                    evidence_type=(
                        EvidenceType.COMPANY_INTELLIGENCE
                    ),
                    title=signal.title,
                    explanation=signal.description,
                    direction=direction,
                    confidence=signal.confidence,
                    reliability=EvidenceReliability.UNKNOWN,
                    observation_at=observation_at,
                    source_ids=(),
                    provenance_ids=(),
                )
            )

    return items


def _company_intelligence_report(
    snapshot: CompanyResearchSnapshot | None,
    *,
    fallback_present: bool = False,
    fallback_signal_count: int = 0,
    fallback_positive_count: int = 0,
    fallback_negative_count: int = 0,
) -> CompanyIntelligenceReport:
    if snapshot is None:
        return CompanyIntelligenceReport(
            present=fallback_present,
            signal_count=fallback_signal_count,
            positive_signal_count=fallback_positive_count,
            negative_signal_count=fallback_negative_count,
        )

    return CompanyIntelligenceReport(
        present=True,
        signal_count=snapshot.signal_count,
        material_signal_count=snapshot.material_signal_count,
        positive_signal_count=snapshot.positive_signal_count,
        negative_signal_count=snapshot.negative_signal_count,
        financial_observations=tuple(
            snapshot.financial_observations
        ),
        ownership_observations=tuple(
            snapshot.ownership_observations
        ),
        management_observations=tuple(
            snapshot.management_observations
        ),
        related_party_observations=tuple(
            snapshot.related_party_observations
        ),
        event_observations=tuple(
            snapshot.event_observations
        ),
        market_observations=tuple(
            snapshot.market_observations
        ),
        risk_observations=tuple(
            snapshot.risk_observations
        ),
        future_readiness=snapshot.future_readiness,
        ai_participation=snapshot.ai_participation,
        innovation_execution=snapshot.innovation_execution,
        technology_diversification=(
            snapshot.technology_diversification
        ),
    )


def _thesis(
    *,
    symbol: str,
    conclusion: ResearchConclusion,
    signals: list[ResearchSignal],
    company_intelligence_present: bool = False,
    company_intelligence_signal_count: int = 0,
    company_intelligence_positive_count: int = 0,
    company_intelligence_negative_count: int = 0,
) -> str:
    if not signals:
        if company_intelligence_present:
            return (
                f"{symbol} has company-intelligence data available, "
                "but there is not enough validated point-in-time "
                "evidence to form a broader research conclusion."
            )

        return (
            f"{symbol} does not have enough validated "
            "point-in-time evidence to form a research conclusion."
        )

    positive = [
        signal
        for signal in signals
        if signal.direction == SignalDirection.POSITIVE
    ]

    negative = [
        signal
        for signal in signals
        if signal.direction == SignalDirection.NEGATIVE
    ]

    if conclusion == ResearchConclusion.POSITIVE:
        base_thesis = (
            f"{symbol} shows a predominantly positive research "
            f"profile across the available evidence, with "
            f"{len(positive)} positive signal(s) versus "
            f"{len(negative)} negative signal(s)."
        )

    elif conclusion == ResearchConclusion.NEGATIVE:
        base_thesis = (
            f"{symbol} shows a predominantly negative research "
            f"profile across the available evidence, with "
            f"{len(negative)} negative signal(s) versus "
            f"{len(positive)} positive signal(s)."
        )

    elif conclusion == ResearchConclusion.MIXED:
        base_thesis = (
            f"{symbol} presents mixed research evidence. "
            f"The available dataset contains {len(positive)} "
            f"positive and {len(negative)} negative signal(s)."
        )

    elif conclusion == ResearchConclusion.INSUFFICIENT_EVIDENCE:
        base_thesis = (
            f"{symbol} does not have enough validated "
            "point-in-time evidence to form a research conclusion."
        )

    else:
        base_thesis = (
            f"{symbol} has validated research evidence, but the "
            "available signals do not establish a strong directional "
            "conclusion."
        )

    if company_intelligence_present:
        base_thesis += (
            f" Company intelligence contributed "
            f"{company_intelligence_signal_count} signal(s), "
            f"including {company_intelligence_positive_count} "
            f"positive and {company_intelligence_negative_count} "
            f"negative observation(s)."
        )

    return base_thesis

def build_company_report(
    *,
    symbol: str,
    as_of: datetime,
    features: list[FeatureValue],
    signals: list[ResearchSignal] | None = None,
    trend_summaries: list[FinancialTrendSummary] | None = None,
    company_snapshot: CompanyResearchSnapshot | None = None,
    financial_snapshots: list[FinancialSnapshot] | None = None,
    market_snapshot: MarketFeatureSnapshot | None = None,
    provenance_ids: tuple[str, ...] = (),
    company_intelligence_present: bool = False,
    company_intelligence_signal_count: int = 0,
    company_intelligence_positive_count: int = 0,
    company_intelligence_negative_count: int = 0,
) -> ResearchReport:
    """
    Build a deterministic point-in-time company research report.

    Features, supplied signals, financial trends, and company
    intelligence are assembled without creating new intelligence.
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

    trend_signals = _trend_signals(
        trend_summaries or [],
        symbol=symbol,
        as_of=as_of,
    )

    all_signals = [
        *filtered_signals,
        *trend_signals,
    ]

    feature_ids = tuple(
        sorted(
            {
                feature.feature_id
                for feature in usable
            }
        )
    )

    positive_evidence = _feature_evidence(
        usable,
        symbol=symbol,
    )

    signal_positive, signal_negative = _signal_evidence(
        all_signals
    )

    positive_evidence.extend(signal_positive)

    intelligence = _company_intelligence_report(
        company_snapshot,
        fallback_present=company_intelligence_present,
        fallback_signal_count=company_intelligence_signal_count,
        fallback_positive_count=(
            company_intelligence_positive_count
        ),
        fallback_negative_count=(
            company_intelligence_negative_count
        ),
    )

    conclusion = _conclusion(all_signals)

    synthesis_evidence = _research_evidence_items(
        positive=positive_evidence,
        negative=signal_negative,
        as_of=as_of,
    )

    synthesis_evidence.extend(
        _company_intelligence_evidence_items(
            company_snapshot,
            symbol=symbol,
            as_of=as_of,
        )
    )

    evidence_synthesis = synthesize_evidence(
        symbol=symbol,
        as_of=as_of,
        evidence=synthesis_evidence,
    )

    evidence_narrative = build_evidence_narrative(
        evidence_synthesis
    )

    research_intelligence = build_research_intelligence(
        symbol=symbol,
        as_of=as_of,
        features=usable,
        trend_summaries=trend_summaries or [],
        company_snapshot=company_snapshot,
        financial_snapshots=financial_snapshots or [],
        market_snapshot=market_snapshot,
        provenance_ids=provenance_ids,
    )

    return ResearchReport(
        symbol=symbol,
        as_of=as_of,
        conclusion=conclusion,
        confidence=_confidence(
            usable,
            all_signals,
        ),
        thesis=_thesis(
            symbol=symbol,
            conclusion=conclusion,
            signals=all_signals,
            company_intelligence_present=(
                intelligence.present
            ),
            company_intelligence_signal_count=(
                intelligence.signal_count
            ),
            company_intelligence_positive_count=(
                intelligence.positive_signal_count
            ),
            company_intelligence_negative_count=(
                intelligence.negative_signal_count
            ),
        ),
        features=feature_ids,
        signals=tuple(all_signals),
        positive_evidence=tuple(positive_evidence),
        negative_evidence=tuple(signal_negative),
        evidence_synthesis=evidence_synthesis,
        evidence_narrative=evidence_narrative,
        research_intelligence=research_intelligence,
        data_quality_notes=(
            (
                "Only VALID features whose observation and "
                "calculation timestamps are on or before the "
                "report as-of timestamp were included."
            ),
            (
                "Financial trend summaries are converted into "
                "point-in-time research signals before conclusion "
                "and confidence calculations."
            ),
            (
                "Company intelligence is carried into the report "
                "as descriptive evidence and future-intelligence "
                "context; it does not constitute a trading signal."
            ),
        ),
        company_intelligence=intelligence,
        company_intelligence_present=intelligence.present,
        company_intelligence_signal_count=(
            intelligence.signal_count
        ),
        company_intelligence_positive_count=(
            intelligence.positive_signal_count
        ),
        company_intelligence_negative_count=(
            intelligence.negative_signal_count
        ),
    )


__all__ = [
    "build_company_report",
]
