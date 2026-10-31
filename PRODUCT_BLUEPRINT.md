# QRQuant Product Blueprint
## A clear, connected, full-stack financial research workspace

**Current scope:** India-listed equities; additional asset classes only after real data contracts and ingestion exist.  
**Product promise:** Research a company or market question from discovery through evidence, analysis, comparison, monitoring, and export in one workspace.

## 1. Product definition

QRQuant should be a broad financial research terminal for individual researchers, serious market participants, analysts, students, and small research teams. It should combine useful workflows from company-data platforms, charting tools, news terminals, screeners, filing trackers, and research workspaces. It should not pretend to have coverage or data it does not have.

QRQuant is **not just an evidence viewer**. Evidence is the trust layer underneath a much broader product.

### User outcomes
- Find a company, security, sector, theme, event, filing, metric, or saved research item.
- Understand a company's business model, revenue drivers, competitive context, risks, and financial health.
- Explore historical financials, cash generation, margins, leverage, growth, ownership, valuation context, and market behaviour.
- Follow company developments, exchange filings, results, corporate actions, policy changes, and relevant news.
- Investigate a major price move using a time-ordered event timeline and market/sector context—without asserting causation from coincidence.
- Compare companies and periods with aligned definitions, units, reporting periods, and coverage.
- Build a screener from explicit observable criteria, save it when persistence exists, and export results.
- Maintain watchlists, notes, research questions, change history, and alerts when genuine storage/scheduling/delivery exists.
- Produce a report/data package with sources, dates, methods, caveats, and reproducible calculations.

## 2. Non-negotiable product rules

1. **No invented data or coverage.** Distinguish available, partial, stale, missing, conflicting, and unsupported.
2. **No fake live claims.** Label recorded/snapshot data and its as-of time.
3. **No opaque recommendations.** No buy/sell calls, hidden overall scores, winner/loser labels, or popularity rankings.
4. **Separate fact from interpretation.** Label reported facts, derived calculations, contextual observations, hypotheses, and unresolved questions.
5. **Point-in-time integrity.** Historical views must exclude information not knowable at the selected date.
6. **Comparable means comparable.** Align period end, fiscal/calendar basis, currency, units, corporate-action adjustments, and metric definitions.
7. **Ratings are context, not authority.** If analyst calls are added, include provider, rating scale, publication/update time, target horizon, revision history, source, and limitations.
8. **Privacy by design.** Clearly label device-only state; user data needs explicit storage, account, and privacy semantics.
9. **Working thin slice over a wide mock.** Every released capability needs real data, tests, loading/empty/error states, and stated limits.

## 3. Information architecture

Use user-oriented work areas rather than exposing every internal module equally.

### Discover
- Research Home and recent activity
- Global search
- Company universe
- Sectors and industries
- Themes and technologies
- Events and results calendar
- Market movers and breadth, after reliable market-wide data exists

### Analyze
- Company overview and business model
- Financial statements and trends
- Financial quality: cash flow, working capital, leverage, margins, returns
- Valuation context and peer comparison
- Price charts and technical observations
- Ownership and shareholding changes
- Business/competitive intelligence
- News, filings, events, and timelines
- Evidence, source lineage, and coverage

### Screen & Compare
- Fundamental and market screeners
- Saved screens (persistent storage required)
- Side-by-side comparison
- Peer universe and sector context
- Historical/as-of comparisons

### Monitor
- Watchlists and recently viewed
- Research changes
- Corporate events and results calendar
- Alerts (scheduler and delivery required)
- Saved research contexts and notes (persistence required)

### Research & Output
- Research notebook: thesis, questions, and notes
- Company and thematic reports
- Research history and point-in-time snapshots
- CSV/JSON exports and verified PDF reports
- Evidence packages with source metadata and integrity checks

### Data health & settings
- Source catalogue, update cadence, and provider status
- Coverage/freshness dashboard
- Account, privacy, notification, and display preferences when accounts exist

Keep asset-class workspaces visible only with honest coverage states. Do not call ETF, mutual fund, IPO, or F&O tabs supported until each has a real model, provider/ingestion path, tests, and end-to-end workflow.

## 4. High-value use cases

### A. “Help me understand this company”
1. Search by name/ticker and confirm exchange/security identity.
2. See business summary, latest available period, data freshness, and coverage.
3. Explore business segments, demand drivers, competition, financial history, cash flow, leverage, ownership, valuation context, and risks.
4. Open any important figure to see definition, units, period, source, reported/derived status, and calculation inputs.
5. Save a note or export a report.

### B. “Why did this share move?”
1. Choose a security and time window.
2. Show price/volume movement and benchmark/sector context with timestamps.
3. Build a timeline from filings, results, corporate actions, official notices, and news.
4. Mark whether each source was published before or after the movement.
5. Present possible explanations as hypotheses, link sources, and say when evidence is insufficient. Never claim causation from timing alone.

