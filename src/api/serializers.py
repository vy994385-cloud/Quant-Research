"""
Serializers from the recorded research result to the L3 API contract.

These functions only project already-produced research evidence into
the response contract. They never invent scores, evidence, or timing.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from src.api.query_utils import utc_iso
from src.research.synthesis.models import EvidenceDirection

_HORIZONS = (
    "INTRADAY",
    "SWING",
    "LONG_TERM",
)


def _utc_iso(value: datetime | date | str | None) -> str | None:
    return utc_iso(value)


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
        "timeline": _intel_timeline(
            result.intelligence.timeline
            if result.intelligence is not None
            else None
        ),
        "research_status": _intel_research_status(
            result.intelligence.status
            if result.intelligence is not None
            else None
        ),
        "deep_financial_insights": _deep_financial_insights(
            result.intelligence.deep_financial_insights
            if result.intelligence is not None
            else None
        ),
        "source_statuses": [
            _source_status(s)
            for s in (
                result.intelligence.source_statuses
                if result.intelligence is not None
                else ()
            )
        ],
        "hidden_information": _hidden_information(
            result.intelligence.hidden_information
            if result.intelligence is not None
            else None
        ),
        "cash_flow_quality": _cash_flow_quality(
            result.intelligence.cash_flow_quality
            if result.intelligence is not None
            else None
        ),
        "balance_sheet_deep": _balance_sheet_deep(
            result.intelligence.balance_sheet_deep
            if result.intelligence is not None
            else None
        ),
        "research_gaps": _research_gaps(
            result.intelligence.research_gaps
            if result.intelligence is not None
            else None
        ),
        "cross_domain": _cross_domain(
            result.intelligence.cross_domain
            if result.intelligence is not None
            else None
        ),
        "financial_anomalies": _financial_anomalies(
            result.intelligence.financial_anomalies
            if result.intelligence is not None
            else None
        ),
        "provider_failures": list(
            result.intelligence.provider_failures
            if result.intelligence is not None
            else ()
        ),
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
    sector: str | None,
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
        "intel_category": (
            item.intel_category.value
            if item.intel_category is not None
            else None
        ),
        "derivation": item.derivation,
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
        "effective_at": _utc_iso(statement.effective_at),
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
        "subsidiaries": list(statement.subsidiaries),
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
        "effective_at": _utc_iso(period.effective_at),
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
        "subsidiaries": list(period.subsidiaries),
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
        "statement_count": financial.statement_count,
        "segment_count": financial.segment_count,
        "subsidiary_count": financial.subsidiary_count,
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
        "previous_title": change.previous_title,
        "semantic_category": (
            change.semantic_category.value
            if change.semantic_category is not None
            else None
        ),
        "intel_category": (
            change.intel_category.value
            if change.intel_category is not None
            else None
        ),
        "event_type": (
            change.event_type.value
            if change.event_type is not None
            else None
        ),
        "published_at": _utc_iso(change.published_at),
        "available_at": _utc_iso(change.available_at),
        "as_of": _utc_iso(change.as_of),
    }


def _intel_timeline_entry(entry) -> dict:
    source = entry.source

    return {
        "entry_id": entry.entry_id,
        "symbol": entry.symbol,
        "kind": entry.kind.value,
        "intel_category": entry.intel_category.value,
        "semantic_category": entry.semantic_category.value,
        "verification_status": entry.verification_status.value,
        "event_type": (
            entry.event_type.value
            if entry.event_type is not None
            else None
        ),
        "topic": entry.topic,
        "title": entry.title,
        "description": entry.description,
        "stance": entry.stance.value,
        "direction": entry.direction.value,
        "published_at": _utc_iso(entry.published_at),
        "available_at": _utc_iso(entry.available_at),
        "effective_at": _utc_iso(entry.effective_at),
        "timeline_at": _utc_iso(entry.timeline_at),
        "source": {
            "source_name": source.source_name,
            "source_type": source.source_type,
            "source_url": source.source_url,
            "reliability_tier": source.reliability_tier,
            "provenance_id": source.provenance_id,
        },
        "provenance_id": entry.provenance_id,
        "checksum": entry.checksum,
    }


def _intel_timeline(timeline) -> dict | None:
    if timeline is None:
        return None

    return {
        "company": timeline.company,
        "as_of": _utc_iso(timeline.as_of),
        "entries": [
            _intel_timeline_entry(entry)
            for entry in timeline.entries
        ],
        "counts": dict(timeline.counts),
        "latest_at": _utc_iso(timeline.latest_at),
        "earliest_at": _utc_iso(timeline.earliest_at),
        "notes": list(timeline.notes),
    }


def _intel_research_status(status) -> dict | None:
    if status is None:
        return None

    freshness = status.freshness
    coverage = status.coverage
    quality = status.quality

    return {
        "company": status.company,
        "as_of": _utc_iso(status.as_of),
        "freshness": {
            "latest_published_at": _utc_iso(
                freshness.latest_published_at
            ),
            "latest_available_at": _utc_iso(
                freshness.latest_available_at
            ),
            "latest_effective_at": _utc_iso(
                freshness.latest_effective_at
            ),
            "oldest_published_at": _utc_iso(
                freshness.oldest_published_at
            ),
            "oldest_available_at": _utc_iso(
                freshness.oldest_available_at
            ),
            "oldest_effective_at": _utc_iso(
                freshness.oldest_effective_at
            ),
            "days_since_latest_published": (
                freshness.days_since_latest_published
            ),
            "days_since_latest_available": (
                freshness.days_since_latest_available
            ),
            "stale": freshness.stale,
            "notes": list(freshness.notes),
        },
        "coverage": {
            "item_count": coverage.item_count,
            "by_kind": dict(coverage.by_kind),
            "by_category": dict(coverage.by_category),
            "by_semantic": dict(coverage.by_semantic),
            "by_status": dict(coverage.by_status),
            "missing_categories": list(
                coverage.missing_categories
            ),
            "notes": list(coverage.notes),
        },
        "quality": {
            "conflict_count": quality.conflict_count,
            "evidence_link_count": quality.evidence_link_count,
            "deduplicated_count": quality.deduplicated_count,
            "source_id_count": quality.source_id_count,
            "provenance_id_count": quality.provenance_id_count,
            "insufficient_evidence_notes": list(
                quality.insufficient_evidence_notes
            ),
            "notes": list(quality.notes),
        },
    }


def _deep_metric_observation(obs) -> dict:
    return {
        "observation_id": obs.observation_id,
        "symbol": obs.symbol,
        "metric": obs.metric,
        "period_id": obs.period_id,
        "period_end": _utc_iso(obs.period_end),
        "period_type": obs.period_type.value,
        "consolidation": obs.consolidation.value,
        "observation_type": obs.observation_type.value,
        "unit": obs.unit,
        "value": _str(obs.value) if obs.value is not None else None,
        "previous_value": (
            _str(obs.previous_value)
            if obs.previous_value is not None
            else None
        ),
        "delta": (
            _str(obs.delta) if obs.delta is not None else None
        ),
        "delta_pct": (
            _str(obs.delta_pct)
            if obs.delta_pct is not None
            else None
        ),
        "derivation": obs.derivation,
        "published_at": _utc_iso(obs.published_at),
        "available_at": _utc_iso(obs.available_at),
        "provenance_id": obs.provenance_id,
    }


def _deep_financial_series(series) -> dict:
    return {
        "series_id": series.series_id,
        "symbol": series.symbol,
        "period_type": series.period_type.value,
        "consolidation": series.consolidation.value,
        "period_count": series.period_count,
        "period_ends": [
            _utc_iso(p) for p in series.period_ends
        ],
        "metrics": list(series.metrics),
    }


def _deep_financial_insights(insights) -> dict | None:
    if insights is None:
        return None

    return {
        "symbol": insights.symbol,
        "as_of": _utc_iso(insights.as_of),
        "series": [
            _deep_financial_series(s) for s in insights.series
        ],
        "observations": [
            _deep_metric_observation(o)
            for o in insights.observations
        ],
        "comparability_notes": list(insights.comparability_notes),
        "financial_type_counts": dict(
            insights.financial_type_counts
        ),
    }


def _source_status(status) -> dict:
    return {
        "source_name": status.source_name,
        "source_type": status.source_type,
        "item_count": status.item_count,
        "categories": list(status.categories),
        "latest_published_at": _utc_iso(
            status.latest_published_at
        ),
        "latest_available_at": _utc_iso(
            status.latest_available_at
        ),
        "days_since_latest_published": (
            status.days_since_latest_published
        ),
        "stale": status.stale,
        "provenance_completeness": status.provenance_completeness,
        "notes": list(status.notes),
    }


def _derived_observation(obs) -> dict:
    return {
        "observation_id": obs.observation_id,
        "symbol": obs.symbol,
        "label": obs.label,
        "semantic_category": obs.semantic_category.value,
        "description": obs.description,
        "derivation": obs.derivation,
        "source_ids": list(obs.source_ids),
        "provenance_ids": list(obs.provenance_ids),
        "related_item_ids": list(obs.related_item_ids),
        "as_of": _utc_iso(obs.as_of),
        "severity": obs.severity,
    }


def _hidden_information(hidden) -> dict | None:
    if hidden is None:
        return None

    return {
        "symbol": hidden.symbol,
        "as_of": _utc_iso(hidden.as_of),
        "observations": [
            _derived_observation(o)
            for o in hidden.observations
        ],
        "notes": list(hidden.notes),
    }


def _quality_observation(obs) -> dict:
    """Shared shape for derived quality observations."""
    return {
        "observation_id": obs.observation_id,
        "symbol": obs.symbol,
        "label": obs.observation_type,
        "semantic_category": obs.category,
        "description": obs.explanation,
        "calculation_inputs": dict(obs.calculation_inputs) if obs.calculation_inputs else {},
        "methodology": getattr(obs, "calculation_method", "") or "",
        "confidence": getattr(obs, "confidence", None),
        "severity": obs.severity,
        "as_of": _utc_iso(obs.as_of),
    }


def _cash_flow_quality(cfq) -> dict | None:
    if cfq is None:
        return None

    return {
        "symbol": cfq.symbol,
        "as_of": _utc_iso(cfq.as_of),
        "direction": cfq.direction,
        "observation_count": cfq.observation_count,
        "observations": [
            _quality_observation(o)
            for o in cfq.observations
        ],
        "notes": list(cfq.notes),
    }


def _balance_sheet_deep(bsd) -> dict | None:
    if bsd is None:
        return None

    return {
        "symbol": bsd.symbol,
        "as_of": _utc_iso(bsd.as_of),
        "direction": bsd.direction,
        "observation_count": bsd.observation_count,
        "observations": [
            _quality_observation(o)
            for o in bsd.observations
        ],
        "notes": list(bsd.notes),
    }


def _research_gap(gap) -> dict:
    return {
        "gap_id": gap.gap_id,
        "symbol": gap.symbol,
        "category": gap.category,
        "description": gap.gap,
        "status": gap.status,
        "severity": gap.priority,
        "reason": getattr(gap, "reason", "") or "",
        "suggested_action": getattr(gap, "what_would_resolve", "") or "",
        "sources_checked": list(getattr(gap, "sources_checked", ())),
        "evidence_refs": list(getattr(gap, "evidence_refs", ())),
        "related_metrics": list(getattr(gap, "related_metrics", ())),
        "supporting_data": dict(getattr(gap, "supporting_data", {})),
        "as_of": _utc_iso(gap.as_of),
    }


def _research_gaps(rg) -> dict | None:
    if rg is None:
        return None

    return {
        "symbol": rg.symbol,
        "as_of": _utc_iso(rg.as_of),
        "gap_count": rg.gap_count,
        "gaps": [
            _research_gap(g)
            for g in rg.gaps
        ],
        "status_counts": dict(getattr(rg, "status_counts", {})),
        "category_counts": dict(getattr(rg, "category_counts", {})),
        "coverage_score": rg.coverage_score,
        "coverage_explanation": getattr(rg, "coverage_explanation", "") or "",
        "notes": list(rg.notes),
    }


def _cross_domain_observation(obs) -> dict:
    return {
        "observation_id": obs.observation_id,
        "symbol": obs.symbol,
        "label": obs.observation_type,
        "semantic_category": obs.category,
        "description": obs.explanation,
        "domain_1_name": getattr(obs, "domain_1_name", ""),
        "domain_1_metric": getattr(obs, "domain_1_metric", ""),
        "domain_1_value": getattr(obs, "domain_1_value", None),
        "domain_1_direction": getattr(obs, "domain_1_direction", "UNKNOWN"),
        "domain_2_name": getattr(obs, "domain_2_name", ""),
        "domain_2_metric": getattr(obs, "domain_2_metric", ""),
        "domain_2_value": getattr(obs, "domain_2_value", None),
        "domain_2_direction": getattr(obs, "domain_2_direction", "UNKNOWN"),
        "relationship": getattr(obs, "relationship", ""),
        "direction": getattr(obs, "direction", "NEUTRAL"),
        "limitations": list(getattr(obs, "limitations", ())),
        "calculation_inputs": dict(obs.calculation_inputs) if obs.calculation_inputs else {},
        "methodology": getattr(obs, "calculation_method", "") or "",
        "confidence": getattr(obs, "confidence", None),
        "severity": obs.severity,
        "as_of": _utc_iso(obs.as_of),
        "source_name": getattr(obs, "source_name", None),
        "related_metrics": list(getattr(obs, "related_metrics", ())),
        "supporting_data": dict(getattr(obs, "supporting_data", {})),
    }


def _cross_domain(cd) -> dict | None:
    if cd is None:
        return None

    return {
        "symbol": cd.symbol,
        "as_of": _utc_iso(cd.as_of),
        "observation_count": cd.observation_count,
        "observations": [
            _cross_domain_observation(o)
            for o in cd.observations
        ],
        "positive_count": cd.positive_count,
        "negative_count": cd.negative_count,
        "mixed_count": cd.mixed_count,
        "neutral_count": cd.neutral_count,
        "notes": list(cd.notes),
    }


def _financial_anomaly_item(item) -> dict:
    return {
        "metric": item.metric,
        "current_change": item.current_change,
        "comparison_change": item.comparison_change,
        "severity": item.severity,
        "explanation": item.explanation,
    }


def _financial_anomalies(fa) -> dict | None:
    if fa is None:
        return None

    return {
        "symbol": fa.symbol,
        "as_of": _utc_iso(fa.as_of),
        "anomaly_count": fa.anomaly_count,
        "anomalies": [
            _financial_anomaly_item(a)
            for a in fa.anomalies
        ],
        "notes": list(fa.notes),
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
        "deep_financial_insights": _deep_financial_insights(
            intelligence.deep_financial_insights
        ),
        "source_statuses": [
            _source_status(s)
            for s in intelligence.source_statuses
        ],
        "hidden_information": _hidden_information(
            intelligence.hidden_information
        ),
        "cash_flow_quality": _cash_flow_quality(
            intelligence.cash_flow_quality
        ),
        "balance_sheet_deep": _balance_sheet_deep(
            intelligence.balance_sheet_deep
        ),
        "research_gaps": _research_gaps(
            intelligence.research_gaps
        ),
        "cross_domain": _cross_domain(
            intelligence.cross_domain
        ),
        "financial_anomalies": _financial_anomalies(
            intelligence.financial_anomalies
        ),
        "provider_failures": list(
            intelligence.provider_failures
        ),
        "timeline": _intel_timeline(intelligence.timeline),
        "research_status": _intel_research_status(
            intelligence.status
        ),
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


def _company_envelope(result, *, company_name: str | None) -> dict:
    """Canonical company envelope shared by all L3 contract builders."""

    return {
        "symbol": result.company,
        "company_name": company_name,
        "sector": result.sector,
        "as_of": _utc_iso(result.as_of),
    }


def _require_intelligence(result):
    intelligence = getattr(result, "intelligence", None)
    if intelligence is None:
        raise ValueError(
            "result does not contain a company intelligence snapshot"
        )
    return intelligence


def timeline_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize timeline for a company."""

    intelligence = _require_intelligence(result)

    if intelligence.timeline is None:
        raise ValueError(
            "result does not contain a company timeline"
        )

    return {
        "company": _company_envelope(result, company_name=company_name),
        "timeline": _intel_timeline(intelligence.timeline),
    }


