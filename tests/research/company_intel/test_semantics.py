from __future__ import annotations

from src.research.company_intel import (
    classify_semantic_category,
    insufficient_evidence_message,
)
from src.research.company_intel.semantics import (
    IntelKind,
    SemanticCategory,
    VerificationStatus,
)

from .conftest import make_item


def test_management_commentary_classification():
    item = make_item(
        item_id="a",
        kind=IntelKind.MANAGEMENT_COMMENTARY,
        verification_status=VerificationStatus.REPORTED,
    )

    assert (
        classify_semantic_category(item)
        == SemanticCategory.MANAGEMENT_COMMENTARY
    )


def test_allegation_never_becomes_fact():
    item = make_item(
        item_id="a",
        kind=IntelKind.RISK_DEVELOPMENT,
        verification_status=VerificationStatus.ALLEGED,
    )

    assert (
        classify_semantic_category(item)
        == SemanticCategory.ALLEGATION
    )


def test_reported_claim_stays_a_claim():
    item = make_item(
        item_id="a",
        kind=IntelKind.BUSINESS_EVENT,
        verification_status=VerificationStatus.REPORTED,
    )

    assert (
        classify_semantic_category(item)
        == SemanticCategory.REPORTED_CLAIM
    )


def test_confirmed_fact_is_classified_as_fact():
    item = make_item(
        item_id="a",
        kind=IntelKind.BUSINESS_EVENT,
        verification_status=VerificationStatus.CONFIRMED,
        reliability_tier=1,
    )

    assert (
        classify_semantic_category(item)
        == SemanticCategory.FACT
    )


def test_resolved_classifies_as_observation():
    item = make_item(
        item_id="a",
        kind=IntelKind.RISK_DEVELOPMENT,
        verification_status=VerificationStatus.RESOLVED,
    )

    assert (
        classify_semantic_category(item)
        == SemanticCategory.OBSERVATION
    )


def test_explicit_derived_metric_is_preserved():
    item = make_item(
        item_id="a",
        kind=IntelKind.FINANCIAL_PERIOD,
        semantic_category=SemanticCategory.DERIVED_METRIC,
        verification_status=VerificationStatus.CONFIRMED,
        reliability_tier=1,
    )

    assert (
        classify_semantic_category(item)
        == SemanticCategory.DERIVED_METRIC
    )


def test_explicit_conclusion_is_preserved():
    item = make_item(
        item_id="a",
        semantic_category=SemanticCategory.CONCLUSION,
        verification_status=VerificationStatus.CONFIRMED,
        reliability_tier=1,
    )

    assert (
        classify_semantic_category(item)
        == SemanticCategory.CONCLUSION
    )


def test_insufficient_evidence_message_is_canonical():
    assert insufficient_evidence_message() == (
        "Insufficient evidence for a firm conclusion."
    )
