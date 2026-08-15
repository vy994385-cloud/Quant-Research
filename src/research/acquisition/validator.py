from __future__ import annotations

from datetime import datetime

from src.research.acquisition.models import SourceCandidate


class SourceValidator:
    """
    Validates discovered source candidates before they can enter
    the evidence/extraction pipeline.

    Validation failure means UNKNOWN/REJECTED.
    It must never become negative company evidence.
    """

    def validate(
        self,
        source: SourceCandidate,
        as_of: datetime,
    ) -> bool:
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")

        if source.available_at is None:
            return False

        if (
            source.available_at.tzinfo is None
            or source.available_at.utcoffset() is None
        ):
            return False

        if source.available_at > as_of:
            return False

        if (
            source.published_at is not None
            and (
                source.published_at.tzinfo is None
                or source.published_at.utcoffset() is None
            )
        ):
            return False

        if source.published_at is not None and source.published_at > as_of:
            return False

        return True

    def validate_many(
        self,
        sources: list[SourceCandidate],
        as_of: datetime,
    ) -> list[SourceCandidate]:
        accepted: list[SourceCandidate] = []
        seen: set[str] = set()

        for source in sources:
            if source.source_id in seen:
                continue

            if self.validate(source, as_of):
                accepted.append(source)
                seen.add(source.source_id)

        return accepted
