from datetime import date
from decimal import Decimal

from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
    EvidenceReference,
    IntelligenceDirection,
    IntelligenceSignal,
    build_company_research_snapshot,
)


def make_signal(
    code,
    direction,
    materiality=3,
):
    return IntelligenceSignal(
        code=code,
        title=code,
        description="Research observation.",
        direction=direction,
        materiality=materiality,
        confidence=Decimal("0.80"),
    )


def test_empty_company_snapshot_is_neutral():

    snapshot = build_company_research_snapshot(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
    )

    assert snapshot.symbol == "TEST"
    assert snapshot.direction == IntelligenceDirection.NEUTRAL
    assert snapshot.signal_count == 0
    assert snapshot.material_signal_count == 0
    assert not snapshot.is_mixed
    assert snapshot.is_trade_signal is False


def test_positive_signals_produce_positive_direction():

    snapshot = build_company_research_snapshot(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        signals=[
            make_signal(
                "PROFIT_GROWTH",
                IntelligenceDirection.POSITIVE,
            ),
            make_signal(
                "CASH_FLOW",
                IntelligenceDirection.POSITIVE,
            ),
        ],
    )

    assert snapshot.direction == IntelligenceDirection.POSITIVE
    assert snapshot.positive_signal_count == 2
    assert snapshot.negative_signal_count == 0


def test_negative_signals_produce_negative_direction():

    snapshot = build_company_research_snapshot(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        signals=[
            make_signal(
                "DEBT_RISE",
                IntelligenceDirection.NEGATIVE,
            ),
            make_signal(
                "RECEIVABLES_ANOMALY",
                IntelligenceDirection.NEGATIVE,
            ),
        ],
    )

    assert snapshot.direction == IntelligenceDirection.NEGATIVE
    assert snapshot.negative_signal_count == 2


def test_positive_and_negative_signals_produce_mixed():

    snapshot = build_company_research_snapshot(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        signals=[
            make_signal(
                "REVENUE_GROWTH",
                IntelligenceDirection.POSITIVE,
            ),
            make_signal(
                "DEBT_RISE",
                IntelligenceDirection.NEGATIVE,
            ),
        ],
    )

    assert snapshot.direction == IntelligenceDirection.MIXED
    assert snapshot.is_mixed


def test_material_signals_are_counted():

    snapshot = build_company_research_snapshot(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        signals=[
            make_signal(
                "MINOR_EVENT",
                IntelligenceDirection.NEUTRAL,
                materiality=2,
            ),
            make_signal(
                "MAJOR_EVENT",
                IntelligenceDirection.NEGATIVE,
                materiality=5,
            ),
            make_signal(
                "IMPORTANT_EVENT",
                IntelligenceDirection.POSITIVE,
                materiality=4,
            ),
        ],
    )

    assert snapshot.signal_count == 3
    assert snapshot.material_signal_count == 2


def test_evidence_is_preserved():

    evidence = EvidenceReference(
        source_name="Example Exchange",
        source_type="REGULATORY",
        title="Corporate announcement",
        published_date=date(2026, 8, 7),
        reliability_tier=1,
        reference="example-ref",
    )

    signal = IntelligenceSignal(
        code="MANAGEMENT_CHANGE",
        title="Management change",
        description="Senior management changed.",
        direction=IntelligenceDirection.NEUTRAL,
        materiality=4,
        confidence=Decimal("0.95"),
        evidence=[evidence],
    )

    snapshot = build_company_research_snapshot(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        signals=[signal],
        evidence=[evidence],
    )

    assert len(snapshot.evidence) == 1
    assert len(snapshot.signals[0].evidence) == 1
    assert snapshot.signals[0].evidence[0].reliability_tier == 1


def test_company_observation_categories_are_preserved():

    snapshot = build_company_research_snapshot(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        financial_observations=[
            "Operating cash flow improved."
        ],
        ownership_observations=[
            "Institutional ownership increased."
        ],
        management_observations=[
            "New CFO appointed."
        ],
        related_party_observations=[
            "Related-party transaction detected."
        ],
        event_observations=[
            "Major corporate event recorded."
        ],
        market_observations=[
            "Unusual volume detected."
        ],
        risk_observations=[
            "Receivables require review."
        ],
    )

    assert len(snapshot.financial_observations) == 1
    assert len(snapshot.ownership_observations) == 1
    assert len(snapshot.management_observations) == 1
    assert len(snapshot.related_party_observations) == 1
    assert len(snapshot.event_observations) == 1
    assert len(snapshot.market_observations) == 1
    assert len(snapshot.risk_observations) == 1


def test_neutral_signals_do_not_create_direction():

    snapshot = build_company_research_snapshot(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
        signals=[
            make_signal(
                "MANAGEMENT_CHANGE",
                IntelligenceDirection.NEUTRAL,
            ),
        ],
    )

    assert snapshot.direction == IntelligenceDirection.NEUTRAL


def test_snapshot_is_not_a_trade_signal():

    snapshot = CompanyResearchSnapshot(
        symbol="TEST",
        as_of_date=date(2026, 8, 8),
    )

    assert snapshot.is_trade_signal is False
