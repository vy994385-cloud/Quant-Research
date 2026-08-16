"""
Serializers from the recorded research result to the L3 API contract.

These functions only project already-produced research evidence into
the response contract. They never invent scores, evidence, or timing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from src.research.synthesis.models import EvidenceDirection

_HORIZONS = (
    "INTRADAY",
    "SWING",
    "LONG_TERM",
)


def _utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None

    return value.astimezone(timezone.utc).isoformat()


def _str(value) -> str:
    if isinstance(value, Decimal):
        return str(value)

    return str(value)


def _evidence_item(item) -> dict:
    return {
        "evidence_id": item.evidence_id,
        "title": item.title,
        "explanation": item.explanation,
        "symbol": item.symbol,
        "evidence_type": item.evidence_type.value,
        "direction": item.direction.value,
        "confidence": _str(item.confidence),
        "reliability": item.reliability.value,
        "observation_at": _utc_iso(item.observation_at),
        "source_ids": list(item.source_ids),
        "provenance_ids": list(item.provenance_ids),
    }


def _section(section) -> dict | None:
    if section is None:
        return None

    return {
        "status": section.status.value,
        "confidence": section.confidence.value,
        "observations": [
            observation.claim
            for observation in section.observations
        ],
        "unknown": list(section.unknown),
        "positive_count": len(section.positive_evidence),
        "negative_count": len(section.negative_evidence),
        "source_ids": list(section.source_ids),
        "provenance_ids": list(section.provenance_ids),
    }


def _intelligence(result) -> dict:
    intelligence = result.report.research_intelligence

    if intelligence is None:
        return {"unknown_missing": []}

    return {
        "business_quality": _section(
            intelligence.business_quality
        ),
        "financial_quality": _section(
            intelligence.financial_quality
        ),
        "transformation": _section(
            intelligence.transformation
        ),
        "capital_allocation": _section(
            intelligence.capital_allocation
        ),
        "competitive_position": _section(
            intelligence.competitive_position
        ),
        "innovation": _section(intelligence.innovation),
        "future_technology": _section(
            intelligence.future_technology
        ),
        "customer_intelligence": _section(
            intelligence.customer_intelligence
        ),
        "management_intelligence": _section(
            intelligence.management_intelligence
        ),
        "market_intelligence": _section(
            intelligence.market_intelligence
        ),
        "risks_anomalies": _section(
            intelligence.risks_anomalies
        ),
        "unknown_missing": list(
            intelligence.unknown_missing
        ),
    }


def _evidence_summary(result) -> dict:
    synthesis = result.report.evidence_synthesis

    if synthesis is None:
        return {
            "positive": [],
            "negative": [],
            "neutral": [],
            "conflict_detected": False,
            "direction": EvidenceDirection.NEUTRAL.value,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
            "positive_weight": "0",
            "negative_weight": "0",
            "average_confidence": "0",
            "weighted_confidence": "0",
        }

    return {
        "positive": [
            _evidence_item(item)
            for item in synthesis.evidence
            if item.direction == EvidenceDirection.POSITIVE
        ],
        "negative": [
            _evidence_item(item)
            for item in synthesis.evidence
            if item.direction == EvidenceDirection.NEGATIVE
        ],
        "neutral": [
            _evidence_item(item)
            for item in synthesis.evidence
            if item.direction == EvidenceDirection.NEUTRAL
        ],
        "conflict_detected": synthesis.conflict_detected,
        "direction": synthesis.direction.value,
        "positive_count": synthesis.positive_count,
        "negative_count": synthesis.negative_count,
        "neutral_count": synthesis.neutral_count,
        "positive_weight": _str(synthesis.positive_weight),
        "negative_weight": _str(synthesis.negative_weight),
        "average_confidence": _str(
            synthesis.average_confidence
        ),
        "weighted_confidence": _str(
            synthesis.weighted_confidence
        ),
    }


def _narrative(result) -> dict | None:
    narrative = result.report.evidence_narrative

    if narrative is None:
        return None

    return {
        "thesis": narrative.thesis,
        "supporting_evidence": list(
            narrative.supporting_evidence
        ),
        "contradicting_evidence": list(
            narrative.contradicting_evidence
        ),
        "strongest_evidence": list(
            narrative.strongest_evidence
        ),
        "uncertainty": list(narrative.uncertainty),
        "key_risks": list(narrative.key_risks),
        "evidence_gaps": list(narrative.evidence_gaps),
        "what_could_change_thesis": list(
            narrative.what_could_change_thesis
        ),
        "has_conflict": narrative.has_conflict,
    }


def _signals(result) -> list[dict]:
    return [
        {
            "signal_id": signal.signal_id,
            "category": signal.category,
            "direction": signal.direction.value,
            "severity": signal.severity.value,
            "confidence": _str(signal.confidence),
            "title": signal.title,
            "explanation": signal.explanation,
            "symbol": signal.symbol,
            "observation_at": _utc_iso(signal.observation_at),
            "supporting_features": list(
                signal.supporting_features
            ),
            "supporting_metrics": list(
                signal.supporting_metrics
            ),
        }
        for signal in result.report.signals
    ]


def _future_evidence_excluded(result) -> int:
    as_of = result.as_of

    return sum(
        1
        for observation in result.acquisition.observations
        if (
            observation.available_at is None
            or observation.available_at.tzinfo is None
            or observation.available_at > as_of
        )
    )


def _point_in_time(result) -> dict:
    synthesis = result.report.evidence_synthesis
    analysis = result.analysis

    pit_checks_passed = all(
        value is True
        for value in result.pit_checks.values()
    )

    notes = [
        (
            "No evidence in this response has an observation "
            "timestamp after the effective as_of."
        ),
        (
            "Acquired evidence is included only when its "
            "availability timestamp is known, timezone-aware, "
            "and on or before the effective as_of."
        ),
    ]

    for name, passed in sorted(result.pit_checks.items()):
        if passed is not True:
            notes.append(f"pit check failed: {name}")

    return {
        "as_of": _utc_iso(result.as_of),
        "effective_as_of": _utc_iso(result.as_of),
        "market_as_of": (
            analysis.as_of_date.isoformat()
            if analysis is not None
            else None
        ),
        "evidence_included": (
            len(synthesis.evidence)
            if synthesis is not None
            else 0
        ),
        "acquired_evidence_included": len(
            result.evidence_items
        ),
        "future_evidence_excluded": _future_evidence_excluded(
            result
        ),
        "sources_discovered": (
            result.acquisition.sources_discovered
        ),
        "sources_accepted": result.acquisition.sources_accepted,
        "sources_rejected": (
            result.acquisition.sources_discovered
            - result.acquisition.sources_accepted
        ),
        "pit_checks_passed": pit_checks_passed,
        "notes": notes,
    }


def _data_quality(result) -> dict:
    ingestion = result.market_ingestion
    feature_snapshot = result.feature_snapshot
    context = result.context_result

    warnings = list(result.report.data_quality_notes)

    if result.financial_record_count == 0:
        warnings.append(
            "financial records are not available"
        )

    if (
        ingestion.rejected
        or ingestion.issues
    ):
        warnings.append(
            "some market records were rejected during ingestion"
        )

    if result.acquisition.provider_failures:
        warnings.append(
            "one or more research source providers failed"
        )

    return {
        "market_validation_status": (
            ingestion.status.value
        ),
        "market_accepted_records": len(
            ingestion.accepted
        ),
        "market_rejected_records": len(
            ingestion.rejected
        ),
        "financial_record_count": result.financial_record_count,
        "financial_data_missing": (
            result.financial_record_count == 0
        ),
        "feature_statuses": {
            feature.feature_id: feature.status.value
            for feature in feature_snapshot.features
        },
        "context": {
            "accepted_observations": context.accepted_count,
            "rejected_observations": context.rejected_count,
            "rejected_missing_availability": (
                context.rejected_missing_availability
            ),
            "rejected_not_known_at": (
                context.rejected_not_known_at
            ),
        },
        "provenance_completeness": {
            "financial_records": bool(
                result.financial_record_count
            ),
            "market_source": bool(
                result.market_provenance.source
            ),
            "financial_source": bool(
                result.financial_provenance.source
            ),
            "evidence_with_provenance": sum(
                bool(item.provenance_ids)
                for item in result.evidence_items
            ),
        },
        "warnings": warnings,
        "provider_failures": list(
            result.acquisition.provider_failures
        ),
    }


def _provenance(result) -> dict:
    market = result.market_provenance
    financials = result.financial_provenance

    return {
        "market": {
            "source": market.source,
            "dataset_id": market.dataset_id,
            "record_id": market.record_id,
            "retrieved_at": _utc_iso(market.retrieved_at),
            "available_at": _utc_iso(market.available_at),
        },
        "financials": {
            "source": financials.source,
            "dataset_id": financials.dataset_id,
            "record_id": financials.record_id,
            "retrieved_at": _utc_iso(
                financials.retrieved_at
            ),
            "available_at": _utc_iso(
                financials.available_at
            ),
        },
        "archived_sources": list(
            result.archived_source_ids
        ),
    }


def _ranking_payload(ranking, *, company_name: str | None) -> dict:
    return {
        "symbol": ranking.symbol,
        "company_name": company_name,
        "horizon": ranking.horizon,
        "score": _str(ranking.score),
        "signal": ranking.rank_signal,
        "confidence": _str(ranking.confidence),
        "coverage": _str(ranking.coverage),
        "missing_components": list(
            ranking.missing_components
        ),
        "components": {
            name: _str(value)
            for name, value in ranking.components.items()
        },
    }


def research_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize a full recorded company research result."""

    report = result.report
    synthesis = report.evidence_synthesis
    analysis = result.analysis

    assessment = {
        "conclusion": report.conclusion.value,
        "confidence": _str(report.confidence),
        "thesis": report.thesis,
        "conflict_detected": bool(
            synthesis is not None
            and synthesis.conflict_detected
        ),
        "direction": (
            synthesis.direction.value
            if synthesis is not None
            else EvidenceDirection.NEUTRAL.value
        ),
        "research_ready": bool(
            analysis is not None
            and analysis.is_research_ready
        ),
    }

    research_score = {}
    rankings = {}

    if analysis is not None:
        score = analysis.research_score

        research_score = {
            "total": _str(score.total),
            "signal": score.signal,
            "confidence": _str(score.confidence),
            "components": {
                "fundamentals": _str(score.fundamentals),
                "financial_trends": _str(
                    score.financial_trends
                ),
                "cash_flow": _str(score.cash_flow),
                "balance_sheet": _str(score.balance_sheet),
                "risk": _str(score.risk),
                "management": _str(score.management),
                "market_behavior": _str(
                    score.market_behavior
                ),
                "evidence_quality": _str(
                    score.evidence_quality
                ),
            },
        }

        rankings = {
            horizon.lower(): _ranking_payload(
                getattr(analysis, horizon.lower()),
                company_name=company_name,
            )
            for horizon in _HORIZONS
        }

    return {
        "company": {
            "symbol": result.company,
            "company_name": company_name,
            "sector": result.sector,
            "as_of": _utc_iso(result.as_of),
        },
        "assessment": assessment,
        "point_in_time": _point_in_time(result),
        "intelligence": _intelligence(result),
        "evidence": _evidence_summary(result),
        "narrative": _narrative(result),
        "signals": _signals(result),
        "data_quality": _data_quality(result),
        "provenance": _provenance(result),
        "rankings": rankings,
        "research_score": research_score,
    }