### C. “What changed since my last review?”
- Compare current and previous research snapshots.
- Group changes into disclosures, business developments, ownership, corporate actions, market observations, and data-quality changes.
- Show old/new value, period, effective date, recorded date, and source.
- Filter by company/type/date and open the evidence record.

### D. “Find companies with these characteristics”
- Compose explicit filters (for example revenue growth, operating margin, leverage, cash conversion, market cap, or price/volume conditions) only where fields are actually available.
- Show units, as-of period, missing-field context, and availability per row.
- Allow column selection, sorting by observed values, compare, and export.
- Save screens and create alerts only after storage and scheduled re-evaluation exist.
- Never replace missing values with zero or silently add an overall score.

### E. “Compare companies”
Align periods and definitions; compare business, financial, valuation, market, ownership, and evidence dimensions. Keep nulls and incomparable metrics explicit. Do not automatically select a winner.

### F. “Understand a sector or theme”
Show a defined universe, constituent companies, inclusion rationale, and evidence. Separate confirmed product/revenue exposure from mentions or third-party speculation. Add sector KPIs, market sizing, regulation, demand drivers, and competitive dynamics only when sourced and maintained.

### G. “Create a professional research note”
Build from a company and as-of date. Include summary, business model, financials, market context, events, positive/negative/conflicting evidence, risks, unknowns, sources, methods, and coverage. Link narrative claims to records and preserve the chosen snapshot in exports.

## 5. Capability inventory and release gates

The repository has foundations for company research, financial history/insights, market and technical observations, news/events/corporate actions, evidence lineage, coverage gaps, comparison, screener APIs, reports, and exports. Re-check implementation and tests before treating a capability as production-complete.

| Capability | Target | Current constraint / gate |
|---|---|---|
| Company research | Coherent overview/business/financials/events/ownership/market/evidence workspace | Recorded universe is six companies; freshness and coverage must be explicit |
| Financial intelligence | Period-aligned statements, cash-flow quality, leverage, margins, returns | Validate metric definitions, units, fiscal periods, restatements, and sources |
| Market intelligence | Price/volume, benchmarks, volatility, drawdowns, technical context | Label provider, timestamp, adjustments, and recorded-vs-live state |
| News/events | Source-linked filings, results, corporate actions, news timeline | Source breadth, publication time, duplicate handling, and update cadence |
| “Why it moved?” | Event timeline plus market/sector context and candidate explanations | Do not imply causation from temporal proximity |
| Screener | Composable filters, result columns, sorting, compare/export | Bulk data and metric definitions must agree; disclose missing fields |
| Compare | Multi-company and multi-period comparisons | Keep nulls and incomparable metrics explicit |
| Themes/industries | Evidence-backed exposure, sector metrics, competition, regulation | Cross-company intelligence is a known gap; taxonomy/data must be real |
| Ownership | Shareholding pattern and changes | Reliable official filings and reporting periods required |
| Analyst ratings/calls | Provider-specific ratings, targets, horizon, revisions, historical context | Licensing, provenance, timestamps, coverage, and conflicts must be resolved |
| Watchlists | Cross-device companies and notes | Current state is device-local; account-backed persistence required for sync |
| Saved screens | Reusable filters and columns | Storage, versioning, ownership required |
| Alerts | Threshold/condition and evidence-change alerts | Scheduler, dedupe, preferences, delivery/retry, audit history required |
| Reports | Narrative, tables, sources, caveats | Validate output quality and export fidelity |
| CSV/JSON/PDF | Reproducible, labelled exports | Preserve units, as-of date, source metadata, missingness, and checksums |
| ETFs | NAV/market price, holdings, expense ratio, benchmark, overlap | Dedicated instrument model and provider needed |
| Mutual funds | NAV, scheme documents, portfolio, category and benchmark context | Dedicated ingestion/data contract needed |
| IPO | Calendar, offer documents, price band, subscription, allotment, listing history | Official IPO-specific data sources needed |
| F&O | Contract master, expiry, option chain, OI, IV, Greeks, futures basis | Derivatives provider and separate market-risk/data design needed |
| Portfolio | Holdings, cost basis, transactions, corporate actions, P&L | Secure account data and corporate-action handling needed |
| Natural-language research | Transparent query, cited answer, reproducible filters | Must cite retrieved sources, distinguish inference, and admit uncertainty |

## 6. Delivery roadmap

### Phase 0 — Protect and establish a reliable baseline
- Keep `main` untouched while work is reviewed on a feature branch.
- Run frontend lint/tests/build, backend tests, API smoke checks, and browser QA.
- Confirm API URL, CORS, deployed frontend origin, and actual data responses.
- Inventory routes, APIs, data sources, and feature maturity: working / partial / device-local / blocked / planned.
- Correct documentation drift; old test counts are historical only.

**Exit:** repeatable checks, known deployment state, no broken primary routes, and an honest capability map.

