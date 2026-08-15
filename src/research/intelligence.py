"""Evidence-first company intelligence assembly.

This module only normalizes outputs already produced by providers and
analysis modules. It never supplies a default positive or negative view when
the underlying dataset is absent.
"""

from __future__ import annotations

from datetime import datetime, time, timezone
from decimal import Decimal
from typing import Iterable

from src.analysis.financial_anomalies import analyze_financial_change
from src.analysis.financial_ratios import (
    cash_conversion_ratio,
    free_cash_flow_margin,
    net_profit_margin,
    operating_cash_flow_margin,
)
from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
    IntelligenceDirection,
)
from src.data.company.financials import FinancialSnapshot
from src.features.market_snapshot import MarketFeatureSnapshot
from src.research.features.financial_trends import FinancialTrendSummary
from src.research.features.models import FeatureStatus, FeatureValue
from src.research.report.models import (
    IntelligenceConfidence,
    IntelligenceSectionStatus,
    ResearchEvidence,
    ResearchIntelligence,
    ResearchIntelligenceSection,
    ResearchObservation,
)


def _at_date(value) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def _confidence(values: Iterable[Decimal]) -> IntelligenceConfidence:
    values = list(values)
    if not values:
        return IntelligenceConfidence.UNKNOWN
    average = sum(values, Decimal("0")) / Decimal(len(values))
    if average >= Decimal("0.8"):
        return IntelligenceConfidence.HIGH
    if average >= Decimal("0.55"):
        return IntelligenceConfidence.MEDIUM
    return IntelligenceConfidence.LOW


def _confidence_value(value: Decimal | float | None) -> Decimal | None:
    if value is None:
        return None
    normalized = Decimal(str(value))
    if normalized > Decimal("1"):
        normalized /= Decimal("100")
    return max(Decimal("0"), min(Decimal("1"), normalized))


def _status(
    positive: list[ResearchEvidence],
    negative: list[ResearchEvidence],
    observations: list[ResearchObservation],
) -> IntelligenceSectionStatus:
    if positive and negative:
        return IntelligenceSectionStatus.MIXED
    if positive:
        return IntelligenceSectionStatus.SUPPORTED
    if negative:
        return IntelligenceSectionStatus.CONTRADICTED
    if observations:
        return IntelligenceSectionStatus.PARTIAL
    return IntelligenceSectionStatus.UNKNOWN


def _section(
    *,
    as_of: datetime,
    observations: list[ResearchObservation] | None = None,
    positive: list[ResearchEvidence] | None = None,
    negative: list[ResearchEvidence] | None = None,
    unknown: list[str] | None = None,
    source_ids: Iterable[str] = (),
    provenance_ids: Iterable[str] = (),
) -> ResearchIntelligenceSection:
    observations = observations or []
    positive = positive or []
    negative = negative or []
    unknown = unknown or []
    evidence = [*positive, *negative]
    confidence_values = [
        item.confidence
        for item in evidence
        if item.confidence is not None
    ]
    confidence_values.extend(
        item.confidence
        for item in observations
        if item.confidence is not None
    )
    all_source_ids = set(source_ids)
    all_provenance_ids = set(provenance_ids)
    for item in evidence:
        all_source_ids.update(item.source_ids)
        all_provenance_ids.update(item.provenance_ids)
    for item in observations:
        all_source_ids.update(item.source_ids)
        all_provenance_ids.update(item.provenance_ids)
    return ResearchIntelligenceSection(
        status=_status(positive, negative, observations),
        confidence=_confidence(confidence_values),
        observations=tuple(observations),
        positive_evidence=tuple(positive),
        negative_evidence=tuple(negative),
        unknown=tuple(unknown),
        as_of=as_of,
        source_ids=tuple(sorted(all_source_ids)),
        provenance_ids=tuple(sorted(all_provenance_ids)),
    )


def _observation(
    *,
    observation_id: str,
    claim: str,
    explanation: str,
    observed_at: datetime,
    confidence: Decimal | None = None,
    source_ids: Iterable[str] = (),
    provenance_ids: Iterable[str] = (),
) -> ResearchObservation:
    return ResearchObservation(
        observation_id=observation_id,
        claim=claim,
        explanation=explanation,
        observed_at=observed_at,
        confidence=confidence,
        source_ids=tuple(source_ids),
        provenance_ids=tuple(provenance_ids),
    )


