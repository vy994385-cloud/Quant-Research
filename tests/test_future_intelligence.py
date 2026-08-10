from decimal import Decimal

import pytest

from src.analysis.future_intelligence import (
    FutureTechnologyArea,
    FutureTechnologySignal,
    FutureTechnologyProfile,
    InnovationEvidenceStrength,
    InnovationSignalDirection,
    ai_participation_score,
    build_future_technology_profile,
    future_readiness_score,
    innovation_execution_score,
    technology_diversification_score,
)


def make_signal(
    *,
    code: str = "AI_PRODUCT",
    direction: InnovationSignalDirection = (
        InnovationSignalDirection.POSITIVE
    ),
    materiality: int = 5,
    confidence: Decimal = Decimal("0.95"),
    evidence_strength: InnovationEvidenceStrength = (
        InnovationEvidenceStrength.VERIFIED
    ),
    technology_area: FutureTechnologyArea = (
        FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE
    ),
) -> FutureTechnologySignal:
    return FutureTechnologySignal(
        code=code,
        title="AI product deployment",
        description=(
            "The company has documented deployment of "
            "AI technology into a commercial product."
        ),
        technology_area=technology_area,
        direction=direction,
        materiality=materiality,
        confidence=confidence,
        evidence_strength=evidence_strength,
        evidence_codes=["PRIMARY_001"],
    )


def test_empty_symbol_is_rejected():
    with pytest.raises(ValueError):
        build_future_technology_profile("")


def test_symbol_is_normalized():
    profile = build_future_technology_profile(
        "  test  ",
    )

    assert profile.symbol == "TEST"


def test_empty_profile_returns_neutral_score():
    profile = build_future_technology_profile(
        "TEST",
    )

    assert future_readiness_score(profile) == Decimal("50")


def test_verified_positive_signal_scores_above_neutral():
    profile = build_future_technology_profile(
        "TEST",
        signals=[
            make_signal(),
        ],
    )

    assert future_readiness_score(profile) > Decimal("50")


def test_verified_negative_signal_scores_below_neutral():
    profile = build_future_technology_profile(
        "TEST",
        signals=[
            make_signal(
                direction=InnovationSignalDirection.NEGATIVE,
            ),
        ],
    )

    assert future_readiness_score(profile) < Decimal("50")


def test_unverified_signal_does_not_drive_score():
    profile = build_future_technology_profile(
        "TEST",
        signals=[
            make_signal(
                evidence_strength=(
                    InnovationEvidenceStrength.UNVERIFIED
                ),
            ),
        ],
    )

    assert future_readiness_score(profile) == Decimal("50")


def test_mixed_signals_are_supported():
    profile = build_future_technology_profile(
        "TEST",
        signals=[
            make_signal(
                code="AI_POSITIVE",
                direction=(
                    InnovationSignalDirection.POSITIVE
                ),
            ),
            make_signal(
                code="TECH_RISK",
                direction=(
                    InnovationSignalDirection.NEGATIVE
                ),
                technology_area=(
                    FutureTechnologyArea.SEMICONDUCTORS
                ),
            ),
        ],
    )

    assert profile.is_mixed
    assert profile.signal_count == 2


def test_profile_counts_material_and_verified_signals():
    profile = build_future_technology_profile(
        "TEST",
        signals=[
            make_signal(),
            make_signal(
                code="WEAK_SIGNAL",
                materiality=2,
                evidence_strength=(
                    InnovationEvidenceStrength.WEAK
                ),
            ),
        ],
    )

    assert profile.material_signal_count == 1
    assert profile.verified_signal_count == 1


def test_multiple_technology_areas_are_counted():
    profile = build_future_technology_profile(
        "TEST",
        signals=[
            make_signal(
                technology_area=(
                    FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE
                ),
            ),
            make_signal(
                code="ROBOTICS",
                technology_area=(
                    FutureTechnologyArea.ROBOTICS
                ),
            ),
            make_signal(
                code="CLOUD",
                technology_area=(
                    FutureTechnologyArea.CLOUD
                ),
            ),
        ],
    )

    assert profile.technology_area_count == 3