def company_rankings_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize all-horizon rankings for one company."""

    analysis = result.analysis

    rankings = {}

    if analysis is not None:
        for horizon in _HORIZONS:
            rankings[horizon.lower()] = _ranking_payload(
                getattr(analysis, horizon.lower()),
                company_name=company_name,
            )

    return {
        "symbol": result.company,
        "company_name": company_name,
        "as_of": _utc_iso(result.as_of),
        "point_in_time": _point_in_time(result),
        "rankings": rankings,
    }


def universe_rankings_contract(
    results,
    *,
    horizon: str,
    company_names: dict[str, str],
) -> dict:
    """Serialize horizon rankings across a set of companies."""

    payloads: list[dict] = []

    for result in results:
        analysis = result.analysis

        if analysis is None:
            continue

        ranking = getattr(
            analysis,
            horizon.lower(),
        )

        payloads.append(
            _ranking_payload(
                ranking,
                company_name=company_names.get(
                    result.company
                ),
            )
        )

    payloads.sort(
        key=lambda item: (
            -Decimal(item["score"]),
            item["symbol"],
        )
    )

    return {
        "as_of": _utc_iso(results[0].as_of),
        "horizon": horizon,
        "count": len(payloads),
        "point_in_time": _point_in_time(results[0]),
        "results": payloads,
    }


def discovery_item(
    symbol: str,
    *,
    sector: str,
    company_name: str | None,
    research_available: bool,
) -> dict:
    return {
        "symbol": symbol,
        "company_name": company_name,
        "sector": sector,
        "research_available": research_available,
    }


def _intel_item(item) -> dict:
    source = item.source

    return {
        "item_id": item.item_id,
        "symbol": item.symbol,
        "kind": item.kind.value,
        "semantic_category": item.semantic_category.value,
        "verification_status": item.verification_status.value,
        "event_type": (
            item.event_type.value
            if item.event_type is not None
            else None
        ),
        "topic": item.topic,
        "title": item.title,
        "description": item.description,
        "stance": item.stance.value,
        "direction": item.direction.value,
        "published_at": _utc_iso(item.published_at),
        "available_at": _utc_iso(item.available_at),
        "effective_at": _utc_iso(item.effective_at),
        "source": {
            "source_name": source.source_name,
            "source_type": source.source_type,
            "source_url": source.source_url,
            "reliability_tier": source.reliability_tier,
            "provenance_id": source.provenance_id,
        },
        "related_entities": list(item.related_entities),
        "relevance": item.relevance,
        "confidence": (
            _str(item.confidence)
            if item.confidence is not None
            else None
        ),
        "provenance_id": item.provenance_id,
        "checksum": item.checksum,
    }


def _intel_segment(segment) -> dict:
    return {
        "segment_name": segment.segment_name,
        "revenue": (
            _str(segment.revenue)
            if segment.revenue is not None
            else None
        ),
        "profit": (
            _str(segment.profit)
            if segment.profit is not None
            else None
        ),
        "note": segment.note,
    }


def _intel_statement(statement) -> dict:
    return {
        "statement_id": statement.statement_id,
        "symbol": statement.symbol,
        "statement_type": statement.statement_type.value,
        "period_type": statement.period_type.value,
        "consolidation": statement.consolidation.value,
        "period_start": (
            statement.period_start.isoformat()
            if statement.period_start is not None
            else None
        ),
        "period_end": statement.period_end.isoformat(),
        "published_at": _utc_iso(statement.published_at),
        "available_at": _utc_iso(statement.available_at),
        "source_name": statement.source_name,
        "source_type": statement.source_type,
        "source_url": statement.source_url,
        "provenance_id": statement.provenance_id,
        "currency": statement.currency,
        "items": {
            name: _str(value)
            for name, value in statement.items.items()
        },
        "segments": [
            _intel_segment(segment)
            for segment in statement.segments
        ],
        "notes": list(statement.notes),
    }


def _intel_period(period) -> dict:
    return {
        "period_id": period.period_id,
        "symbol": period.symbol,
        "period_start": (
            period.period_start.isoformat()
            if period.period_start is not None
            else None
        ),
        "period_end": period.period_end.isoformat(),
        "period_type": period.period_type.value,
        "consolidation": period.consolidation.value,
        "published_at": _utc_iso(period.published_at),
        "available_at": _utc_iso(period.available_at),
        "source_name": period.source_name,
        "source_type": period.source_type,
        "source_url": period.source_url,
        "provenance_id": period.provenance_id,
        "currency": period.currency,
        "metrics": {
            name: _str(value)
            for name, value in period.metrics.items()
        },
        "segments": [
            _intel_segment(segment)
            for segment in period.segments
        ],
        "statements": [
            _intel_statement(statement)
            for statement in period.statements
        ],
    }


def _intel_financial(financial) -> dict | None:
    if financial is None:
        return None

    return {
        "symbol": financial.symbol,
        "as_of": _utc_iso(financial.as_of),
        "period_count": financial.period_count,
        "quarterly_count": financial.quarterly_count,
        "semiannual_count": financial.semiannual_count,
        "annual_count": financial.annual_count,
        "unknown_period_count": financial.unknown_period_count,
        "consolidated_count": financial.consolidated_count,
        "standalone_count": financial.standalone_count,
        "unknown_consolidation_count": (
            financial.unknown_consolidation_count
        ),
        "latest_period_end": (
            financial.latest_period_end.isoformat()
            if financial.latest_period_end is not None
            else None
        ),
        "earliest_period_end": (
            financial.earliest_period_end.isoformat()
            if financial.earliest_period_end is not None
            else None
        ),
        "coverage": dict(financial.coverage),
        "periods": [
            _intel_period(period)
            for period in financial.periods
        ],
        "notes": list(financial.notes),
    }


def _intel_conflict_side(side) -> dict:
    return {
        "item_id": side.item_id,
        "title": side.title,
        "semantic_category": side.semantic_category.value,
        "verification_status": side.verification_status.value,
        "stance": side.stance.value,
        "direction": side.direction.value,
        "source_name": side.source_name,
        "excerpt": side.excerpt,
    }


def _intel_conflict(conflict) -> dict:
    return {
        "conflict_id": conflict.conflict_id,
        "symbol": conflict.symbol,
        "topic": conflict.topic,
        "description": conflict.description,
        "management_involved": conflict.management_involved,
        "first": _intel_conflict_side(conflict.first),
        "second": _intel_conflict_side(conflict.second),
        "as_of": _utc_iso(conflict.as_of),
    }


def _intel_change(change) -> dict:
    return {
        "change_type": change.change_type.value,
        "item_id": change.item_id,
        "kind": change.kind.value,
        "title": change.title,
        "description": change.description,
        "previous_checksum": change.previous_checksum,
        "current_checksum": change.current_checksum,
        "as_of": _utc_iso(change.as_of),
    }


def intelligence_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize the deep company intelligence snapshot."""
    intelligence = result.intelligence

    if intelligence is None:
        raise ValueError(
            "result does not contain a company intelligence snapshot"
        )

    financial = intelligence.financial_intelligence

    return {
        "company": {
            "symbol": result.company,
            "company_name": company_name,
            "sector": result.sector,
            "as_of": _utc_iso(result.as_of),
        },
        "as_of": _utc_iso(intelligence.as_of),
        "financial_intelligence": _intel_financial(financial),
        "business_events": [
            _intel_item(item)
            for item in intelligence.business_events
        ],
        "management_commentary": [
            _intel_item(item)
            for item in intelligence.management_commentary
        ],
        "risk_intelligence": [
            _intel_item(item)
            for item in intelligence.risk_intelligence
        ],
        "indirect_intelligence": [
            _intel_item(item)
            for item in intelligence.indirect_intelligence
        ],
        "financial_intelligence_items": [
            _intel_item(item)
            for item in intelligence.financial_intelligence_items
        ],
        "other_intelligence": [
            _intel_item(item)
            for item in intelligence.other_intelligence
        ],
        "conflicts": [
            _intel_conflict(conflict)
            for conflict in intelligence.conflicts
        ],
        "changes": [
            _intel_change(change)
            for change in intelligence.changes
        ],
        "item_count": intelligence.item_count,
        "source_ids": list(intelligence.source_ids),
        "provenance_ids": list(intelligence.provenance_ids),
        "coverage": dict(intelligence.coverage),
        "semantic_summary": dict(
            intelligence.semantic_summary
        ),
        "status_summary": dict(intelligence.status_summary),
        "insufficient_evidence_notes": list(
            intelligence.insufficient_evidence_notes
        ),
        "notes": list(intelligence.notes),
    }


__all__ = [
    "company_rankings_contract",
    "discovery_item",
    "intelligence_contract",
    "research_contract",
    "universe_rankings_contract",
]