def _evidence(
    *,
    evidence_id: str,
    title: str,
    explanation: str,
    symbol: str,
    observed_at: datetime,
    confidence: Decimal,
    source_ids: Iterable[str] = (),
    provenance_ids: Iterable[str] = (),
) -> ResearchEvidence:
    return ResearchEvidence(
        evidence_id=evidence_id,
        title=title,
        explanation=explanation,
        symbol=symbol,
        observation_at=observed_at,
        confidence=max(Decimal("0"), min(Decimal("1"), confidence)),
        source_ids=tuple(source_ids),
        provenance_ids=tuple(provenance_ids),
    )


def _trend_direction(metric: str, direction: str) -> str:
    """Return the evidence polarity of a raw trend."""
    if metric in {"total_debt", "receivables", "payables"}:
        return "negative" if direction == "INCREASING" else "positive"
    return "positive" if direction == "INCREASING" else "negative"


def _financial_section(
    *,
    symbol: str,
    as_of: datetime,
    features: list[FeatureValue],
    trends: list[FinancialTrendSummary],
    snapshots: list[FinancialSnapshot],
    provenance_ids: tuple[str, ...],
) -> ResearchIntelligenceSection:
    observations: list[ResearchObservation] = []
    positive: list[ResearchEvidence] = []
    negative: list[ResearchEvidence] = []

    valid_features = [
        feature for feature in features
        if feature.status == FeatureStatus.VALID
        and feature.value is not None
        and feature.observation_at <= as_of
        and feature.calculated_at <= as_of
    ]
    for feature in valid_features:
        observations.append(_observation(
            observation_id=f"OBS_FEATURE_{feature.feature_id}",
            claim=f"{feature.feature_id} is available",
            explanation=(
                f"Validated {feature.feature_id} observation is available "
                "at this point in time."
            ),
            observed_at=feature.observation_at,
            confidence=_confidence_value(feature.confidence),
            source_ids=feature.source_ids,
            provenance_ids=feature.provenance_ids,
        ))

    for summary in trends:
        if summary.observations <= 0:
            continue
        observed_at = as_of
        evidence = _evidence(
            evidence_id=f"TREND_{summary.metric.upper()}",
            title=f"{summary.metric.replace('_', ' ').title()} trend",
            explanation=summary.explanation,
            symbol=symbol,
            observed_at=observed_at,
            confidence=_confidence_value(summary.consistency),
            provenance_ids=provenance_ids,
        )
        polarity = _trend_direction(summary.metric, summary.direction)
        (positive if polarity == "positive" else negative).append(evidence)
        observations.append(_observation(
            observation_id=f"OBS_TREND_{summary.metric.upper()}",
            claim=evidence.title,
            explanation=summary.explanation,
            observed_at=observed_at,
            confidence=_confidence_value(summary.consistency),
            provenance_ids=provenance_ids,
        ))

    ordered = sorted(
        (
            item for item in snapshots
            if item.period_end <= as_of.date()
        ),
        key=lambda item: item.period_end,
    )
    if ordered:
        current = ordered[-1]
        current_at = _at_date(current.period_end)
        values = current.model_dump(exclude={"symbol", "period_end"})
        for metric, value in values.items():
            if value is None:
                continue
            observations.append(_observation(
                observation_id=f"OBS_FINANCIAL_{metric.upper()}_{current.period_end.isoformat()}",
                claim=f"{metric.replace('_', ' ').title()} is reported",
                explanation=f"{metric.replace('_', ' ').title()} is available for the {current.period_end.isoformat()} reporting period.",
                observed_at=current_at,
                confidence=Decimal("0.9"),
                provenance_ids=provenance_ids,
            ))
        ratio_values = {
            "Net profit margin": net_profit_margin(current),
            "Operating cash-flow margin": operating_cash_flow_margin(current),
            "Free cash-flow margin": free_cash_flow_margin(current),
            "Cash conversion": cash_conversion_ratio(current),
        }
        for label, value in ratio_values.items():
            if value is not None:
                observations.append(_observation(
                    observation_id=f"OBS_RATIO_{label.upper().replace(' ', '_').replace('-', '')}",
                    claim=f"{label} is measurable",
                    explanation=f"{label} is {value:.2f}% for the latest available reporting period.",
                    observed_at=current_at,
                    confidence=Decimal("0.9"),
                    provenance_ids=provenance_ids,
                ))

    for previous, current in zip(ordered, ordered[1:]):
        for anomaly in analyze_financial_change(previous, current):
            negative.append(_evidence(
                evidence_id=f"ANOMALY_{anomaly.metric.upper()}_{current.period_end.isoformat()}",
                title=f"{anomaly.metric.replace('_', ' ').title()} growth divergence",
                explanation=anomaly.explanation,
                symbol=symbol,
                observed_at=_at_date(current.period_end),
                confidence=Decimal("0.8"),
                provenance_ids=provenance_ids,
            ))

        if current.profit_cash_flow_divergence:
            negative.append(_evidence(
                evidence_id=f"ANOMALY_PROFIT_CASH_{current.period_end.isoformat()}",
                title="Profit and cash-flow divergence",
                explanation="Reported net profit is positive while operating cash flow is negative.",
                symbol=symbol,
                observed_at=_at_date(current.period_end),
                confidence=Decimal("0.95"),
                provenance_ids=provenance_ids,
            ))

    unknown = []
    if not snapshots:
        unknown.append("Financial statements are not available from the current provider response.")
    if not trends:
        unknown.append("Multi-period financial trend summaries are not available.")
    return _section(
        as_of=as_of,
        observations=observations,
        positive=positive,
        negative=negative,
        unknown=unknown,
        provenance_ids=provenance_ids,
    )


