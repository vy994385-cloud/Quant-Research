# QRQuant Core Research Workflow — API Trace

**Audit date:** 2026-10-31  
**Inspected base:** `qrquant/product-foundation-audit`  
**Audit branch:** `qrquant/phase-0-audit`  
**Status:** Static source trace. No runtime/API response verification performed.

## 1. Company discovery and research

The newer API is registered under the `/api/v1` prefix in `src/api/research_router.py`.

Confirmed routes include:
- `GET /api/v1/companies`
- `GET /api/v1/companies/{symbol}/research`
- `GET /api/v1/companies/{symbol}/intelligence`
- `GET /api/v1/companies/{symbol}/timeline`
- `GET /api/v1/companies/{symbol}/rankings` (legacy/product-rule conflict; investigate)

The router delegates to `RecordedCompanyResearchService`. This service:
- Derives its company registry from the verification registry.
- Uses recorded fixtures and a deterministic verification path.
- Defaults to a recorded `DEFAULT_AS_OF` when no timestamp is supplied.
- Requires an explicit `as_of` timestamp to be timezone-aware.
- Caches results by symbol and timestamp.
- Returns a research-data-unavailable error when recorded data cannot be used.

This is a useful deterministic foundation for a reproducible beta, but it is not live market-data ingestion.

## 2. Company research page

The frontend route `/companies/:symbol` loads `CompanyResearchPage`. Static inspection shows it calls `fetchResearch(symbol)`, and it has a second path that passes a requested as-of value.

The page itself is only 257 lines and uses a tabbed company workspace. The full downstream tab implementation and all network responses still need browser/runtime validation.

## 3. Professional report path

The frontend `ProfessionalReportPage` calls `fetchProfessionalReport(symbol)` and renders a document-like report with:
- Research snapshot
- Business context
- Financial performance and quality
- Market context
- Business developments
- Management and strategy
- Competitive position
- Innovation and R&D
- Industry context
- Capital allocation
- Corporate actions
- Timeline
- Research gaps
- Evidence appendix, conflicts, methodology, and limitations

The backend route is in `src/api/f8_router.py`:
- `GET /api/v1/companies/{symbol}/research-report`

It obtains the recorded research result, builds an F7 evidence lineage, and constructs an F8 professional report from that lineage and intelligence data. The route documentation states that it is deterministic, point-in-time aware, evidence-backed, and does not provide scores, rankings, recommendations, or trading signals.

This is a strong report architecture to preserve. It still requires verification that the report's individual sections have sufficient source data for each supported company and that missing sections are clearly represented rather than implied to be complete.

## 4. Financials, events, and ownership

The candidate branch has dedicated routers:
- `src/api/fundamentals_router.py` — financial history and deep fundamentals.
- `src/api/events_router.py` — event analysis.
- `src/api/ownership_router.py` — ownership analysis.

Static route inspection confirms dedicated API handlers, but does not prove data completeness, production availability, or frontend integration for every field. These should be traced one by one from page/API call to service and fixture.

## 5. Critical product-rule conflict: legacy API

The legacy `src/api/main.py` still contains:
- A synthetic `DEMO` company research payload.
- Hard-coded demo ranking values for intraday, swing, and long-term horizons.
- `/api/rankings/{horizon}`.
- `/api/stocks/{symbol}/rankings`.
- Stock research/detail routes that return demo ranking data for the `DEMO` symbol.
- A ranking implementation that sorts company results by numeric score and emits a priority field.

This contradicts the repository README's explicit product rules: no buy/sell calls, no opaque company scores, and no winner/loser rankings.

### Recommended resolution

Do not delete the legacy endpoints immediately. First:
1. Search all frontend callers, external consumers, tests, deployment references, and scripts.
2. Identify which backend app is deployed and which API base path the production frontend uses.
3. Add regression tests proving the primary UI uses the intended `/api/v1` research contracts.
4. Deprecate or isolate legacy scoring/ranking routes behind an explicit compatibility boundary.
5. Remove synthetic demo rankings from user-facing production flows; keep demo fixtures only in clearly labelled development/demo contexts if still useful.
6. Update API documentation and navigation so no user mistakes demo data for real company research.

## 6. First implementation candidate

After runtime validation, the best initial end-to-end slice is:
1. Company search/discovery.
2. Company overview and as-of context.
3. Financial history/deep fundamentals.
4. Timeline/news/events and ownership.
5. Professional report with evidence lineage and explicit gaps.

Avoid starting with live ingestion or a full asset-class expansion. First prove the recorded equity workflow is internally consistent and reliable.

## 7. Remaining checks before code changes

- Verify which FastAPI app and route set are actually deployed.
- Inspect `frontend/src/api/client.ts` to confirm each company tab calls the intended API path.
- Trace financial-history, event, and ownership services to their actual fixtures/providers.
- Confirm test coverage for invalid symbols, missing fixtures, timezone-aware `as_of`, future-dated evidence exclusion, and missing source sections.
- Run the candidate branch in a reproducible environment and capture API responses for one company.
- Verify report export output and that source/as-of/methodology details survive export.
