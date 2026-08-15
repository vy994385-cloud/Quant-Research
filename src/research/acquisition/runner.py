from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.research.acquisition.agent import (
    AgentObservationBridge,
    ResearchAgent,
)
from src.research.acquisition.models import (
    ResearchObservation,
    SourceCandidate,
)
from src.research.acquisition.planner import ResearchPlanner
from src.research.acquisition.providers import ResearchSourceProvider
from src.research.acquisition.relevance import SourceRelevanceRouter
from src.research.acquisition.validator import SourceValidator


@dataclass(frozen=True)
class AcquisitionResult:
    company: str
    as_of: datetime
    questions_count: int
    sources_discovered: int
    sources_accepted: int
    observations_created: int
    observations: list[ResearchObservation]
    sources: list[SourceCandidate]


class ResearchAcquisitionRunner:
    """
    Coordinates research acquisition without making investment
    conclusions.

    All source admissibility remains controlled by SourceValidator.
    """

    def __init__(
        self,
        planner: ResearchPlanner,
        providers: list[ResearchSourceProvider],
        validator: SourceValidator,
        agent: ResearchAgent,
        relevance: SourceRelevanceRouter | None = None,
    ) -> None:
        self.planner = planner
        self.providers = providers
        self.validator = validator
        self.bridge = AgentObservationBridge(agent)
        self.relevance = relevance or SourceRelevanceRouter()

    def run(
        self,
        company: str,
        as_of: datetime,
        extracted_at: datetime,
    ) -> AcquisitionResult:
        questions = self.planner.plan(
            company,
            as_of,
        )

        discovered: list[SourceCandidate] = []

        for question in questions:
            for provider in self.providers:
                discovered.extend(
                    provider.search(
                        company,
                        question,
                        as_of,
                    )
                )

        accepted = self.validator.validate_many(
            discovered,
            as_of,
        )

        observations: list[ResearchObservation] = []
        seen_observation_ids: set[str] = set()

        for question in questions:
            question_sources = self.relevance.filter(
                question,
                accepted,
            )

            for source in question_sources:
                observation = self.bridge.run(
                    company=company,
                    question=question,
                    source=source,
                    extracted_at=extracted_at,
                )

                if observation.observation_id in seen_observation_ids:
                    continue

                seen_observation_ids.add(
                    observation.observation_id
                )
                observations.append(observation)

        return AcquisitionResult(
            company=company,
            as_of=as_of,
            questions_count=len(questions),
            sources_discovered=len(discovered),
            sources_accepted=len(accepted),
            observations_created=len(observations),
            observations=observations,
            sources=accepted,
        )
