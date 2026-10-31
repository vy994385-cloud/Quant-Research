# Phase 0 Data-Source Audit

**Repository:** `vy994385-cloud/Quant-Research`  
**Inspected ref:** `qrquant/product-foundation-audit`  
**Audit branch:** `qrquant/phase-0-audit`  
**Status:** Static code inspection; no runtime/provider requests were executed for this report.

## Executive finding

The repository contains several genuinely useful research engines and external-provider adapters, but its data coverage is uneven. A route returning HTTP 200 or a typed response must not be interpreted as proof that the underlying dataset is populated, historical, current, or complete.

The highest-risk gaps are:
1. The Events analysis route currently passes an explicitly empty event list to its analysis engine.
2. Ownership data from Yahoo is a latest-only snapshot, not a historical ownership series; the provider documents that FII/DII separation, insider transactions, bulk/block deals, and detailed pledge history are unavailable.
3. Analyst intelligence is fetched from Yahoo quote-summary modules, but provider failures and empty results are converted into empty typed data, which can be mistaken for genuine absence of analyst activity.
4. Some routes accept an `as_of` value but do not actually enforce point-in-time replay against source publication/availability timestamps.
5. The product's deterministic recorded-research path and the external-provider paths coexist in one FastAPI application. Their different freshness, history, and failure semantics need to be visible in the UI.

## Data-source matrix

| Research area | API / implementation | Source mode | Coverage and caveats | Audit assessment |
|---|---|---|---|---|
| Core company research | `/api/v1/companies/{symbol}/research`; `RecordedCompanyResearchService` | Committed recorded fixtures and deterministic verification path | Registry is limited to the configured six-company universe. Not live ingestion. `as_of` is parsed and passed to the recorded service. | Useful reproducible baseline; must be labelled recorded and bounded. |
| Professional report | `/api/v1/companies/{symbol}/research-report`; F8 router | Derived from recorded research + PIT-filtered evidence lineage | Report includes multiple detailed sections, evidence appendix, conflicts, methodology and limitations. It inherits the recorded universe and source limitations. | Preserve and extend; strong report foundation, not proof of comprehensive live coverage. |
| Market prices | Yahoo chart provider; used by technical, timeline, attribution and real-company research paths | External HTTP provider | Daily bars; NSE symbols normalized to `.NS`; provider errors raise RuntimeError in the market provider. No durable central refresh/scheduler was established by this inspection. | Provider-backed, but needs shared ingestion, retrieval metadata, caching and source terms review. |
| Financial statements / deep fundamentals | `/api/v1/companies/{symbol}/financial-history`, `/deep-fundamentals`; Yahoo fundamentals time-series provider | External HTTP provider | Annual metrics only in the inspected provider; missing metric values remain null. Router catches RuntimeError/ValueError and returns an empty snapshot list, so provider outage and genuinely absent records can look alike. | Valuable coverage; needs explicit source status/error distinction, units, period availability and retrieval timestamps. |
| Events analysis | `/api/v1/companies/{symbol}/events`; `events_router.py` | No provider currently wired | Code initializes `events = []` and passes that empty list into `analyze_events`. The response can be structurally valid while event_count is zero. | **P0 product-integrity gap:** do not present this route as populated event research. |
| Unified company Events UI | `CompanyEventsPanel` | Calls news and corporate-actions endpoints; merges those with recorded timeline entries | The panel itself does not call the empty events-analysis endpoint. It uses `Promise.allSettled`, shows available pools and only displays a load error if both requests fail. Missing one pool may therefore be subtle. | UI is better than the empty analysis route, but each source pool needs independent status/coverage messaging. |
| Ownership analysis | `/api/v1/companies/{symbol}/ownership`; Yahoo ownership provider | External HTTP provider | Provider doc states latest-only snapshot. No historical time series. FII/DII separate breakdown, insider transactions, bulk/block deals and detailed pledge history are not available. Snapshot date is set to `date.today()`; query window only gates whether today is inside the requested range. | **P0/P1 semantics gap:** do not imply historical ownership changes or point-in-time replay. |
| Ownership summary / top holders | `/ownership-summary`; Yahoo ownership + profile providers | External HTTP provider | Current summary and holder data only; endpoint uses today's date and does not accept `as_of`. Provider can return null/empty on unavailable data. | Useful current snapshot only; needs as-of label and explicit unavailable state. |
| Analyst intelligence / rating changes | `/analyst-intelligence`; Yahoo analyst provider | External HTTP provider | Uses recommendationTrend, upgradeDowngradeHistory, earningsHistory, calendarEvents, summaryDetail and defaultKeyStatistics. HTTP/network failure or empty quoteSummary result returns an empty typed object, not an error. No `as_of` parameter on the inspected route. | **P1 transparency gap:** zero records cannot be distinguished from failed/unavailable coverage. Not a complete ratings-agency universe. |
| Research changes / replay | `/api/v1/research-changes`, `research-delta`, `coverage/delta`, context endpoints | Recorded fixture snapshots | Explicit baseline/current timestamps are checked and replayed through recorded service. | Good deterministic change-detection foundation, but cannot detect new live news/filings until ingestion exists. |
| Price attribution | `/price-attribution`; Yahoo market bars + attribution engine | External price data plus derived candidate explanations | Route fetches daily bars; output describes candidate explanations and explicitly disclaims causality. It is not evidence that news/event datasets are complete. | Keep as exploratory/derived analysis with visible coverage limits. |

