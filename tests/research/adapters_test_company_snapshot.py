from datetime import date
from decimal import Decimal

import pytest

from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
    IntelligenceDirection,
    IntelligenceSignal,
)
from src.research.adapters.company_snapshot import (
    snapshot_to_research_signals,
)
from src.research.signals.models import (
    SignalDirection,
    SignalSeverity,
)


def make_snapshot() -> CompanyResearchSnapshot:
    return CompanyResearchSnapshot(
        symbol=" test ",
        as_of_date=date(2026, 8, 10),
        signals=[
            IntelligenceSignal(
                code="REVENUE_GROWTH",
                title="Revenue growth",
                description="Revenue increased.",
                direction=IntelligenceDirection.POSITIVE,
                materiality=4,
                confidence=Decimal("0.90"),
            ),
            IntelligenceSignal(
                code="CFO_RESIGNATION",
                title="CFO resignation",
                description="CFO resigned.",
                direction=IntelligenceDirection.NEGATIVE,
                materiality=5,
                confidence=Decimal("0.80"),
            ),
        ],
    )


def test_snapshot_converts_to_research_signals():
    signals = snapshot_to_research_signals(
        make_snapshot()
    )

    assert len(signals) == 2

    assert signals[0].signal_id == "REVENUE_GROWTH"
    assert signals[0].symbol == "TEST"
    assert signals[0].direction == SignalDirection.POSITIVE
    assert signals[0].severity == SignalSeverity.HIGH
    assert signals[0].confidence == Decimal("0.90")


def test_snapshot_date_becomes_timezone_aware():
    signals = snapshot_to_research_signals(
        make_snapshot()
    )

    assert signals[0].observation_at.tzinfo is not None

    assert signals[0].observation_at.isoformat() == (
        "2026-08-10T00:00:00+00:00"
    )


def test_materiality_maps_to_severity():
    snapshot = CompanyResearchSnapshot(
        symbol="TEST",
        as_of_date=date(2026, 8, 10),
        signals=[
            IntelligenceSignal(
                code="INFO",
                title="Info",
                description="Information.",
                direction=IntelligenceDirection.NEUTRAL,
                materiality=1,
                confidence=Decimal("0.50"),
            ),
            IntelligenceSignal(
                code="LOW",
                title="Low",
                description="Low importance.",
                direction=IntelligenceDirection.NEUTRAL,
                materiality=2,
                confidence=Decimal("0.50"),
            ),
            IntelligenceSignal(
                code="MEDIUM",
                title="Medium",
                description="Medium importance.",
                direction=IntelligenceDirection.NEUTRAL,
                materiality=3,
                confidence=Decimal("0.50"),
            ),
            IntelligenceSignal(
                code="HIGH",
                title="High",
                description="High importance.",
                direction=IntelligenceDirection.NEUTRAL,
                materiality=4,
                confidence=Decimal("0.50"),
            ),
            IntelligenceSignal(
                code="CRITICAL",
                title="Critical",
                description="Critical importance.",
                direction=IntelligenceDirection.NEUTRAL,
                materiality=5,
                confidence=Decimal("0.50"),
            ),
        ],
    )

    signals = snapshot_to_research_signals(snapshot)

    assert [signal.severity for signal in signals] == [
        SignalSeverity.INFO,
        SignalSeverity.LOW,
        SignalSeverity.MEDIUM,
        SignalSeverity.HIGH,
        SignalSeverity.CRITICAL,
    ]


def test_empty_snapshot_creates_no_signals():
    snapshot = CompanyResearchSnapshot(
        symbol="TEST",
        as_of_date=date(2026, 8, 10),
    )

    assert snapshot_to_research_signals(snapshot) == ()


def test_adapter_does_not_create_trade_signal():
    snapshot = make_snapshot()

    assert snapshot.is_trade_signal is False


def test_snapshot_signal_symbol_is_normalized():
    signals = snapshot_to_research_signals(
        make_snapshot()
    )

    assert all(
        signal.symbol == "TEST"
        for signal in signals
    )
