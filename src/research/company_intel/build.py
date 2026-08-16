"""
Deterministic builders for company intelligence.

Every function here is point-in-time aware: any input that could not
be known at `as_of` is excluded. Output ordering is deterministic.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from typing import Sequence

from src.data.company.financials import FinancialSnapshot
from src.research.acquisition.models import ResearchCategory, ResearchObservation
from src.research.company_intel.evidence import (
    build_evidence_links,
    conclusion_gate,
    detect_evidence_conflicts,
)
from src.research.company_intel.change import detect_changes
from src.research.company_intel.models import (
    CompanyIntelligenceSnapshot,
    CorporateIntelItem,
    FinancialIntelligence,
    FinancialPeriod,
    FinancialStatement,
    SourceRef,
)
from src.research.company_intel.semantics import (
    BusinessEventType,
    ConsolidationScope,
    FinancialStatementType,
    IntelDirection,
    IntelKind,
    ReportingPeriodType,
    SemanticCategory,
    VerificationStatus,
)

_METRIC_FIELDS = (
    "revenue",
    "operating_profit",
    "net_profit",
    "operating_cash_flow",
    "free_cash_flow",
    "total_assets",
    "total_debt",
    "cash_and_equivalents",
    "receivables",
    "payables",
)

_INCOME_FIELDS = ("revenue", "operating_profit", "net_profit")
_CASH_FIELDS = ("operating_cash_flow", "free_cash_flow")
_BALANCE_FIELDS = (
    "total_assets",
    "total_debt",
    "cash_and_equivalents",
    "receivables",
    "payables",
)

_EXPLICIT_SEMANTIC_CATEGORIES = {
    SemanticCategory.CONCLUSION,
    SemanticCategory.DERIVED_METRIC,
    SemanticCategory.MANAGEMENT_COMMENTARY,
    SemanticCategory.ALLEGATION,
}


def item_checksum(item: CorporateIntelItem) -> str:
    """
    Deterministic SHA-256 checksum of an item.

    The checksum covers item content but not the checksum field
    itself, so change detection is stable.
    """

    payload = item.model_dump(
        mode="json",
        exclude={"checksum"},
    )

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        ensure_ascii=False,
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def classify_semantic_category(
    item: CorporateIntelItem,
) -> SemanticCategory:
    """
    Classify an item into the semantic vocabulary.

    Explicitly constructed categories (CONCLUSION, DERIVED_METRIC,
    MANAGEMENT_COMMENTARY, ALLEGATION) are preserved. Everything
    else is derived from kind and verification status. A claim is
    never upgraded to a fact.
    """

    if item.semantic_category in _EXPLICIT_SEMANTIC_CATEGORIES:
        return item.semantic_category

    if item.kind == IntelKind.MANAGEMENT_COMMENTARY:
        return SemanticCategory.MANAGEMENT_COMMENTARY

    if item.verification_status == VerificationStatus.ALLEGED:
        return SemanticCategory.ALLEGATION

    if item.verification_status in {
        VerificationStatus.REPORTED,
        VerificationStatus.UNVERIFIED,
        VerificationStatus.CONTRADICTED,
    }:
        return SemanticCategory.REPORTED_CLAIM

    if item.verification_status == VerificationStatus.CONFIRMED:
        return SemanticCategory.FACT

    return SemanticCategory.OBSERVATION


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")


def _snapshot_known_at(
    snapshot: FinancialSnapshot,
    as_of: datetime,
    default_available_at: datetime | None,
) -> bool:
    if snapshot.period_end > as_of.date():
        return False

    available = snapshot.available_at or default_available_at

    if available is not None:
        if available.tzinfo is None:
            raise ValueError("available_at must be timezone-aware")

        if available > as_of:
            return False

    return True


def _median(intervals: list[int]) -> int:
    ordered = sorted(intervals)
    middle = len(ordered) // 2
    return ordered[middle]


def _infer_period_type(
    snapshots: Sequence[FinancialSnapshot],
) -> ReportingPeriodType:
    explicit = [s.period_type for s in snapshots if s.period_type]

    if explicit:
        try:
            return ReportingPeriodType(explicit[0].upper())
        except ValueError:
            pass

    ends = sorted({s.period_end for s in snapshots})

    if len(ends) < 2:
        return ReportingPeriodType.UNKNOWN

    intervals = [
        (second - first).days
        for first, second in zip(ends, ends[1:])
    ]
    median = _median(intervals)

    if 60 <= median <= 110:
        return ReportingPeriodType.QUARTERLY

    if 150 <= median <= 220:
        return ReportingPeriodType.SEMI_ANNUAL

    if 330 <= median <= 400:
        return ReportingPeriodType.ANNUAL

    return ReportingPeriodType.UNKNOWN


def _infer_consolidation_scope(
    snapshots: Sequence[FinancialSnapshot],
) -> ConsolidationScope:
    explicit = [
        s.consolidation
        for s in snapshots
        if s.consolidation
    ]

    if explicit:
        try:
            return ConsolidationScope(explicit[0].upper())
        except ValueError:
            pass

    return ConsolidationScope.UNKNOWN


def _period_type_for_snapshot(
    snapshot: FinancialSnapshot,
    inferred: ReportingPeriodType,
) -> ReportingPeriodType:
    if snapshot.period_type:
        try:
            return ReportingPeriodType(snapshot.period_type.upper())
        except ValueError:
            pass

    return inferred


def _consolidation_for_snapshot(
    snapshot: FinancialSnapshot,
    inferred: ConsolidationScope,
) -> ConsolidationScope:
    if snapshot.consolidation:
        try:
            return ConsolidationScope(snapshot.consolidation.upper())
        except ValueError:
            pass

    return inferred


def _period_id(
    symbol: str,
    period_end: date,
    period_type: ReportingPeriodType,
    consolidation: ConsolidationScope,
) -> str:
    return (
        f"{symbol}:{period_end.isoformat()}:"
        f"{period_type.value}:{consolidation.value}"
    )


def _statements_from_snapshot(
    snapshot: FinancialSnapshot,
    *,
    period_type: ReportingPeriodType,
    consolidation: ConsolidationScope,
    source_name: str,
    source_type: str,
    source_url: str | None,
    default_available_at: datetime | None,
) -> tuple[FinancialStatement, ...]:
    base = _period_id(
        snapshot.symbol,
        snapshot.period_end,
        period_type,
        consolidation,
    )
    available = snapshot.available_at or default_available_at

    groups = (
        (
            "-IS",
            _INCOME_FIELDS,
            FinancialStatementType.INCOME_STATEMENT,
        ),
        (
            "-BS",
            _BALANCE_FIELDS,
            FinancialStatementType.BALANCE_SHEET,
        ),
        (
            "-CF",
            _CASH_FIELDS,
            FinancialStatementType.CASH_FLOW_STATEMENT,
        ),
    )

    statements: list[FinancialStatement] = []

    for suffix, fields, statement_type in groups:
        items = {
            field: value
            for field in fields
            if (value := getattr(snapshot, field)) is not None
        }

        if not items:
            continue

        statements.append(
            FinancialStatement(
                statement_id=base + suffix,
                symbol=snapshot.symbol,
                statement_type=statement_type,
                period_type=period_type,
                consolidation=consolidation,
                period_start=snapshot.period_start,
                period_end=snapshot.period_end,
                published_at=snapshot.published_at,
                available_at=available,
                source_name=(
                    snapshot.source_name or source_name
                ),
                source_type=(
                    snapshot.source_type or source_type
                ),
                source_url=(
                    snapshot.source_url or source_url
                ),
                currency=snapshot.currency,
                items=items,
            )
        )

    if not statements:
        statements.append(
            FinancialStatement(
                statement_id=base,
                symbol=snapshot.symbol,
                statement_type=FinancialStatementType.OTHER,
                period_type=period_type,
                consolidation=consolidation,
                period_start=snapshot.period_start,
                period_end=snapshot.period_end,
                published_at=snapshot.published_at,
                available_at=available,
                source_name=(
                    snapshot.source_name or source_name
                ),
                source_type=(
                    snapshot.source_type or source_type
                ),
                source_url=(
                    snapshot.source_url or source_url
                ),
                currency=snapshot.currency,
                items={},
            )
        )

    return tuple(statements)


def financial_periods_from_snapshots(
    snapshots: Sequence[FinancialSnapshot],
    *,
    as_of: datetime,
    source_name: str = "recorded_financials",
    source_type: str = "COMPANY_FILINGS",
    source_url: str | None = None,
    default_available_at: datetime | None = None,
) -> tuple[FinancialPeriod, ...]:
    """
    Convert financial snapshots into point-in-time financial periods.

    Snapshots that are not knowable at `as_of` are excluded.
    """

    _require_aware(as_of)

    known = [
        snapshot
        for snapshot in snapshots
        if _snapshot_known_at(
            snapshot,
            as_of,
            default_available_at,
        )
    ]

    inferred_period = _infer_period_type(known)
    inferred_consolidation = _infer_consolidation_scope(known)

    periods: list[FinancialPeriod] = []

    for snapshot in sorted(
        known,
        key=lambda s: (
            s.period_end,
            s.consolidation or "",
            s.symbol,
        ),
    ):
        period_type = _period_type_for_snapshot(
            snapshot,
            inferred_period,
        )
        consolidation = _consolidation_for_snapshot(
            snapshot,
            inferred_consolidation,
        )
        available = snapshot.available_at or default_available_at

        metrics = {
            field: value
            for field, value in snapshot.model_dump().items()
            if field in _METRIC_FIELDS
            and value is not None
        }

        statements = _statements_from_snapshot(
            snapshot,
            period_type=period_type,
            consolidation=consolidation,
            source_name=source_name,
            source_type=source_type,
            source_url=source_url,
            default_available_at=default_available_at,
        )

        periods.append(
            FinancialPeriod(
                period_id=_period_id(
                    snapshot.symbol,
                    snapshot.period_end,
                    period_type,
                    consolidation,
                ),
                symbol=snapshot.symbol,
                period_start=snapshot.period_start,
                period_end=snapshot.period_end,
                period_type=period_type,
                consolidation=consolidation,
                published_at=snapshot.published_at,
                available_at=available,
                source_name=(
                    snapshot.source_name or source_name
                ),
                source_type=(
                    snapshot.source_type or source_type
                ),
                source_url=(
                    snapshot.source_url or source_url
                ),
                provenance_id=None,
                currency=snapshot.currency,
                metrics=metrics,
                statements=statements,
            )
        )

    return tuple(periods)


def build_financial_intelligence(
    symbol: str,
    periods: Sequence[FinancialPeriod],
    *,
    as_of: datetime,
) -> FinancialIntelligence:
    """
    Deterministic, descriptive summary of reporting history.
    """

    _require_aware(as_of)

    known = [p for p in periods if p.is_known_at(as_of)]

    ordered = tuple(
        sorted(
            known,
            key=lambda p: (
                p.period_end,
                p.consolidation.value,
                p.period_id,
            ),
        )
    )

    period_count = len(ordered)

    def _count(predicate) -> int:
        return sum(1 for p in ordered if predicate(p))

    coverage: Counter[str] = Counter()

    for period in ordered:
        for metric in period.metrics:
            coverage[metric] += 1

    latest = (
        ordered[-1].period_end
        if ordered
        else None
    )
    earliest = (
        ordered[0].period_end
        if ordered
        else None
    )

    notes: list[str] = []

    if (
        any(p.period_type == ReportingPeriodType.QUARTERLY for p in ordered)
        and any(p.period_type == ReportingPeriodType.ANNUAL for p in ordered)
    ):
        notes.append(
            "Both quarterly and annual reporting periods are present. "
            "Quarterly and annual figures must not be compared directly."
        )

    if (
        any(p.consolidation == ConsolidationScope.CONSOLIDATED for p in ordered)
        and any(p.consolidation == ConsolidationScope.STANDALONE for p in ordered)
    ):
        notes.append(
            "Both consolidated and standalone reporting periods are present. "
            "The consolidation scope must be preserved when comparing periods."
        )

    if not ordered:
        notes.append(
            "No reporting periods were knowable at as_of."
        )

    return FinancialIntelligence(
        symbol=symbol,
        as_of=as_of,
        period_count=period_count,
        quarterly_count=_count(
            lambda p: p.period_type == ReportingPeriodType.QUARTERLY
        ),
        semiannual_count=_count(
            lambda p: p.period_type == ReportingPeriodType.SEMI_ANNUAL
        ),
        annual_count=_count(
            lambda p: p.period_type == ReportingPeriodType.ANNUAL
        ),
        unknown_period_count=_count(
            lambda p: p.period_type == ReportingPeriodType.UNKNOWN
        ),
        consolidated_count=_count(
            lambda p: p.consolidation == ConsolidationScope.CONSOLIDATED
        ),
        standalone_count=_count(
            lambda p: p.consolidation == ConsolidationScope.STANDALONE
        ),
        unknown_consolidation_count=_count(
            lambda p: p.consolidation == ConsolidationScope.UNKNOWN
        ),
        latest_period_end=latest,
        earliest_period_end=earliest,
        coverage=dict(coverage),
        periods=ordered,
        notes=tuple(notes),
    )


def _period_summary(period: FinancialPeriod) -> str:
    revenue = period.metrics.get("revenue")
    net_profit = period.metrics.get("net_profit")

    parts = [
        f"{period.symbol} {period.period_type.value} financials "
        f"for the period ending {period.period_end.isoformat()}.",
    ]

    if revenue is not None:
        parts.append(f"Reported revenue {revenue}.")

    if net_profit is not None:
        parts.append(f"Reported net profit {net_profit}.")

    return " ".join(parts)


def financial_periods_to_items(
    periods: Sequence[FinancialPeriod],
    *,
    as_of: datetime,
    source_name: str = "recorded_financials",
    source_type: str = "COMPANY_FILINGS",
    source_url: str | None = None,
    reliability_tier: int = 1,
    provenance_id: str | None = None,
) -> tuple[CorporateIntelItem, ...]:
    """One FACT item per known financial period."""

    _require_aware(as_of)

    items: list[CorporateIntelItem] = []

    for period in sorted(
        periods,
        key=lambda p: (p.period_end, p.period_id),
    ):
        if not period.is_known_at(as_of):
            continue

        if period.available_at is None:
            continue

        items.append(
            CorporateIntelItem(
                item_id=f"{period.period_id}:period",
                symbol=period.symbol,
                kind=IntelKind.FINANCIAL_PERIOD,
                semantic_category=SemanticCategory.FACT,
                verification_status=VerificationStatus.CONFIRMED,
                topic="financial_reporting",
                title=(
                    f"{period.symbol} {period.period_type.value} financials "
                    f"for the period ending {period.period_end.isoformat()}"
                ),
                description=_period_summary(period),
                direction=IntelDirection.NEUTRAL,
                published_at=period.published_at,
                available_at=period.available_at,
                source=SourceRef(
                    source_name=period.source_name or source_name,
                    source_type=period.source_type or source_type,
                    source_url=period.source_url or source_url,
                    reliability_tier=reliability_tier,
                    provenance_id=provenance_id,
                ),
                provenance_id=period.provenance_id or provenance_id,
            )
        )

    return tuple(items)


def derived_metric_items(
    periods: Sequence[FinancialPeriod],
    *,
    as_of: datetime,
    source_name: str = "recorded_financials",
    source_type: str = "COMPANY_FILINGS",
    source_url: str | None = None,
    reliability_tier: int = 1,
    provenance_id: str | None = None,
) -> tuple[CorporateIntelItem, ...]:
    """
    One DERIVED_METRIC item per known period with a usable metric.

    Metrics are computed from reported numbers; they are descriptive
    research output, not predictions.
    """

    _require_aware(as_of)

    items: list[CorporateIntelItem] = []

    for period in sorted(
        periods,
        key=lambda p: (p.period_end, p.period_id),
    ):
        if not period.is_known_at(as_of):
            continue

        if period.available_at is None:
            continue

        revenue = period.metrics.get("revenue")
        operating_profit = period.metrics.get("operating_profit")

        if revenue is not None:
            items.append(
                CorporateIntelItem(
                    item_id=f"{period.period_id}:revenue-metric",
                    symbol=period.symbol,
                    kind=IntelKind.FINANCIAL_PERIOD,
                    semantic_category=SemanticCategory.DERIVED_METRIC,
                    verification_status=VerificationStatus.CONFIRMED,
                    topic="financial_metrics",
                    title=(
                        f"{period.symbol} {period.period_type.value} revenue "
                        f"for the period ending {period.period_end.isoformat()}"
                    ),
                    description=(
                        f"Reported revenue {revenue} for the period ending "
                        f"{period.period_end.isoformat()}."
                    ),
                    direction=IntelDirection.NEUTRAL,
                    published_at=period.published_at,
                    available_at=period.available_at,
                    source=SourceRef(
                        source_name=period.source_name or source_name,
                        source_type=period.source_type or source_type,
                        source_url=period.source_url or source_url,
                        reliability_tier=reliability_tier,
                        provenance_id=provenance_id,
                    ),
                    provenance_id=period.provenance_id or provenance_id,
                )
            )

        if revenue is not None and operating_profit is not None:
            margin = operating_profit / revenue

            items.append(
                CorporateIntelItem(
                    item_id=f"{period.period_id}:margin-metric",
                    symbol=period.symbol,
                    kind=IntelKind.FINANCIAL_PERIOD,
                    semantic_category=SemanticCategory.DERIVED_METRIC,
                    verification_status=VerificationStatus.CONFIRMED,
                    topic="financial_metrics",
                    title=(
                        f"{period.symbol} {period.period_type.value} "
                        f"operating margin for the period ending "
                        f"{period.period_end.isoformat()}"
                    ),
                    description=(
                        f"Operating profit {operating_profit} divided by "
                        f"revenue {revenue} for the period ending "
                        f"{period.period_end.isoformat()} equals an "
                        f"operating margin of {margin}."
                    ),
                    direction=IntelDirection.NEUTRAL,
                    published_at=period.published_at,
                    available_at=period.available_at,
                    source=SourceRef(
                        source_name=period.source_name or source_name,
                        source_type=period.source_type or source_type,
                        source_url=period.source_url or source_url,
                        reliability_tier=reliability_tier,
                        provenance_id=provenance_id,
                    ),
                    provenance_id=period.provenance_id or provenance_id,
                )
            )

    return tuple(items)


def _kind_for_category(category: ResearchCategory) -> IntelKind:
    mapping = {
        ResearchCategory.MATERIAL_EVENTS: IntelKind.BUSINESS_EVENT,
        ResearchCategory.MANAGEMENT: IntelKind.MANAGEMENT_COMMENTARY,
        ResearchCategory.RISKS: IntelKind.RISK_DEVELOPMENT,
        ResearchCategory.REGULATORY: IntelKind.RISK_DEVELOPMENT,
        ResearchCategory.INDUSTRY: IntelKind.INDIRECT_INTELLIGENCE,
    }

    return mapping.get(category, IntelKind.OTHER)


def intel_items_from_observations(
    observations: Sequence[ResearchObservation],
    *,
    as_of: datetime,
    source_type: str = "research_acquisition",
    default_reliability_tier: int = 3,
    provenance_id: str | None = None,
) -> tuple[CorporateIntelItem, ...]:
    """
    Convert acquisition observations into intelligence items.

    Observations that are not point-in-time knowable at `as_of` are
    excluded. No direction is inferred from an observation.
    """

    _require_aware(as_of)

    items: list[CorporateIntelItem] = []

    for observation in observations:
        if not observation.is_known_at(as_of):
            continue

        reliability = (
            observation.reliability_tier
            or default_reliability_tier
        )

        items.append(
            CorporateIntelItem(
                item_id=f"observation:{observation.observation_id}",
                symbol=observation.company,
                kind=_kind_for_category(observation.category),
                semantic_category=SemanticCategory.OBSERVATION,
                verification_status=VerificationStatus.REPORTED,
                topic=observation.category.value,
                title=observation.claim,
                description=observation.evidence_excerpt,
                direction=IntelDirection.UNKNOWN,
                published_at=observation.published_at,
                available_at=observation.available_at,
                source=SourceRef(
                    source_name=observation.source_id,
                    source_type=source_type,
                    reliability_tier=reliability,
                    provenance_id=provenance_id,
                ),
                confidence=(
                    Decimal(str(observation.confidence))
                    if observation.confidence is not None
                    else None
                ),
                provenance_id=provenance_id,
            )
        )

    return tuple(items)


def _reclassify(
    item: CorporateIntelItem,
    category: SemanticCategory,
) -> CorporateIntelItem:
    reclassified = item.model_copy(
        update={"semantic_category": category}
    )
    checksum = item_checksum(reclassified)
    return reclassified.model_copy(
        update={"checksum": checksum}
    )


def build_company_intelligence_snapshot(
    *,
    symbol: str,
    as_of: datetime,
    captured_at: datetime | None = None,
    items: Sequence[CorporateIntelItem] = (),
    financial_periods: Sequence[FinancialPeriod] = (),
    previous_snapshot: CompanyIntelligenceSnapshot | None = None,
    provenance_ids: Sequence[str] = (),
) -> CompanyIntelligenceSnapshot:
    """
    Build the deep intelligence snapshot for one company at `as_of`.

    Integrity guarantees:

    - only items / periods knowable at `as_of` are included;
    - items are deduplicated by id (first occurrence wins);
    - semantic categories are classified deterministically;
    - conclusions survive only when the evidence gate supports them;
    - evidence conflicts are surfaced, never auto-resolved.
    """

    _require_aware(as_of)

    captured = captured_at or as_of

    known_items: list[CorporateIntelItem] = []
    seen: set[str] = set()
    candidate_count = 0

    for item in items:
        if item.symbol != symbol:
            continue

        if not item.is_known_at(as_of):
            continue

        candidate_count += 1

        if item.item_id in seen:
            continue

        seen.add(item.item_id)
        known_items.append(item)

    classified: list[CorporateIntelItem] = [
        _reclassify(item, classify_semantic_category(item))
        for item in sorted(
            known_items,
            key=lambda i: (
                i.available_at.isoformat() if i.available_at else "",
                i.item_id,
            ),
        )
    ]

    confirmed_pool = [
        item
        for item in classified
        if item.verification_status == VerificationStatus.CONFIRMED
        and item.source.reliability_tier <= 2
    ]

    insufficient: set[str] = set()
    surviving: list[CorporateIntelItem] = []

    for item in classified:
        if (
            item.semantic_category == SemanticCategory.CONCLUSION
        ):
            # A conclusion must not support itself: the gate is
            # evaluated over confirmed evidence only, never over
            # other conclusion items.
            pool = [
                candidate
                for candidate in confirmed_pool
                if candidate.item_id != item.item_id
                and candidate.semantic_category
                != SemanticCategory.CONCLUSION
            ]
            gate = conclusion_gate(pool)

            if not gate.supported:
                insufficient.add(gate.reason)
                continue

        surviving.append(item)

    business_events = _group_by_kind(
        surviving,
        IntelKind.BUSINESS_EVENT,
    )
    management_commentary = _group_by_kind(
        surviving,
        IntelKind.MANAGEMENT_COMMENTARY,
    )
    risk_intelligence = _group_by_kind(
        surviving,
        IntelKind.RISK_DEVELOPMENT,
    )
    indirect_intelligence = _group_by_kind(
        surviving,
        IntelKind.INDIRECT_INTELLIGENCE,
    )
    financial_items = _group_by_kind(
        surviving,
        IntelKind.FINANCIAL_PERIOD,
    )
    other_intelligence = _group_by_kind(
        surviving,
        IntelKind.OTHER,
    )

    financial_intelligence = build_financial_intelligence(
        symbol,
        financial_periods,
        as_of=as_of,
    )

    conflicts = detect_evidence_conflicts(
        surviving,
        as_of=as_of,
    )
    evidence_links = build_evidence_links(
        surviving,
        as_of=as_of,
    )

    changes: tuple = ()

    if previous_snapshot is not None:
        diff = detect_changes(
            company=symbol,
            as_of=as_of,
            before=previous_snapshot.items,
            after=surviving,
        )
        changes = diff.changes

    source_ids = sorted(
        {
            item.source.source_name
            for item in surviving
            if item.source.source_name
        }
    )

    all_provenance: set[str] = set(provenance_ids)

    for item in surviving:
        if item.provenance_id:
            all_provenance.add(item.provenance_id)

    for period in financial_periods:
        if period.provenance_id:
            all_provenance.add(period.provenance_id)

    coverage: Counter[str] = Counter()
    semantic_summary: Counter[str] = Counter()
    status_summary: Counter[str] = Counter()

    for item in surviving:
        coverage[item.kind.value] += 1
        semantic_summary[item.semantic_category.value] += 1
        status_summary[item.verification_status.value] += 1

    notes: list[str] = [
        f"Snapshot is point-in-time as of {as_of.isoformat()}.",
    ]

    if conflicts:
        notes.append(
            "Evidence conflicts are surfaced with both sides. "
            "The system does not automatically determine which side "
            "is correct."
        )

    if candidate_count > len(classified):
        notes.append(
            f"{candidate_count - len(classified)} duplicate item(s) "
            "were excluded from the snapshot."
        )

    if insufficient:
        notes.append(
            "One or more conclusion items were excluded because the "
            "evidence gate was not satisfied."
        )

    return CompanyIntelligenceSnapshot(
        company=symbol,
        as_of=as_of,
        captured_at=captured,
        business_events=business_events,
        management_commentary=management_commentary,
        risk_intelligence=risk_intelligence,
        indirect_intelligence=indirect_intelligence,
        financial_intelligence_items=financial_items,
        other_intelligence=other_intelligence,
        financial_intelligence=financial_intelligence,
        conflicts=conflicts,
        evidence_links=evidence_links,
        changes=changes,
        item_count=len(surviving),
        source_ids=tuple(source_ids),
        provenance_ids=tuple(sorted(all_provenance)),
        coverage=dict(coverage),
        semantic_summary=dict(semantic_summary),
        status_summary=dict(status_summary),
        insufficient_evidence_notes=tuple(sorted(insufficient)),
        notes=tuple(notes),
    )


def _group_by_kind(
    items: Sequence[CorporateIntelItem],
    kind: IntelKind,
) -> tuple[CorporateIntelItem, ...]:
    return tuple(
        item
        for item in sorted(
            items,
            key=lambda i: (
                i.available_at.isoformat() if i.available_at else "",
                i.item_id,
            ),
        )
        if item.kind == kind
    )


__all__ = [
    "build_company_intelligence_snapshot",
    "build_financial_intelligence",
    "classify_semantic_category",
    "derived_metric_items",
    "financial_periods_from_snapshots",
    "financial_periods_to_items",
    "intel_items_from_observations",
    "item_checksum",
]