### Phase 1 — Excellent core equity workflow
1. Global search and company identity
2. Company overview with freshness and coverage
3. Financial statements and period-aligned trends
4. Events, official filings, and source-linked timeline
5. “What changed?” with old/new values and dates
6. Compare and screener using consistent metric definitions
7. Research report and exports
8. Consistent loading, empty, stale, conflict, error, and unavailable states

**Exit:** users can investigate, compare, and export the current six-company universe without dead ends or misleading states.

### Phase 2 — Data breadth and freshness
- Create a source/provider registry with licensing, update cadence, fields, attribution, and failure semantics.
- Expand coverage in measured batches, verifying a full research path per company.
- Prioritise official exchange filings, company investor-relations releases, and official corporate-action sources.
- Add reliable market/benchmark series and historical as-of retrieval.
- Improve segments, ownership changes, valuation context, and peer/sector definitions.
- Expose source health and freshness.

**Exit:** expanded coverage is reproducible; quality and freshness are measured rather than assumed.

### Phase 3 — Research productivity
- User accounts and saved workspaces
- Cross-device watchlists, notes, and saved screens
- Change history and research snapshots
- Scheduled alerts with in-app/email delivery and audit history
- Verified CSV/JSON/PDF exports and report templates

**Exit:** saved work persists across devices, alerts run on a schedule, and report outputs are verified.

### Phase 4 — Market/event explanation
- Market-wide movers, sector context, breadth, and benchmark-relative returns
- Event-study windows before/after disclosures
- “Why it moved?” timeline with publication times and limitations
- Cautious links between events and financial changes
- Historical comparison/time-machine views

**Exit:** explanations are traceable, time-aware, and separate association from causation.

### Phase 5 — Multi-asset expansion
Build one class at a time:
1. ETFs
2. Mutual funds
3. IPOs
4. F&O
5. Portfolio tracking after secure storage and corporate-action support

**Exit:** each class has a real data model, provider, tests, source/freshness rules, and end-to-end workflow before being called supported.

### Phase 6 — Advanced research
- Theme/industry aggregation and competitive intelligence
- Analyst ratings/target-price history with licensed sources
- Research notebooks, assumptions, reproducible calculations, historical performance context
- Natural-language research with citations and transparent query interpretation
- Team workspaces and permissions

**Exit:** advanced features add verifiable value without obscuring source quality or becoming an opaque recommendation engine.

## 7. UX quality bar

- One obvious primary action per page; avoid metadata walls and repetitive KPI-card grids.
- Consistent typography, spacing, tables, badges, and page headers.
- High-contrast text; reserve semantic colour for status and change.
- Compact/comfortable density where it improves research.
- Responsive layout without page-level horizontal overflow; tables scroll inside their own containers.
- Keyboard navigation, visible focus, meaningful accessible names, and reduced-motion support.
- Search results identify company and ticker; keyboard selection and useful empty states work.
- Loading/error/retry states should not hide unaffected data.
- Never show zero in place of unavailable data.
- Visual polish should support scanning, comparison, and trust.

## 8. Data contract and trust layer

For each metric/event/claim/observation, preserve what applies:
- Entity/instrument identity
- Metric definition, unit, and currency
- Value and explicit null/missingness reason
- Fiscal period or event effective date
- Published/available timestamp and recorded timestamp
- Source name, identifier/URL, and source class
- Reported / derived / inferred classification
- Calculation method and input identifiers
- As-of timestamp and point-in-time eligibility
- Freshness, validation, conflict, and coverage state
- Methodology/version and export provenance

Reported facts and derived ratios may coexist but must not be indistinguishable. Restatements should be retained as dated versions, not silently overwrite history.

## 9. Competitor audit before major expansion

Audit relevant products and official sources, not their branding:
- Market dashboards/charting: overview, charting, alerts, watchlists, screeners
- Company/fundamentals platforms: statements, ratios, peers, segments, ownership
- News and filing terminals: source coverage, event timelines, search
- Analyst estimates/ratings platforms: coverage, revisions, historical outcomes, licensing
- Research/workspace tools: notes, saved screens, collaboration, exports
- Indian-market platforms and official exchange/regulator sources

For each, record user segment, workflows/pages, data breadth, refresh cadence, provenance, screening/comparison, alerts, exports, price/access model, licensing constraints, and recurring user pain points. Use official pages for claimed capabilities; community reviews help identify pain points but do not prove technical capability.

**Deliverable:** capability matrix labelled **must match / differentiate / defer / do not build**, each tied to user value, data dependency, effort, licensing risk, and measurable acceptance criteria.

## 10. Working protocol

For each checkpoint:
1. Inspect existing code and API contracts before editing.
2. Work on a dedicated branch; never rewrite or merge `main` implicitly.
3. Make a coherent, reviewable set of changes.
4. Add/update tests and run available checks.
5. Review desktop/mobile visuals and interactions.
6. Report what changed, what was tested, what remains blocked, and how to verify.
7. Pause for product feedback before the next major feature.

**Definition of done:** not merely that a page renders, but that its data path, workflow, failure states, accessibility, source/freshness semantics, tests, and deployment behaviour are verified.
