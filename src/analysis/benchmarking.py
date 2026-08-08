from dataclasses import dataclass
from decimal import Decimal

from src.data.company.financials import FinancialSnapshot


@dataclass(frozen=True)
class BenchmarkResult:
    metric: str
    company_value: Decimal
    peer_median: Decimal
    percentile: Decimal
    relative_to_peers: str


def median(values: list[Decimal]) -> Decimal:
    if not values:
        raise ValueError("Cannot calculate median of empty values.")

    ordered = sorted(values)

    middle = len(ordered) // 2

    if len(ordered) % 2:
        return ordered[middle]

    return (
        ordered[middle - 1]
        + ordered[middle]
    ) / Decimal("2")


def percentile_rank(
    value: Decimal,
    values: list[Decimal],
) -> Decimal:

    if not values:
        raise ValueError(
            "Cannot calculate percentile without peers."
        )

    below_or_equal = sum(
        candidate <= value
        for candidate in values
    )

    return (
        Decimal(below_or_equal)
        / Decimal(len(values))
    ) * Decimal("100")


def benchmark_metric(
    company: FinancialSnapshot,
    peers: list[FinancialSnapshot],
    metric: str,
) -> BenchmarkResult | None:

    company_value = getattr(
        company,
        metric,
        None,
    )

    if company_value is None:
        return None

    peer_values = [
        getattr(peer, metric)
        for peer in peers
        if getattr(peer, metric, None) is not None
    ]

    if not peer_values:
        return None

    peer_median = median(peer_values)

    percentile = percentile_rank(
        company_value,
        peer_values,
    )

    if company_value > peer_median:
        relative = "ABOVE_PEER_MEDIAN"

    elif company_value < peer_median:
        relative = "BELOW_PEER_MEDIAN"

    else:
        relative = "AT_PEER_MEDIAN"

    return BenchmarkResult(
        metric=metric,
        company_value=company_value,
        peer_median=peer_median,
        percentile=percentile,
        relative_to_peers=relative,
    )


def benchmark_standard_metrics(
    company: FinancialSnapshot,
    peers: list[FinancialSnapshot],
) -> list[BenchmarkResult]:

    metrics = [
        "revenue",
        "net_profit",
        "receivables",
        "payables",
        "operating_cash_flow",
        "free_cash_flow",
        "total_debt",
        "cash_and_equivalents",
    ]

    results: list[BenchmarkResult] = []

    for metric in metrics:

        result = benchmark_metric(
            company,
            peers,
            metric,
        )

        if result is not None:
            results.append(result)

    return results