def deep_financial_insights_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize deep financial insights for a company."""

    intelligence = _require_intelligence(result)

    return {
        "company": _company_envelope(result, company_name=company_name),
        "deep_financial_insights": _deep_financial_insights(
            intelligence.deep_financial_insights
        ),
    }


def source_statuses_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize source statuses for a company."""

    intelligence = _require_intelligence(result)

    return {
        "company": _company_envelope(result, company_name=company_name),
        "source_statuses": [
            _source_status(s)
            for s in intelligence.source_statuses
        ],
    }


def hidden_information_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize hidden information for a company."""

    intelligence = _require_intelligence(result)

    return {
        "company": _company_envelope(result, company_name=company_name),
        "hidden_information": _hidden_information(
            intelligence.hidden_information
        ),
    }


def cash_flow_quality_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize cash flow quality for a company."""

    intelligence = _require_intelligence(result)

    return {
        "company": _company_envelope(result, company_name=company_name),
        "cash_flow_quality": _cash_flow_quality(
            intelligence.cash_flow_quality
        ),
    }


def balance_sheet_deep_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize balance sheet deep for a company."""

    intelligence = _require_intelligence(result)

    return {
        "company": _company_envelope(result, company_name=company_name),
        "balance_sheet_deep": _balance_sheet_deep(
            intelligence.balance_sheet_deep
        ),
    }


def research_gaps_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize research gaps for a company."""

    intelligence = _require_intelligence(result)

    return {
        "company": _company_envelope(result, company_name=company_name),
        "research_gaps": _research_gaps(
            intelligence.research_gaps
        ),
    }


