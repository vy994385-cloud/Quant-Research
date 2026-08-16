# QUANT-RESEARCH — LAUNCH CHECKPOINT

## Current Status

**Test baseline:** 1160 backend + 43 frontend
**Latest commit:** evidence timeline and research status (timeline + status endpoint, dashboard timeline view)
**Working tree:** clean
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
- deep company intelligence foundation (`src/research/company_intel/`): semantic
  vocabulary, verification statuses, point-in-time financial intelligence,
  evidence conflicts (surfaced, never auto-resolved), deterministic change
  detection between snapshots, and a provider-driven periodic update engine
  (validate → dedupe → archive → extract) with provider failure isolation

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
- company intelligence contract: GET /api/v1/companies/{symbol}/intelligence?as_of=
  (semantic categories, verification statuses, financial periods/statements,
  evidence conflicts with both sides, changes, coverage/summary, source +
  provenance ids, insufficient-evidence notes; point-in-time pure)

### Frontend
The v1 research dashboard (L4) is now the default UI: modular React 19 + Vite +
TypeScript app consuming only the /api/v1 contract, replacing the legacy
monolithic stock view. Zero network/invention in tests; client is covered by
component + integration tests against recorded fixtures.

Views: company search (keyboard navigable), research overview with research
score / confidence / evidence coverage, horizon rankings (intraday / swing /
long-term) with coverage + missing-evidence badges, cross-company universe
comparison table (sorted by score, horizon switchable), evidence columns
(positive / contradicting / neutral with provenance-flagged degraded rows),
financial trends, signals ledger, risks (negative evidence + data-quality
warnings + provider failures), business-intelligence sections, sources &
point-in-time context (as_of / effective_as_of / market_as_of, PIT check
status, provenance dataset + archived source ids).

Degraded/error handling: structured loading and error states surface the
`{"error": {"code", "message", "details"}}` contract verbatim (code + details
shown, network failures labeled), and a "Degraded research context" banner
aggregates PIT failures, provider_failures, financial_data_missing, and
market_rejected_records with drill-downs in Risks/Sources.

Point-in-time UX: header as-of picker re-runs research with `as_of=YYYY-MM-DD`;
every panel displays its effective as-of; full timestamps are rendered as
locale strings; date-only as-of is parsed without timezone drift.

Target launch workflow (remaining):
- L5 ranking dashboard
- L6 backtest/validation UI

## Current Verified Test Baseline

1160 backend tests passing.

43 frontend tests passing (format helpers, discovery filtering, API client
request building + error handling, company search interaction, rankings panel
incl. universe switching, timeline + research status, full dashboard
integration).

These numbers supersede all older checkpoint counts.

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

Done (`frontend/`): search command bar with keyboard navigation (fetchDiscovery
via /api/v1/companies), header with as-of picker + refresh, overview (score
donut, metrics, strengths/weaknesses, confidence, evidence coverage, thesis +
conflict + research_ready), horizon rankings with coverage badges and missing
evidence, universe comparison table (/api/v1/rankings/{horizon}), evidence
columns, financial trends, signals ledger, risks + data-quality warnings +
provider failures, intelligence sections, sources + PIT context
(as_of/effective_as_of/market_as_of, PIT checks, provenance dataset + archived
source ids). Structured loading/error states surface the error contract
(code + details + network fallback); degraded alerts banner aggregates
provider_failures / PIT failures / financial_data_missing /
market_rejected_records.

Test infra: vitest + @testing-library/react (jsdom), recorded fixtures only.
39 frontend tests: format, discovery filter, API client (query building, error
mapping incl. /health status check), company search interaction, rankings
(universe switch + horizon), full App integration (empty → select → dashboard,
loading, structured error, degraded banner). `npm test`, `npm run lint`,
`npm run build` all green.

Known frontend limitations: no live data-refresh polling; as-of picker is
date-only (the API accepts full ISO via query string, but the picker sends
YYYY-MM-DD); universe comparison covers the recorded six-company universe.

Status: COMPLETE

