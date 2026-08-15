from datetime import datetime, timezone

from src.research.acquisition.agent import (
    AgentExtraction,
    AgentObservationBridge,
    DeterministicResearchAgent,
)
from src.research.acquisition.models import (
    ResearchCategory,
    ResearchQuestion,
    SourceCandidate,
)


AS_OF = datetime(
    2026,
    8,
    15,
    12,
    tzinfo=timezone.utc,
)


def make_question() -> ResearchQuestion:
    return ResearchQuestion(
        question_id="ai-technology",
        category=ResearchCategory.AI_TECHNOLOGY,
        question="What evidence exists of AI adoption?",
        priority=1,
    )


def make_source() -> SourceCandidate:
    return SourceCandidate(
        source_id="source-1",
        source_name="Example Source",
        source_type="REGULATORY",
        url="https://example.com/source-1",
        title="Example filing",
        available_at=datetime(
            2026,
            8,
            10,
            12,
            tzinfo=timezone.utc,
        ),
        reliability_tier=1,
    )


def test_deterministic_agent_returns_structured_extraction():
    agent = DeterministicResearchAgent()

    result = agent.extract(
        company="TCS",
        question=make_question(),
        source=make_source(),
    )

    assert isinstance(result, AgentExtraction)
    assert result.claim
    assert result.evidence_excerpt
    assert 0.0 <= result.confidence <= 1.0


def test_agent_bridge_creates_canonical_observation():
    bridge = AgentObservationBridge(
        agent=DeterministicResearchAgent()
    )

    observation = bridge.run(
        company="TCS",
        question=make_question(),
        source=make_source(),
        extracted_at=AS_OF,
    )

    assert observation.company == "TCS"
    assert observation.source_id == "source-1"
    assert observation.category == ResearchCategory.AI_TECHNOLOGY
    assert observation.available_at == make_source().available_at


def test_agent_bridge_preserves_point_in_time_metadata():
    bridge = AgentObservationBridge(
        agent=DeterministicResearchAgent()
    )

    observation = bridge.run(
        company="TCS",
        question=make_question(),
        source=make_source(),
        extracted_at=AS_OF,
    )

    assert observation.is_known_at(AS_OF)
    assert not observation.is_known_at(
        datetime(
            2026,
            8,
            9,
            12,
            tzinfo=timezone.utc,
        )
    )
