from decimal import Decimal

from src.data.company.financials import FinancialSnapshot


class FinancialAnomaly:
    """
    Represents an analytical observation.

    An anomaly is NOT automatically a negative event.
    It simply identifies something worth investigating.
    """

    def __init__(
        self,
        metric: str,
        current_change: Decimal,
        comparison_change: Decimal | None,
        severity: str,
        explanation: str,
    ):
        self.metric = metric
        self.current_change = current_change
        self.comparison_change = comparison_change
        self.severity = severity
        self.explanation = explanation

    def __repr__(self) -> str:
        return (
            f"FinancialAnomaly("
            f"metric={self.metric!r}, "
            f"severity={self.severity!r})"
        )


def percentage_change(
    previous: Decimal | None,
    current: Decimal | None,
) -> Decimal | None:

    if previous is None or current is None:
        return None

    if previous == 0:
        return None

    return ((current - previous) / abs(previous)) * Decimal("100")


def analyze_financial_change(
    previous: FinancialSnapshot,
    current: FinancialSnapshot,
) -> list[FinancialAnomaly]:

    anomalies: list[FinancialAnomaly] = []

    revenue_change = percentage_change(
        previous.revenue,
        current.revenue,
    )

    receivables_change = percentage_change(
        previous.receivables,
        current.receivables,
    )

    payables_change = percentage_change(
        previous.payables,
        current.payables,
    )

    if (
        revenue_change is not None
        and receivables_change is not None
    ):

        divergence = receivables_change - revenue_change

        if divergence >= Decimal("20"):

            anomalies.append(
                FinancialAnomaly(
                    metric="receivables",
                    current_change=receivables_change,
                    comparison_change=revenue_change,
                    severity="MEDIUM",
                    explanation=(
                        "Receivables are growing materially faster "
                        "than revenue. This may warrant investigation "
                        "of collection, customer concentration, "
                        "credit terms, or revenue recognition."
                    ),
                )
            )

    if (
        revenue_change is not None
        and payables_change is not None
    ):

        divergence = payables_change - revenue_change

        if divergence >= Decimal("20"):

            anomalies.append(
                FinancialAnomaly(
                    metric="payables",
                    current_change=payables_change,
                    comparison_change=revenue_change,
                    severity="MEDIUM",
                    explanation=(
                        "Payables are growing materially faster "
                        "than revenue. Possible areas for investigation "
                        "include supplier terms, working-capital pressure, "
                        "or changes in purchasing activity."
                    ),
                )
            )

    return anomalies