### Deep Company Intelligence Foundation (Continuous Intelligence)
Build the evidence-based intelligence layer on top of the verified research
path: point-in-time financial intelligence, semantic classification,
verification statuses, evidence conflicts, change detection, and a
provider-driven periodic update engine. Deliberately contains no scores, no
recommendations, and no predictions of future returns.

New module: `src/research/company_intel/` (`semantics.py`, `models.py`,
`build.py`, `evidence.py`, `change.py`, `sources.py`, `update.py`).

- semantics: SemanticCategory (FACT / DERIVED_METRIC / OBSERVATION /
  MANAGEMENT_COMMENTARY / REPORTED_CLAIM / ALLEGATION / CONCLUSION),
  VerificationStatus (CONFIRMED / REPORTED / ALLEGED / UNVERIFIED /
  CONTRADICTED / RESOLVED), ChangeType (NEW / UPDATED / UNCHANGED / RESOLVED /
  CONFLICTING), IntelKind, direction, stance, relationship, reporting period
  type, consolidation scope, financial statement type
- a claim is never silently upgraded to a fact; management statements are
  MANAGEMENT_COMMENTARY, unproven allegations are ALLEGATION; the canonical
  unsupported-conclusion message is "Insufficient evidence for a firm conclusion."
- point-in-time financial intelligence: `financial_periods_from_snapshots` PIT
  filters recorded financial snapshots, preserves standalone vs consolidated
  scope and explicit period types, and infers quarterly/semi-annual/annual from
  median reporting intervals; Income / Balance / Cash-Flow statements are
  normalized per period; `build_financial_intelligence` produces a descriptive
  coverage summary with notes when quarterly+annual or consolidated+standalone
  periods would otherwise be compared
- snapshot builder (`build_company_intelligence_snapshot`): point-in-time pure
  (future items excluded), deduplicated by item id, deterministic semantic
  classification + checksums, split into business events / management commentary /
  risk / indirect / financial / other intelligence, evidence conflict + link
  detection, change detection vs a previous snapshot, coverage/semantic/status
  summaries, source + provenance ids, insufficient-evidence notes
- evidence conflicts (`detect_evidence_conflicts`): explicit `conflicts_with`
  declarations plus supportive-vs-contrary stance pairs on the same topic;
  same-source pairs are skipped; every conflict is surfaced with both sides and
  their provenance and is never auto-resolved (notes state this explicitly)
- conclusion gate (`conclusion_gate`): a CONCLUSION survives only with >=2
  CONFIRMED items at reliability tier <=2 from >=2 distinct sources, and a
  conclusion never counts as its own support; otherwise it is excluded with the
  canonical insufficient-evidence note
- change detection (`detect_changes`): NEW / UPDATED (checksum diff) /
  UNCHANGED / RESOLVED / CONFLICTING; items that disappear are ignored because
  snapshots are cumulative PIT views
- periodic update engine (`PeriodicUpdateEngine`): providers return
  `IntelCandidate` objects; the engine validates (company match, aware
  timestamps, available_at <= as_of), deduplicates by content identity
  (company/source/URL/normalized title/published ts), archives raw records via
  RawArchive, extracts items, and isolates provider failures (run marked
  DEGRADED, remaining providers still processed). `RecordedIntelSourceProvider`
  replays committed fixtures network-free.
- recorded intel fixtures for all six verified companies
  (`fixtures/real_data/*_intel.json`), generated deterministically by
  `scripts/build_intel_fixtures.py`; each fixture includes a future-dated
  contamination candidate that is rejected at the recorded as_of
- integrated into `src/verification/real_data.py`: each company result now
  carries a `CompanyIntelligenceSnapshot` (intel feed + acquisition observations
  + financial periods/items with provenance), and three new PIT checks
  (`intelligence_items_known_at_as_of`, `no_future_intelligence_items`,
  `financial_periods_known_at_as_of`) are added to the multi-company verification
- API: `GET /api/v1/companies/{symbol}/intelligence?as_of=` returns the
  `CompanyIntelligenceContract` (items, financial intelligence, conflicts with
  both sides, changes, summaries, source + provenance ids); unknown company 404,
  naive-with-time as_of 400, date-only as_of accepted

