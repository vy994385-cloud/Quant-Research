"""
Semantic vocabulary for company intelligence.

The vocabulary describes evidence, not opinions. None of these
categories express an investment recommendation, a score, or a
prediction of future returns.
"""

from __future__ import annotations

from enum import Enum


class SemanticCategory(str, Enum):
    """
    How a piece of intelligence should be interpreted.

    - FACT:               established, verified factual information.
    - DERIVED_METRIC:     a metric computed from reported numbers.
    - OBSERVATION:        an analyst framing of available facts.
    - MANAGEMENT_COMMENTARY: statements made by company management.
    - REPORTED_CLAIM:     a claim carried by a secondary source.
    - ALLEGATION:         an unproven claim of wrongdoing.
    - CONCLUSION:         a synthesis statement drawn from evidence.

    A claim is never silently upgraded to a fact.
    """

    FACT = "FACT"
    DERIVED_METRIC = "DERIVED_METRIC"
    OBSERVATION = "OBSERVATION"
    MANAGEMENT_COMMENTARY = "MANAGEMENT_COMMENTARY"
    REPORTED_CLAIM = "REPORTED_CLAIM"
    ALLEGATION = "ALLEGATION"
    CONCLUSION = "CONCLUSION"


class VerificationStatus(str, Enum):
    """
    How strongly a piece of intelligence is verified.

    - CONFIRMED:    verified against primary / regulatory / audited sources.
    - REPORTED:     carried by a credible secondary source, not yet verified.
    - ALLEGED:      claimed but unproven (e.g. an allegation).
    - UNVERIFIED:   present in the feed but not verified.
    - CONTRADICTED: contradicted by other evidence.
    - RESOLVED:     previously open concern that has since been resolved.
    """

    CONFIRMED = "CONFIRMED"
    REPORTED = "REPORTED"
    ALLEGED = "ALLEGED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTED = "CONTRADICTED"
    RESOLVED = "RESOLVED"


class ChangeType(str, Enum):
    """
    Classification of a change between two intelligence snapshots.

    - NEW:         the item did not exist before.
    - UPDATED:     the item changed (content or metadata changed).
    - UNCHANGED:   the item is byte-identical.
    - RESOLVED:    the item moved to RESOLVED status.
    - CONFLICTING: the item moved to CONTRADICTED status.
    """

    NEW = "NEW"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"
    RESOLVED = "RESOLVED"
    CONFLICTING = "CONFLICTING"


class IntelKind(str, Enum):
    """
    Functional kind of a piece of company intelligence.

    - BUSINESS_EVENT:        a discrete corporate event.
    - MANAGEMENT_COMMENTARY: management statements.
    - RISK_DEVELOPMENT:      a risk-related development.
    - INDIRECT_INTELLIGENCE: outside-in industry / macro / counterparty info.
    - FINANCIAL_PERIOD:      a financial reporting period or derived metric.
    - OTHER:                 anything else that is still evidence-based.
    """

    BUSINESS_EVENT = "BUSINESS_EVENT"
    MANAGEMENT_COMMENTARY = "MANAGEMENT_COMMENTARY"
    RISK_DEVELOPMENT = "RISK_DEVELOPMENT"
    INDIRECT_INTELLIGENCE = "INDIRECT_INTELLIGENCE"
    FINANCIAL_PERIOD = "FINANCIAL_PERIOD"
    OTHER = "OTHER"


