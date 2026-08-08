from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ResearchScore:
    """
    Composite research score.

    Scores are normalized to 0-100.

    This is a research-ranking metric, NOT a guarantee of future
    returns or a prediction of market direction.
    """

    total: Decimal

    fundamentals: Decimal
    financial_trends: Decimal
    cash_flow: Decimal
    balance_sheet: Decimal
    risk: Decimal
    management: Decimal
    market_behavior: Decimal
    evidence_quality: Decimal

    signal: str
    confidence: Decimal

    @property
    def is_positive(self) -> bool:
        return self.signal == "POSITIVE"

    @property
    def is_negative(self) -> bool:
        return self.signal == "NEGATIVE"


# Initial weights.
#
# These are deliberately explicit rather than hidden inside the
# calculation so that they can later be optimized using historical
# out-of-sample validation.
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


def _validate_component(value: Decimal, name: str) -> Decimal:
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
    Estimate confidence from the consistency of component scores.

    This is intentionally NOT a prediction-confidence metric.

    It measures how internally consistent the supplied research
    components are. Later we can replace this with a calibrated
    historical confidence model.
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
) -> ResearchScore:
    """
    Calculate the composite company research score.

    Every component must be between 0 and 100.

    The function is deterministic and contains no market prediction
    logic. Historical validation will be required before weights are
    considered production-quality.
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

    total = sum(
        values[name] * weight
        for name, weight in _WEIGHTS.items()
    )

    total = max(
        Decimal("0"),
        min(Decimal("100"), total),
    )

    signal = _signal_for_score(total)

    confidence = _confidence_for_scores(
        list(values.values())
    )

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
    )
