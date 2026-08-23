"""
F8 — Professional Research Report serializers.

Serialization functions that convert the internal professional report
models to the API contract dictionaries.
"""

from __future__ import annotations

from src.api.query_utils import utc_iso as _utc_iso


def _report_item(item) -> dict:
    return {
        "item_id": item.item_id,
        "text": item.text,
        "epistemic_type": item.epistemic_type,
        "evidence_ids": list(item.evidence_ids),
        "source_ids": list(item.source_ids),
        "confidence": item.confidence,
        "observation_at": _utc_iso(item.observation_at),
        "metadata": dict(item.metadata),
    }


def _report_section(section) -> dict | None:
    if section is None:
        return None
    return {
        "section_id": section.section_id,
        "title": section.title,
        "status": section.status,
        "epistemic_type": section.epistemic_type,
        "items": [_report_item(i) for i in section.items],
        "evidence_ids": list(section.evidence_ids),
        "source_ids": list(section.source_ids),
        "total_items": section.total_items,
        "notes": list(section.notes),
        "metadata": dict(section.metadata),
    }


def _evidence_item_simple(item) -> dict:
    return {
        "evidence_id": item.evidence_id,
        "symbol": item.symbol,
        "title": item.title,
        "explanation": item.explanation,
        "evidence_type": item.evidence_type,
        "direction": item.direction,
        "confidence": item.confidence,
        "reliability": item.reliability,
        "epistemic_type": (
            item.epistemic_type.value
            if hasattr(item.epistemic_type, "value")
            else str(item.epistemic_type)
        ),
        "verification_status": item.verification_status,
        "observation_at": _utc_iso(item.observation_at),
        "source_ids": list(item.source_ids),
    }


def _evidence_section(section) -> dict | None:
    if section is None:
        return None
    return {
        "section_id": section.section_id,
        "title": section.title,
        "items": [
            _evidence_item_simple(i) for i in section.items
        ],
        "total_items": section.total_items,
        "notes": list(section.notes),
    }


def _conflict_detail(detail) -> dict:
    return {
        "conflict_id": detail.conflict_id,
        "topic": detail.topic,
        "description": detail.description,
        "management_involved": detail.management_involved,
        "first_item_id": detail.first_item_id,
        "first_title": detail.first_title,
        "first_direction": detail.first_direction,
        "first_source": detail.first_source,
        "first_excerpt": detail.first_excerpt,
        "second_item_id": detail.second_item_id,
        "second_title": detail.second_title,
        "second_direction": detail.second_direction,
        "second_source": detail.second_source,
        "second_excerpt": detail.second_excerpt,
    }


def _executive_overview(overview) -> dict | None:
    if overview is None:
        return None
    return {
        "symbol": overview.symbol,
        "company_name": overview.company_name,
        "as_of": _utc_iso(overview.as_of),
        "evidence_direction": overview.evidence_direction,
        "evidence_direction_confidence": (
            overview.evidence_direction_confidence
        ),
        "total_evidence": overview.total_evidence,
        "positive_count": overview.positive_count,
        "negative_count": overview.negative_count,
        "conflicting_count": overview.conflicting_count,
        "key_findings": [
            _report_item(i) for i in overview.key_findings
        ],
        "key_risks": [
            _report_item(i) for i in overview.key_risks
        ],
        "uncertainties": list(overview.uncertainties),
        "cannot_assess": list(overview.cannot_assess),
        "what_changed": [
            _report_item(i) for i in overview.what_changed
        ],
        "hidden_insights": [
            _report_item(i) for i in overview.hidden_insights
        ],
    }


def _quality_indicator(indicator) -> dict:
    return {
        "indicator_id": indicator.indicator_id,
        "name": indicator.name,
        "status": indicator.status,
        "value": indicator.value,
        "explanation": indicator.explanation,
    }


def _quality_layer(layer) -> dict | None:
    if layer is None:
        return None
    return {
        "evidence_coverage_pct": layer.evidence_coverage_pct,
        "provenance_coverage_pct": layer.provenance_coverage_pct,
        "source_freshness_pct": layer.source_freshness_pct,
        "unresolved_conflict_count": layer.unresolved_conflict_count,
        "critical_gap_count": layer.critical_gap_count,
        "stale_input_count": layer.stale_input_count,
        "unsupported_dimension_count": layer.unsupported_dimension_count,
        "pit_status": layer.pit_status,
        "indicators": [
            _quality_indicator(i) for i in layer.indicators
        ],
        "notes": list(layer.notes),
    }


