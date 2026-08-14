from __future__ import annotations

from decimal import Decimal

from src.analysis.research_coverage import (
    ResearchComponentStatus,
    ResearchCoverage,
    ResearchComponentCoverage,
)


class ResearchScore:
    """
    Composite research score.

    Scores are normalized to 0-100.

    This is a research-ranking metric, NOT a guarantee of future
    returns or a prediction of market direction.
    """

    def __init__(
        self,
        *,
        total: Decimal,
        fundamentals: Decimal,
        financial_trends: Decimal,
        cash_flow: Decimal,
        balance_sheet: Decimal,
        risk: Decimal,
        management: Decimal,
        market_behavior: Decimal,
        evidence_quality: Decimal,
        signal: str,
        confidence: Decimal,
        coverage: ResearchCoverage,
    ) -> None:
        self.total = total
        self.fundamentals = fundamentals
        self.financial_trends = financial_trends
        self.cash_flow = cash_flow
        self.balance_sheet = balance_sheet
        self.risk = risk
        self.management = management
        self.market_behavior = market_behavior
        self.evidence_quality = evidence_quality
        self.signal = signal
        self.confidence = confidence
        self.coverage = coverage

    @property
    def is_positive(self) -> bool:
        return self.signal == "POSITIVE"

    @property
    def is_negative(self) -> bool:
        return self.signal == "NEGATIVE"


_WEIGHTS = {
    "fundamentals": Decimal("0.18"),
    "financial_trends": Decimal("0.16"),
    "cash_flow": Decimal("0.14"),
    "balance_sheet": Decimal("0.12"),
    "risk": Decimal("0.12"),
    "management": Decimal("0.10"),
    "market_behavior": Decimal("0.10"),
    "evidence_quality": Decimal("0.08"),
}


def _validate_component(
    value: Decimal,
    name: str,
) -> Decimal:
    value = Decimal(value)

    if value < 0 or value > 100:
        raise ValueError(
            f"{name} score must be between 0 and 100"
        )

    return value


def _signal_for_score(score: Decimal) -> str:
    if score >= Decimal("70"):
        return "POSITIVE"

    if score <= Decimal("40"):
        return "NEGATIVE"

    return "NEUTRAL"


def _confidence_for_scores(
    scores: list[Decimal],
) -> Decimal:
    """
    Descriptive consistency metric.

    This is not a probability of being correct.
    """

    if not scores:
        return Decimal("0")

    mean = sum(scores) / Decimal(len(scores))

    deviation = sum(
        abs(score - mean)
        for score in scores
    ) / Decimal(len(scores))

    confidence = Decimal("100") - deviation

    return max(
        Decimal("0"),
        min(Decimal("100"), confidence),
    )


def _normalize_status(
    value: ResearchComponentStatus | str | bool,
) -> ResearchComponentStatus:
    """
    Preserve compatibility with the old boolean availability API.

    True  -> AVAILABLE
    False -> MISSING
    """

    if isinstance(value, bool):
        return (
            ResearchComponentStatus.AVAILABLE
            if value
            else ResearchComponentStatus.MISSING
        )

    if isinstance(value, ResearchComponentStatus):
        return value

    return ResearchComponentStatus(str(value).upper())


def _build_coverage(
    *,
    component_status: dict[
        str,
        ResearchComponentStatus,
    ],
) -> ResearchCoverage:
    components = tuple(
        ResearchComponentCoverage(
            component=name,
            status=status,
            score_contribution=(
                status
                in {
                    ResearchComponentStatus.AVAILABLE,
                    ResearchComponentStatus.PARTIAL,
                }
            ),
        )
        for name, status in component_status.items()
    )

    return ResearchCoverage(
        components=components,
    )


def calculate_research_score(
    *,
    fundamentals: Decimal,
    financial_trends: Decimal,
    cash_flow: Decimal,
    balance_sheet: Decimal,
    risk: Decimal,
    management: Decimal,
    market_behavior: Decimal,
    evidence_quality: Decimal,
    component_availability: dict[
        str,
        bool | str | ResearchComponentStatus,
    ]
    | None = None,
) -> ResearchScore:
    """
    Calculate the composite company research score.

    Missing evidence is NOT treated as a neutral 50.

    Available components contribute their weighted score.
    Partial components contribute their score with their existing
    value, while missing/unverified/stale/conflicting components
    are excluded from the composite.

    Existing callers using boolean component_availability remain
    compatible.
    """

    values = {
        "fundamentals": _validate_component(
            fundamentals,
            "fundamentals",
        ),
        "financial_trends": _validate_component(
            financial_trends,
            "financial_trends",
        ),
        "cash_flow": _validate_component(
            cash_flow,
            "cash_flow",
        ),
        "balance_sheet": _validate_component(
            balance_sheet,
            "balance_sheet",
        ),
        "risk": _validate_component(
            risk,
            "risk",
        ),
        "management": _validate_component(
            management,
            "management",
        ),
        "market_behavior": _validate_component(
            market_behavior,
            "market_behavior",
        ),
        "evidence_quality": _validate_component(
            evidence_quality,
            "evidence_quality",
        ),
    }

    if component_availability is None:
        component_availability = {
            name: ResearchComponentStatus.AVAILABLE
            for name in values
        }

    component_status = {
        name: _normalize_status(
            component_availability.get(
                name,
                ResearchComponentStatus.AVAILABLE,
            )
        )
        for name in values
    }

    coverage = _build_coverage(
        component_status=component_status,
    )

    usable_names = {
        name
        for name, status in component_status.items()
        if status
        in {
            ResearchComponentStatus.AVAILABLE,
            ResearchComponentStatus.PARTIAL,
        }
    }

    if not usable_names:
        total = Decimal("0")
        confidence = Decimal("0")
    else:
        usable_weight = sum(
            _WEIGHTS[name]
            for name in usable_names
        )

        weighted_total = sum(
            values[name] * _WEIGHTS[name]
            for name in usable_names
        )

        # Renormalize only across components for which evidence
        # is actually usable.
        total = (
            weighted_total / usable_weight
            if usable_weight
            else Decimal("0")
        )

        confidence = _confidence_for_scores(
            [
                values[name]
                for name in usable_names
            ]
        )

    total = max(
        Decimal("0"),
        min(Decimal("100"), total),
    )

    signal = _signal_for_score(total)

    return ResearchScore(
        total=total,
        fundamentals=values["fundamentals"],
        financial_trends=values["financial_trends"],
        cash_flow=values["cash_flow"],
        balance_sheet=values["balance_sheet"],
        risk=values["risk"],
        management=values["management"],
        market_behavior=values["market_behavior"],
        evidence_quality=values["evidence_quality"],
        signal=signal,
        confidence=confidence,
        coverage=coverage,
    )