def test_verified_execution_beats_unverified_ai_hype():
    hype_signal = FutureTechnologySignal(
        code="AI_HYPE",
        title="AI announcement",
        description="Company announced an AI initiative.",
        technology_area=FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE,
        direction=InnovationSignalDirection.POSITIVE,
        materiality=3,
        confidence=Decimal("0.90"),
        evidence_strength=InnovationEvidenceStrength.UNVERIFIED,
        technology_relevance=Decimal("90"),
        execution_strength=Decimal("20"),
        commercialization_strength=Decimal("10"),
        strategic_importance=Decimal("70"),
    )

    execution_signal = FutureTechnologySignal(
        code="AI_EXECUTION",
        title="AI commercial deployment",
        description="Company deployed AI commercially.",
        technology_area=FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE,
        direction=InnovationSignalDirection.POSITIVE,
        materiality=5,
        confidence=Decimal("0.95"),
        evidence_strength=InnovationEvidenceStrength.VERIFIED,
        technology_relevance=Decimal("95"),
        execution_strength=Decimal("90"),
        commercialization_strength=Decimal("90"),
        strategic_importance=Decimal("95"),
    )

    hype_profile = build_future_technology_profile(
        "TEST",
        signals=[hype_signal],
    )

    execution_profile = build_future_technology_profile(
        "TEST",
        signals=[execution_signal],
    )

    assert (
        future_readiness_score(execution_profile)
        > future_readiness_score(hype_profile)
    )


def test_no_ai_activity_is_not_negative_future_readiness():
    signal = FutureTechnologySignal(
        code="ADVANCED_MANUFACTURING",
        title="Advanced manufacturing",
        description="Company is investing in advanced manufacturing.",
        technology_area=FutureTechnologyArea.ADVANCED_MANUFACTURING,
        direction=InnovationSignalDirection.POSITIVE,
        materiality=5,
        confidence=Decimal("0.95"),
        evidence_strength=InnovationEvidenceStrength.VERIFIED,
        technology_relevance=Decimal("95"),
        execution_strength=Decimal("90"),
        commercialization_strength=Decimal("85"),
        strategic_importance=Decimal("90"),
    )

    profile = build_future_technology_profile(
        "TEST",
        signals=[signal],
    )

    assert ai_participation_score(profile) == Decimal("0")
    assert future_readiness_score(profile) > Decimal("50")


def test_ai_participation_requires_ai_signals():
    signal = FutureTechnologySignal(
        code="CLOUD",
        title="Cloud expansion",
        description="Company expanded cloud infrastructure.",
        technology_area=FutureTechnologyArea.CLOUD,
        direction=InnovationSignalDirection.POSITIVE,
        materiality=4,
        confidence=Decimal("0.90"),
        evidence_strength=InnovationEvidenceStrength.STRONG,
        technology_relevance=Decimal("85"),
        execution_strength=Decimal("80"),
        commercialization_strength=Decimal("75"),
        strategic_importance=Decimal("80"),
    )

    profile = build_future_technology_profile(
        "TEST",
        signals=[signal],
    )

    assert ai_participation_score(profile) == Decimal("0")


def test_execution_score_rewards_commercialization():
    signal = FutureTechnologySignal(
        code="ROBOTICS",
        title="Robotics deployment",
        description="Robotics deployed into production.",
        technology_area=FutureTechnologyArea.ROBOTICS,
        direction=InnovationSignalDirection.POSITIVE,
        materiality=5,
        confidence=Decimal("1"),
        evidence_strength=InnovationEvidenceStrength.VERIFIED,
        technology_relevance=Decimal("90"),
        execution_strength=Decimal("90"),
        commercialization_strength=Decimal("95"),
        strategic_importance=Decimal("85"),
    )

    profile = build_future_technology_profile(
        "TEST",
        signals=[signal],
    )

    assert innovation_execution_score(profile) >= Decimal("90")


def test_technology_diversification_rewards_multiple_areas():
    signals = []

    areas = [
        FutureTechnologyArea.ARTIFICIAL_INTELLIGENCE,
        FutureTechnologyArea.ROBOTICS,
        FutureTechnologyArea.CLOUD,
        FutureTechnologyArea.CYBERSECURITY,
    ]

    for index, area in enumerate(areas):
        signals.append(
            FutureTechnologySignal(
                code=f"TECH_{index}",
                title=f"Technology {index}",
                description="Verified technology activity.",
                technology_area=area,
                direction=InnovationSignalDirection.POSITIVE,
                materiality=4,
                confidence=Decimal("0.90"),
                evidence_strength=InnovationEvidenceStrength.VERIFIED,
            )
        )

    profile = build_future_technology_profile(
        "TEST",
        signals=signals,
    )

    assert technology_diversification_score(profile) == Decimal("82")
