from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from src.research.features.snapshot_engine import FeatureDefinition


@dataclass(frozen=True)
class FinancialTrendSummary:
    """
    Multi-period summary of one financial metric.

    This is descriptive research evidence only.
    It does not predict future returns.
    """

    metric: str
    direction: str
    observations: int
    average_change: Decimal
    positive_periods: int
    negative_periods: int
    stable_periods: int
    consistency: Decimal
    explanation: str


def _number_or_none(value: object) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def absolute_change(
    observations: Mapping[str, object],
    *,
    current_key: str,
    previous_key: str,
) -> float | None:
    current = _number_or_none(observations.get(current_key))
    previous = _number_or_none(observations.get(previous_key))

    if current is None or previous is None:
        return None

    return current - previous


def percentage_change(
    observations: Mapping[str, object],
    *,
    current_key: str,
    previous_key: str,
) -> float | None:
    current = _number_or_none(observations.get(current_key))
    previous = _number_or_none(observations.get(previous_key))

    if current is None or previous is None:
        return None

    if previous == 0:
        return None

    return ((current - previous) / abs(previous)) * 100.0


def revenue_change(
    observations: Mapping[str, object],
) -> float | None:
    return absolute_change(
        observations,
        current_key="revenue",
        previous_key="previous_revenue",
    )


def operating_profit_change(
    observations: Mapping[str, object],
) -> float | None:
    return absolute_change(
        observations,
        current_key="operating_profit",
        previous_key="previous_operating_profit",
    )


def net_profit_change(
    observations: Mapping[str, object],
) -> float | None:
    return absolute_change(
        observations,
        current_key="net_profit",
        previous_key="previous_net_profit",
    )


def operating_cash_flow_change(
    observations: Mapping[str, object],
) -> float | None:
    return absolute_change(
        observations,
        current_key="operating_cash_flow",
        previous_key="previous_operating_cash_flow",
    )


def free_cash_flow_change(
    observations: Mapping[str, object],
) -> float | None:
    return absolute_change(
        observations,
        current_key="free_cash_flow",
        previous_key="previous_free_cash_flow",
    )


def total_debt_change(
    observations: Mapping[str, object],
) -> float | None:
    return absolute_change(
        observations,
        current_key="total_debt",
        previous_key="previous_total_debt",
    )


def cash_change(
    observations: Mapping[str, object],
) -> float | None:
    return absolute_change(
        observations,
        current_key="cash_and_equivalents",
        previous_key="previous_cash_and_equivalents",
    )


def receivables_change(
    observations: Mapping[str, object],
) -> float | None:
    return absolute_change(
        observations,
        current_key="receivables",
        previous_key="previous_receivables",
    )


def payables_change(
    observations: Mapping[str, object],
) -> float | None:
    return absolute_change(
        observations,
        current_key="payables",
        previous_key="previous_payables",
    )


def revenue_growth_change(
    observations: Mapping[str, object],
) -> float | None:
    return percentage_change(
        observations,
        current_key="revenue",
        previous_key="previous_revenue",
    )


FINANCIAL_TREND_FEATURE_DEFINITIONS = (
    FeatureDefinition(
        feature_id="revenue_change",
        feature_version="1.0",
        unit="absolute",
        calculator=revenue_change,
        required_inputs=("revenue", "previous_revenue"),
    ),
    FeatureDefinition(
        feature_id="revenue_growth_change",
        feature_version="1.0",
        unit="percent",
        calculator=revenue_growth_change,
        required_inputs=("revenue", "previous_revenue"),
    ),
    FeatureDefinition(
        feature_id="operating_profit_change",
        feature_version="1.0",
        unit="absolute",
        calculator=operating_profit_change,
        required_inputs=(
            "operating_profit",
            "previous_operating_profit",
        ),
    ),
    FeatureDefinition(
        feature_id="net_profit_change",
        feature_version="1.0",
        unit="absolute",
        calculator=net_profit_change,
        required_inputs=("net_profit", "previous_net_profit"),
    ),
    FeatureDefinition(
        feature_id="operating_cash_flow_change",
        feature_version="1.0",
        unit="absolute",
        calculator=operating_cash_flow_change,
        required_inputs=(
            "operating_cash_flow",
            "previous_operating_cash_flow",
        ),
    ),
    FeatureDefinition(
        feature_id="free_cash_flow_change",
        feature_version="1.0",
        unit="absolute",
        calculator=free_cash_flow_change,
        required_inputs=(
            "free_cash_flow",
            "previous_free_cash_flow",
        ),
    ),
    FeatureDefinition(
        feature_id="total_debt_change",
        feature_version="1.0",
        unit="absolute",
        calculator=total_debt_change,
        required_inputs=("total_debt", "previous_total_debt"),
    ),
    FeatureDefinition(
        feature_id="cash_change",
        feature_version="1.0",
        unit="absolute",
        calculator=cash_change,
        required_inputs=(
            "cash_and_equivalents",
            "previous_cash_and_equivalents",
        ),
    ),
    FeatureDefinition(
        feature_id="receivables_change",
        feature_version="1.0",
        unit="absolute",
        calculator=receivables_change,
        required_inputs=("receivables", "previous_receivables"),
    ),
    FeatureDefinition(
        feature_id="payables_change",
        feature_version="1.0",
        unit="absolute",
        calculator=payables_change,
        required_inputs=("payables", "previous_payables"),
    ),
)
