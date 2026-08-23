"""
Recorded backtest / validation service.

Loads recorded market data fixtures for the verified companies and
runs deterministic backtest + ranking validation using the existing
backtest engine and validation pipeline.

No live network access. All data comes from committed CSV fixtures.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from threading import Lock

from src.api.errors import (
    InvalidHorizonError,
    ResearchDataUnavailableError,
    UnknownCompanyError,
)
from src.api.recorded_research import (
    COMPANY_NAMES,
    RecordedCompanyResearchService,
)
from src.backtest.benchmark import BenchmarkResult
from src.backtest.metrics import BacktestMetrics, calculate_backtest_metrics
from src.backtest.models import BacktestBar
from src.backtest.report import BacktestReport, build_backtest_report
from src.backtest.runner import BacktestRunner
from src.backtest.strategy import ThresholdStrategy
from src.data.providers.csv_provider import CSVMarketDataProvider
from src.validation.ranking_outcomes import RankingOutcome, build_ranking_outcome
from src.validation.ranking_validation import (
    RankingObservation,
    RankingValidationResult,
    validate_rankings,
)
from src.validation.ranking_validation_report import (
    RankingValidationReport,
    build_ranking_validation_report,
)
from src.validation.validation_quality_report import (
    ValidationQualityReport,
    build_validation_quality_report,
)
from src.verification.real_data import (
    COMPANIES,
    COMPANY_SECTORS,
    DEFAULT_AS_OF,
    DEFAULT_FIXTURE_DIR,
)

# Horizon lookforward days for ranking validation
_HORIZON_DAYS: dict[str, int] = {
    "INTRADAY": 1,
    "SWING": 5,
    "LONG_TERM": 20,
}

_BACKTEST_INITIAL_CAPITAL = Decimal("1000000")
_BACKTEST_TRANSACTION_COST_RATE = Decimal("0.001")
_MIN_BACKTEST_BARS = 30

_CACHE_MAX_ENTRIES = 128


def _load_stock_bars(
    symbol: str,
    fixture_dir: Path,
) -> list[BacktestBar]:
    """Load stock price bars from the recorded CSV fixture."""
    prefix = symbol.strip().upper().lower()
    csv_path = fixture_dir / f"{prefix}_market.csv"

    if not csv_path.exists():
        raise FileNotFoundError(
            f"Market data fixture not found: {csv_path}"
        )

    provider = CSVMarketDataProvider(csv_path)

    from datetime import timedelta

    end = date(2026, 12, 31)
    start = date(2020, 1, 1)

    price_bars = provider.get_daily_prices(symbol, start, end)

    return [
        BacktestBar(
            symbol=bar.symbol,
            trading_date=bar.trading_date,
            close=bar.close,
        )
        for bar in price_bars
        if bar.symbol == symbol
    ]


def _load_benchmark_bars(
    symbol: str,
    fixture_dir: Path,
) -> list[BacktestBar]:
    """Load Nifty 50 benchmark bars from the same CSV fixture."""
    prefix = symbol.strip().upper().lower()
    csv_path = fixture_dir / f"{prefix}_market.csv"

    if not csv_path.exists():
        return []

    provider = CSVMarketDataProvider(csv_path)

    from datetime import timedelta

    end = date(2026, 12, 31)
    start = date(2020, 1, 1)

    price_bars = provider.get_daily_prices("^NSEI", start, end)

    return [
        BacktestBar(
            symbol="^NSEI",
            trading_date=bar.trading_date,
            close=bar.close,
        )
        for bar in price_bars
    ]


def _align_benchmark(
    stock_bars: list[BacktestBar],
    benchmark_bars: list[BacktestBar],
) -> list[BacktestBar]:
    """Filter benchmark bars to match stock bar date range."""
    if not stock_bars or not benchmark_bars:
        return []

    stock_dates = {bar.trading_date for bar in stock_bars}

    return [
        bar for bar in benchmark_bars
        if bar.trading_date in stock_dates
    ]


def _compute_score(
    close_prices: dict[date, Decimal],
    current_date: date,
    lookback: int = 20,
) -> Decimal | None:
    """
    Compute a momentum score (0-100) from price history.

    Uses a percentile-based approach: where the current price sits
    within the recent lookback range. 0 = at the low, 100 = at the high.
    """
    sorted_dates = sorted(d for d in close_prices if d <= current_date)

    if len(sorted_dates) < lookback:
        return None

    recent = sorted_dates[-lookback:]
    prices = [close_prices[d] for d in recent]

    current = prices[-1]
    low = min(prices)
    high = max(prices)

    if high <= low:
        return Decimal("50")

    position = (current - low) / (high - low)

    score = position * Decimal("100")

    return score.quantize(Decimal("0.1"))


def _run_backtest(
    stock_bars: list[BacktestBar],
    benchmark_bars: list[BacktestBar] | None,
    strategy: ThresholdStrategy,
) -> tuple[
    BacktestReport | None,
    BacktestMetrics | None,
    BenchmarkResult | None,
    BacktestValidation | None,
]:
    """Run a complete backtest and return the results."""
    from src.backtest.validation import (
        BacktestValidation,
        validate_backtest_inputs,
    )

    price_map = {bar.trading_date: bar.close for bar in stock_bars}
    # Bars without enough history have no computable score; they are
    # excluded rather than fabricated with a neutral placeholder, so
    # backtest inputs contain only genuine observations. Insufficient
    # coverage is then reported explicitly by input validation.
    scored_bars = [
        BacktestBar(
            symbol=bar.symbol,
            trading_date=bar.trading_date,
            close=bar.close,
            score=score,
        )
        for bar in stock_bars
        if (score := _compute_score(price_map, bar.trading_date))
        is not None
    ]

    signals = strategy.generate_signals(scored_bars)

    validation = validate_backtest_inputs(
        scored_bars,
        signals,
        minimum_bars=_MIN_BACKTEST_BARS,
    )

    if validation.is_rejected:
        return None, None, None, validation

    runner = BacktestRunner(
        _BACKTEST_INITIAL_CAPITAL,
        transaction_cost_rate=_BACKTEST_TRANSACTION_COST_RATE,
    )

    aligned_benchmark = None
    if benchmark_bars:
        # Align on the scored series so both legs cover the identical
        # trading-date range after warm-up exclusion.
        aligned_benchmark = _align_benchmark(scored_bars, benchmark_bars)

    run = runner.run_strategy(
        scored_bars,
        strategy,
        benchmark_bars=aligned_benchmark if aligned_benchmark else None,
    )

    return run.report, run.metrics, run.benchmark, run.validation


def _build_ranking_observations(
    stock_bars: list[BacktestBar],
    benchmark_bars: list[BacktestBar],
    horizon: str,
    research_score: Decimal,
) -> list[RankingObservation]:
    """
    Build ranking observations by pairing score with forward returns.

    Uses the recorded research score applied at each historical date,
    with forward returns computed from actual market data.
    """
    lookforward = _HORIZON_DAYS.get(horizon, 5)
    bar_map = {bar.trading_date: bar.close for bar in stock_bars}
    bench_map = {bar.trading_date: bar.close for bar in benchmark_bars}

    sorted_dates = sorted(bar_map.keys())
    observations: list[RankingObservation] = []

    for i, ranking_date in enumerate(sorted_dates):
        outcome_idx = i + lookforward

        if outcome_idx >= len(sorted_dates):
            continue

        outcome_date = sorted_dates[outcome_idx]
        entry_price = bar_map[ranking_date]
        outcome_price = bar_map[outcome_date]

        benchmark_return = None
        if ranking_date in bench_map and outcome_date in bench_map:
            b_entry = bench_map[ranking_date]
            b_exit = bench_map[outcome_date]
            if b_entry > Decimal("0"):
                benchmark_return = (b_exit / b_entry) - Decimal("1")

        outcome = build_ranking_outcome(
            symbol="STOCK",
            ranking_date=ranking_date,
            outcome_date=outcome_date,
            horizon=horizon,
            entry_price=entry_price,
            outcome_price=outcome_price,
            benchmark_return=benchmark_return,
        )

        observations.append(
            RankingObservation(
                symbol="STOCK",
                ranking_date=ranking_date,
                horizon=horizon,
                score=research_score,
                outcome=outcome,
            )
        )

    return observations


def _run_validation(
    observations: list[RankingObservation],
    horizon: str,
    window_size: int = 60,
) -> tuple[
    ValidationQualityReport | None,
    RankingValidationReport | None,
    list[dict],
]:
    """Run walk-forward validation on ranking observations."""
    if not observations:
        return None, None, []

    window_results: list[RankingValidationResult] = []

    for start in range(0, len(observations), window_size):
        window_obs = observations[start : start + window_size]

        if len(window_obs) < 5:
            continue

        result = validate_rankings(window_obs)
        window_results.append(result)

    if not window_results:
        return None, None, []

    report = build_ranking_validation_report(window_results)

    consolidated = validate_rankings(observations)
    quality = build_validation_quality_report(consolidated)

    window_details: list[dict] = []
    sorted_dates = sorted(
        {obs.ranking_date for obs in observations}
    )

    for idx, result in enumerate(window_results):
        start_idx = idx * window_size
        end_idx = min(start_idx + window_size, len(sorted_dates))

        w_dates = sorted_dates[start_idx:end_idx]

        window_details.append({
            "window_index": idx,
            "train_start": str(w_dates[0]) if w_dates else None,
            "train_end": str(w_dates[-1]) if w_dates else None,
            "observation_count": result.observation_count,
            "average_forward_return": str(
                result.average_forward_return.quantize(Decimal("0.0001"))
            ),
            "positive_return_rate": str(
                result.positive_return_rate.quantize(Decimal("0.0001"))
            ),
            "score_return_correlation": (
                str(result.score_return_correlation.quantize(Decimal("0.0001")))
                if result.score_return_correlation is not None
                else None
            ),
        })

    return quality, report, window_details


class RecordedValidationService:
    """
    Deterministic backtest + validation service for recorded data.

    Results are cached per (symbol, horizon) because the recorded
    fixtures are immutable.
    """

    def __init__(
        self,
        *,
        research_service: RecordedCompanyResearchService | None = None,
        fixture_dir: str | Path | None = None,
    ) -> None:
        self._research = research_service or RecordedCompanyResearchService()
        self._fixture_dir = Path(fixture_dir or DEFAULT_FIXTURE_DIR)

        self._cache: dict[tuple[str, str], dict] = {}
        self._cache_lock = Lock()

    @property
    def companies(self) -> tuple[str, ...]:
        return COMPANIES

    def validate_company(self, symbol: str) -> str:
        normalized = symbol.strip().upper()

        if not normalized:
            raise UnknownCompanyError(
                "symbol cannot be empty",
                details={"symbol": symbol},
            )

        if normalized not in COMPANY_SECTORS:
            raise UnknownCompanyError(
                "unknown company",
                details={
                    "symbol": normalized,
                    "supported": list(COMPANIES),
                },
            )

        return normalized

    def run(
        self,
        symbol: str,
        horizon: str = "LONG_TERM",
        *,
        as_of: datetime | None = None,
    ) -> dict:
        """Run backtest + validation for one company and horizon."""
        normalized = self.validate_company(symbol)
        horizon = horizon.strip().upper()

        if horizon not in _HORIZON_DAYS:
            raise InvalidHorizonError(
                "unsupported ranking horizon",
                details={
                    "horizon": horizon,
                    "supported": list(_HORIZON_DAYS),
                },
            )

        key = (normalized, horizon)

        with self._cache_lock:
            cached = self._cache.get(key)
            if cached is not None:
                return cached

        try:
            stock_bars = _load_stock_bars(normalized, self._fixture_dir)
            benchmark_bars = _load_benchmark_bars(normalized, self._fixture_dir)
        except FileNotFoundError as exc:
            raise ResearchDataUnavailableError(
                f"market data is not available for {normalized}",
                details={"symbol": normalized, "horizon": horizon},
            ) from exc

        if len(stock_bars) < _MIN_BACKTEST_BARS:
            result = {
                "symbol": normalized,
                "horizon": horizon,
                "as_of": (as_of or DEFAULT_AS_OF).isoformat(),
                "backtest": None,
                "backtest_validation": None,
                "validation_quality": None,
                "validation_report": None,
                "windows": [],
                "strategy_description": (
                    "Insufficient market data for backtest evaluation."
                ),
                "data_coverage": {"stock_bars": len(stock_bars)},
                "notes": [
                    f"Only {len(stock_bars)} market observations available, "
                    f"minimum {_MIN_BACKTEST_BARS} required."
                ],
            }

            with self._cache_lock:
                self._cache[key] = result

            return result

        strategy = ThresholdStrategy(
            buy_threshold=Decimal("70"),
            sell_threshold=Decimal("40"),
        )

        price_map = {bar.trading_date: bar.close for bar in stock_bars}

        scores = []
        for bar in stock_bars:
            score = _compute_score(price_map, bar.trading_date)
            if score is not None:
                scores.append(score)

        avg_score = (
            sum(scores) / Decimal(len(scores))
            if scores
            else Decimal("50")
        )

        backtest_report, backtest_metrics, benchmark_result, bt_validation = (
            _run_backtest(stock_bars, benchmark_bars, strategy)
        )

        backtest_dict = None
        if backtest_report is not None:
            backtest_dict = _serialize_backtest_report(
                backtest_report, benchmark_result
            )

        bt_validation_dict = None
        if bt_validation is not None:
            bt_validation_dict = {
                "status": bt_validation.status,
                "errors": list(bt_validation.errors),
                "warnings": list(bt_validation.warnings),
            }

        observations = _build_ranking_observations(
            stock_bars, benchmark_bars, horizon, avg_score
        )

        quality, report, window_details = _run_validation(
            observations, horizon
        )

        quality_dict = None
        if quality is not None:
            quality_dict = _serialize_quality_report(quality)

        report_dict = None
        if report is not None:
            report_dict = _serialize_validation_report(report)

        result = {
            "symbol": normalized,
            "horizon": horizon,
            "as_of": (as_of or DEFAULT_AS_OF).isoformat(),
            "backtest": backtest_dict,
            "backtest_validation": bt_validation_dict,
            "validation_quality": quality_dict,
            "validation_report": report_dict,
            "windows": window_details,
            "strategy_description": (
                "Threshold strategy: BUY when score >= 70, "
                "SELL when score <= 40. Score computed from "
                "20-day price momentum normalized to 0-100."
            ),
            "data_coverage": {
                "stock_bars": len(stock_bars),
                "benchmark_bars": len(
                    _align_benchmark(stock_bars, benchmark_bars)
                ),
                "ranking_observations": len(observations),
                "validation_windows": len(window_details),
            },
            "notes": [
                "Backtest results describe historical performance only.",
                "Historical results do not guarantee future returns.",
                "Transaction costs: 0.1% per trade.",
                "Benchmark: Nifty 50 (^NSEI) buy-and-hold.",
            ],
        }

        with self._cache_lock:
            if len(self._cache) >= _CACHE_MAX_ENTRIES:
                oldest = next(iter(self._cache))
                self._cache.pop(oldest)
            self._cache[key] = result

        return result

    def run_universe(
        self,
        horizon: str = "LONG_TERM",
        *,
        as_of: datetime | None = None,
        symbols: tuple[str, ...] | None = None,
    ) -> list[dict]:
        """Run backtest + validation for all companies."""
        targets = symbols or self.companies

        results = []
        for symbol in targets:
            try:
                result = self.run(
                    symbol, horizon, as_of=as_of
                )
                results.append(result)
            except Exception:
                continue

        return results


def _serialize_backtest_report(
    report: BacktestReport,
    benchmark: BenchmarkResult | None,
) -> dict:
    """Serialize a BacktestReport to an API contract dict."""
    benchmark_dict = None

    if benchmark is not None:
        benchmark_dict = {
            "benchmark_symbol": benchmark.benchmark_symbol,
            "benchmark_return": str(benchmark.benchmark_return.quantize(Decimal("0.01"))),
            "strategy_return": str(benchmark.strategy_return.quantize(Decimal("0.01"))),
            "excess_return": str(benchmark.excess_return.quantize(Decimal("0.01"))),
            "benchmark_max_drawdown": str(benchmark.benchmark_max_drawdown.quantize(Decimal("0.01"))),
            "benchmark_max_drawdown_percent": str(benchmark.benchmark_max_drawdown_percent.quantize(Decimal("0.01"))),
            "outperforming": benchmark.outperforming,
        }

    return {
        "initial_capital": str(report.initial_capital.quantize(Decimal("0.01"))),
        "final_equity": str(report.final_equity.quantize(Decimal("0.01"))),
        "profit_loss": str(report.profit_loss.quantize(Decimal("0.01"))),
        "total_return": str(report.total_return.quantize(Decimal("0.01"))),
        "trade_count": report.trade_count,
        "winning_trades": report.winning_trades,
        "losing_trades": report.losing_trades,
        "win_rate": str(report.win_rate.quantize(Decimal("0.01"))),
        "max_drawdown": str(report.max_drawdown.quantize(Decimal("0.01"))),
        "max_drawdown_percent": str(report.max_drawdown_percent.quantize(Decimal("0.01"))),
        "exposure_percent": str(report.exposure_percent.quantize(Decimal("0.01"))),
        "cagr": str(report.cagr.quantize(Decimal("0.01"))) if report.cagr is not None else None,
        "sample_size_warning": report.sample_size_warning,
        "research_signal": report.research_signal,
        "limitations": list(report.limitations),
        "benchmark": benchmark_dict,
    }


def _serialize_quality_report(quality: ValidationQualityReport) -> dict:
    """Serialize a ValidationQualityReport to an API contract dict."""
    return {
        "quality": quality.quality.value,
        "score": str(quality.score.quantize(Decimal("0.0001"))),
        "confidence": str(quality.confidence.quantize(Decimal("0.0001"))),
        "observation_count": quality.observation_count,
        "average_forward_return": str(quality.average_forward_return.quantize(Decimal("0.0001"))),
        "median_forward_return": str(quality.median_forward_return.quantize(Decimal("0.0001"))),
        "positive_return_rate": str(quality.positive_return_rate.quantize(Decimal("0.0001"))),
        "average_excess_return": (
            str(quality.average_excess_return.quantize(Decimal("0.0001")))
            if quality.average_excess_return is not None
            else None
        ),
        "positive_excess_return_rate": (
            str(quality.positive_excess_return_rate.quantize(Decimal("0.0001")))
            if quality.positive_excess_return_rate is not None
            else None
        ),
        "score_return_correlation": (
            str(quality.score_return_correlation.quantize(Decimal("0.0001")))
            if quality.score_return_correlation is not None
            else None
        ),
        "reasons": list(quality.reasons),
        "is_actionable": quality.is_actionable,
        "is_strong": quality.is_strong,
        "is_insufficient": quality.is_insufficient,
    }


def _serialize_validation_report(report: RankingValidationReport) -> dict:
    """Serialize a RankingValidationReport to an API contract dict."""
    return {
        "horizon": report.horizon,
        "window_count": report.window_count,
        "observation_count": report.observation_count,
        "average_forward_return": str(report.average_forward_return.quantize(Decimal("0.0001"))),
        "median_forward_return": str(report.median_forward_return.quantize(Decimal("0.0001"))),
        "positive_return_rate": str(report.positive_return_rate.quantize(Decimal("0.0001"))),
        "average_excess_return": (
            str(report.average_excess_return.quantize(Decimal("0.0001")))
            if report.average_excess_return is not None
            else None
        ),
        "positive_excess_return_rate": (
            str(report.positive_excess_return_rate.quantize(Decimal("0.0001")))
            if report.positive_excess_return_rate is not None
            else None
        ),
        "average_score_return_correlation": (
            str(report.average_score_return_correlation.quantize(Decimal("0.0001")))
            if report.average_score_return_correlation is not None
            else None
        ),
        "successful_window_rate": str(report.successful_window_rate.quantize(Decimal("0.0001"))),
        "weak_window_count": report.weak_window_count,
        "robust": report.robust,
        "strengths": list(report.strengths),
        "weaknesses": list(report.weaknesses),
        "unknowns": list(report.unknowns),
        "minimum_window_count": report.minimum_window_count,
        "minimum_successful_window_rate": str(report.minimum_successful_window_rate.quantize(Decimal("0.0001"))),
    }


__all__ = [
    "RecordedValidationService",
]
