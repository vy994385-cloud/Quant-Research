"""
Business intelligence research API routes.

Exposes deep business intelligence data through typed contracts.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from src.api.contracts import (
    CompanyBusinessIntelligenceContract,
    ContractBusinessAnalysis,
    ContractBusinessDerivedObservation,
    ContractBusinessIntelligence,
    ContractBusinessQualitySignal,
    ContractCapitalAllocationSignal,
    ContractCompetitiveAnalysis,
    ContractCompetitiveMetric,
    ContractCompetitiveSignal,
    ContractDerivedObservations,
    ContractManagementAnalysis,
    ContractManagementPattern,
    ContractRiskAnalysis,
    ContractRiskObservation,
    ContractSegmentConcentration,
    ContractSegmentShare,
    ContractSegmentTrend,
)


def _serialize_segment_share(s) -> ContractSegmentShare:
    return ContractSegmentShare(
        segment_name=s.segment_name,
        revenue=s.revenue,
        share_pct=s.share_pct,
    )


def _serialize_segment_concentration(c) -> ContractSegmentConcentration:
    return ContractSegmentConcentration(
        period=c.period,
        total_revenue=c.total_revenue,
        segment_count=c.segment_count,
        dominant_segment=c.dominant_segment,
        dominant_segment_pct=c.dominant_segment_pct,
        hhi=c.hhi,
        concentration_level=c.concentration_level,
        segment_shares=[_serialize_segment_share(s) for s in c.segment_shares],
        explanation=c.explanation,
    )


def _serialize_segment_trend(t) -> ContractSegmentTrend:
    return ContractSegmentTrend(
        segment_name=t.segment_name,
        direction=t.direction,
        periods_analyzed=t.periods_analyzed,
        first_period=t.first_period,
        last_period=t.last_period,
        share_change=t.share_change,
        explanation=t.explanation,
    )


def _serialize_quality_signal(s) -> ContractBusinessQualitySignal:
    return ContractBusinessQualitySignal(
        signal_id=s.signal_id,
        signal_type=s.signal_type,
        direction=s.direction,
        title=s.title,
        description=s.description,
        metric=s.metric,
        value=s.value,
        threshold=s.threshold,
    )


def _serialize_business_analysis(ba) -> ContractBusinessAnalysis:
    return ContractBusinessAnalysis(
        has_profile=ba.has_profile,
        sector=ba.sector,
        industry=ba.industry,
        country=ba.country,
        employees=ba.employees,
        segment_concentrations=[
            _serialize_segment_concentration(c)
            for c in ba.segment_concentrations
        ],
        segment_trends=[
            _serialize_segment_trend(t) for t in ba.segment_trends
        ],
        quality_signals=[
            _serialize_quality_signal(s) for s in ba.quality_signals
        ],
        available_analyses=list(ba.available_analyses),
        missing_analyses=list(ba.missing_analyses),
    )


def _serialize_competitive_metric(m) -> ContractCompetitiveMetric:
    return ContractCompetitiveMetric(
        metric=m.metric,
        company_value=m.company_value,
        peer_median=m.peer_median,
        percentile=m.percentile,
        position=m.position,
        explanation=m.explanation,
    )


def _serialize_competitive_signal(s) -> ContractCompetitiveSignal:
    return ContractCompetitiveSignal(
        signal_id=s.signal_id,
        signal_type=s.signal_type,
        direction=s.direction,
        title=s.title,
        description=s.description,
        metric=s.metric,
        company_value=s.company_value,
        peer_value=s.peer_value,
    )


def _serialize_competitive_analysis(ca) -> ContractCompetitiveAnalysis:
    return ContractCompetitiveAnalysis(
        has_peer_data=ca.has_peer_data,
        peer_count=ca.peer_count,
        metrics=[_serialize_competitive_metric(m) for m in ca.metrics],
        signals=[_serialize_competitive_signal(s) for s in ca.signals],
        available_analyses=list(ca.available_analyses),
        missing_analyses=list(ca.missing_analyses),
    )


def _serialize_management_pattern(p) -> ContractManagementPattern:
    return ContractManagementPattern(
        pattern_id=p.pattern_id,
        pattern_type=p.pattern_type,
        change_count=p.change_count,
        roles_affected=list(p.roles_affected),
        date_range=p.date_range,
        explanation=p.explanation,
    )


def _serialize_allocation_signal(s) -> ContractCapitalAllocationSignal:
    return ContractCapitalAllocationSignal(
        signal_id=s.signal_id,
        signal_type=s.signal_type,
        direction=s.direction,
        title=s.title,
        description=s.description,
        metric=s.metric,
        value=s.value,
        explanation=s.explanation,
    )


def _serialize_management_analysis(ma) -> ContractManagementAnalysis:
    return ContractManagementAnalysis(
        change_count=ma.change_count,
        patterns=[_serialize_management_pattern(p) for p in ma.patterns],
        allocation_signals=[
            _serialize_allocation_signal(s)
            for s in ma.allocation_signals
        ],
        available_analyses=list(ma.available_analyses),
        missing_analyses=list(ma.missing_analyses),
    )


def _serialize_risk_observation(o) -> ContractRiskObservation:
    return ContractRiskObservation(
        risk_id=o.risk_id,
        risk_dimension=o.risk_dimension,
        severity=o.severity,
        title=o.title,
        description=o.description,
        explanation=o.explanation,
    )


def _serialize_risk_analysis(ra) -> ContractRiskAnalysis:
    return ContractRiskAnalysis(
        observations=[_serialize_risk_observation(o) for o in ra.observations],
        dimension_counts=dict(ra.dimension_counts),
        severity_counts=dict(ra.severity_counts),
        available_analyses=list(ra.available_analyses),
        missing_analyses=list(ra.missing_analyses),
    )


def _serialize_derived_observation(o) -> ContractBusinessDerivedObservation:
    return ContractBusinessDerivedObservation(
        observation_id=o.observation_id,
        evidence_classification=o.evidence_classification,
        domain=o.domain,
        title=o.title,
        description=o.description,
        source_domains=list(o.source_domains),
        explanation=o.explanation,
    )


def _serialize_derived_observations(dr) -> ContractDerivedObservations:
    return ContractDerivedObservations(
        observations=[
            _serialize_derived_observation(o) for o in dr.observations
        ],
        fact_count=dr.fact_count,
        observation_count=dr.observation_count,
        interpretation_count=dr.interpretation_count,
        available_analyses=list(dr.available_analyses),
        missing_analyses=list(dr.missing_analyses),
    )


def _serialize_bi_result(result) -> ContractBusinessIntelligence:
    return ContractBusinessIntelligence(
        symbol=result.symbol,
        as_of=result.as_of,
        has_profile=result.has_profile,
        sector=result.sector,
        industry=result.industry,
        country=result.country,
        employees=result.employees,
        business_analysis=(
            _serialize_business_analysis(result.business_analysis)
            if result.business_analysis
            else None
        ),
        competitive_analysis=(
            _serialize_competitive_analysis(result.competitive_analysis)
            if result.competitive_analysis
            else None
        ),
        management_analysis=(
            _serialize_management_analysis(result.management_analysis)
            if result.management_analysis
            else None
        ),
        risk_analysis=(
            _serialize_risk_analysis(result.risk_analysis)
            if result.risk_analysis
            else None
        ),
        derived_observations=(
            _serialize_derived_observations(result.derived_observations)
            if result.derived_observations
            else None
        ),
        total_observations=result.total_observations,
        risk_count=result.risk_count,
        derived_count=result.derived_count,
        available_analyses=list(result.available_analyses),
        missing_analyses=list(result.missing_analyses),
        notes=list(result.notes),
    )


def create_business_router() -> APIRouter:
    router = APIRouter(
        prefix="/api/v1/companies",
        tags=["business-intelligence"],
    )

    @router.get(
        "/{symbol}/business-intelligence",
        response_model=CompanyBusinessIntelligenceContract,
    )
    async def get_business_intelligence(
        symbol: str,
        as_of: str | None = Query(
            None,
            description="Point-in-time date (ISO format). Defaults to latest.",
        ),
    ) -> CompanyBusinessIntelligenceContract:
        """
        Deep business intelligence for a company.

        Returns business profile, segment analysis, competitive
        positioning, management analysis, risk observations,
        and cross-domain derived observations.
        """
        from src.analysis.business_intelligence import (
            analyze_business_intelligence,
        )
        from src.data.providers.yahoo_profile import (
            YahooProfileProvider,
        )
        from src.data.providers.yahoo_financials import (
            YahooFinanceFinancialProvider,
        )

        as_of_dt = (
            datetime.fromisoformat(as_of).replace(tzinfo=timezone.utc)
            if as_of
            else datetime.now(timezone.utc)
        )

        # Fetch profile
        profile_provider = YahooProfileProvider()
        try:
            profile = profile_provider.get_business_profile(symbol)
        except RuntimeError:
            profile = None

        if profile is None:
            from src.api.recorded_research import (
                RecordedCompanyResearchService,
            )

            _svc = RecordedCompanyResearchService()
            _cname = _svc.company_name(symbol)
            return CompanyBusinessIntelligenceContract(
                company={
                    "symbol": symbol,
                    "company_name": _cname or symbol,
                },
                business_intelligence=ContractBusinessIntelligence(
                    symbol=symbol,
                    as_of=as_of_dt.isoformat(),
                    has_profile=False,
                ),
            )

        # Fetch financials
        financial_provider = YahooFinanceFinancialProvider()
        from datetime import timedelta

        end_date = as_of_dt.date()
        start_date = end_date - timedelta(days=365 * 10)

        try:
            snapshots = financial_provider.get_annual_financials(
                symbol, start_date, end_date
            )
        except Exception:
            snapshots = []

        # Run business intelligence analysis
        result = analyze_business_intelligence(
            snapshots=snapshots,
            profile=profile,
            peer_snapshots=[],
            management_changes=[],
            symbol=symbol,
            as_of=as_of_dt,
        )

        company_info: dict[str, object] = {
            "symbol": symbol,
            "company_name": profile.company_name if profile else symbol,
        }

        return CompanyBusinessIntelligenceContract(
            company=company_info,
            business_intelligence=_serialize_bi_result(result),
        )

    return router
