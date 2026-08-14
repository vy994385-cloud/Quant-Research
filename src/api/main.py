from datetime import date, timedelta
from decimal import Decimal
from threading import Lock
from time import monotonic

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from src.analysis.company_intelligence import (
    EvidenceReference,
    IntelligenceDirection,
    IntelligenceSignal,
    build_company_research_snapshot,
)
from src.analysis.financial_trends import FinancialTrend
from src.analysis.financial_trends_engine import summarize_trends
from src.analysis.research_scoring import calculate_research_score
from src.data.providers.yahoo_provider import (
    YahooFinanceMarketDataProvider,
)
from src.data.providers.yahoo_financials import (
    YahooFinanceFinancialProvider,
)
from src.research.market_engine import (
    run_market_research,
)


app = FastAPI(
    title="Quant Research API",
    version="0.2.0",
    description=(
        "Research and company-intelligence API. "
        "Provides descriptive analytical evidence, "
        "rankings and research signals. "
        "It does not issue trading instructions."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------

market_provider = YahooFinanceMarketDataProvider()
financial_provider = YahooFinanceFinancialProvider()

DEFAULT_BENCHMARK = "^NSEI"

# Market data needs enough history for 20-day features.
MARKET_LOOKBACK_DAYS = 365

# Financial provider returns annual observations.
FINANCIAL_LOOKBACK_DAYS = 3650

# ---------------------------------------------------------------------
# Market research cache
# ---------------------------------------------------------------------

RESEARCH_CACHE_TTL_SECONDS = 300


class _ResearchCache:
    """
    Small process-local cache for expensive universe research.

    The cache is intentionally isolated from the research engine so
    that the engine remains deterministic and reusable by backtests,
    notebooks and other callers.

    A future production deployment can replace this with Redis or a
    persistent cache without changing the research pipeline.
    """

    def __init__(
        self,
        ttl_seconds: int = RESEARCH_CACHE_TTL_SECONDS,
    ) -> None:
        if ttl_seconds <= 0:
            raise ValueError(
                "ttl_seconds must be greater than zero."
            )

        self.ttl_seconds = ttl_seconds
        self._lock = Lock()
        self._value = None
        self._expires_at = 0.0
        self._key = None

    def get(self, key):
        now = monotonic()

        with self._lock:
            if (
                self._value is None
                or self._key != key
                or now >= self._expires_at
            ):
                return None

            return self._value

    def set(self, key, value) -> None:
        with self._lock:
            self._key = key
            self._value = value
            self._expires_at = (
                monotonic() + self.ttl_seconds
            )

    def clear(self) -> None:
        with self._lock:
            self._key = None
            self._value = None
            self._expires_at = 0.0


research_cache = _ResearchCache()

# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "quant-research-api",
        "version": "0.2.0",
        "providers": {
            "market": "yahoo_finance",
            "financials": "yahoo_finance",
        },
    }


# ---------------------------------------------------------------------
# DEMO RESEARCH DATASET
# ---------------------------------------------------------------------

def demo_research() -> dict:
    """
    Deterministic synthetic research payload.

    DEMO remains available for frontend development and tests.
    """

    trends = [
        FinancialTrend(
            metric="revenue",
            direction="INCREASING",
            observations=2,
            average_change=Decimal("850"),
            explanation=(
                "Revenue increased across the supplied "
                "reporting periods."
            ),
            change=Decimal("850"),
        ),
        FinancialTrend(
            metric="net_profit",
            direction="INCREASING",
            observations=2,
            average_change=Decimal("210"),
            explanation=(
                "Net profit increased across the supplied "
                "reporting periods."
            ),
            change=Decimal("210"),
        ),
        FinancialTrend(
            metric="operating_cash_flow",
            direction="INCREASING",
            observations=2,
            average_change=Decimal("175"),
            explanation=(
                "Operating cash flow increased across the "
                "supplied reporting periods."
            ),
            change=Decimal("175"),
        ),
        FinancialTrend(
            metric="total_debt",
            direction="DECREASING",
            observations=2,
            average_change=Decimal("-120"),
            explanation=(
                "Total debt decreased across the supplied "
                "reporting periods."
            ),
            change=Decimal("-120"),
        ),
        FinancialTrend(
            metric="receivables",
            direction="INCREASING",
            observations=2,
            average_change=Decimal("95"),
            explanation=(
                "Receivables increased across the supplied "
                "reporting periods."
            ),
            change=Decimal("95"),
        ),
    ]

    summaries = summarize_trends(trends)

    signals = [
        IntelligenceSignal(
            code="REVENUE_GROWTH",
            title="Revenue growth",
            description=(
                "Revenue shows a persistent increasing "
                "direction across the supplied periods."
            ),
            direction=IntelligenceDirection.POSITIVE,
            materiality=4,
            confidence=Decimal("0.91"),
        ),
        IntelligenceSignal(
            code="DEBT_REDUCTION",
            title="Debt reduction",
            description=(
                "Total debt has declined across the supplied "
                "reporting periods."
            ),
            direction=IntelligenceDirection.POSITIVE,
            materiality=4,
            confidence=Decimal("0.88"),
        ),
        IntelligenceSignal(
            code="RECEIVABLES_GROWTH",
            title="Receivables increasing",
            description=(
                "Receivables are increasing and should be "
                "monitored alongside revenue and cash flow."
            ),
            direction=IntelligenceDirection.NEGATIVE,
            materiality=3,
            confidence=Decimal("0.76"),
        ),
    ]

    evidence = [
        EvidenceReference(
            source_name="Research Dataset",
            source_type="ANALYTICAL",
            title="Synthetic company research dataset",
            published_date=date(2026, 8, 8),
            reliability_tier=3,
            reference="demo-company-001",
        )
    ]

    snapshot = build_company_research_snapshot(
        symbol="DEMO",
        company_name="Demo Industries",
        as_of_date=date(2026, 8, 8),
        signals=signals,
        financial_observations=[
            "Revenue: 8,450",
            "Net profit: 1,240",
            "Operating cash flow: 1,110",
            "Free cash flow: 920",
        ],
        ownership_observations=[
            "Promoter ownership: 51.2%",
            "Institutional ownership: 27.4%",
            "Public ownership: 21.4%",
        ],
        management_observations=[
            "No material management change detected.",
        ],
        event_observations=[
            "Quarterly financial results available.",
        ],
        market_observations=[
            "Price structure is currently constructive.",
            "Relative strength remains above baseline.",
        ],
        risk_observations=[
            "Receivables growth requires monitoring.",
        ],
        evidence=evidence,
    )

    score = calculate_research_score(
        fundamentals=Decimal("82"),
        financial_trends=Decimal("86"),
        cash_flow=Decimal("84"),
        balance_sheet=Decimal("81"),
        risk=Decimal("68"),
        management=Decimal("78"),
        market_behavior=Decimal("80"),
        evidence_quality=Decimal("88"),
    )

    return {
        "company": {
            "symbol": snapshot.symbol,
            "name": snapshot.company_name,
            "as_of": snapshot.as_of_date.isoformat(),
        },
        "research_score": {
            "total": str(score.total),
            "signal": score.signal,
            "confidence": str(score.confidence),
            "components": {
                "fundamentals": str(score.fundamentals),
                "financial_trends": str(
                    score.financial_trends
                ),
                "cash_flow": str(score.cash_flow),
                "balance_sheet": str(score.balance_sheet),
                "risk": str(score.risk),
                "management": str(score.management),
                "market_behavior": str(
                    score.market_behavior
                ),
                "evidence_quality": str(
                    score.evidence_quality
                ),
            },
        },
        "intelligence": {
            "direction": snapshot.direction.value,
            "signal_count": snapshot.signal_count,
            "material_signal_count": (
                snapshot.material_signal_count
            ),
            "positive_signal_count": (
                snapshot.positive_signal_count
            ),
            "negative_signal_count": (
                snapshot.negative_signal_count
            ),
            "signals": [
                {
                    "code": signal.code,
                    "title": signal.title,
                    "description": signal.description,
                    "direction": signal.direction.value,
                    "materiality": signal.materiality,
                    "confidence": str(
                        signal.confidence
                    ),
                }
                for signal in snapshot.signals
            ],
        },
        "financial_trends": [
            {
                "metric": summary.metric,
                "direction": summary.direction,
                "observations": summary.observations,
                "average_change": str(
                    summary.average_change
                ),
                "positive_periods": (
                    summary.positive_periods
                ),
                "negative_periods": (
                    summary.negative_periods
                ),
                "stable_periods": (
                    summary.stable_periods
                ),
                "consistency": str(
                    summary.consistency
                ),
                "explanation": summary.explanation,
            }
            for summary in summaries
        ],
        "observations": {
            "financial": (
                snapshot.financial_observations
            ),
            "ownership": (
                snapshot.ownership_observations
            ),
            "management": (
                snapshot.management_observations
            ),
            "related_parties": (
                snapshot.related_party_observations
            ),
            "events": snapshot.event_observations,
            "market": snapshot.market_observations,
            "risk": snapshot.risk_observations,
        },
        "evidence": [
            {
                "source_name": item.source_name,
                "source_type": item.source_type,
                "title": item.title,
                "published_date": (
                    item.published_date.isoformat()
                    if item.published_date
                    else None
                ),
                "reliability_tier": (
                    item.reliability_tier
                ),
                "reference": item.reference,
            }
            for item in snapshot.evidence
        ],
        "is_trade_signal": snapshot.is_trade_signal,
    }


# ---------------------------------------------------------------------
# Demo research endpoint
# ---------------------------------------------------------------------

@app.get("/api/research/demo")
def get_demo_research() -> dict:
    return demo_research()


# ---------------------------------------------------------------------
# Ranking serialization
# ---------------------------------------------------------------------

def _ranking_payload(ranking) -> dict:
    return {
        "symbol": ranking.symbol,
        "horizon": ranking.horizon,
        "score": str(ranking.score),
        "signal": ranking.rank_signal,
        "confidence": str(ranking.confidence),
        "priority": ranking.priority,
        "is_high_priority": ranking.is_high_priority,
        "components": {
            key: str(value)
            for key, value in ranking.components.items()
        },
    }


# ---------------------------------------------------------------------
# Stock report serialization
# ---------------------------------------------------------------------

def _report_payload(report) -> dict:
    snapshot = report.company_intelligence

    return {
        "company": {
            "symbol": report.symbol,
            "name": snapshot.company_name,
            "as_of": report.as_of_date.isoformat(),
        },

        "research_score": {
            "total": str(
                report.research_score.total
            ),
            "signal": report.research_score.signal,
            "confidence": str(
                report.research_score.confidence
            ),
            "components": {
                "fundamentals": str(
                    report.research_score.fundamentals
                ),
                "financial_trends": str(
                    report.research_score.financial_trends
                ),
                "cash_flow": str(
                    report.research_score.cash_flow
                ),
                "balance_sheet": str(
                    report.research_score.balance_sheet
                ),
                "risk": str(
                    report.research_score.risk
                ),
                "management": str(
                    report.research_score.management
                ),
                "market_behavior": str(
                    report.research_score.market_behavior
                ), 
                "evidence_quality": str(
                    report.research_score.evidence_quality
                ),
            },
        },

        "rankings": {
            "intraday": _ranking_payload(
                report.intraday
            ),
            "swing": _ranking_payload(
                report.swing
            ),
            "long_term": _ranking_payload(
                report.long_term
            ),
        },

        "highest_priority_horizon": (
            report.highest_priority_horizon
        ),

        "average_ranking_score": str(
            report.average_ranking_score
        ),

        "research_ready": report.is_research_ready,

        "intelligence": {
            "direction": snapshot.direction.value,
            "signal_count": snapshot.signal_count,
            "material_signal_count": (
                snapshot.material_signal_count
            ),
            "positive_signal_count": (
                snapshot.positive_signal_count
            ),
            "negative_signal_count": (
                snapshot.negative_signal_count
            ),
            "signals": [
                {
                    "code": signal.code,
                    "title": signal.title,
                    "description": signal.description,
                    "direction": signal.direction.value,
                    "materiality": signal.materiality,
                    "confidence": str(
                        signal.confidence
                    ),
                }
                for signal in snapshot.signals
            ],
        },

        "observations": {
            "financial": (
                snapshot.financial_observations
            ),
            "ownership": (
                snapshot.ownership_observations
            ),
            "management": (
                snapshot.management_observations
            ),
            "related_parties": (
                snapshot.related_party_observations
            ),
            "events": snapshot.event_observations,
            "market": snapshot.market_observations,
            "risk": snapshot.risk_observations,
        },

        "evidence": [
            {
                "source_name": item.source_name,
                "source_type": item.source_type,
                "title": item.title,
                "published_date": (
                    item.published_date.isoformat()
                    if item.published_date
                    else None
                ),
                "reliability_tier": (
                    item.reliability_tier
                ),
                "reference": item.reference,
            }
            for item in snapshot.evidence
        ],

        "is_trade_signal": (
            snapshot.is_trade_signal
        ),
    }


# ---------------------------------------------------------------------
# Internal real-stock research
# ---------------------------------------------------------------------

def _run_real_stock_research(
    symbol: str,
):
    """
    Run the existing provider -> feature -> analysis pipeline
    for one real NSE equity.

    This function deliberately keeps external-provider logic
    outside the scoring layer.
    """

    normalized = symbol.strip().upper()

    if not normalized:
        raise ValueError(
            "symbol cannot be empty"
        )

    end_date = date.today()

    market_start = (
        end_date
        - timedelta(days=MARKET_LOOKBACK_DAYS)
    )

    financial_start = (
        end_date
        - timedelta(days=FINANCIAL_LOOKBACK_DAYS)
    )

    # A small temporary universe file lets the existing
    # research engine operate on one requested symbol without
    # changing its provider-independent architecture.
    import tempfile
    from pathlib import Path

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
    ) as handle:
        handle.write("symbol\n")
        handle.write(f"{normalized}\n")
        universe_file = handle.name

    try:
        result = run_market_research(
            provider=market_provider,
            financial_provider=financial_provider,
            universe_file=universe_file,
            benchmark_symbol=DEFAULT_BENCHMARK,
            start_date=market_start,
            end_date=end_date,
        )
    finally:
        Path(universe_file).unlink(
            missing_ok=True
        )

    if not result.results:
        raise RuntimeError(
            f"No usable market data was returned "
            f"for {normalized}."
        )

    return result.results[0]


