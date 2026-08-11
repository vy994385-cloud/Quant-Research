from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.research.report.models import (
    ResearchConclusion,
    ResearchEvidence,
    ResearchReport,
)


AS_OF = datetime(
    2026,
    8,
    10,
    12,
    0,
    tzinfo=timezone.utc,
)


def test_report_normalizes_symbol():
    report = ResearchReport(
        symbol=" test ",
        as_of=AS_OF,
        conclusion=ResearchConclusion.NEUTRAL,
        confidence=Decimal("0.8"),
        thesis="Evidence is currently balanced.",
    )

    assert report.symbol == "TEST"


def test_report_requires_timezone():
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        ResearchReport(
            symbol="TEST",
            as_of=datetime(2026, 8, 10, 12, 0),
            conclusion=ResearchConclusion.NEUTRAL,
            confidence=Decimal("0.8"),
            thesis="Test.",
        )


def test_evidence_requires_timezone():
    with pytest.raises(
        ValueError,
        match="timezone-aware",
    ):
        ResearchEvidence(
            evidence_id="TEST",
            title="Test",
            explanation="Test evidence.",
            symbol="TEST",
            observation_at=datetime(2026, 8, 10, 12, 0),
            confidence=Decimal("0.8"),
        )