class IntelCategory(str, Enum):
    """
    High-level category of a piece of company intelligence.

    Categories describe where the information comes from, not its
    investment meaning. They let coverage tracking distinguish, for
    example, a credit-rating action from a legal proceeding even when
    both are regulatory in nature.

    - FINANCIAL_DISCLOSURE:      regulated financial disclosures and
      figures derived deterministically from them.
    - BUSINESS_NEWS:             discrete business events and
      developments without a more specific category.
    - MANAGEMENT_STATEMENT:      statements made by company management.
    - CORPORATE_ACTION:          dividends, buybacks, board meetings,
      shareholder meetings, and other shareholder / board actions.
    - REGULATORY_LEGAL:          regulatory and compliance matters and
      legal proceedings.
    - EXECUTIVE_CHANGE:          appointments, resignations, and other
      changes in management or board roles.
    - ORDER_CONTRACT:            contract wins, losses, renewals, and
      order-intake developments.
    - ACQUISITION_DIVESTMENT:    acquisitions, divestments, stake
      purchases and sales, and corporate restructuring.
    - CAPEX_EXPANSION:           capital expenditure, capacity
      expansion, and investment in fixed assets.
    - PRODUCT_BUSINESS_UPDATE:   product launches, partnerships,
      services launches, and operational business updates.
    - SUBSIDIARY_UPDATE:         subsidiary incorporation, winding-up,
      and subsidiary-level developments.
    - SEGMENT_UPDATE:            reporting-segment performance and
      segment-level disclosures.
    - OWNERSHIP_DISCLOSURE:      shareholding-pattern and ownership
      disclosures including pledges.
    - INSIDER_ACTIVITY:          trades and activity by insiders,
      promoters, and connected persons.
    - CONFERENCE_CALL:           earnings calls, investor meets, and
      analyst calls.
    - INVESTOR_PRESENTATION:     investor presentations, annual
      reports, and other company-issued research materials.
    - CREDIT_RATING_ACTION:      credit-rating assignments, changes,
      and outlook actions by rating agencies.
    - LEGAL_PROCEEDING:          litigation, regulatory proceedings,
      orders, and penalties.
    - FORECAST_GUIDANCE:         management forecasts, guidance, and
      outlook statements.
    - OTHER:                     anything else that is still
      evidence-based.
    """

    FINANCIAL_DISCLOSURE = "FINANCIAL_DISCLOSURE"
    BUSINESS_NEWS = "BUSINESS_NEWS"
    MANAGEMENT_STATEMENT = "MANAGEMENT_STATEMENT"
    CORPORATE_ACTION = "CORPORATE_ACTION"
    REGULATORY_LEGAL = "REGULATORY_LEGAL"
    EXECUTIVE_CHANGE = "EXECUTIVE_CHANGE"
    ORDER_CONTRACT = "ORDER_CONTRACT"
    ACQUISITION_DIVESTMENT = "ACQUISITION_DIVESTMENT"
    CAPEX_EXPANSION = "CAPEX_EXPANSION"
    PRODUCT_BUSINESS_UPDATE = "PRODUCT_BUSINESS_UPDATE"
    SUBSIDIARY_UPDATE = "SUBSIDIARY_UPDATE"
    SEGMENT_UPDATE = "SEGMENT_UPDATE"
    OWNERSHIP_DISCLOSURE = "OWNERSHIP_DISCLOSURE"
    INSIDER_ACTIVITY = "INSIDER_ACTIVITY"
    CONFERENCE_CALL = "CONFERENCE_CALL"
    INVESTOR_PRESENTATION = "INVESTOR_PRESENTATION"
    CREDIT_RATING_ACTION = "CREDIT_RATING_ACTION"
    LEGAL_PROCEEDING = "LEGAL_PROCEEDING"
    FORECAST_GUIDANCE = "FORECAST_GUIDANCE"
    OTHER = "OTHER"


class IntelDirection(str, Enum):
    """
    Directional coloring of an item.

    This describes the nature of the information (e.g. a cost increase),
    not a recommendation and not an expected return.

    - POSITIVE: the information is favorable to the company's operations.
    - NEGATIVE: the information is adverse to the company's operations.
    - NEUTRAL:  the information is neutral.
    - UNKNOWN:  direction is not known or not applicable.
    """

    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class EvidenceStance(str, Enum):
    """
    Whether an item supports or challenges a topic.

    - SUPPORTIVE: supports the topic thesis.
    - CONTRARY:   challenges / contradicts the topic thesis.
    - NEUTRAL:    neither clearly supportive nor contrary.
    """

    SUPPORTIVE = "SUPPORTIVE"
    CONTRARY = "CONTRARY"
    NEUTRAL = "NEUTRAL"


