from __future__ import annotations

from src.research.acquisition.models import (
    ResearchCategory,
    ResearchObservation,
)
from src.research.company_intel import (
    intel_items_from_observations,
)
from src.research.company_intel.semantics import (
    IntelKind,
    SemanticCategory,
    VerificationStatus,
)

from .conftest import AS_OF, ts


def make_observation(
    *,
    observation_id: str,
    company: str = "TCS",
    category: ResearchCategory = ResearchCategory.MATERIAL_EVENTS,
    claim: str = "Claim",
    excerpt: str = "Excerpt",
    source_id: str = "source-1",
    available_at=AS_OF,
) -> ResearchObservation:
    return ResearchObservation(
        observation_id=observation_id,
        company=company,
        category=category,
        claim=claim,
        evidence_excerpt=excerpt,
        source_id=source_id,
        reliability_tier=2,
        published_at=available_at,
        available_at=available_at,
        extracted_at=available_at,
        confidence=0.8,
    )


def test_observation_maps_category_to_kind():
    cases = [
        (
            ResearchCategory.MATERIAL_EVENTS,
            IntelKind.BUSINESS_EVENT,
        ),
        (
            ResearchCategory.MANAGEMENT,
            IntelKind.MANAGEMENT_COMMENTARY,
        ),
        (
            ResearchCategory.RISKS,
            IntelKind.RISK_DEVELOPMENT,
        ),
        (
            ResearchCategory.REGULATORY,
            IntelKind.RISK_DEVELOPMENT,
        ),
        (
            ResearchCategory.INDUSTRY,
            IntelKind.INDIRECT_INTELLIGENCE,
        ),
    ]

    for category, expected_kind in cases:
        items = intel_items_from_observations(
            [
                make_observation(
                    observation_id=f"obs-{category.value}",
                    category=category,
                )
            ],
            as_of=AS_OF,
        )

        assert items[0].kind == expected_kind
        assert items[0].semantic_category == SemanticCategory.OBSERVATION
        assert (
            items[0].verification_status
            == VerificationStatus.REPORTED
        )


def test_observation_item_id_is_stable():
    items = intel_items_from_observations(
        [
            make_observation(observation_id="obs-1"),
        ],
        as_of=AS_OF,
    )

    assert items[0].item_id == "observation:obs-1"


def test_observation_available_at_is_preserved():
    items = intel_items_from_observations(
        [
            make_observation(
                observation_id="obs-1",
                available_at=ts(2026, 7, 1),
            ),
        ],
        as_of=AS_OF,
    )

    assert items[0].available_at == ts(2026, 7, 1)
    assert items[0].is_known_at(AS_OF)


def test_future_observation_is_excluded():
    items = intel_items_from_observations(
        [
            make_observation(
                observation_id="future",
                available_at=ts(2026, 9, 1),
            ),
        ],
        as_of=AS_OF,
    )

    assert items == ()


def test_observation_reliability_default():
    items = intel_items_from_observations(
        [
            make_observation(
                observation_id="obs-1",
            ).model_copy(
                update={"reliability_tier": None}
            ),
        ],
        as_of=AS_OF,
        default_reliability_tier=4,
    )

    assert items[0].source.reliability_tier == 4
