from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EvidenceNarrative(BaseModel):
    """
    Structured interpretation of synthesized research evidence.

    This is an explanatory research layer. It does not forecast
    returns and does not produce a BUY or SELL instruction.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str = Field(min_length=1)

    thesis: str = Field(min_length=1)

    supporting_evidence: tuple[str, ...] = ()
    contradicting_evidence: tuple[str, ...] = ()

    strongest_evidence: tuple[str, ...] = ()
    uncertainty: tuple[str, ...] = ()

    key_risks: tuple[str, ...] = ()
    evidence_gaps: tuple[str, ...] = ()

    what_could_change_thesis: tuple[str, ...] = ()

    @property
    def has_conflict(self) -> bool:
        return bool(
            self.supporting_evidence
            and self.contradicting_evidence
        )


__all__ = [
    "EvidenceNarrative",
]
