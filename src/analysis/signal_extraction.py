from decimal import Decimal

from src.analysis.company_intelligence import (
    EvidenceReference,
    IntelligenceDirection,
    IntelligenceSignal,
)
from src.data.company.events import CompanyEvent
from src.data.company.financials import FinancialSnapshot
from src.data.company.management import ManagementChange
from src.data.company.ownership import OwnershipSnapshot
from src.data.company.related_parties import RelatedPartyTransaction


def financial_signals(
    snapshot: FinancialSnapshot,
) -> list[IntelligenceSignal]:
    signals: list[IntelligenceSignal] = []

    if snapshot.profit_cash_flow_divergence:
        signals.append(
            IntelligenceSignal(
                code="PROFIT_CASH_FLOW_DIVERGENCE",
                title="Profit and operating cash flow divergence",
                description=(
                    "Net profit is positive while operating cash "
                    "flow is negative for the reporting period."
                ),
                direction=IntelligenceDirection.NEGATIVE,
                materiality=4,
                confidence=Decimal("0.95"),
            )
        )

    return signals


def management_signals(
    change: ManagementChange,
) -> list[IntelligenceSignal]:
    direction = IntelligenceDirection.NEUTRAL

    if change.change_type.upper() in {
        "RESIGNATION",
        "REMOVAL",
    }:
        direction = IntelligenceDirection.NEGATIVE

    return [
        IntelligenceSignal(
            code=f"MANAGEMENT_{change.change_type.upper()}",
            title=f"Management {change.change_type.lower()}",
            description=(
                f"{change.person_name} experienced a management "
                f"change involving the role of {change.role}."
            ),
            direction=direction,
            materiality=4,
            confidence=Decimal("0.90"),
        )
    ]


def ownership_signals(
    snapshot: OwnershipSnapshot,
) -> list[IntelligenceSignal]:
    signals: list[IntelligenceSignal] = []

    if (
        snapshot.promoter_percentage is not None
        and snapshot.promoter_percentage < Decimal("25")
    ):
        signals.append(
            IntelligenceSignal(
                code="LOW_PROMOTER_OWNERSHIP",
                title="Low promoter ownership",
                description=(
                    "Promoter ownership is below the configured "
                    "screening threshold of 25%."
                ),
                direction=IntelligenceDirection.NEUTRAL,
                materiality=2,
                confidence=Decimal("0.95"),
            )
        )

    return signals


def related_party_signals(
    transaction: RelatedPartyTransaction,
) -> list[IntelligenceSignal]:
    return [
        IntelligenceSignal(
            code="RELATED_PARTY_TRANSACTION",
            title="Related-party transaction",
            description=(
                f"A {transaction.transaction_type.lower()} transaction "
                f"with related party {transaction.related_party_name} "
                f"was recorded for the reporting period."
            ),
            direction=IntelligenceDirection.NEUTRAL,
            materiality=3,
            confidence=Decimal("0.90"),
        )
    ]


def event_signal(
    event: CompanyEvent,
) -> IntelligenceSignal:
    try:
        direction = IntelligenceDirection(event.direction.upper())
    except ValueError:
        direction = IntelligenceDirection.NEUTRAL

    return IntelligenceSignal(
        code=f"EVENT_{event.category.upper()}",
        title=event.title,
        description=event.description,
        direction=direction,
        materiality=event.materiality,
        confidence=Decimal("0.90"),
    )


def attach_evidence(
    signal: IntelligenceSignal,
    evidence: EvidenceReference,
) -> IntelligenceSignal:
    return signal.model_copy(
        update={
            "evidence": [
                *signal.evidence,
                evidence,
            ]
        }
    )
