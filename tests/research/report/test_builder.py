from datetime import datetime, timezone
from decimal import Decimal

from src.research.features.financial_trends import (
    FinancialTrendSummary,
)
from src.research.features.models import FeatureValue
from src.research.report.builder import build_company_report
from src.research.report.models import ResearchConclusion
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


def trend(
    metric: str,
    direction: str,
    explanation: str,
) -> FinancialTrendSummary:
    return FinancialTrendSummary(
        metric=metric,
        direction=direction,
        observations=4,
        average_change=Decimal("10"),
        positive_periods=3,
        negative_periods=1,
        stable_periods=0,
        consistency=Decimal("0.75"),
        explanation=explanation,
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


def test_increasing_debt_trend_is_negative():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        trend_summaries=[
            trend(
                "total_debt",
                "INCREASING",
                "Total debt increased across the observed periods.",
            ),
        ],
    )

    assert len(report.signals) == 1
    assert report.signals[0].signal_id == (
        "TREND_RISK_TOTAL_DEBT"
    )
    assert report.signals[0].direction == (
        SignalDirection.NEGATIVE
    )
    assert report.conclusion == ResearchConclusion.NEGATIVE
    assert len(report.negative_evidence) == 1


def test_increasing_non_debt_trend_is_positive():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        trend_summaries=[
            trend(
                "revenue",
                "INCREASING",
                "Revenue increased across the observed periods.",
            ),
        ],
    )

    assert len(report.signals) == 1
    assert report.signals[0].signal_id == (
        "TREND_REVENUE"
    )
    assert report.signals[0].direction == (
        SignalDirection.POSITIVE
    )
    assert report.conclusion == ResearchConclusion.POSITIVE
    assert len(report.positive_evidence) == 1


def test_positive_and_negative_trends_are_mixed():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        trend_summaries=[
            trend(
                "revenue",
                "INCREASING",
                "Revenue increased.",
            ),
            trend(
                "total_debt",
                "INCREASING",
                "Debt increased.",
            ),
        ],
    )

    assert len(report.signals) == 2
    assert report.conclusion == ResearchConclusion.NEGATIVE


def test_trend_signals_contribute_to_confidence():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        trend_summaries=[
            trend(
                "revenue",
                "INCREASING",
                "Revenue increased.",
            ),
        ],
    )

    assert report.confidence == Decimal("0.80")


def test_trend_signals_are_exposed_in_report():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        trend_summaries=[
            trend(
                "total_debt",
                "INCREASING",
                "Debt increased.",
            ),
        ],
    )

    assert len(report.signals) == 1
    assert report.signals[0].category == (
        "FINANCIAL_TREND"
    )


def test_report_contains_evidence_synthesis():
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

    assert report.evidence_synthesis is not None
    assert report.evidence_synthesis.symbol == "TEST"
    assert report.evidence_synthesis.positive_count >= 1
    assert report.evidence_synthesis.negative_count == 0


def test_report_evidence_synthesis_detects_conflict():
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

    synthesis = report.evidence_synthesis

    assert synthesis is not None
    assert synthesis.positive_count >= 1
    assert synthesis.negative_count >= 1
    assert synthesis.conflict_detected is True
    assert synthesis.direction.value == "MIXED"


def test_report_evidence_synthesis_excludes_future_evidence():
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
                "future_revenue",
                50.0,
                observation_at=later,
            ),
        ],
    )

    synthesis = report.evidence_synthesis

    assert synthesis is not None
    assert synthesis.evidence == ()
    assert synthesis.positive_count == 0
    assert synthesis.negative_count == 0

from datetime import date

from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
    EvidenceReference,
    IntelligenceDirection,
    IntelligenceSignal,
)


def intelligence_signal(
    code: str,
    direction: IntelligenceDirection,
    *,
    reliability_tier: int = 1,
) -> IntelligenceSignal:
    return IntelligenceSignal(
        code=code,
        title=code,
        description="Company intelligence evidence.",
        direction=direction,
        materiality=4,
        confidence=Decimal("0.9"),
        evidence=[
            EvidenceReference(
                source_name="Test Source",
                source_type="PRIMARY",
                title="Test evidence",
                reliability_tier=reliability_tier,
                reference=f"SRC_{code}",
            )
        ],
    )


def company_snapshot(
    *,
    snapshot_date: date = AS_OF.date(),
    signals: list[IntelligenceSignal] | None = None,
) -> CompanyResearchSnapshot:
    return CompanyResearchSnapshot(
        symbol="TEST",
        company_name="Test Company",
        as_of_date=snapshot_date,
        signals=signals or [],
    )


