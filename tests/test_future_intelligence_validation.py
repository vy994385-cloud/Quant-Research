from datetime import date
from decimal import Decimal

import pytest

from src.analysis.future_intelligence import (
    FutureTechnologyArea,
    FutureTechnologyProfile,
    FutureTechnologySignal,
    InnovationEvidenceStrength,
    InnovationSignalDirection,
)
from src.validation.future_intelligence_validation import (
    FutureIntelligenceObservation,
    FutureIntelligenceOutcome,
    validate_observation,
    validate_observations,
    validate_temporal_order,
)


def make_profile(symbol: str = "TEST") -> FutureTechnologyProfile:
    return FutureTechnologyProfile(
        symbol=symbol,
        sector="technology",
        signals=[
            FutureTechnologySignal(
                code="AI_001",
                title="AI product deployment",
                description="AI product deployed to customers.",
                technology_area=(
                    FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE
                ),
                direction=InnovationSignalDirection.POSITIVE,
                materiality=4,
                confidence=Decimal("0.90"),
                evidence_strength=(
                    InnovationEvidenceStrength.VERIFIED
                ),
                execution_strength=Decimal("85"),
                commercialization_strength=Decimal("80"),
                technology_relevance=Decimal("90"),
                strategic_importance=Decimal("85"),
            )
        ],
    )


def test_future_outcome_must_be_after_observation():

    assert validate_temporal_order(
        observation_date=date(2025, 1, 1),
        outcome_date=date(2025, 2, 1),
    )

    assert not validate_temporal_order(
        observation_date=date(2025, 2, 1),
        outcome_date=date(2025, 2, 1),
    )

    assert not validate_temporal_order(
        observation_date=date(2025, 3, 1),
        outcome_date=date(2025, 2, 1),
    )


def test_validation_rejects_same_day_outcome():

    observation = FutureIntelligenceObservation(
        symbol="TEST",
        as_of_date=date(2025, 1, 1),
        profile=make_profile(),
    )

    outcome = FutureIntelligenceOutcome(
        symbol="TEST",
        outcome_date=date(2025, 1, 1),
        metric="revenue_growth",
        value=Decimal("10"),
    )

    result = validate_observation(
        observation,
        outcome,
    )

    assert result.valid_temporal_order is False
    assert result.is_valid is False


def test_validation_accepts_later_outcome():

    observation = FutureIntelligenceObservation(
        symbol="TEST",
        as_of_date=date(2025, 1, 1),
        profile=make_profile(),
    )

    outcome = FutureIntelligenceOutcome(
        symbol="TEST",
        outcome_date=date(2025, 4, 1),
        metric="revenue_growth",
        value=Decimal("15"),
    )

    result = validate_observation(
        observation,
        outcome,
    )

    assert result.valid_temporal_order
    assert result.is_valid
    assert result.future_readiness > Decimal("50")
    assert result.outcome_value == Decimal("15")


def test_validation_rejects_symbol_mismatch():

    observation = FutureIntelligenceObservation(
        symbol="TEST",
        as_of_date=date(2025, 1, 1),
        profile=make_profile(),
    )

    outcome = FutureIntelligenceOutcome(
        symbol="OTHER",
        outcome_date=date(2025, 4, 1),
        metric="revenue_growth",
        value=Decimal("15"),
    )

    with pytest.raises(ValueError):
        validate_observation(
            observation,
            outcome,
        )


def test_bulk_validation_excludes_future_and_same_day_outcomes():

    observation = FutureIntelligenceObservation(
        symbol="TEST",
        as_of_date=date(2025, 1, 1),
        profile=make_profile(),
    )

    outcomes = [
        FutureIntelligenceOutcome(
            symbol="TEST",
            outcome_date=date(2024, 12, 1),
            metric="revenue_growth",
            value=Decimal("5"),
        ),
        FutureIntelligenceOutcome(
            symbol="TEST",
            outcome_date=date(2025, 1, 1),
            metric="revenue_growth",
            value=Decimal("6"),
        ),
        FutureIntelligenceOutcome(
            symbol="TEST",
            outcome_date=date(2025, 4, 1),
            metric="revenue_growth",
            value=Decimal("15"),
        ),
        FutureIntelligenceOutcome(
            symbol="OTHER",
            outcome_date=date(2025, 5, 1),
            metric="revenue_growth",
            value=Decimal("20"),
        ),
    ]

    results = validate_observations(
        observations=[observation],
        outcomes=outcomes,
    )

    assert len(results) == 1
    assert results[0].outcome_date == date(2025, 4, 1)


def test_bulk_validation_is_deterministic():

    observation = FutureIntelligenceObservation(
        symbol="TEST",
        as_of_date=date(2025, 1, 1),
        profile=make_profile(),
    )

    outcomes = [
        FutureIntelligenceOutcome(
            symbol="TEST",
            outcome_date=date(2025, 6, 1),
            metric="margin",
            value=Decimal("12"),
        ),
        FutureIntelligenceOutcome(
            symbol="TEST",
            outcome_date=date(2025, 3, 1),
            metric="revenue_growth",
            value=Decimal("10"),
        ),
    ]

    results = validate_observations(
        observations=[observation],
        outcomes=outcomes,
    )

    assert [
        (
            result.outcome_date,
            result.metric,
        )
        for result in results
    ] == [
        (
            date(2025, 3, 1),
            "revenue_growth",
        ),
        (
            date(2025, 6, 1),
            "margin",
        ),
    ]
