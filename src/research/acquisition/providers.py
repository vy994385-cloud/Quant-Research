from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.research.acquisition.models import (
    ResearchQuestion,
    SourceCandidate,
)


class ResearchSourceProvider(ABC):
    """
    Interface for discovering source candidates.

    Implementations may use:
    - web/search APIs
    - financial-data providers
    - company IR sources
    - regulatory databases
    - an AI research agent

    Providers only discover candidates.
    They do not decide whether evidence is valid.
    """

    @abstractmethod
    def search(
        self,
        company: str,
        question: ResearchQuestion,
        as_of: datetime,
    ) -> list[SourceCandidate]:
        """
        Return source candidates relevant to a research question.

        Implementations must not return information that was unavailable
        after the requested as_of timestamp.
        """
        raise NotImplementedError