def _snapshot_section(
    *,
    symbol: str,
    as_of: datetime,
    snapshot: CompanyResearchSnapshot | None,
    area: str,
    unknown_message: str,
) -> ResearchIntelligenceSection:
    observations: list[ResearchObservation] = []
    positive: list[ResearchEvidence] = []
    negative: list[ResearchEvidence] = []
    if snapshot is None:
        return _section(as_of=as_of, unknown=[unknown_message])
    observed_at = _at_date(snapshot.as_of_date)
    texts = getattr(snapshot, area, [])
    for index, text in enumerate(texts):
        observations.append(_observation(
            observation_id=f"OBS_{area.upper()}_{index}",
            claim=text,
            explanation=text,
            observed_at=observed_at,
            confidence=Decimal("0.7"),
        ))
    for signal in snapshot.signals:
        if area == "management_observations" and "MANAGEMENT" not in signal.code.upper():
            continue
        if area == "event_observations" and "EVENT" not in signal.code.upper():
            continue
        if area == "risk_observations" and signal.direction != IntelligenceDirection.NEGATIVE:
            continue
        evidence = _evidence(
            evidence_id=f"INTELLIGENCE_{signal.code}",
            title=signal.title,
            explanation=signal.description,
            symbol=symbol,
            observed_at=observed_at,
            confidence=signal.confidence,
            source_ids=[reference.reference for reference in signal.evidence if reference.reference],
        )
        if signal.direction == IntelligenceDirection.POSITIVE:
            positive.append(evidence)
        elif signal.direction == IntelligenceDirection.NEGATIVE:
            negative.append(evidence)
    return _section(
        as_of=as_of,
        observations=observations,
        positive=positive,
        negative=negative,
        unknown=[] if texts or positive or negative else [unknown_message],
    )


def _technology_section(
    *,
    symbol: str,
    as_of: datetime,
    snapshot: CompanyResearchSnapshot | None,
) -> ResearchIntelligenceSection:
    profile = snapshot.future_technology_profile if snapshot else None
    if profile is None or not profile.signals:
        return _section(as_of=as_of, unknown=["Insufficient evidence to assess future technology exposure."])
    observed_at = _at_date(snapshot.as_of_date)
    positive: list[ResearchEvidence] = []
    negative: list[ResearchEvidence] = []
    observations: list[ResearchObservation] = []
    for signal in profile.signals:
        evidence = _evidence(
            evidence_id=f"TECH_{signal.code}",
            title=signal.title,
            explanation=f"{signal.description} Evidence strength: {signal.evidence_strength.value}.",
            symbol=symbol,
            observed_at=observed_at,
            confidence=signal.confidence,
            source_ids=signal.evidence_codes,
        )
        if signal.direction.value == "POSITIVE":
            positive.append(evidence)
        elif signal.direction.value == "NEGATIVE":
            negative.append(evidence)
        observations.append(_observation(
            observation_id=f"OBS_TECH_{signal.code}",
            claim=f"{signal.technology_area.value} exposure is evidenced",
            explanation=signal.description,
            observed_at=observed_at,
            confidence=signal.confidence,
            source_ids=signal.evidence_codes,
        ))
    return _section(as_of=as_of, observations=observations, positive=positive, negative=negative)


