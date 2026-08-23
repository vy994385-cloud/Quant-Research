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

    if current.profit_cash_flow_divergence:
        anomalies.append(
            FinancialAnomaly(
                metric="profit_cfo_divergence",
                current_change=(
                    current.operating_cash_flow
                    or Decimal("0")
                ),
                comparison_change=None,
                severity="MEDIUM",
                explanation=(
                    "Net profit is positive while operating "
                    "cash flow is negative. This divergence "
                    "may indicate accrual-based earnings that "
                    "are not backed by cash generation."
                ),
            )
        )

    # Revenue vs cash generation divergence
    cash_flow_change = percentage_change(
        previous.operating_cash_flow,
        current.operating_cash_flow,
    )

    if (
        revenue_change is not None
        and cash_flow_change is not None
    ):
        divergence = revenue_change - cash_flow_change

        if divergence >= Decimal("20"):
            anomalies.append(
                FinancialAnomaly(
                    metric="revenue_cash_flow_divergence",
                    current_change=revenue_change,
                    comparison_change=cash_flow_change,
                    severity="MEDIUM",
                    explanation=(
                        "Revenue is growing materially faster "
                        "than operating cash flow. This may "
                        "indicate revenue recognition issues, "
                        "working capital build-up, or "
                        "collection challenges."
                    ),
                )
            )

    # Growth vs margin divergence
    if (
        revenue_change is not None
        and revenue_change > Decimal("10")
    ):
        # Calculate margin change
        prev_margin = None
        curr_margin = None

        if (
            previous.revenue is not None
            and previous.revenue > 0
            and previous.net_profit is not None
        ):
            prev_margin = (
                previous.net_profit / previous.revenue
            ) * Decimal("100")

        if (
            current.revenue is not None
            and current.revenue > 0
            and current.net_profit is not None
        ):
            curr_margin = (
                current.net_profit / current.revenue
            ) * Decimal("100")

        if prev_margin is not None and curr_margin is not None:
            margin_change = curr_margin - prev_margin

            if margin_change < Decimal("-5"):
                anomalies.append(
                    FinancialAnomaly(
                        metric="growth_margin_divergence",
                        current_change=revenue_change,
                        comparison_change=margin_change.quantize(
                            Decimal("0.01")
                        ),
                        severity="MEDIUM",
                        explanation=(
                            f"Revenue grew {revenue_change:.1f}% "
                            f"but net margin declined by "
                            f"{abs(margin_change):.1f}pp. This "
                            "may indicate pricing pressure, "
                            "cost inflation, or mix shift."
                        ),
                    )
                )

    # Earnings vs FCF divergence
    earnings_change = percentage_change(
        previous.net_profit,
        current.net_profit,
    )
    fcf_change = percentage_change(
        previous.free_cash_flow,
        current.free_cash_flow,
    )

    if (
        earnings_change is not None
        and fcf_change is not None
    ):
        divergence = earnings_change - fcf_change

        if divergence >= Decimal("30"):
            anomalies.append(
                FinancialAnomaly(
                    metric="earnings_fcf_divergence",
                    current_change=earnings_change,
                    comparison_change=fcf_change,
                    severity="MEDIUM",
                    explanation=(
                        "Earnings are growing materially faster "
                        "than free cash flow. This may indicate "
                        "capital intensity, working capital "
                        "build-up, or earnings quality concerns."
                    ),
                )
            )

    # Debt vs cash generation divergence
    debt_change = percentage_change(
        previous.total_debt,
        current.total_debt,
    )

    if (
        debt_change is not None
        and cash_flow_change is not None
    ):
        divergence = debt_change - cash_flow_change

        if divergence >= Decimal("20"):
            anomalies.append(
                FinancialAnomaly(
                    metric="debt_cash_flow_divergence",
                    current_change=debt_change,
                    comparison_change=cash_flow_change,
                    severity="MEDIUM",
                    explanation=(
                        "Debt is growing materially faster "
                        "than operating cash flow. This may "
                        "indicate leverage building without "
                        "corresponding cash generation."
                    ),
                )
            )

    return anomalies
