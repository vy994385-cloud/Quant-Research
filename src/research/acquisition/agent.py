from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from src.research.acquisition.extractor import ObservationExtractor
from src.research.acquisition.models import (
    ResearchObservation,
    ResearchQuestion,
    SourceCandidate,
)


@dataclass(frozen=True)
class AgentExtraction:
    """
    Raw extraction returned by an AI or deterministic research agent.

    The agent does not decide whether the source is admissible and does
    not assign investment meaning to the observation.
    """

    claim: str
    evidence_excerpt: str
    confidence: float


class ResearchAgent(ABC):
    """
    Replaceable boundary for AI-assisted research extraction.

    Implementations may use an LLM, another model, or deterministic
    extraction. The rest of the research system must not depend on the
    specific agent implementation.
    """

    @abstractmethod
    def extract(
        self,
        company: str,
        question: ResearchQuestion,
        source: SourceCandidate,
    ) -> AgentExtraction:
        raise NotImplementedError


class DeterministicResearchAgent(ResearchAgent):
    """
    Minimal reference implementation used for testing.

    This deliberately does not call an external model.
    """

    def extract(
        self,
        company: str,
        question: ResearchQuestion,
        source: SourceCandidate,
    ) -> AgentExtraction:
        return AgentExtraction(
            claim=(
                f"Source {source.source_id} contains evidence relevant "
                f"to the research question."
            ),
            evidence_excerpt=source.title,
            confidence=0.5,
        )


class AgentObservationBridge:
    """
    Converts agent output into the canonical observation model.

    The bridge keeps AI output separate from the trusted research model.
    """

    def __init__(
        self,
        agent: ResearchAgent,
        extractor: ObservationExtractor | None = None,
    ) -> None:
        self.agent = agent
        self.extractor = extractor or ObservationExtractor()

    def run(
        self,
        company: str,
        question: ResearchQuestion,
        source: SourceCandidate,
        extracted_at: datetime,
    ) -> ResearchObservation:
        result = self.agent.extract(
            company=company,
            question=question,
            source=source,
        )

        return self.extractor.extract(
            company=company,
            question=question,
            source=source,
            claim=result.claim,
            evidence_excerpt=result.evidence_excerpt,
            extracted_at=extracted_at,
            confidence=result.confidence,
        )
