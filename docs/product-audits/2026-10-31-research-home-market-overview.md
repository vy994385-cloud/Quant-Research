# QRQuant Product Audit Backlog
**Audit date:** 31 October 2026  
**Scope reviewed:** Research Home (`/discover`) and Market Intelligence / HDFCBANK only.  
**Evidence boundary:** screenshots and implementation review; no exchange-price or financial-statement validation. Other modules remain unaudited.

## Product decision
Protect the provenance-led research positioning, but stop treating visible coverage gaps as the primary product experience. Lead with usable, current research data where integrated; show explicit source, event time, ingestion time, freshness and limitations wherever it is not.

Do not claim Nifty 500 coverage, live market feeds, current financial periods, provider attribution or corporate-action-adjusted prices until the source, licensing and ingestion path are verified.

## P0 — Credibility and correctness
1. **Freshness model**
   - Separate event/effective/published date from ingestion/recorded timestamp.
   - Add module-level `data as of`, source/provider, source timestamp and ingestion timestamp.
   - Ensure Last 7 days / Last 30 days filters use event time, not ingestion time.
   - Audit financial periods and source documents; identify why FY25/FY26/latest quarterly periods are absent before changing labels or fabricating coverage.
2. **Market-data timestamp semantics**
   - Replace page-load “Analysis cutoff” with exchange last-close timestamp and timezone only when backed by the price source.
   - Name the actual provider; never use a generic “provider OHLC” label.
   - Keep calculation run time distinct from market-data time.
3. **Price chart correctness**
   - Clip plotted lines to the plot viewport.
   - Calculate SMA values on full available history, then window the displayed range.
   - Expose the exact SMA window and warm-up policy.
   - Resolve raw vs adjusted OHLC semantics; add a Raw / Adjusted selector only when both valid series exist.
   - Add corporate-action markers only from verified action records.
4. **Research Home integrity**
   - Make Research Activity event date and ingestion date distinct.
   - Split Source, Source type, Reliability, Verification status and Basis/method into semantically correct fields.
   - Replace duplicate Coverage Changes with actual coverage-state deltas; otherwise remove it.
   - Reconcile all displayed counts against the rows and definitions they summarize.
   - Remove duplicate financial-disclosure/development taxonomy and annual-financial/revenue duplicates.
5. **Accessibility and consistency**
   - Fix low-contrast text and controls; verify WCAG AA for normal text.
   - Standardize accent, table headers and status presentation.
   - Never communicate status by colour alone.

## P1 — Research Home and Market Overview
- Reduce the hero to a compact header; remove redundant quick-link cards that duplicate navigation.
- Keep one global search entry point and define the command-palette contract (Cmd/Ctrl+K); do not ship a fake natural-language parser.
- Replace the 36-row home-page gap dump with a company × research-area coverage heatmap and a concise summary; retain the full gap table in Coverage & Gaps.
- Make activity rows meaningful, searchable/filterable and traceable to source documents where links exist.
- Consolidate Recently Researched and Company Index into one reusable company table; show recents/watchlist context without implying ranking.
- Align company classification with a consistent macro / sector / industry / basic-industry taxonomy.
- Remove unsupported theme marketing claims.
- Reconcile page title, nav label and URL for Market Overview / Market Intelligence.
- For Market Overview, either integrate licensed, source-backed market data or present a deliberate, useful “feeds not connected” state without pretending the page is complete.

## P2 — HDFCBANK company experience
- Header identity: exchange, ISIN, series, last-close time and named source.
- Add price currency, day change, OHLC, volume and 52-week context when sourced.
- Use a bank-specific financial template (NII, NIM, CASA, GNPA/NNPA, PCR, CAR, ROA, ROE); do not flag cash/equivalents as a generic bank gap.
- Improve chart ranges, neutral price-line styling, axes/grid/crosshair, OHLC/candlestick view and drawdown scale.
- Add comparison overlays, technical indicators and event markers as separately scoped increments with verified inputs.
- Version methodology documentation with formula, lookback, units, data lineage and calculation status.

## P3 — Coverage and research depth
- Validate source availability, licensing and ingestion feasibility before committing to Nifty 500 coverage.
- Prioritize latest annual and quarterly financials, results calendar, shareholding/pledge, corporate actions, bulk/block deals, insider disclosures and F&O.
- Add peer comparison, query-language plus visual screener, watchlists and alerts.
- Add annual-report/concall document search with page-level citations.

## P4 — Differentiation
- Evidence links on every material value; as-reported vs restated views.
- Point-in-time datasets and survivorship-bias-free universes.
- Reproducible factor research/backtesting with Indian market frictions.
- API/SDK, notebooks and data export.
- Optional transparent descriptive factor statistics only after legal review; no implicit recommendations.
- Exportable citation-linked Evidence Packages.

## Acceptance gates
- No displayed data timestamp is inferred from page-load time.
- Every displayed value has a defined source, period, unit, freshness and availability state, or an explicit reason it is unavailable.
- Counts reconcile with their underlying records.
- Chart indicators are invariant to display-range selection when their lookback requires earlier observations.
- A user can distinguish event time, publication time, ingestion time and calculation time.
- UI status remains understandable without colour.
- Tests cover empty, partial, stale, malformed and valid data states.

## Next audit scope
Companies, Financial Intelligence, Peer Research, Technical Analysis, News & Events, Evidence Center, Coverage & Gaps, Screener, Watchlists and Reports are not assessed in this audit. Their designs should be reviewed before finalizing cross-product navigation and shared component contracts.
