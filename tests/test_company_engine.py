from datetime import datetime, timezone

import pytest

from src.research.company_engine import (
    CompanyResearchEngine,
    CompanyResearchInput,
    run_company_research,
)


AS_OF = datetime(
    2026,
    8,
    12,
    10,
    0,
    tzinfo=timezone.utc,
)


def test_company_research_input_normalizes_symbol():
    value = CompanyResearchInput(
        symbol="  tcs  ",
        as_of=AS_OF,
    )

    assert value.symbol == "TCS"


def test_company_research_input_rejects_empty_symbol():
    with pytest.raises(ValueError):
        CompanyResearchInput(
            symbol="   ",
            as_of=AS_OF,
        )


def test_company_research_input_requires_timezone():
    with pytest.raises(ValueError):
        CompanyResearchInput(
            symbol="TCS",
            as_of=datetime(2026, 8, 12, 10, 0),
        )


def test_engine_returns_report():
    engine = CompanyResearchEngine()

    report = engine.run(
        CompanyResearchInput(
            symbol="TCS",
            as_of=AS_OF,
        )
    )

    assert report.symbol == "TCS"
    assert report.as_of == AS_OF


def test_engine_does_not_create_fake_evidence():
    report = run_company_research(
        symbol="TCS",
        as_of=AS_OF,
    )

    assert report.symbol == "TCS"
    assert report.signals == ()
    assert report.positive_evidence == ()
    assert report.negative_evidence == ()


def test_convenience_api_normalizes_symbol():
    report = run_company_research(
        symbol="  tcs ",
        as_of=AS_OF,
    )

    assert report.symbol == "TCS"


def test_company_engine_carries_acquired_observations_to_report():
    from src.research.acquisition.models import (
        ResearchCategory,
        ResearchObservation,
    )
    from src.research.synthesis.models import EvidenceType

    observation = ResearchObservation(
        observation_id="TCS:innovation:source-1",
        company="TCS",
        category=ResearchCategory.INNOVATION,
        claim="Company filed a new patent application.",
        evidence_excerpt="Example evidence excerpt.",
        source_id="source-1",
        reliability_tier=2,
        available_at=AS_OF,
        extracted_at=AS_OF,
        confidence=0.8,
    )

    report = run_company_research(
        symbol="TCS",
        as_of=AS_OF,
        acquired_observations=[observation],
    )

    synthesis = report.evidence_synthesis

    assert synthesis is not None
    assert any(
        item.evidence_type == EvidenceType.ACQUIRED
        for item in synthesis.evidence
    )
