# QUANT-RESEARCH — LAUNCH CHECKPOINT

## Current Status

**Test baseline:** 944 passed  
**Latest commit:** add real-data research verification  
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

944 tests passing.

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

Real-data research verification is DONE for TCS:
- recorded real TCS + ^NSEI market bars, real TCS financials, and real
  dated TCS disclosures replayed through the existing provider
  architecture (no scraping, no provenance bypass, no network in tests)
- full path verified: recorded provider → raw archive + provenance →
  acquisition → ResearchObservation → EvidenceItem → synthesis → report
- all point-in-time checks pass for as_of 2026-08-10T12:00Z; future-dated
  contamination is rejected by the validator/evidence gates and never
  reaches the report; insufficient provenance is never trusted
- verification is deterministic and reproducible (identical artifacts +
  artifact checksum), fixtures documented in scripts/capture_real_data_fixtures.py

Status: IN PROGRESS (broader real-provider failure-path verification remains)

### L3 — Frontend Research Dashboard
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

### L4 — Ranking Dashboard
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

### L5 — Backtest / Validation UI
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

### L6 — Production Hardening
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

### L7 — Beta Deployment
Deploy backend + frontend only after L1-L6 pass.

Status: NOT STARTED

## Launch Gate

Beta is considered READY only when:

[ ] 944+ backend tests pass
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
API: ~75–85% complete  
Frontend: ~20–30% complete  
End-to-end integration: ~60–70% complete  
Deployment hardening: ~40% complete

Overall beta launch readiness: approximately 75–80%.

The remaining work is primarily integration, UI, production verification and deployment — not another major research-engine rewrite.