def _source_health_entry(entry) -> dict:
    return {
        "source_id": entry.source_id,
        "name": entry.name,
        "source_type": entry.source_type,
        "tier": entry.tier,
        "reliability_tier": entry.reliability_tier,
        "evidence_count": entry.evidence_count,
        "latest_observation": _utc_iso(entry.latest_observation),
        "freshness_status": entry.freshness_status,
        "coverage_status": entry.coverage_status,
        "stale": entry.stale,
        "provenance_complete": entry.provenance_complete,
        "categories": list(entry.categories),
    }


def _source_health(health) -> dict | None:
    if health is None:
        return None
    return {
        "total_sources": health.total_sources,
        "healthy_sources": health.healthy_sources,
        "degraded_sources": health.degraded_sources,
        "missing_sources": health.missing_sources,
        "stale_sources": health.stale_sources,
        "entries": [
            _source_health_entry(e) for e in health.entries
        ],
        "provider_failures": list(health.provider_failures),
        "notes": list(health.notes),
    }


def _provenance_chain(chain) -> dict | None:
    if chain is None:
        return None
    records = []
    for rec in chain.records:
        records.append({
            "source": rec.source,
            "source_url": rec.source_url,
            "retrieved_at": _utc_iso(rec.retrieved_at),
            "published_at": _utc_iso(rec.published_at),
            "available_at": _utc_iso(rec.available_at),
            "dataset_id": rec.dataset_id,
            "record_id": rec.record_id,
            "checksum": rec.checksum,
        })
    return {
        "total_provenance": chain.total_provenance,
        "with_available_at": chain.with_available_at,
        "with_published_at": chain.with_published_at,
        "records": records,
        "notes": list(chain.notes),
    }


def _pit_integrity(pit) -> dict | None:
    if pit is None:
        return None
    return {
        "as_of": _utc_iso(pit.as_of),
        "effective_as_of": _utc_iso(pit.effective_as_of),
        "market_as_of": pit.market_as_of,
        "evidence_included": pit.evidence_included,
        "future_evidence_excluded": pit.future_evidence_excluded,
        "sources_discovered": pit.sources_discovered,
        "sources_accepted": pit.sources_accepted,
        "pit_checks_passed": pit.pit_checks_passed,
        "notes": list(pit.notes),
    }


def _methodology(method) -> dict | None:
    if method is None:
        return None
    return {
        "methodology_summary": method.methodology_summary,
        "known_limitations": list(method.known_limitations),
        "data_freshness_note": method.data_freshness_note,
        "PIT_policy": method.PIT_policy,
        "epistemic_disclosure": method.epistemic_disclosure,
        "notes": list(method.notes),
    }


def professional_report_contract(
    report,
    *,
    company_name: str | None,
) -> dict:
    """
    Serialize a ProfessionalResearchReport to the API contract dict.
    """
    return {
        "company": {
            "symbol": report.symbol,
            "company_name": company_name,
            "as_of": _utc_iso(report.as_of),
        },
        "report": {
            "symbol": report.symbol,
            "as_of": _utc_iso(report.as_of),
            "company_name": company_name,
            "report_version": report.report_version,
            "executive_overview": _executive_overview(
                report.executive_overview
            ),
            "research_snapshot": _report_section(
                report.research_snapshot
            ),
            "business_context": _report_section(
                report.business_context
            ),
            "financial_performance": _report_section(
                report.financial_performance
            ),
            "financial_quality": _report_section(
                report.financial_quality
            ),
            "market_context": _report_section(
                report.market_context
            ),
            "business_developments": _report_section(
                report.business_developments
            ),
            "management_strategy": _report_section(
                report.management_strategy
            ),
            "competitive_position": _report_section(
                report.competitive_position
            ),
            "innovation": _report_section(
                report.innovation
            ),
            "future_technology": _report_section(
                report.future_technology
            ),
            "industry_context": _report_section(
                report.industry_context
            ),
            "capital_allocation": _report_section(
                report.capital_allocation
            ),
            "corporate_actions": _report_section(
                report.corporate_actions
            ),
            "timeline": _report_section(
                report.timeline
            ),
            "positive_evidence": _evidence_section(
                report.positive_evidence
            ),
            "negative_evidence": _evidence_section(
                report.negative_evidence
            ),
            "conflicting_evidence": _evidence_section(
                report.conflicting_evidence
            ),
            "conflict_details": [
                _conflict_detail(d) for d in report.conflict_details
            ],
            "research_gaps": _report_section(
                report.research_gaps
            ),
            "source_health": _source_health(
                report.source_health
            ),
            "provenance_chain": _provenance_chain(
                report.provenance_chain
            ),
            "pit_integrity": _pit_integrity(
                report.pit_integrity
            ),
            "methodology": _methodology(
                report.methodology
            ),
            "quality_layer": _quality_layer(
                report.quality_layer
            ),
            "notes": list(report.notes),
        },
    }


__all__ = [
    "professional_report_contract",
]
