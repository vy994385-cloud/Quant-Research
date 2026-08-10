from __future__ import annotations

from typing import Mapping

from src.research.features.snapshot_engine import FeatureDefinition


def _decimal_or_none(value: object) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_divide(
    numerator: object,
    denominator: object,
) -> float | None:
    numerator_value = _decimal_or_none(numerator)
    denominator_value = _decimal_or_none(denominator)

    if numerator_value is None or denominator_value is None:
        return None

    if denominator_value == 0:
        return None

    return numerator_value / denominator_value


def _percentage(
    value: float | None,
) -> float | None:
    if value is None:
        return None

    return value * 100.0


def revenue_growth(
    observations: Mapping[str, object],
) -> float | None:
    """
    Calculate revenue growth from already point-in-time-filtered
    current and previous revenue observations.

    Expected inputs:
        revenue
        previous_revenue
    """

    current = _decimal_or_none(
        observations.get("revenue")
    )
    previous = _decimal_or_none(
        observations.get("previous_revenue")
    )

    if current is None or previous is None:
        return None

    if previous == 0:
        return None

    return (
        (current - previous)
        / abs(previous)
    ) * 100.0


def net_profit_margin(
    observations: Mapping[str, object],
) -> float | None:
    return _percentage(
        _safe_divide(
            observations.get("net_profit"),
            observations.get("revenue"),
        )
    )


def operating_cash_flow_margin(
    observations: Mapping[str, object],
) -> float | None:
    return _percentage(
        _safe_divide(
            observations.get("operating_cash_flow"),
            observations.get("revenue"),
        )
    )


def free_cash_flow_margin(
    observations: Mapping[str, object],
) -> float | None:
    return _percentage(
        _safe_divide(
            observations.get("free_cash_flow"),
            observations.get("revenue"),
        )
    )


def receivables_to_revenue(
    observations: Mapping[str, object],
) -> float | None:
    return _percentage(
        _safe_divide(
            observations.get("receivables"),
            observations.get("revenue"),
        )
    )


def payables_to_revenue(
    observations: Mapping[str, object],
) -> float | None:
    return _percentage(
        _safe_divide(
            observations.get("payables"),
            observations.get("revenue"),
        )
    )


def debt_to_revenue(
    observations: Mapping[str, object],
) -> float | None:
    return _safe_divide(
        observations.get("total_debt"),
        observations.get("revenue"),
    )


def cash_to_debt(
    observations: Mapping[str, object],
) -> float | None:
    return _safe_divide(
        observations.get("cash_and_equivalents"),
        observations.get("total_debt"),
    )


def cash_conversion_ratio(
    observations: Mapping[str, object],
) -> float | None:
    return _percentage(
        _safe_divide(
            observations.get("operating_cash_flow"),
            observations.get("net_profit"),
        )
    )


FINANCIAL_FEATURE_DEFINITIONS = (
    FeatureDefinition(
        feature_id="revenue_growth",
        feature_version="1.0",
        unit="percent",
        calculator=revenue_growth,
        required_inputs=(
            "revenue",
            "previous_revenue",
        ),
    ),
    FeatureDefinition(
        feature_id="net_profit_margin",
        feature_version="1.0",
        unit="percent",
        calculator=net_profit_margin,
        required_inputs=(
            "net_profit",
            "revenue",
        ),
    ),
    FeatureDefinition(
        feature_id="operating_cash_flow_margin",
        feature_version="1.0",
        unit="percent",
        calculator=operating_cash_flow_margin,
        required_inputs=(
            "operating_cash_flow",
            "revenue",
        ),
    ),
    FeatureDefinition(
        feature_id="free_cash_flow_margin",
        feature_version="1.0",
        unit="percent",
        calculator=free_cash_flow_margin,
        required_inputs=(
            "free_cash_flow",
            "revenue",
        ),
    ),
    FeatureDefinition(
        feature_id="receivables_to_revenue",
        feature_version="1.0",
        unit="percent",
        calculator=receivables_to_revenue,
        required_inputs=(
            "receivables",
            "revenue",
        ),
    ),
    FeatureDefinition(
        feature_id="payables_to_revenue",
        feature_version="1.0",
        unit="percent",
        calculator=payables_to_revenue,
        required_inputs=(
            "payables",
            "revenue",
        ),
    ),
    FeatureDefinition(
        feature_id="debt_to_revenue",
        feature_version="1.0",
        unit="ratio",
        calculator=debt_to_revenue,
        required_inputs=(
            "total_debt",
            "revenue",
        ),
    ),
    FeatureDefinition(
        feature_id="cash_to_debt",
        feature_version="1.0",
        unit="ratio",
        calculator=cash_to_debt,
        required_inputs=(
            "cash_and_equivalents",
            "total_debt",
        ),
    ),
    FeatureDefinition(
        feature_id="cash_conversion_ratio",
        feature_version="1.0",
        unit="percent",
        calculator=cash_conversion_ratio,
        required_inputs=(
            "operating_cash_flow",
            "net_profit",
        ),
    ),
)