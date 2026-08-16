# QUANT-RESEARCH — LAUNCH CHECKPOINT

## Current Status

**Test baseline:** 1004 passed
**Latest commit:** build production research api contract
**Working tree:** clean at last verified checkpoint
**Phase:** Final Beta Launch Sprint

## Product

Evidence-driven quantitative research and company-intelligence platform for Indian markets.

The product is intentionally NOT a simple screener or BUY/SELL generator.

Core pipeline:

REAL DATA
→ RAW ARCHIVE
→ PROVENANCE
→ VALIDATION
→ POINT-IN-TIME CONTEXT
→ FEATURES
→ SIGNALS
→ EVIDENCE SYNTHESIS
→ NARRATIVE
→ COMPANY RESEARCH REPORT
→ RANKING
→ BACKTEST
→ WALK-FORWARD VALIDATION
→ PAPER TRADING
→ ONLY AFTER EXTENSIVE VALIDATION: POSSIBLE EXECUTION

## Completed Core Systems

### Data
- provider abstractions
- Yahoo market provider
- Yahoo financial provider
- company data models
- market ingestion
- provenance
- validation
- security/data contracts
- NSE provider contract/stub

### Company Intelligence
- financial snapshots
- events/news structure
- management
- ownership
- related parties
- evidence references
- company intelligence snapshots
- company research assembly

### Financial Analysis
- ratios
- multi-period trends
- financial anomalies
- financial risk scoring
- financial scoring
- cash-flow analysis
- peer benchmarking

### Research Intelligence
- point-in-time research context
- leakage protection
- feature snapshots
- feature quality evaluation
- research feature engine
- research signals
- evidence synthesis
- conflict detection
- evidence narrative
- company research reports
- source acquisition pipeline (planner / providers / validator / agent / runner)
- relevance-routed, deduplicated research observation extraction
- acquired-observation evidence integration (point-in-time safe)
- real-data research verification (recorded TCS fixtures, full-path PIT checks)
- multi-company real-data verification (TCS, RELIANCE, INFY, HDFCBANK,
  SUNPHARMA, M&M across 5 sectors; recorded market/financials/sources fixtures;
  per-company point-in-time + provenance checks; provider failure isolation with
  graceful degradation under missing/stale/failed/partial/conflicting sources)

### Ranking
- horizon-specific ranking
- Intraday
- Swing
- Long-term
- evidence-aware weighting
- partial-data handling
- coverage
- confidence
- missing-component reporting
- sector-fit/future-oriented components
- deterministic ranking

### Validation / Backtesting
- backtest engine
- event context
- benchmark comparison
- optimization contracts
- walk-forward framework
- ranking validation
- ranking outcomes
- validation quality
- future-intelligence validation
- validation artifacts
- stress validation

### API
- FastAPI application
- health endpoint
- research/ranking infrastructure
- provider integration
- CORS configuration
- process-local research cache
- deterministic demo research dataset
- production research API contract (v1): structured error contract,
  company discovery, company research, company rankings, universe rankings
- point-in-time contract: as_of / effective_as_of / market_as_of,
  evidence counts, future-evidence exclusion, discovered/accepted/rejected
  source counts, pit checks, notes
- provenance contract: market/financials dataset records + archived source
  ids surfacing through API serialization
- data-quality contract: market validation status, accepted/rejected
  records, financial coverage, feature statuses, warnings, provider failures

### Frontend
Current frontend exists but remains the major productization area.

Target launch workflow:

SEARCH COMPANY
→ COMPANY RESEARCH
→ EVIDENCE
→ RISKS
→ TRENDS
→ FUTURE READINESS
→ RANKING
→ VALIDATION

## Current Verified Test Baseline

1004 tests passing.

This number supersedes all older checkpoint counts.

## Final Beta Launch Work

### L1 — API End-to-End
Verify:

company search
→ real provider
→ validation
→ point-in-time research
→ evidence
→ report
→ ranking

Status: IN PROGRESS

### L2 — Production Data Verification
Verify real provider behavior, failures, missing fields, provenance and date boundaries.

Real-data research verification is DONE for six recorded companies:
- recorded real market bars + financials + dated disclosure fixtures replayed
  through the existing provider architecture (no scraping, no provenance
  bypass, no network in tests) for TCS, RELIANCE, INFY, HDFCBANK, SUNPHARMA,
  M&M across 5 sectors; captured via scripts/capture_multi_company_fixtures.py
- full path verified per company: recorded provider → raw archive + provenance →
  acquisition → ResearchObservation → EvidenceItem → synthesis → report
- all point-in-time checks pass for as_of 2026-08-10T12:00Z per company
  (market bars, market/financial/source records available on or before as_of,
  future-source rejection, every acquired evidence item resolves to an archived
  source); future-dated contamination and naive timestamps are rejected by the
  validator/evidence gates and never reach any report
- provider failure isolation: a failing optional source provider no longer
  crashes acquisition; failures are recorded per provider/question and the
  report still builds from unrelated market/financial evidence
- availability failure modes verified end to end: missing, stale, failed,
  partial, and conflicting sources; conflict is retained and flagged by
  evidence synthesis; stale sources remain point-in-time valid
- verification is deterministic and reproducible (identical artifacts +
  artifact checksum) for every company

Status: COMPLETE

### L3 — Production Research API and Product Contract
Build a clean, stable, deterministic API contract for the research product,
backed by the recorded verification path (no network, no invented evidence).

