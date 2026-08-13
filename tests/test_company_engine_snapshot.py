from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
    IntelligenceDirection,
    IntelligenceSignal,
)
from src.research.company_engine import (
    CompanyResearchEngine,
    CompanyResearchInput,
    run_company_research,
)
from src.research.report.models import ResearchConclusion


AS_OF = datetime(
    2026,
    8,
    12,
    10,
    0,
    tzinfo=timezone.utc,
)


def snapshot(
    symbol: str = "TEST",
) -> CompanyResearchSnapshot:
    return CompanyResearchSnapshot(
        symbol=symbol,
        as_of_date=date(2026, 8, 10),
        signals=[
            IntelligenceSignal(
                code="REVENUE_GROWTH",
                title="Revenue growth",
                description="Revenue increased.",
                direction=IntelligenceDirection.POSITIVE,
                materiality=4,
                confidence=Decimal("0.90"),
            ),
        ],
    )


def test_engine_accepts_company_snapshot():

    report = CompanyResearchEngine().run(
        CompanyResearchInput(
            symbol="TEST",
            as_of=AS_OF,
            company_snapshot=snapshot(),
        )
    )

    assert report.symbol == "TEST"
    assert len(report.signals) == 1
    assert report.signals[0].signal_id == "REVENUE_GROWTH"
    assert report.conclusion == ResearchConclusion.POSITIVE


def test_convenience_api_accepts_company_snapshot():

    report = run_company_research(
        symbol="TEST",
        as_of=AS_OF,
        company_snapshot=snapshot(),
    )

    assert report.symbol == "TEST"
    assert len(report.signals) == 1
    assert report.signals[0].category == (
        "COMPANY_INTELLIGENCE"
    )


def test_snapshot_symbol_must_match():

    with pytest.raises(
        ValueError,
        match="company snapshot symbol",
    ):
        CompanyResearchInput(
            symbol="TEST",
            as_of=AS_OF,
            company_snapshot=snapshot("OTHER"),
        )


def test_snapshot_cannot_be_from_future():

    future_snapshot = CompanyResearchSnapshot(
        symbol="TEST",
        as_of_date=date(2026, 8, 13),
        signals=[],
    )

    with pytest.raises(
        ValueError,
        match="cannot be after as_of",
    ):
        CompanyResearchInput(
            symbol="TEST",
            as_of=AS_OF,
            company_snapshot=future_snapshot,
        )


def test_empty_snapshot_does_not_create_fake_evidence():

    report = run_company_research(
        symbol="TEST",
        as_of=AS_OF,
        company_snapshot=CompanyResearchSnapshot(
            symbol="TEST",
            as_of_date=date(2026, 8, 10),
        ),
    )

    assert report.signals == ()
    assert report.positive_evidence == ()
    assert report.negative_evidence == ()
    assert report.conclusion == (
        ResearchConclusion.INSUFFICIENT_EVIDENCE
    )


def test_existing_signals_and_snapshot_are_combined():

    from src.research.signals.models import (
        ResearchSignal,
        SignalDirection,
        SignalSeverity,
    )

    existing = ResearchSignal(
        signal_id="EXISTING",
        category="FINANCIAL",
        direction=SignalDirection.NEGATIVE,
        severity=SignalSeverity.MEDIUM,
        confidence=Decimal("0.80"),
        title="Existing risk",
        explanation="Existing research evidence.",
        symbol="TEST",
        observation_at=AS_OF,
    )

    report = run_company_research(
        symbol="TEST",
        as_of=AS_OF,
        signals=[existing],
        company_snapshot=snapshot(),
    )

    assert len(report.signals) == 2

    signal_ids = {
        signal.signal_id
        for signal in report.signals
    }

    assert signal_ids == {
        "EXISTING",
        "REVENUE_GROWTH",
    }


def test_report_exposes_company_intelligence_summary():

    report = run_company_research(
        symbol="TEST",
        as_of=AS_OF,
        company_snapshot=snapshot(),
    )

    assert report.has_company_intelligence is True
    assert report.company_intelligence_signal_count == 1
    assert report.company_intelligence_positive_count == 1
    assert report.company_intelligence_negative_count == 0
    assert report.company_intelligence_is_mixed is False


def test_report_without_snapshot_has_no_company_intelligence():

    report = run_company_research(
        symbol="TEST",
        as_of=AS_OF,
    )

    assert report.has_company_intelligence is False
    assert report.company_intelligence_signal_count == 0
    assert report.company_intelligence_positive_count == 0
    assert report.company_intelligence_negative_count == 0