def cross_domain_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize cross domain for a company."""

    intelligence = _require_intelligence(result)

    return {
        "company": _company_envelope(result, company_name=company_name),
        "cross_domain": _cross_domain(
            intelligence.cross_domain
        ),
    }


def financial_anomalies_contract(
    result,
    *,
    company_name: str | None,
) -> dict:
    """Serialize financial anomalies for a company."""

    intelligence = _require_intelligence(result)

    return {
        "company": _company_envelope(result, company_name=company_name),
        "financial_anomalies": _financial_anomalies(
            intelligence.financial_anomalies
        ),
    }


# ── F6 serializers (delegated to f6_serializers module) ──────────
from src.api.f6_serializers import (  # noqa: E402, F401
    chart_data_contract,
    corporate_actions_contract,
    industry_context_contract,
    news_contract,
    tracking_contract,
)


__all__ = [
    "balance_sheet_deep_contract",
    "cash_flow_quality_contract",
    "chart_data_contract",
    "company_rankings_contract",
    "corporate_actions_contract",
    "cross_domain_contract",
    "deep_financial_insights_contract",
    "discovery_item",
    "financial_anomalies_contract",
    "hidden_information_contract",
    "industry_context_contract",
    "intelligence_contract",
    "news_contract",
    "research_contract",
    "research_gaps_contract",
    "source_statuses_contract",
    "timeline_contract",
    "tracking_contract",
    "universe_rankings_contract",
]
