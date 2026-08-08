from decimal import Decimal

from src.data.company.financials import FinancialSnapshot


def safe_divide(
    numerator: Decimal | None,
    denominator: Decimal | None,
) -> Decimal | None:

    if numerator is None or denominator is None:
        return None

    if denominator == 0:
        return None

    return numerator / denominator


def percentage(
    value: Decimal | None,
) -> Decimal | None:

    if value is None:
        return None

    return value * Decimal("100")


def revenue_growth(
    previous: FinancialSnapshot,
    current: FinancialSnapshot,
) -> Decimal | None:

    if previous.revenue is None or current.revenue is None:
        return None

    if previous.revenue == 0:
        return None

    return (
        (current.revenue - previous.revenue)
        / abs(previous.revenue)
    ) * Decimal("100")


def net_profit_margin(
    snapshot: FinancialSnapshot,
) -> Decimal | None:

    return percentage(
        safe_divide(
            snapshot.net_profit,
            snapshot.revenue,
        )
    )


def operating_cash_flow_margin(
    snapshot: FinancialSnapshot,
) -> Decimal | None:

    return percentage(
        safe_divide(
            snapshot.operating_cash_flow,
            snapshot.revenue,
        )
    )


def free_cash_flow_margin(
    snapshot: FinancialSnapshot,
) -> Decimal | None:

    return percentage(
        safe_divide(
            snapshot.free_cash_flow,
            snapshot.revenue,
        )
    )


def receivables_to_revenue(
    snapshot: FinancialSnapshot,
) -> Decimal | None:

    return percentage(
        safe_divide(
            snapshot.receivables,
            snapshot.revenue,
        )
    )


def payables_to_revenue(
    snapshot: FinancialSnapshot,
) -> Decimal | None:

    return percentage(
        safe_divide(
            snapshot.payables,
            snapshot.revenue,
        )
    )


def debt_to_revenue(
    snapshot: FinancialSnapshot,
) -> Decimal | None:

    return safe_divide(
        snapshot.total_debt,
        snapshot.revenue,
    )


def cash_to_debt(
    snapshot: FinancialSnapshot,
) -> Decimal | None:

    return safe_divide(
        snapshot.cash_and_equivalents,
        snapshot.total_debt,
    )


def cash_conversion_ratio(
    snapshot: FinancialSnapshot,
) -> Decimal | None:

    return percentage(
        safe_divide(
            snapshot.operating_cash_flow,
            snapshot.net_profit,
        )
    )