## Concrete issues and recommended priority

### P0 — Prevent misleading completeness
- Mark Events analysis as unavailable/not integrated until an actual event source is connected; do not interpret an empty result as “no events occurred”.
- Add source-pool status to the Events UI: loaded, empty-but-successful, unavailable, stale, and not integrated should be distinguishable for timeline, news and corporate actions.
- Label ownership analysis as a latest snapshot. Disable historical-change claims and PIT replay for this dataset until historical filings/snapshots are ingested.
- Add data-mode and as-of semantics to each area: recorded snapshot, provider-fetched current data, derived calculation, or unavailable.

### P1 — Improve source transparency and reliability
- Preserve provider failures as structured source status instead of silently translating them to empty datasets in financial and analyst endpoints.
- Include `source_name`, `retrieved_at`, provider observation/reporting date, period, currency/unit, and coverage notes in API responses where relevant.
- Add a provider adapter boundary and a normalized ingestion/archive layer for news, filings, corporate actions, analyst changes and ownership disclosures.
- Ensure analyst rating coverage is explicitly attributed to the actual provider and not described as comprehensive agency coverage.
- Review inconsistent `as_of` parsing: several routes use `datetime.fromisoformat(...).replace(tzinfo=UTC)`, which overwrites an explicit offset rather than normalizing it. Standardize on shared `parse_as_of`.

### P2 — Build complete research capability
- Add reliable source coverage for exchange filings/disclosures, results, corporate actions, shareholding patterns, bulk/block deals, insider/promoter transactions, credit-rating actions, broker rating changes, news and macro/sector events.
- Store raw source payloads, retrieval metadata, publication/availability timestamps, normalized records and provenance.
- Add scheduled refresh, retry/backoff, rate-limit handling, stale-data policy, provider health and historical backfill.
- Build cross-source event deduplication and link each event to company, security, source, publication time, effective time and related price movement.
- Add dataset-specific contract and integration tests for missing, stale, partial, failed, and out-of-order source responses.

## Important implementation observations

- Render's blueprint points to `uvicorn src.api.main:app`; that file registers the recorded research router and the fundamentals, technical, business, events, ownership, analyst, timeline, attribution, F6/F7/F8 and change routers in one FastAPI application.
- The production entrypoint therefore combines recorded fixtures with external Yahoo-backed endpoints. A single generic “research available” state is insufficient to describe all sections.
- The core recorded research router explicitly describes itself as network-free and deterministic. Keep that property for reproducibility; add live ingestion as a separate pipeline rather than silently changing the deterministic contract.
- The Yahoo ownership provider explicitly sets the snapshot period to today's date. That is retrieval-day labelling, not a verified filing/reporting date.
- The Yahoo analyst provider's empty fallback makes failure indistinguishable from zero analyst coverage unless the API adds status metadata.
- The frontend Events panel uses news + corporate actions + recorded timeline; the separate events analysis router currently has no effect on that panel.

## Next verification work

1. Inspect the exact news and corporate-action router implementations and their provider adapters; confirm whether they are live, recorded, or empty.
2. Verify the deployed frontend API URL and Render service URL against the deployment configuration and route registration.
3. Map each Company workspace tab to the API endpoints actually called by its child components.
4. Inspect tests for provider failures, empty responses, historical/as-of behavior and data freshness.
5. Only then implement the first narrow P0 fix with regression tests. Do not remove legacy endpoints or alter the recorded research contract before checking all consumers.


## Follow-up verification: frontend/backend event contract (confirmed)

A second pass inspected the complete `src/api` directory listing, the production FastAPI registration file, the frontend API client and the Events component.

