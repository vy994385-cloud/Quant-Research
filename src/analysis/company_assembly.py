from datetime import date

from src.analysis.company_intelligence import (
    CompanyResearchSnapshot,
    EvidenceReference,
    IntelligenceSignal,
    build_company_research_snapshot,
)
from src.analysis.signal_extraction import (
    event_signal,
    financial_signals,
    management_signals,
    ownership_signals,
    related_party_signals,
)
from src.data.company.events import CompanyEvent
from src.data.company.financials import FinancialSnapshot
from src.data.company.management import ManagementChange
from src.data.company.ownership import OwnershipSnapshot
from src.data.company.related_parties import RelatedPartyTransaction


def _deduplicate_signals(
    signals: list[IntelligenceSignal],
) -> list[IntelligenceSignal]:
    """
    Remove exact duplicate signal observations.

    Signals with the same code remain separate only when their
    descriptions differ, because those may represent separate
    underlying events.
    """

    result: list[IntelligenceSignal] = []
    seen: set[tuple[str, str]] = set()

    for signal in signals:
        key = (
            signal.code,
            signal.description,
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(signal)

    return result


def assemble_company_intelligence(
    *,
    symbol: str,
    as_of_date: date,
    company_name: str | None = None,
    financial_snapshots: list[FinancialSnapshot] | None = None,
    management_changes: list[ManagementChange] | None = None,
    ownership_snapshots: list[OwnershipSnapshot] | None = None,
    related_party_transactions: list[
        RelatedPartyTransaction
    ] | None = None,
    company_events: list[CompanyEvent] | None = None,
    evidence: list[EvidenceReference] | None = None,
) -> CompanyResearchSnapshot:
    """
    Assemble all currently supported company-intelligence
    observations into one normalized research snapshot.

    This function is descriptive only.

    It does not:
    - produce BUY/SELL recommendations
    - predict returns
    - label a company fraudulent
    - invent missing information
    """

    signals: list[IntelligenceSignal] = []

    financial_observations: list[str] = []
    ownership_observations: list[str] = []
    management_observations: list[str] = []
    related_party_observations: list[str] = []
    event_observations: list[str] = []

    for snapshot in financial_snapshots or []:
        extracted = financial_signals(snapshot)
        signals.extend(extracted)

        if snapshot.revenue is not None:
            financial_observations.append(
                f"Revenue reported: {snapshot.revenue}"
            )

        if snapshot.net_profit is not None:
            financial_observations.append(
                f"Net profit reported: {snapshot.net_profit}"
            )

        if snapshot.operating_cash_flow is not None:
            financial_observations.append(
                "Operating cash flow reported: "
                f"{snapshot.operating_cash_flow}"
            )

    for change in management_changes or []:
        extracted = management_signals(change)
        signals.extend(extracted)

        management_observations.append(
            f"{change.change_type}: "
            f"{change.person_name} — {change.role}"
        )

    for ownership in ownership_snapshots or []:
        extracted = ownership_signals(ownership)
        signals.extend(extracted)

        if ownership.promoter_percentage is not None:
            ownership_observations.append(
                "Promoter ownership: "
                f"{ownership.promoter_percentage}%"
            )

        if ownership.institutional_percentage is not None:
            ownership_observations.append(
                "Institutional ownership: "
                f"{ownership.institutional_percentage}%"
            )

        if ownership.public_percentage is not None:
            ownership_observations.append(
                "Public ownership: "
                f"{ownership.public_percentage}%"
            )

    for transaction in related_party_transactions or []:
        extracted = related_party_signals(transaction)
        signals.extend(extracted)

        related_party_observations.append(
            f"{transaction.transaction_type}: "
            f"{transaction.related_party_name} — "
            f"{transaction.amount}"
        )

    for event in company_events or []:
        signal = event_signal(event)
        signals.append(signal)

        event_observations.append(
            f"{event.category}: {event.title}"
        )

    signals = _deduplicate_signals(signals)

    return build_company_research_snapshot(
        symbol=symbol,
        company_name=company_name,
        as_of_date=as_of_date,
        signals=signals,
        financial_observations=financial_observations,
        ownership_observations=ownership_observations,
        management_observations=management_observations,
        related_party_observations=related_party_observations,
        event_observations=event_observations,
        evidence=evidence,
    )
