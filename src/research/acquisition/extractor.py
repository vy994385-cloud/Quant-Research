from __future__ import annotations

from datetime import datetime

from src.research.acquisition.models import (
    ResearchObservation,
    ResearchQuestion,
    SourceCandidate,
)


class ObservationExtractor:
    """
    Converts accepted sources into factual research observations.

    Extraction does not produce scores, recommendations, or investment
    conclusions. Those remain downstream responsibilities.
    """

    def extract(
        self,
        company: str,
        question: ResearchQuestion,
        source: SourceCandidate,
        claim: str,
        evidence_excerpt: str,
        extracted_at: datetime,
        confidence: float,
    ) -> ResearchObservation:
        if not company.strip():
            raise ValueError("company must not be empty")

        if not claim.strip():
            raise ValueError("claim must not be empty")

        if not evidence_excerpt.strip():
            raise ValueError("evidence_excerpt must not be empty")

        if (
            extracted_at.tzinfo is None
            or extracted_at.utcoffset() is None
        ):
            raise ValueError("extracted_at must be timezone-aware")

        return ResearchObservation(
            observation_id=(
                f"{company}:{question.question_id}:{source.source_id}"
            ),
            company=company,
            category=question.category,
            claim=claim,
            evidence_excerpt=evidence_excerpt,
            source_id=source.source_id,
            reliability_tier=source.reliability_tier,
            published_at=source.published_at,
            available_at=source.available_at,
            extracted_at=extracted_at,
            confidence=confidence,
        )