# ---------------------------------------------------------------------
# Stock search
# IMPORTANT: this route must appear before /api/stocks/{symbol}
# ---------------------------------------------------------------------

@app.get("/api/stocks/search")
def search_stocks(
    q: str = Query(
        default="",
        min_length=0,
        description=(
            "Search by NSE stock symbol. "
            "A symbol is validated against the live "
            "market-data provider."
        ),
    ),
) -> dict:

    query = q.strip().upper()

    if not query:
        return {
            "query": q,
            "count": 1,
            "results": [
                {
                    "symbol": "DEMO",
                    "company_name": "Demo Industries",
                    "score": "81.00",
                    "signal": "POSITIVE",
                    "research_ready": True,
                }
            ],
        }

    if query == "DEMO":
        return {
            "query": q,
            "count": 1,
            "results": [
                {
                    "symbol": "DEMO",
                    "company_name": "Demo Industries",
                    "score": "81.00",
                    "signal": "POSITIVE",
                    "research_ready": True,
                }
            ],
        }

    try:
        report = _run_real_stock_research(
            query
        )
    except (RuntimeError, ValueError):
        return {
            "query": q,
            "count": 0,
            "results": [],
        }

    return {
        "query": q,
        "count": 1,
        "results": [
            {
                "symbol": report.symbol,
                "company_name": (
                    report.company_intelligence.company_name
                    or report.symbol
                ),
                "score": str(
                    report.research_score.total
                ),
                "signal": report.research_score.signal,
                "research_ready": (
                    report.is_research_ready
                ),
            }
        ],
    }