Tests added (100): `tests/research/company_intel/` (semantics, financial
periods/statements, snapshot build/dedup/PIT, conclusions/insufficient evidence,
conflicts/links, change detection, sources/extractor/dedupe, update engine
isolation/degraded/archive, observations) + `tests/test_intelligence_api.py`
(endpoint contract for every verified company, TCS conflict, determinism,
404/400, earlier-as_of PIT purity, no future items) + intelligence assertions in
`tests/test_multi_company_verification.py`.

Verification: full backend suite 1104 passed; recorded TCS snapshot yields 29
items across business/management/risk/indirect/financial/other with 4 annual
periods and one management-involved evidence conflict on demand_environment; all
PIT checks pass for every company.

Status: COMPLETE

### L5 — Continuous Company Research & Evidence Expansion
Add a chronological evidence timeline and a descriptive research-status view
(freshness / coverage / data quality) for each company, backed by the company
intelligence layer. Deliberately descriptive: statuses describe the *research
itself*, never the company's prospects, and the timeline never adds an opinion.

New modules: `src/research/company_intel/timeline.py` (timeline construction),
`src/research/company_intel/quality.py` (freshness/coverage/quality statuses).

- `IntelCategory` (FINANCIAL_DISCLOSURE / BUSINESS_NEWS /
  MANAGEMENT_STATEMENT / CORPORATE_ACTION / REGULATORY_LEGAL / OTHER):
  describes where information comes from, not its investment meaning;
  `default_intel_category(kind, event_type)` assigns it deterministically and
  never invents facts; candidates may carry an explicit `intel_category`
  (extractor preserves it verbatim), and the default is applied at snapshot
  build
- evidence timeline (`build_timeline`): point-in-time pure, deterministic
  ordering by `timeline_at` (published → effective → available), tie-broken by
  entry id; entries mirror their source item verbatim with source/provenance/
  checksum and per-category counts
- research status (`build_research_status`): freshness (latest/oldest
  published/available/effective, days-since, stale when no known items, no
  latest published, or > 90 days), coverage (counts by kind/category/semantic/
  status, missing categories), quality (conflicts, evidence links,
  deduplication, source/provenance counts, insufficient-evidence notes)
- financial intelligence: snapshots/statements/periods now carry
  `effective_at`, segments and subsidiaries (preserved verbatim from the
  provider), free-form `items` are bucketed into statements by deterministic
  normalized-name classification (underscore-insensitive), and coverage notes
  when segment detail exists; derived metrics record their exact derivation
  text for auditability
- update engine: `PeriodicUpdateResult.category_summary` reports the
  deduplicated candidate categories; validator rejects candidates whose
  `published_at` is after `available_at`
- API: `GET /api/v1/companies/{symbol}/timeline?as_of=` returns the
  `CompanyTimelineContract`; the research and intelligence contracts now also
  include `timeline` and `research_status`; real-data verification records
  timeline/research-status summaries and three new PIT checks
  (`timeline_entries_known_at_as_of`, `no_future_timeline_entries`,
  `timeline_is_chronological`)
- Frontend: new `Timeline` dashboard view — `TimelinePanel` renders the
  freshness/coverage/quality status cards with notes plus the chronological
  evidence timeline (category + verification tags, provenance); `fetchTimeline`
  client; types/fixtures updated

Tests added (52 backend + 4 frontend): `tests/research/company_intel/test_timeline.py`
(10), `tests/research/company_intel/test_quality.py` (12), `tests/test_timeline_api.py`
(14), plus extensions to test_snapshot / test_financial_periods / test_sources /
test_update_engine / test_research_contract_api / test_multi_company_verification;
frontend `TimelinePanel.test.tsx` (4) + App integration assertions.

Verification: full backend suite 1160 passed; frontend 43 passed, `npm run lint`
and `npm run build` clean; `git diff --check` clean.

Status: COMPLETE

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

[ ] 1160+ backend tests pass
[x] frontend builds
[x] frontend lint passes
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
Frontend: ~55% complete
End-to-end integration: ~70% complete
Deployment hardening: ~40% complete

Overall beta launch readiness: approximately 80–85%.

The remaining work is primarily integration, UI, production verification and deployment — not another major research-engine rewrite.