def _market_section(
    *,
    as_of: datetime,
    market: MarketFeatureSnapshot | None,
    provenance_ids: tuple[str, ...],
) -> ResearchIntelligenceSection:
    if market is None:
        return _section(as_of=as_of, unknown=["Market intelligence is not available."])
    observed_at = _at_date(market.trading_date)
    technical = market.technical
    observations: list[ResearchObservation] = []
    positive: list[ResearchEvidence] = []
    negative: list[ResearchEvidence] = []
    if technical.volume_ratio is not None:
        volume_ratio = technical.volume_ratio
        title = "Volume anomaly" if volume_ratio >= Decimal("2") else "Volume context"
        explanation = f"Observed volume was {volume_ratio:.2f}× the prior 20-session average."
        evidence = _evidence(
            evidence_id="MARKET_VOLUME_RATIO",
            title=title,
            explanation=explanation,
            symbol=market.symbol,
            observed_at=observed_at,
            confidence=Decimal("0.9"),
            provenance_ids=provenance_ids,
        )
        (negative if volume_ratio >= Decimal("2") else positive).append(evidence)
        observations.append(_observation(
            observation_id="OBS_MARKET_VOLUME_RATIO",
            claim=title,
            explanation=explanation,
            observed_at=observed_at,
            confidence=Decimal("0.9"),
            provenance_ids=provenance_ids,
        ))
    if technical.volatility_20d is not None:
        observations.append(_observation(
            observation_id="OBS_MARKET_VOLATILITY_20D",
            claim="20-session volatility is measurable",
            explanation=f"20-session volatility was {technical.volatility_20d:.2f}.",
            observed_at=observed_at,
            confidence=Decimal("0.9"),
            provenance_ids=provenance_ids,
        ))
    return _section(as_of=as_of, observations=observations, positive=positive, negative=negative, unknown=[] if observations else ["Market features are not available."], provenance_ids=provenance_ids)


def build_research_intelligence(
    *,
    symbol: str,
    as_of: datetime,
    features: list[FeatureValue] | None = None,
    trend_summaries: list[FinancialTrendSummary] | None = None,
    company_snapshot: CompanyResearchSnapshot | None = None,
    financial_snapshots: list[FinancialSnapshot] | None = None,
    market_snapshot: MarketFeatureSnapshot | None = None,
    provenance_ids: tuple[str, ...] = (),
) -> ResearchIntelligence:
    """Build deterministic intelligence sections without filling gaps."""
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValueError("symbol cannot be empty")
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    snapshot = (
        company_snapshot
        if company_snapshot is not None
        and company_snapshot.as_of_date <= as_of.date()
        else None
    )
    market_snapshot = (
        market_snapshot
        if market_snapshot is not None
        and market_snapshot.trading_date <= as_of.date()
        else None
    )
    financial = _financial_section(
        symbol=symbol,
        as_of=as_of,
        features=features or [],
        trends=trend_summaries or [],
        snapshots=financial_snapshots or [],
        provenance_ids=provenance_ids,
    )
    business = _snapshot_section(
        symbol=symbol, as_of=as_of, snapshot=snapshot,
        area="financial_observations",
        unknown_message="Business quality evidence is not available from the current dataset.",
    )
    transformation = _snapshot_section(
        symbol=symbol, as_of=as_of, snapshot=snapshot,
        area="event_observations",
        unknown_message="Insufficient evidence to assess business transformation.",
    )
    management = _snapshot_section(
        symbol=symbol, as_of=as_of, snapshot=snapshot,
        area="management_observations",
        unknown_message="Management and strategic intelligence is not available from the current dataset.",
    )
    risks = _snapshot_section(
        symbol=symbol, as_of=as_of, snapshot=snapshot,
        area="risk_observations",
        unknown_message="No validated risk observations are available.",
    )
    ownership = _snapshot_section(
        symbol=symbol, as_of=as_of, snapshot=snapshot,
        area="ownership_observations",
        unknown_message="Capital allocation and ownership evidence is not available.",
    )
    related = _snapshot_section(
        symbol=symbol, as_of=as_of, snapshot=snapshot,
        area="related_party_observations",
        unknown_message="Competitive position evidence is not available from the current dataset.",
    )
    market = _market_section(as_of=as_of, market=market_snapshot, provenance_ids=provenance_ids)
    technology = _technology_section(symbol=symbol, as_of=as_of, snapshot=snapshot)
    customer = _section(as_of=as_of, unknown=["Customer concentration intelligence is not available from the current dataset."])
    innovation = technology
    unknown_missing = tuple(
        sorted({message for section in (
            transformation, technology, customer, management, related,
        ) for message in section.unknown})
    )
    return ResearchIntelligence(
        business_quality=business,
        financial_quality=financial,
        transformation=transformation,
        capital_allocation=ownership,
        competitive_position=related,
        innovation=innovation,
        future_technology=technology,
        customer_intelligence=customer,
        management_intelligence=management,
        market_intelligence=market,
        risks_anomalies=risks,
        unknown_missing=unknown_missing,
    )


__all__ = ["build_research_intelligence"]