def _research_cache_key(
    *,
    universe_file: str,
    benchmark_symbol: str,
    start_date: date,
    end_date: date,
) -> tuple:
    """
    Build a deterministic cache key for a research run.
    """

    return (
        universe_file,
        benchmark_symbol,
        start_date,
        end_date,
    )


def _get_market_research():
    """
    Return the current universe research result.

    Multiple API endpoints share this result so a request for
    /api/stocks followed by /api/rankings/LONG_TERM does not
    download and analyze the entire universe twice.
    """

    universe_file = (
        "data/raw/universe/nse_equities.csv"
    )

    end_date = date.today()
    start_date = (
        end_date
        - timedelta(days=MARKET_LOOKBACK_DAYS)
    )

    key = _research_cache_key(
        universe_file=universe_file,
        benchmark_symbol=DEFAULT_BENCHMARK,
        start_date=start_date,
        end_date=end_date,
    )

    cached = research_cache.get(key)

    if cached is not None:
        return cached

    result = run_market_research(
        provider=market_provider,
        financial_provider=financial_provider,
        universe_file=universe_file,
        benchmark_symbol=DEFAULT_BENCHMARK,
        start_date=start_date,
        end_date=end_date,
    )

    research_cache.set(key, result)

    return result

# ---------------------------------------------------------------------
# Stock universe
# ---------------------------------------------------------------------

