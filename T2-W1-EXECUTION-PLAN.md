# T2-W1 EXECUTION PLAN — WHOLE-PRODUCT REIMAGINATION

## PHASE 1: FOUNDATION (execute first, before any page rebuilds)

### Step 1.1: CSS Token Cleanup
- Replace 122 hardcoded `border-radius` values with `--radius-*` tokens
- Replace 100+ hardcoded `font-size` values with `--text-*` tokens
- Remove duplicate CSS rules: `.evidence-filters` (line 815 vs 1460), `.error-details` (lines 1419-1420), `.filter-chip` conflict (lines 3051 vs 3305)
- Remove dead `.page-shell` CSS (defined but unused by any page)

### Step 1.2: Component Consolidation
- Merge `MetricTile` + `MetricStripCell` + `MetricTileCompact` → `Metric` + `MetricStrip` + `MetricCompact` (backward-compatible props)
- Merge `Section` + `ResearchSection` + `PanelHead` + `PanelHeader` → single `Section` primitive
- Replace inline loading/error states with `LoadingState`/`ErrorState` components
- Fix `PITBadge` default label from "PIT VERIFIED" to "PIT verified"

### Step 1.3: Page Header Unification
- Standardize all pages to: `page-hero` with `page-kicker` (eyebrow) + `h1` + `page-subtitle`
- Remove `page-header`, `discover-hero`, `scr-header` variants
- Add `page-kicker` to all pages that lack it

### Step 1.4: SCREAMING_SNAKE Removal
- Fix 28 SCREAMING_SNAKE labels across 9 files → sentence case

### Step 1.5: Foundation Validation
- `npx tsc -b --noEmit && npm run lint && npm test -- --run && npm run build && git diff --check`
- Capture BEFORE/AFTER at 1440 + 390 for Discover, Company, Financials, Screener, Evidence

## PHASE 2: PAGE REBUILDS (mandatory order)

### T2-W1-D: Financial Intelligence (967 lines)
- Adopt `Section` primitive for all sections
- ONE chart area with view selector (remove wall of charts)
- Remove hardcoded CHART palette → use CSS variables
- Apply `humanizeNarrative` to all observation text
- Structure: Financial context → Latest snapshot → Historical performance → Reported history → Derived metrics → Research observations → Financial tensions → Full observation record → Source/PIT

### T2-W1-D: Market Intelligence (618 lines)
- Adopt `Section` primitive
- Remove inline `style={{ width }}` progress bars → use CSS
- Structure: Context → Latest market observations → Historical market context → Technical/market relationships → Freshness → Source/PIT

### T2-W1-D: Technical (490 lines)
- Adopt `Section` primitive
- Fix "OBV" SCREAMING_SNAKE label
- Structure: Indicator context → Recorded indicators → Trend/observation groups → Historical context → Limitations → Source/PIT

### T2-W1-E: Events / Timeline (788 lines)
- Adopt `Section` primitive
- Fix 7 SCREAMING_SNAKE badge labels → sentence case
- Structure: Timeline-first with Date, Event, Category, Verification, Recorded/Announced, Source

### T2-W1-E: Compare (536 lines)
- Adopt `Section` primitive
- Fix 6 SCREAMING_SNAKE labels
- Remove local `CompareSection`/`CompareRow` → use `Section`/`ResearchTable`
- Structure: Shared context → Company set → Aligned periods → Financial → Business → Technology → Events → Coverage → Sources/PIT

### T2-W1-E: Reports (201 lines)
- Adopt `Section` primitive
- Structure: Entry points → Professional Report → Export → Evidence Package

### T2-W1-F: My Research (225 lines)
- Adopt `Section` primitive
- Fix "NOT YET AVAILABLE" SCREAMING_SNAKE
- Structure: Recent → Watchlists → Tracked companies → Saved contexts

### T2-W1-F: Watchlists (111 lines)
- Unify header to `page-hero` + `page-kicker`
- Structure: Local device state, honestly disclosed

### T2-W1-F: Research Changes (189 lines)
- Unify header to `page-hero` + `page-kicker`
- Structure: Baseline → Current → Change summary → Change stream

### T2-W1-F: Evidence Alerts (191 lines)
- Unify header to `page-hero` + `page-kicker`
- Structure: Event type → Company → Change → Time → Source → PIT → Status

### T2-W1-F: Calendar (227 lines)
- Unify header to `page-hero` + `page-kicker`
- Structure: Date → Company → Event → Source (Recorded vs Announced)

### T2-W1-G: Asset Classes (156 lines)
- Fix "ADDITIONAL ASSET CLASSES" SCREAMING_SNAKE
- Structure: Gateway with honest capability states

### T2-W1-G: Export / Evidence Package
- Evidence Package currently reuses EvidencePage — needs dedicated component
- Structure: What will be exported → as_of → files → source/provenance → checksums

### T2-W1-G: Global Search (286 lines)
- Unify header to `page-hero` + `page-kicker`
- Structure: Search → Context → Results → Research entry

### T2-W1-G: Themes (377 lines)
- Fix "HOW THEME COVERAGE WORKS TODAY" SCREAMING_SNAKE
- Already uses ResearchPrimitives — adopt `Section` for consistency

### T2-W1-G: Industries (347 lines)
- Fix "HOW INDUSTRY COVERAGE WORKS TODAY" SCREAMING_SNAKE
- Already uses ResearchPrimitives — adopt `Section` for consistency

### T2-W1-G: Peer Research (135 lines)
- Unify header to `page-hero` + `page-kicker`
- Structure: Use same compare/research primitives

## VALIDATION PER SUB-WAVE

After each sub-wave:
1. `npx tsc -b --noEmit`
2. `npm run lint`
3. `npm test -- --run`
4. `npm run build`
5. `git diff --check`
6. Browser QA: 0 console errors, 0 overflow, interactions PASS
7. Update PROJECT_PROGRESS.md

## FINAL ACCEPTANCE (T2-W1-H through J)

- H: Whole-site output cleanup (SCREAMING_SNAKE, duplicates, backend text)
- I: Competitor audit (Screener.in, Tickertape, Trendlyne, TradingView)
- J: Final full-site visual acceptance (all pages, 5 widths, all checks)
