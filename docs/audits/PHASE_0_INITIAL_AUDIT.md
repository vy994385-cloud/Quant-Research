# QRQuant Phase 0 Audit — Initial Findings

**Audit date:** 2026-10-31  
**Audit base:** `qrquant/product-foundation-audit`  
**Working branch:** `qrquant/phase-0-audit`  
**Status:** Initial static repository audit; not a production-readiness certification.

## Executive summary

QRQuant already has a substantial research backend and a broad route-level frontend. The strongest foundation is to consolidate and verify the existing product rather than replace it with a new mock interface.

The current product scope is India-listed equities. The product README identifies a recorded research universe of six companies: TCS, RELIANCE, INFY, HDFCBANK, SUNPHARMA, and M&M. Other asset classes should remain clearly marked as unsupported or planned until real ingestion, data contracts, tests, and complete user workflows exist.

## Confirmed from repository files

- The frontend is React + TypeScript + Vite and uses React Router.
- The backend is Python + FastAPI.
- The frontend defines routes for discovery/search, company research, financial intelligence, market intelligence, technicals, events/timeline, evidence, screeners, comparison, watchlists, research changes, alerts, calendar, reports, and asset-class entry points.
- The backend registers multiple routers for research, fundamentals, technicals, business intelligence, events, ownership, attribution, timeline, validation, analyst information, capability status, and change tracking.
- The frontend API client includes calls for discovery, company research, timelines, company news, corporate actions, technicals, cross-domain research, research gaps, evidence lineage, and professional reports.
- The capability matrix reports 12 capabilities as SUPPORTED, 3 as PARTIAL, 2 as MISSING, and 2 as INTENTIONALLY_UNSUPPORTED. These are repository-authored statuses, not independently validated audit results.
- The capability matrix identifies persisted research memory and production live market/news ingestion for change detection as MISSING. It marks interactive point-in-time replay, a visual change timeline, and provenance drill-down as PARTIAL.
- The product blueprint's release roadmap correctly places a coherent core equity workflow before broader asset-class expansion.

## Priority risks and inconsistencies

### P0 — Establish one reproducible, trusted baseline
1. Run the frontend lint, test, and production-build checks on the exact candidate branch.
2. Run backend tests and API smoke tests against the same candidate branch.
3. Confirm the deployment's API URL, CORS allowlist, health endpoint, and actual responses from the deployed frontend.
4. Inventory the working tree separately from remote branch state. Do not reset, clean, or overwrite local uncommitted work as part of this audit.

**Reason:** prior local checks reported backend tests passing and the frontend build passing, but frontend lint failed and Vitest reported no test files discovered. Those results describe the local working tree at that time, not this remote branch. Re-run before using them as release gates.

### P0 — Align legacy ranking/score paths with the product rules
The candidate branch's `src/api/main.py` still imports `calculate_research_score` and ranking response schemas, exposes a `/api/rankings/{horizon}` endpoint, and describes the API as providing rankings and research signals. This conflicts with the product blueprint's rule against opaque company scores, buy/sell calls, and winner/loser rankings.

**Action:** trace all consumers and tests. Remove or deprecate ranking/score outputs only after verifying their dependencies; replace any user-facing rank with explicit observable filters and transparent metrics. Preserve useful underlying descriptive calculations where valid.

### P1 — Verify capability claims against end-to-end behaviour
The capability matrix is useful as an inventory, but SUPPORTED should mean the entire path works with tested data, correct as-of handling, explicit missingness, source lineage, and useful failure states. Mark a capability PARTIAL or MISSING when any required step is fixture-only, device-local, disconnected, or unavailable in deployment.

### P1 — Clarify data freshness and provider semantics
The repository has both recorded research fixtures and provider-based market/financial code. User-facing screens must distinguish live/provider-fetched data from recorded snapshots, including as-of time, retrieval time, coverage, provider failures, and licensing/attribution limits. Do not promise broad news, analyst ratings, or live market coverage without verifying source access and permitted use.

### P1 — Restore frontend test discoverability
The candidate branch contains Vitest tests under `frontend/src`, including API-client and discovery tests. The previous local working tree reported no tests discovered. Compare local Vite/Vitest configuration and file changes with this candidate branch before assuming tests are absent or silently changing the test include pattern.

## Recommended first complete workflow

Deliver one reliable India-equity research path end to end:

1. Search and identify a supported company.
2. Open the company overview and see the exact data as-of time, freshness, and coverage.
3. Inspect financial statements and period-aligned metrics.
4. Follow source-linked news, official disclosures, events, and ownership changes.
5. Compare companies or periods with clear metric definitions and explicit missing values.
6. Save/export a research report that preserves dates, sources, calculations, and caveats.

The first release should not pretend to have cross-device saved work or scheduled alerts until storage, scheduling, delivery, and audit history are implemented and tested.

## Proposed order of work

1. **Baseline and branch reconciliation:** reproduce checks on the isolated candidate; compare relevant code with `main`, `improve/phase-0-stabilization`, and `redesign/whole-product-v1`.
2. **Product-rule consistency:** trace ranking/score behaviour and identify any UI/API contradictions.
3. **Core workflow audit:** trace one supported company from UI to API to data source and report/export.
4. **Small fixes with regression tests:** address only confirmed defects; avoid a broad rewrite.
5. **Review checkpoint:** inspect visual behaviour, data correctness, tests, and deployment before starting the next workflow.

## Boundaries

- This audit does not certify current production uptime or live-provider coverage.
- Static GitHub inspection does not execute the application or validate browser behaviour.
- No changes to `main` are proposed.
- Do not merge this branch without review and passing checks.