@app.get("/api/stocks")
def list_stocks() -> dict:
    """
    Run the live research pipeline across the configured
    NSE universe.

    Individual symbols that fail provider validation are skipped.
    """

    result = _get_market_research()

    results = []

    for report in result.results:
        results.append(
            {
                "symbol": report.symbol,
                "company_name": (
                    report.company_intelligence.company_name
                    or report.symbol
                ),
                "score": str(
                    report.research_score.total
                ),
                "signal": report.research_score.signal,
                "research_ready": (
                    report.is_research_ready
                ),
            }
        )

        results.sort(
        key=lambda item: Decimal(item["score"]),
        reverse=True,
    )

    return {
        "horizon": normalized,
        "count": len(results),
        "results": results,
    }


# ---------------------------------------------------------------------
# Horizon rankings
# ---------------------------------------------------------------------

@app.get("/api/rankings/{horizon}")
def get_rankings(horizon: str) -> dict:
    requested = horizon.strip().upper()

    aliases = {
        "INTRADAY": "INTRADAY",
        "INTRA": "INTRADAY",
        "SWING": "SWING",
        "LONG_TERM": "LONG_TERM",
        "LONG-TERM": "LONG_TERM",
        "LONGTERM": "LONG_TERM",
    }

    normalized = aliases.get(requested)

    if normalized is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_horizon",
                "supported": [
                    "INTRADAY",
                    "SWING",
                    "LONG_TERM",
                ],
            },
        )

    result = _get_market_research()

    results = []

    # Always expose the deterministic DEMO research fixture.
    results.append(
        _demo_ranking(normalized)
    )

    for report in result.results:
        if report.symbol == "DEMO":
            continue

        if normalized == "INTRADAY":
            ranking = report.intraday
        elif normalized == "SWING":
            ranking = report.swing
        else:
            ranking = report.long_term

        results.append(
            _ranking_payload(ranking)
        )

    return {
        "horizon": normalized,
        "count": len(results),
        "results": results,
    }


