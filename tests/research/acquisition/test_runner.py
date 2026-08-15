from datetime import datetime, timezone

from src.research.acquisition.agent import DeterministicResearchAgent
from src.research.acquisition.models import (
    ResearchCategory,
    ResearchQuestion,
    SourceCandidate,
)
from src.research.acquisition.planner import ResearchPlanner
from src.research.acquisition.providers import ResearchSourceProvider
from src.research.acquisition.runner import ResearchAcquisitionRunner
from src.research.acquisition.validator import SourceValidator


AS_OF = datetime(
    2026,
    8,
    15,
    12,
    tzinfo=timezone.utc,
)

RELEVANT_TITLE = (
    "AI technology innovation digital transformation "
    "products revenue customer leadership competitive "
    "industry partnerships business financial"
)


def make_source(
    source_id: str,
    *,
    title: str = RELEVANT_TITLE,
    source_type: str = "REGULATORY",
    available_at: datetime = datetime(
        2026,
        8,
        10,
        12,
        tzinfo=timezone.utc,
    ),
) -> SourceCandidate:
    return SourceCandidate(
        source_id=source_id,
        source_name="Example Source",
        source_type=source_type,
        url=f"https://example.com/{source_id}",
        title=title,
        available_at=available_at,
        reliability_tier=1,
    )


class ExampleProvider(ResearchSourceProvider):
    def search(self, company, question, as_of):
        return [
            make_source(
                f"{question.question_id}-source",
            )
        ]


class FutureProvider(ResearchSourceProvider):
    def search(self, company, question, as_of):
        return [
            make_source(
                f"{question.question_id}-future",
                available_at=datetime(
                    2026,
                    8,
                    20,
                    12,
                    tzinfo=timezone.utc,
                ),
            )
        ]


class MixedRelevanceProvider(ResearchSourceProvider):
    """
    Returns one relevant and one unrelated source for every question.
    """

    def search(self, company, question, as_of):
        return [
            make_source(
                f"{question.question_id}-relevant",
            ),
            make_source(
                f"{question.question_id}-unrelated",
                title="Historical dividend announcement",
                source_type="NEWS",
            ),
        ]


def make_runner(providers):
    return ResearchAcquisitionRunner(
        planner=ResearchPlanner(),
        providers=providers,
        validator=SourceValidator(),
        agent=DeterministicResearchAgent(),
    )


def test_runner_discovers_and_extracts_research():
    result = make_runner(
        [ExampleProvider()]
    ).run(
        company="TCS",
        as_of=AS_OF,
        extracted_at=AS_OF,
    )

    assert result.company == "TCS"
    assert result.questions_count > 0
    assert result.sources_discovered > 0
    assert result.sources_accepted > 0
    assert result.observations_created > 0
    assert len(result.observations) == result.observations_created


def test_runner_rejects_future_sources():
    result = make_runner(
        [FutureProvider()]
    ).run(
        company="TCS",
        as_of=AS_OF,
        extracted_at=AS_OF,
    )

    assert result.sources_discovered > 0
    assert result.sources_accepted == 0
    assert result.observations_created == 0
    assert result.observations == []


def test_runner_only_extracts_observations_for_relevant_sources():
    result = make_runner(
        [MixedRelevanceProvider()]
    ).run(
        company="TCS",
        as_of=AS_OF,
        extracted_at=AS_OF,
    )

    observation_source_ids = {
        observation.source_id
        for observation in result.observations
    }

    assert "ai-technology-relevant" in observation_source_ids
    assert "ai-technology-unrelated" not in observation_source_ids

    assert all(
        source.source_id.endswith("-relevant")
        for source in result.observations
    )


class DuplicateQuestionPlanner(ResearchPlanner):
    """
    Returns the same question twice to force colliding observation ids.
    """

    def plan(self, company, as_of):
        question = ResearchQuestion(
            question_id="duplicate",
            category=ResearchCategory.AI_TECHNOLOGY,
            question="What AI evidence exists?",
            priority=1,
        )

        return [question, question]


def test_runner_deduplicates_colliding_observation_ids():
    runner = ResearchAcquisitionRunner(
        planner=DuplicateQuestionPlanner(),
        providers=[ExampleProvider()],
        validator=SourceValidator(),
        agent=DeterministicResearchAgent(),
    )

    result = runner.run(
        company="TCS",
        as_of=AS_OF,
        extracted_at=AS_OF,
    )

    observation_ids = [
        observation.observation_id
        for observation in result.observations
    ]

    assert len(observation_ids) == len(set(observation_ids))
    assert len(result.observations) == 1
