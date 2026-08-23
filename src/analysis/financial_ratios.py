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


def return_on_equity(
    snapshot: FinancialSnapshot,
) -> Decimal | None:

    return percentage(
        safe_divide(
            snapshot.net_profit,
            getattr(snapshot, "shareholders_equity", None)
            or getattr(snapshot, "total_equity", None),
        )
    )


def return_on_capital_employed(
    snapshot: FinancialSnapshot,
) -> Decimal | None:

    equity = getattr(snapshot, "shareholders_equity", None)
    total_debt = snapshot.total_debt

    if equity is None or total_debt is None:
        return None

    capital_employed = equity + total_debt

    return percentage(
        safe_divide(
            snapshot.operating_profit,
            capital_employed,
        )
    )


def working_capital(
    snapshot: FinancialSnapshot,
) -> Decimal | None:

    current_assets = getattr(snapshot, "current_assets", None)
    current_liabilities = getattr(
        snapshot, "current_liabilities", None
    )

    if current_assets is None or current_liabilities is None:
        return None

    return current_assets - current_liabilities


def current_ratio(
    snapshot: FinancialSnapshot,
) -> Decimal | None:

    return safe_divide(
        getattr(snapshot, "current_assets", None),
        getattr(snapshot, "current_liabilities", None),
    )


def accruals_ratio(
    snapshot: FinancialSnapshot,
) -> Decimal | None:

    if snapshot.total_assets is None or snapshot.total_assets == 0:
        return None

    net_profit = snapshot.net_profit
    operating_cash_flow = snapshot.operating_cash_flow

    if net_profit is None or operating_cash_flow is None:
        return None

    accruals = net_profit - operating_cash_flow

    return safe_divide(
        accruals,
        snapshot.total_assets,
    )
