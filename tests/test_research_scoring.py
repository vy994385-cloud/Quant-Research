from decimal import Decimal

import pytest

from src.analysis.research_scoring import calculate_research_score


def test_strong_company_gets_high_score():
    score = calculate_research_score(
        fundamentals=Decimal("90"),
        financial_trends=Decimal("88"),
        cash_flow=Decimal("92"),
        balance_sheet=Decimal("85"),
        risk=Decimal("82"),
        management=Decimal("90"),
        market_behavior=Decimal("86"),
        evidence_quality=Decimal("95"),
    )

    assert score.total >= Decimal("85")
    assert score.signal == "POSITIVE"
    assert score.confidence >= Decimal("95")


def test_weak_company_gets_negative_signal():
    score = calculate_research_score(
        fundamentals=Decimal("25"),
        financial_trends=Decimal("30"),
        cash_flow=Decimal("20"),
        balance_sheet=Decimal("28"),
        risk=Decimal("25"),
        management=Decimal("35"),
        market_behavior=Decimal("30"),
        evidence_quality=Decimal("80"),
    )

    assert score.total <= Decimal("40")
    assert score.signal == "NEGATIVE"


def test_mixed_company_gets_neutral_signal():
    score = calculate_research_score(
        fundamentals=Decimal("60"),
        financial_trends=Decimal("55"),
        cash_flow=Decimal("65"),
        balance_sheet=Decimal("50"),
        risk=Decimal("55"),
        management=Decimal("60"),
        market_behavior=Decimal("45"),
        evidence_quality=Decimal("90"),
    )

    assert Decimal("40") < score.total < Decimal("70")
    assert score.signal == "NEUTRAL"


def test_scores_must_be_between_zero_and_hundred():
    with pytest.raises(ValueError):
        calculate_research_score(
            fundamentals=Decimal("101"),
            financial_trends=Decimal("50"),
            cash_flow=Decimal("50"),
            balance_sheet=Decimal("50"),
            risk=Decimal("50"),
            management=Decimal("50"),
            market_behavior=Decimal("50"),
            evidence_quality=Decimal("50"),
        )


def test_confidence_drops_when_components_disagree():
    consistent = calculate_research_score(
        fundamentals=Decimal("80"),
        financial_trends=Decimal("80"),
        cash_flow=Decimal("80"),
        balance_sheet=Decimal("80"),
        risk=Decimal("80"),
        management=Decimal("80"),
        market_behavior=Decimal("80"),
        evidence_quality=Decimal("80"),
    )

    inconsistent = calculate_research_score(
        fundamentals=Decimal("10"),
        financial_trends=Decimal("95"),
        cash_flow=Decimal("20"),
        balance_sheet=Decimal("90"),
        risk=Decimal("30"),
        management=Decimal("85"),
        market_behavior=Decimal("15"),
        evidence_quality=Decimal("100"),
    )

    assert consistent.confidence > inconsistent.confidence


def test_research_score_tracks_partial_coverage():
    from decimal import Decimal

    from src.analysis.research_scoring import calculate_research_score

    score = calculate_research_score(
        fundamentals=Decimal("70"),
        financial_trends=Decimal("70"),
        cash_flow=Decimal("70"),
        balance_sheet=Decimal("70"),
        risk=Decimal("70"),
        management=Decimal("50"),
        market_behavior=Decimal("50"),
        evidence_quality=Decimal("80"),
        component_availability={
            "fundamentals": True,
            "financial_trends": True,
            "cash_flow": True,
            "balance_sheet": True,
            "risk": True,
            "management": False,
            "market_behavior": False,
            "evidence_quality": True,
        },
    )

    assert score.coverage.status == "PARTIAL"
    assert score.coverage.available_components == 6
    assert score.coverage.total_components == 8
    assert "management" in score.coverage.missing_components
    assert "market_behavior" in score.coverage.missing_components
    assert score.coverage.coverage == Decimal("75")


def test_research_score_is_complete_by_default():
    from decimal import Decimal

    from src.analysis.research_scoring import calculate_research_score

    score = calculate_research_score(
        fundamentals=Decimal("70"),
        financial_trends=Decimal("70"),
        cash_flow=Decimal("70"),
        balance_sheet=Decimal("70"),
        risk=Decimal("70"),
        management=Decimal("70"),
        market_behavior=Decimal("70"),
        evidence_quality=Decimal("70"),
    )

    assert score.coverage.status == "COMPLETE"
    assert score.coverage.coverage == Decimal("100")
