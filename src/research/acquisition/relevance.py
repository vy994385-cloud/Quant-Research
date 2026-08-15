from __future__ import annotations

from src.research.acquisition.models import (
    ResearchQuestion,
    SourceCandidate,
)


class SourceRelevanceRouter:
    """
    Deterministic first-pass routing between research questions
    and source candidates.

    This is deliberately conservative. It does not invent relevance.
    """

    def is_relevant(
        self,
        question: ResearchQuestion,
        source: SourceCandidate,
    ) -> bool:
        question_text = (
            f"{question.question} {question.category.value}"
        ).lower()

        source_text = (
            f"{source.title} {source.source_name} "
            f"{source.source_type}"
        ).lower()

        keywords = self._keywords(question_text)

        return any(
            keyword in source_text
            for keyword in keywords
        )

    def filter(
        self,
        question: ResearchQuestion,
        sources: list[SourceCandidate],
    ) -> list[SourceCandidate]:
        seen: set[str] = set()
        result: list[SourceCandidate] = []

        for source in sources:
            if source.source_id in seen:
                continue

            if not self.is_relevant(question, source):
                continue

            seen.add(source.source_id)
            result.append(source)

        return result

    @staticmethod
    def _keywords(text: str) -> set[str]:
        keyword_groups = {
            "ai": {"ai", "artificial intelligence", "machine learning"},
            "technology": {"technology", "digital", "cloud", "software"},
            "innovation": {"innovation", "research", "development", "r&d"},
            "management": {"management", "ceo", "director", "leadership"},
            "customer": {"customer", "client", "contract", "order"},
            "financial": {
                "financial",
                "revenue",
                "profit",
                "cash",
                "debt",
            },
            "competitive": {
                "competition",
                "competitive",
                "market share",
                "competitor",
            },
        }

        matched: set[str] = set()

        for group, words in keyword_groups.items():
            if group in text:
                matched.update(words)

        if not matched:
            matched.update(
                word
                for word in text.split()
                if len(word) >= 5
            )

        return matched