Endpoints added (`src/api/research_router.py`):
- GET /api/v1/companies — company discovery (symbol, company_name, sector,
  research_available) derived from the verification registry
- GET /api/v1/companies/{symbol}/research?as_of= — full research contract
- GET /api/v1/companies/{symbol}/rankings?as_of= — all-horizon rankings
- GET /api/v1/rankings/{horizon}?as_of=&symbols= — universe rankings sorted
  by score desc (horizons: INTRADAY, SWING, LONG_TERM; as_of ISO 8601,
  Z/date-only accepted, naive-with-time rejected; comma-separated symbol subset)

Response contract (`src/api/contracts.py`) exposes: company identity,
assessment (conclusion/confidence/thesis/conflict/direction/research_ready),
point-in-time context (as_of/effective_as_of/market_as_of, evidence included,
acquired evidence, future evidence excluded, sources discovered/accepted/
rejected, pit_checks_passed, notes), intelligence sections, positive/negative/
neutral evidence, narrative, signals, data-quality status/warnings, provenance,
rankings, research score.

Structured error contract (`src/api/errors.py`):
`{"error": {"code", "message", "details"}}` — codes unknown_company (404),
research_data_unavailable (404), invalid_as_of (400), invalid_horizon (400),
malformed_request (400). No tracebacks or implementation details are exposed.

Point-in-time guarantee: the API never leaks future evidence. A contaminated
run (include_future_sources=True) still serializes with zero evidence past
as_of, pit_checks_passed true, and future_source_rejected true; regression
tests prove no future/naive observation can pass through serialization.

Tests added (`tests/test_research_contract_api.py`, 27 tests): successful TCS
research, research for every verified company, explicit as_of, deterministic
repeated requests, unknown company, invalid as_of (format + naive), unavailable
research data, unknown symbol in universe, future-evidence leak regression,
provenance surviving serialization, missing/failed source degradation, company
rankings, universe rankings (subset + ordering), company discovery, and error
body hygiene.

New modules: `src/api/errors.py`, `src/api/contracts.py`,
`src/api/recorded_research.py`, `src/api/serializers.py`,
`src/api/research_router.py`. Existing live API routes are untouched; the
contract routes live under /api/v1 alongside them. `main.py` now registers the
error handlers and the research router (app version 0.3.0).

Known limitations: as_of is restricted to dates covered by the recorded
fixtures; research_data_unavailable surfaces when no market data exists at the
requested as_of; archived_sources contains company-intelligence records while
market/financial evidence resolves through the dataset-level provenance
records; `+hh:mm` offsets in query strings must be URL-encoded (`+` decodes to
space), so Z is the recommended suffix.

Status: COMPLETE

### L4 — Frontend Research Dashboard
Build production-quality UI for:

- company search
- research overview
- research score
- evidence coverage
- confidence
- strengths
- risks
- unknowns
- financial trends
- signals
- evidence narrative
- future readiness
- ranking
- data/provenance information

Status: IN PROGRESS

### L5 — Ranking Dashboard
Expose:

- Intraday
- Swing
- Long-term
- score
- confidence
- coverage
- missing components
- explanation

Status: IN PROGRESS

### L6 — Backtest / Validation UI
Expose:

- historical return
- benchmark comparison
- drawdown
- sample size
- positive-return rate
- excess return
- correlation
- validation quality
- walk-forward status

Status: IN PROGRESS

### L7 — Production Hardening
Run:

- full pytest
- frontend lint
- frontend build
- API health
- API integration
- production CORS
- environment validation
- failure-path checks

Status: IN PROGRESS

### L8 — Beta Deployment
Deploy backend + frontend only after L1-L7 pass.

Status: NOT STARTED

## Launch Gate

Beta is considered READY only when:

[ ] 1004+ backend tests pass
[ ] frontend builds
[ ] frontend lint passes
[ ] API health passes
[ ] real company lookup works
[ ] research report is generated
[ ] evidence narrative is displayed
[ ] ranking works for all supported horizons
[ ] missing data is explicitly surfaced
[ ] provenance/as_of information is exposed
[ ] backtest/validation results are not presented as guaranteed returns
[ ] production CORS works
[ ] deployed frontend reaches deployed API
[ ] deployed real-company lookup succeeds

## Important Constraints

- Never invent missing data.
- Never hide missing evidence.
- Never claim correlation is causation.
- Never label an anomaly as fraud without evidence.
- Never introduce look-ahead bias.
- Never use future information in point-in-time research.
- Never present backtests as guaranteed future performance.
- Preserve provenance.
- Keep raw and normalized data separate.
- Keep research deterministic and testable.
- Keep the architecture modular.
- Do not enable live trading as part of the beta launch.

## Tooling Notes

- Python lint/format tooling is not yet enforced. A Ruff evaluation
  was performed during the source-acquisition milestone; default and
  minimal rule sets flag thousands of pre-existing violations
  (including the intentional `Decimal("...")` idiom used across the
  codebase), so Ruff was NOT introduced. Before production hardening
  (L6), agree on a backend lint policy rather than bulk-refactoring.

## Current Launch Estimate

Core research engine: ~90% complete
Data/provenance/PIT: ~90% complete
Ranking/validation: ~90% complete
API: ~90% complete
Frontend: ~20–30% complete
End-to-end integration: ~60–70% complete
Deployment hardening: ~40% complete

Overall beta launch readiness: approximately 75–80%.

The remaining work is primarily integration, UI, production verification and deployment — not another major research-engine rewrite.