class EvidenceRelationship(str, Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    RELATED = "RELATED"


class BusinessEventType(str, Enum):
    BOARD_MEETING = "BOARD_MEETING"
    EARNINGS = "EARNINGS"
    DIVIDEND = "DIVIDEND"
    BUYBACK = "BUYBACK"
    MERGER_ACQUISITION = "MERGER_ACQUISITION"
    PARTNERSHIP = "PARTNERSHIP"
    PRODUCT_LAUNCH = "PRODUCT_LAUNCH"
    REGULATORY = "REGULATORY"
    CREDIT_ACTION = "CREDIT_ACTION"
    MANAGEMENT_CHANGE = "MANAGEMENT_CHANGE"
    SHAREHOLDER_MEETING = "SHAREHOLDER_MEETING"
    CONTRACT_WIN = "CONTRACT_WIN"
    CONTRACT_LOSS = "CONTRACT_LOSS"
    FORECAST = "FORECAST"
    OTHER = "OTHER"


class ReportingPeriodType(str, Enum):
    QUARTERLY = "QUARTERLY"
    SEMI_ANNUAL = "SEMI_ANNUAL"
    ANNUAL = "ANNUAL"
    UNKNOWN = "UNKNOWN"


class ConsolidationScope(str, Enum):
    CONSOLIDATED = "CONSOLIDATED"
    STANDALONE = "STANDALONE"
    UNKNOWN = "UNKNOWN"


class FinancialStatementType(str, Enum):
    INCOME_STATEMENT = "INCOME_STATEMENT"
    BALANCE_SHEET = "BALANCE_SHEET"
    CASH_FLOW_STATEMENT = "CASH_FLOW_STATEMENT"
    OTHER = "OTHER"


class FinancialObservationType(str, Enum):
    """
    How a deep financial observation was produced.

    - REPORTED:    the value is disclosed / reported by the company.
    - DERIVED:     the value is computed deterministically from
      reported figures (the derivation records the exact formula).
    - UNAVAILABLE: the figure was expected for the period but is not
      present in the recorded evidence.
    """

    REPORTED = "REPORTED"
    DERIVED = "DERIVED"
    UNAVAILABLE = "UNAVAILABLE"


_INSUFFICIENT_EVIDENCE = "Insufficient evidence for a firm conclusion."


class ConclusionGateResult:
    """
    Result of evaluating whether a conclusion is supported.

    Never forces a conclusion: when the gate fails, `reason` holds
    a clear statement that the evidence is insufficient.
    """

    __slots__ = ("_supported", "reason")

    def __init__(self, supported: bool, reason: str = ""):
        self._supported = supported
        self.reason = reason

    @classmethod
    def supported_result(cls) -> "ConclusionGateResult":
        return cls(True)

    @classmethod
    def insufficient_result(cls) -> "ConclusionGateResult":
        return cls(False, _INSUFFICIENT_EVIDENCE)

    def __bool__(self) -> bool:
        return self._supported

    @property
    def supported(self) -> bool:
        return self._supported

    def __repr__(self) -> str:
        return (
            f"ConclusionGateResult(supported={self.supported}, "
            f"reason={self.reason!r})"
        )


def insufficient_evidence_message() -> str:
    """Canonical message for unsupported conclusions."""
    return _INSUFFICIENT_EVIDENCE


def default_intel_category(
    kind: IntelKind,
    event_type: BusinessEventType | None,
) -> IntelCategory:
    """
    Deterministic default category for an item without an explicit one.

    The classifier uses only the item kind and event type. It never
    invents facts, opinions, or investment meaning.
    """

    if kind == IntelKind.MANAGEMENT_COMMENTARY:
        return IntelCategory.MANAGEMENT_STATEMENT

    if kind == IntelKind.FINANCIAL_PERIOD:
        return IntelCategory.FINANCIAL_DISCLOSURE

    if kind == IntelKind.INDIRECT_INTELLIGENCE:
        return IntelCategory.BUSINESS_NEWS

    if event_type == BusinessEventType.EARNINGS:
        return IntelCategory.FINANCIAL_DISCLOSURE

    if event_type == BusinessEventType.REGULATORY:
        return IntelCategory.REGULATORY_LEGAL

    if event_type == BusinessEventType.CREDIT_ACTION:
        return IntelCategory.CREDIT_RATING_ACTION

    if event_type == BusinessEventType.MERGER_ACQUISITION:
        return IntelCategory.ACQUISITION_DIVESTMENT

    if event_type == BusinessEventType.MANAGEMENT_CHANGE:
        return IntelCategory.EXECUTIVE_CHANGE

    if event_type in {
        BusinessEventType.DIVIDEND,
        BusinessEventType.BUYBACK,
        BusinessEventType.BOARD_MEETING,
        BusinessEventType.SHAREHOLDER_MEETING,
    }:
        return IntelCategory.CORPORATE_ACTION

    if event_type in {
        BusinessEventType.CONTRACT_WIN,
        BusinessEventType.CONTRACT_LOSS,
    }:
        return IntelCategory.ORDER_CONTRACT

    if event_type in {
        BusinessEventType.PARTNERSHIP,
        BusinessEventType.PRODUCT_LAUNCH,
    }:
        return IntelCategory.PRODUCT_BUSINESS_UPDATE

    if event_type == BusinessEventType.FORECAST:
        return IntelCategory.FORECAST_GUIDANCE

    if kind in {
        IntelKind.BUSINESS_EVENT,
        IntelKind.RISK_DEVELOPMENT,
    }:
        return IntelCategory.BUSINESS_NEWS

    return IntelCategory.OTHER


__all__ = [
    "BusinessEventType",
    "ChangeType",
    "ConclusionGateResult",
    "ConsolidationScope",
    "EvidenceRelationship",
    "EvidenceStance",
    "FinancialObservationType",
    "FinancialStatementType",
    "IntelCategory",
    "IntelDirection",
    "IntelKind",
    "ReportingPeriodType",
    "SemanticCategory",
    "VerificationStatus",
    "default_intel_category",
    "insufficient_evidence_message",
]