- The backend directory contains no `news_router.py` or `corporate_actions_router.py`.
- `src/api/main.py` registers research, fundamentals, technical, business, events, ownership, attribution, timeline, validation, analyst, ownership summary, F6/F7/F8, capability and change routers. It does not register news or corporate-actions routers.
- The frontend client nevertheless requests:
  - `GET /api/v1/companies/{symbol}/news`
  - `GET /api/v1/companies/{symbol}/corporate-actions`
- `CompanyEventsPanel` invokes both requests with `Promise.allSettled`. If both fail, it shows an error. If only one fails, it silently continues with the other pool and does not expose the failed pool's status. If both succeed with empty arrays, the UI says no events are recorded.
- The panel receives timeline entries from the core company research payload, but the API calls for news and corporate actions are not backed by any registered route in this branch.

**Revised assessment:** this is a confirmed P0 frontend/backend contract mismatch. It is more urgent than merely improving provider freshness. Before implementing providers, either implement the missing endpoint contracts with honest explicit `NOT_INTEGRATED`/unavailable status, or change the UI to avoid calling nonexistent routes and clearly show which pools are not integrated. Do not silently return empty lists, because that would misrepresent missing infrastructure as an absence of events.

## Deployment configuration verification

- `render.yaml` deploys `uvicorn src.api.main:app`, so the route registration above is the configured Render entrypoint.
- Render builds the frontend with Vite and sets `VITE_API_URL=https://quant-research-api-50u0.onrender.com`; `frontend/.env.production` repeats that URL.
- Render backend CORS allowlist currently names `https://quant-research-frontend.onrender.com` and localhost origins. The blueprint itself warns that the actual Render static-site origin must be verified after deployment. The configured API hostname and CORS origin therefore require live deployment verification before calling production integration healthy.
- No Vercel configuration file exists at the audited branch root. This audit cannot confirm any separately configured Vercel deployment from repository files alone.



## Test audit: event and provider integration

The repository does contain event-domain foundations and tests; the gap is integration, not total absence of event code.

- `src/events/provider.py` defines a provider request/raw-event contract, and `src/events/normalizer.py` normalizes events with provenance and publication/availability ordering. Their tests cover symbol normalization, required source URLs, availability-after-publication, sorting and duplicate IDs.
- `tests/test_event_analysis.py` tests classification, clustering, counts and empty-input behavior. Its empty-input test explicitly accepts zero events plus explanatory notes.
- `tests/test_phase3_routers.py` tests the `/events` route but allows either HTTP 200 or HTTP 500. It checks response shape only; it does not assert that the route is connected to a provider or that an event can flow end-to-end from source to API.
- The inspected `events_router.py` still constructs `events: list[CompanyEvent] = []` and does not call the event provider abstraction or normalizer.
- The test tree contains no dedicated tests for the frontend's `/news` and `/corporate-actions` API contracts, and the backend route tree has no such routes.
- `tests/test_phase5a_provider_fixes.py` uses mocked Yahoo payloads for analyst/ownership/financial provider parsing. These are useful parser contract tests, not evidence of production provider availability, data freshness, full coverage, or stable external API access.

**Revised priority:** retain the existing event provider/normalizer/analysis layers. The first implementation should connect a real source adapter to the normalized event contract, then expose one coherent API contract for news + corporate actions + event analysis. Add deterministic integration tests with fixture payloads and explicit empty/unavailable/partial states. Avoid creating parallel duplicate event pipelines.


## First implementation checkpoint: Events source visibility

Implemented on `qrquant/phase-0-audit` in commit `69316757176ee6e34ee027657549852b1bec4fd7`.

Changed `frontend/src/components/CompanyEventsPanel.tsx`:
- Added independent status reporting for the news request and corporate-actions request.
- A failed news request can no longer be silently hidden merely because the corporate-actions request succeeded (and vice versa).
- Successful empty responses are labelled "No records returned", not presented as proof that no real-world events occurred.
- Shows the number of recorded timeline entries supplied to the panel.

This is a deliberately narrow UI integrity fix. It does not pretend to implement the missing backend endpoints or create live event ingestion. The next implementation must establish the API contracts and connect a real source adapter to the existing event normalization pipeline.

**Verification status:** static patch applied through GitHub. Automated frontend tests/build have not yet been run against this isolated branch; do not treat this change as runtime-verified.


## Final audit checkpoint — product coverage and build priorities

**Audit status:** Phase 0 static repository audit is complete for architecture, core company workflow, provider/data semantics, API wiring, deployment configuration and the first competitor capability benchmark. This is not a runtime certification: provider requests, deployed CORS, full build/test suites and live data entitlements have not been independently verified in this audit.

### Company workspace integration findings