# ---------------------------------------------------------------------
# Demo rankings
# ---------------------------------------------------------------------

def _demo_ranking(horizon: str) -> dict:
    score_map = {
        "INTRADAY": {
            "score": "78.00",
            "signal": "HIGH_PRIORITY",
            "confidence": "74.00",
        },
        "SWING": {
            "score": "80.00",
            "signal": "HIGH_PRIORITY",
            "confidence": "81.00",
        },
        "LONG_TERM": {
            "score": "84.00",
            "signal": "HIGH_PRIORITY",
            "confidence": "88.00",
        },
    }

    values = score_map[horizon]

    return {
        "symbol": "DEMO",
        "company_name": "Demo Industries",
        "horizon": horizon,
        **values,
    }


# ---------------------------------------------------------------------
# All horizon rankings for one stock
# ---------------------------------------------------------------------

@app.get("/api/stocks/{symbol}/rankings")
def get_stock_rankings(symbol: str) -> dict:
    requested = symbol.strip().upper()

    if requested == "DEMO":
        return {
            "symbol": "DEMO",
            "company_name": "Demo Industries",
            "rankings": {
                "intraday": _demo_ranking(
                    "INTRADAY"
                ),
                "swing": _demo_ranking(
                    "SWING"
                ),
                "long_term": _demo_ranking(
                    "LONG_TERM"
                ),
            },
        }

    try:
        report = _run_real_stock_research(
            requested
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "stock_not_available",
                "symbol": requested,
                "message": str(exc),
            },
        ) from exc

    return {
        "symbol": report.symbol,
        "company_name": (
            report.company_intelligence.company_name
            or report.symbol
        ),
        "rankings": {
            "intraday": _ranking_payload(
                report.intraday
            ),
            "swing": _ranking_payload(
                report.swing
            ),
            "long_term": _ranking_payload(
                report.long_term
            ),
        },
    }


# ---------------------------------------------------------------------
# Stock research summary
# ---------------------------------------------------------------------

@app.get("/api/stocks/{symbol}/research")
def get_stock_research(symbol: str) -> dict:
    requested = symbol.strip().upper()

    if requested == "DEMO":
        data = demo_research()

        data["rankings"] = {
            "intraday": _demo_ranking("INTRADAY"),
            "swing": _demo_ranking("SWING"),
            "long_term": _demo_ranking("LONG_TERM"),
        }

        return data

    try:
        report = _run_real_stock_research(
            requested
        )
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "stock_not_available",
                "symbol": requested,
                "message": str(exc),
            },
        ) from exc

    return _report_payload(report)

# ---------------------------------------------------------------------
# Stock detail
# ---------------------------------------------------------------------

@app.get("/api/stocks/{symbol}")
def get_stock(symbol: str) -> dict:
    requested = symbol.strip().upper()

    if requested == "DEMO":
        data = demo_research()

        data["rankings"] = {
            "intraday": _demo_ranking("INTRADAY"),
            "swing": _demo_ranking("SWING"),
            "long_term": _demo_ranking("LONG_TERM"),
        }

        return data

    try:
        report = _run_real_stock_research(requested)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "stock_not_available",
                "symbol": requested,
                "message": str(exc),
            },
        ) from exc

    return _report_payload(report)