from src.research.narrative.models import EvidenceNarrative


def test_narrative_detects_conflict():
    narrative = EvidenceNarrative(
        symbol="TEST",
        thesis="Mixed evidence.",
        supporting_evidence=("Positive evidence.",),
        contradicting_evidence=("Negative evidence.",),
    )

    assert narrative.has_conflict is True


def test_narrative_without_conflict():
    narrative = EvidenceNarrative(
        symbol="TEST",
        thesis="Positive evidence.",
        supporting_evidence=("Positive evidence.",),
    )

    assert narrative.has_conflict is False
