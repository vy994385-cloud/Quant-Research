import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from datetime import datetime, timezone

from src.research.company_engine import run_company_research
from src.research.features.models import (
    FeatureStatus,
    FeatureValue,
)
from src.research.signals.models import (
    ResearchSignal,
    SignalDirection,
    SignalSeverity,
)


AS_OF = datetime(
    2026,
    8,
    12,
    10,
    0,
    tzinfo=timezone.utc,
)


def feature(
    feature_id: str,
    value: float,
    unit: str,
    *,
    confidence: float = 0.90,
) -> FeatureValue:
    return FeatureValue(
        feature_id=feature_id,
        feature_version="1.0",
        symbol="TCS",
        value=value,
        unit=unit,
        observation_at=AS_OF,
        calculated_at=AS_OF,
        status=FeatureStatus.VALID,
        source_ids=("demo",),
        provenance_ids=("demo-tcs-2026-08-12",),
        confidence=confidence,
    )


def signal(
    signal_id: str,
    direction: SignalDirection,
    severity: SignalSeverity,
    title: str,
    explanation: str,
    *,
    confidence: str = "0.90",
) -> ResearchSignal:
    return ResearchSignal(
        signal_id=signal_id,
        category="COMPANY_RESEARCH",
        direction=direction,
        severity=severity,
        confidence=confidence,
        title=title,
        explanation=explanation,
        symbol="TCS",
        observation_at=AS_OF,
    )


def main() -> None:
    features = [
        feature(
            "revenue_growth",
            14.2,
            "%",
        ),
        feature(
            "profit_growth",
            11.8,
            "%",
        ),
        feature(
            "operating_cash_flow_growth",
            13.5,
            "%",
        ),
        feature(
            "debt_to_equity",
            0.08,
            "ratio",
        ),
        feature(
            "roe",
            48.5,
            "%",
        ),
        feature(
            "ai_participation",
            87.0,
            "score",
        ),
        feature(
            "innovation_execution",
            81.0,
            "score",
        ),
        feature(
            "future_readiness",
            84.0,
            "score",
        ),
    ]

    signals = [
        signal(
            "REVENUE_GROWTH",
            SignalDirection.POSITIVE,
            SignalSeverity.MEDIUM,
            "Revenue growth remains positive",
            "The research dataset shows sustained positive revenue growth.",
        ),
        signal(
            "CASH_FLOW_QUALITY",
            SignalDirection.POSITIVE,
            SignalSeverity.MEDIUM,
            "Cash-flow quality is supportive",
            "Operating cash-flow growth is positive in the supplied research snapshot.",
        ),
        signal(
            "AI_TRANSFORMATION",
            SignalDirection.POSITIVE,
            SignalSeverity.HIGH,
            "Strong AI participation",
            "The company shows meaningful participation in AI-related business transformation.",
            confidence="0.88",
        ),
        signal(
            "INNOVATION_EXECUTION",
            SignalDirection.POSITIVE,
            SignalSeverity.MEDIUM,
            "Innovation execution is strong",
            "The supplied evidence indicates continued execution across innovation initiatives.",
            confidence="0.86",
        ),
        signal(
            "BALANCE_SHEET",
            SignalDirection.POSITIVE,
            SignalSeverity.MEDIUM,
            "Balance sheet appears strong",
            "The supplied debt-to-equity measure indicates relatively low leverage.",
        ),
        signal(
            "VALUATION_UNKNOWN",
            SignalDirection.NEUTRAL,
            SignalSeverity.INFO,
            "Valuation evidence unavailable",
            "No point-in-time valuation evidence was supplied in this demo dataset.",
            confidence="0.50",
        ),
    ]

    report = run_company_research(
        symbol="TCS",
        as_of=AS_OF,
        features=features,
        signals=signals,
    )

    print()
    print("=" * 62)
    print("             QUANT RESEARCH — COMPANY REPORT")
    print("=" * 62)

    print(f"\nCompany       : {report.symbol}")
    print(f"As of         : {report.as_of.isoformat()}")
    print(f"Conclusion    : {report.conclusion.value}")
    print(f"Confidence    : {float(report.confidence) * 100:.1f}%")

    print("\nTHESIS")
    print("-" * 62)
    print(report.thesis)

    print("\nFEATURES")
    print("-" * 62)

    for item in report.positive_evidence:
        print(
            f"  + {item.title}: "
            f"{item.explanation}"
        )

    if report.negative_evidence:
        print("\nRISKS / NEGATIVE EVIDENCE")
        print("-" * 62)

        for item in report.negative_evidence:
            print(
                f"  - {item.title}: "
                f"{item.explanation}"
            )

    print("\nSIGNALS")
    print("-" * 62)

    for item in report.signals:
        print(
            f"  [{item.direction.value}] "
            f"{item.severity.value:<8} "
            f"{item.title}"
        )

    print("\nDATA QUALITY")
    print("-" * 62)

    for note in report.data_quality_notes:
        print(f"  • {note}")

    print("\nEvidence count:")
    print(f"  Features : {len(report.features)}")
    print(f"  Signals  : {len(report.signals)}")
    print(
        f"  Positive : {len(report.positive_evidence)}"
    )
    print(
        f"  Negative : {len(report.negative_evidence)}"
    )

    print("\n" + "=" * 62)
    print("NOTE: This is research infrastructure, not a trade signal.")
    print("=" * 62)


if __name__ == "__main__":
    main()