def test_company_intelligence_enters_evidence_synthesis():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        company_snapshot=company_snapshot(
            signals=[
                intelligence_signal(
                    "INT_POSITIVE",
                    IntelligenceDirection.POSITIVE,
                ),
            ],
        ),
    )

    synthesis = report.evidence_synthesis

    assert synthesis is not None
    assert len(synthesis.evidence) == 1
    assert (
        synthesis.evidence[0].evidence_type.value
        == "COMPANY_INTELLIGENCE"
    )
    assert synthesis.positive_count == 1
    assert synthesis.negative_count == 0
    assert synthesis.direction.value == "POSITIVE"


def test_company_intelligence_negative_evidence_is_synthesized():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        company_snapshot=company_snapshot(
            signals=[
                intelligence_signal(
                    "INT_NEGATIVE",
                    IntelligenceDirection.NEGATIVE,
                ),
            ],
        ),
    )

    synthesis = report.evidence_synthesis

    assert synthesis is not None
    assert synthesis.negative_count == 1
    assert synthesis.direction.value == "NEGATIVE"


def test_company_intelligence_conflict_is_synthesized():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        company_snapshot=company_snapshot(
            signals=[
                intelligence_signal(
                    "INT_POSITIVE",
                    IntelligenceDirection.POSITIVE,
                ),
                intelligence_signal(
                    "INT_NEGATIVE",
                    IntelligenceDirection.NEGATIVE,
                ),
            ],
        ),
    )

    synthesis = report.evidence_synthesis

    assert synthesis is not None
    assert synthesis.positive_count == 1
    assert synthesis.negative_count == 1
    assert synthesis.conflict_detected is True
    assert synthesis.direction.value == "MIXED"


def test_future_company_intelligence_is_excluded():
    later = date(2026, 8, 11)

    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        company_snapshot=company_snapshot(
            snapshot_date=later,
            signals=[
                intelligence_signal(
                    "INT_FUTURE",
                    IntelligenceDirection.POSITIVE,
                ),
            ],
        ),
    )

    synthesis = report.evidence_synthesis

    assert synthesis is not None
    assert synthesis.evidence == ()
    assert synthesis.positive_count == 0
    assert synthesis.negative_count == 0


def test_company_intelligence_source_reference_is_preserved():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        company_snapshot=company_snapshot(
            signals=[
                intelligence_signal(
                    "INT_SOURCE",
                    IntelligenceDirection.POSITIVE,
                ),
            ],
        ),
    )

    synthesis = report.evidence_synthesis

    assert synthesis is not None
    assert synthesis.evidence[0].source_ids == (
        "SRC_INT_SOURCE",
    )


def test_report_contains_evidence_narrative():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        company_snapshot=company_snapshot(
            signals=[
                intelligence_signal(
                    "INT_NARRATIVE",
                    IntelligenceDirection.POSITIVE,
                ),
            ],
        ),
    )

    assert report.evidence_synthesis is not None
    assert report.evidence_narrative is not None
    assert report.evidence_narrative.symbol == "TEST"
    assert report.evidence_narrative.supporting_evidence


def test_report_narrative_preserves_conflicting_evidence():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        company_snapshot=company_snapshot(
            signals=[
                intelligence_signal(
                    "INT_POSITIVE",
                    IntelligenceDirection.POSITIVE,
                ),
                intelligence_signal(
                    "INT_NEGATIVE",
                    IntelligenceDirection.NEGATIVE,
                ),
            ],
        ),
    )

    narrative = report.evidence_narrative

    assert narrative is not None
    assert narrative.has_conflict is True
    assert narrative.supporting_evidence
    assert narrative.contradicting_evidence
    assert narrative.uncertainty


def test_report_narrative_excludes_future_intelligence():
    later = date(2026, 8, 11)

    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        company_snapshot=company_snapshot(
            snapshot_date=later,
            signals=[
                intelligence_signal(
                    "INT_FUTURE",
                    IntelligenceDirection.POSITIVE,
                ),
            ],
        ),
    )

    narrative = report.evidence_narrative

    assert narrative is not None
    assert narrative.supporting_evidence == ()
    assert narrative.contradicting_evidence == ()
    assert narrative.evidence_gaps