- The production FastAPI entrypoint is `src.api.main:app` and registers the recorded research, fundamentals, technical, business, events, ownership, analyst, timeline, attribution, validation, F6/F7/F8, capability and change routers.
- The frontend API client calls news and corporate-actions endpoints that are absent from this backend branch. The company Events UI now exposes each request's status, but the missing backend endpoints remain unresolved.
- The separate `/{symbol}/events` analysis endpoint still passes an empty event collection to the analysis engine. It must be labelled not integrated until a source adapter is connected.
- Ownership from the inspected Yahoo provider is a latest snapshot, not a historical ownership-change dataset. Analyst provider failures can be represented as empty typed results. These must not be presented as verified absence of activity.
- Core company research and professional reports are based on a bounded recorded-fixture universe; other sections use external Yahoo-backed providers. Their data modes must be explicit and must not be blended into a generic "live research" claim.
- Legacy endpoints and types still contain synthetic demo data and research scores/rankings. They require a consumer/deployment migration plan before removal; they should not be treated as the new product's canonical research contract.

### Competitor capability benchmark (public product documentation)

| Product | Publicly described strengths | QRQuant implication |
|---|---|---|
| Koyfin | Custom market dashboards, financial analysis, equity screening, watchlists, alerts, company snapshots, reports and portfolio analytics. [Features](https://www.koyfin.com/features/) · [Plans](https://www.koyfin.com/Pricing/) | Build an integrated research workspace, saved views and reusable dashboards—not isolated company pages. |
| TradingView | Multi-market charting, technical/fundamental screeners, 100+ fundamental metrics, heatmaps, alerts, financial statements, news and economic calendar. [Features](https://www.tradingview.com/features/) | Treat charts, screeners, heatmaps, calendar and alerting as core navigation, with cross-links into company research. |
| Trendlyne | Indian-market screeners, shareholding/deal alerts, analyst reports, consensus forecasts, portfolio tools, sector/index heatmaps and corporate-event alerts. [Features](https://trendlyne.com/features/) · [Alerts](https://help.trendlyne.com/support/solutions/articles/84000396716-what-are-the-different-types-of-alerts-) | India-specific ownership disclosures, bulk/block/insider deals, research reports and alert workflows are important competitive requirements. Do not copy its opaque score-led positioning. |
| TIKR | Global screener, long financial histories, analyst estimates/revisions, transcripts, filings, ownership and investor portfolio tracking. [Platform](https://www.tikr.com/) · [Coverage](https://www.tikr.com/pricing) | Add deep historical financials, estimates/revisions, transcript/document search and ownership history as data licensing/coverage permits. |

This benchmark is a public-feature review, not a hands-on teardown of every authenticated page or a verification of each vendor's data quality and entitlements.

### Consolidated implementation order

**P0 — Integrity and a coherent working vertical slice**
1. Establish explicit dataset states: live/provider-fetched, recorded, derived, stale, partial, empty, unavailable and not integrated.
2. Resolve the missing news/corporate-action API contract honestly; connect adapters only where a dependable source and permitted access are established.
3. Connect the existing event provider → normalizer → analysis path with fixture-backed integration tests.
4. Add source, publication/availability/effective timestamps, retrieval time, reporting period, units and coverage metadata.
5. Label ownership as latest snapshot until genuine historical filings/snapshots are ingested; make provider failures distinct from empty data.
6. Run the frontend tests/build and backend test suite on this exact branch; verify the deployed API hostname and CORS origin.

**P1 — Complete the daily research workflow**
1. Market overview, sector/industry views, movers, heatmaps and economic/results calendar.
2. Screener with observable filters, sortable tables, saved screens, compare and export.
3. Company workspace: price/chart, annual and quarterly financials, ratios/valuation, peers, technicals, ownership, news, filings, corporate actions, analyst estimates/revisions and transcripts.
4. Watchlists, portfolio tracking, configurable alerts and change feeds.
5. Research notes, evidence-linked reports, document search and export.

**P2 — Institutional depth and expansion**
1. Historical exchange filings and ownership/disclosure archive; bulk/block/insider/SAST and rating-agency actions.
2. Durable ingestion, scheduling, retries, provider health, backfills, deduplication, entitlements and data licensing.
3. Point-in-time replay across every dataset, not only recorded fixtures.
4. ETF, mutual fund, IPO, derivatives, global equities, macro, FX and commodities as each data domain reaches verified coverage.

### Exit decision

The audit is sufficient to start implementation; continuing broad static inspection before building would have diminishing returns. Remaining verification is attached to the relevant implementation checkpoints. Keep this branch isolated from `main`. Do not merge or deploy until exact-branch automated tests/build and production API/CORS checks pass.