def test_report_narrative_is_deterministic():
    kwargs = dict(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        company_snapshot=company_snapshot(
            signals=[
                intelligence_signal(
                    "INT_A",
                    IntelligenceDirection.POSITIVE,
                ),
                intelligence_signal(
                    "INT_B",
                    IntelligenceDirection.NEGATIVE,
                ),
            ],
        ),
    )

    first = build_company_report(**kwargs)
    second = build_company_report(**kwargs)

    assert first.evidence_narrative == second.evidence_narrative


def test_report_narrative_does_not_change_research_conclusion():
    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        company_snapshot=company_snapshot(
            signals=[
                intelligence_signal(
                    "INT_POS",
                    IntelligenceDirection.POSITIVE,
                ),
                intelligence_signal(
                    "INT_NEG",
                    IntelligenceDirection.NEGATIVE,
                ),
            ],
        ),
    )

    assert report.evidence_narrative is not None
    assert report.evidence_narrative.has_conflict is True

    # Narrative is explanatory only. It must not manufacture
    # a BUY/SELL conclusion.
    assert report.evidence_narrative.thesis


# ---------------------------------------------------------------------
# Acquired research observations enter the evidence pipeline
# ---------------------------------------------------------------------

from src.research.acquisition.agent import DeterministicResearchAgent
from src.research.acquisition.models import SourceCandidate
from src.research.acquisition.planner import ResearchPlanner
from src.research.acquisition.providers import ResearchSourceProvider
from src.research.acquisition.runner import ResearchAcquisitionRunner
from src.research.acquisition.validator import SourceValidator
from src.research.synthesis.models import EvidenceType


class RelevantSourceProvider(ResearchSourceProvider):
    def search(self, company, question, as_of):
        return [
            SourceCandidate(
                source_id=f"{question.question_id}-source",
                source_name="Example Source",
                source_type="REGULATORY",
                url="https://example.com/source",
                title=(
                    "AI technology innovation digital transformation "
                    "products revenue customer leadership competitive "
                    "industry partnerships business financial"
                ),
                available_at=datetime(
                    2026,
                    8,
                    10,
                    12,
                    tzinfo=timezone.utc,
                ),
                reliability_tier=1,
            )
        ]


class FutureSourceProvider(ResearchSourceProvider):
    def search(self, company, question, as_of):
        return [
            SourceCandidate(
                source_id=f"{question.question_id}-future",
                source_name="Example Source",
                source_type="REGULATORY",
                url="https://example.com/future",
                title=(
                    "AI technology innovation digital transformation "
                    "products revenue customer leadership competitive "
                    "industry partnerships business financial"
                ),
                available_at=datetime(
                    2026,
                    8,
                    20,
                    12,
                    tzinfo=timezone.utc,
                ),
                reliability_tier=1,
            )
        ]


def acquire_observations(provider: ResearchSourceProvider) -> list:
    runner = ResearchAcquisitionRunner(
        planner=ResearchPlanner(),
        providers=[provider],
        validator=SourceValidator(),
        agent=DeterministicResearchAgent(),
    )

    result = runner.run(
        company="TEST",
        as_of=AS_OF,
        extracted_at=AS_OF,
    )

    return list(result.observations)


def test_acquired_evidence_reaches_the_report_safely():
    observations = acquire_observations(
        RelevantSourceProvider()
    )

    assert observations

    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        acquired_observations=observations,
    )

    synthesis = report.evidence_synthesis

    assert synthesis is not None

    acquired = [
        item
        for item in synthesis.evidence
        if item.evidence_type == EvidenceType.ACQUIRED
    ]

    assert acquired
    assert synthesis.neutral_count >= 1
    assert all(
        item.symbol == "TEST"
        for item in acquired
    )
    assert all(
        item.observation_at <= AS_OF
        for item in acquired
    )
    assert all(
        item.source_ids
        for item in acquired
    )

    narrative = report.evidence_narrative

    assert narrative is not None
    assert any(
        "Source" in strongest
        for strongest in narrative.strongest_evidence
    )
    assert narrative.evidence_gaps == (
        "Available evidence is neutral and does not "
        "establish directional support.",
    )


def test_future_acquired_evidence_never_reaches_the_report():
    observations = acquire_observations(
        FutureSourceProvider()
    )

    assert observations == []

    report = build_company_report(
        symbol="TEST",
        as_of=AS_OF,
        features=[],
        acquired_observations=observations,
    )

    synthesis = report.evidence_synthesis

    assert synthesis is not None
    assert synthesis.evidence == ()

    narrative = report.evidence_narrative

    assert narrative is not None
    assert "No validated point-in-time evidence is available." in (
        narrative.evidence_gaps
    )
