# Research Engine Expansion Plan

## Phase R1: Deep Financial Intelligence

### R1.1 Cash-Flow Quality Analysis
**New file**: `src/analysis/cash_flow_quality.py`

Analyzes:
- CFO/net_income relationship (cash conversion)
- FCF conversion ratio
- CapEx intensity (CapEx/Revenue)
- Working capital contribution
- Receivables behavior (days sales outstanding)
- Inventory behavior (days inventory outstanding)
- Payables behavior (days payables outstanding)
- Cash-generation trend

**Output**: `CashFlowQualityObservation` dataclass with provenance

### R1.2 Balance Sheet Deep Analysis
**New file**: `src/analysis/balance_sheet_deep.py`

Analyzes:
- Net debt (total_debt - cash)
- Debt/revenue ratio
- Cash/debt ratio
- Interest coverage (where data available)
- Leverage trend
- Balance sheet changes

**Output**: `BalanceSheetDeepObservation` dataclass with provenance

### R1.3 Expanded Financial Divergence Detection
**Extend**: `src/analysis/financial_anomalies.py`

Add:
- Revenue vs receivables growth divergence
- Revenue vs cash generation divergence
- Growth vs margin divergence
- Earnings vs FCF divergence
- Debt vs cash generation divergence

---

## Phase R2: Market / Stock-Movement Intelligence

### R2.1 Extended Market Observations
**Extend**: `src/research/market_observations.py`

Add:
- Multi-period returns (50d, 100d, 200d)
- Volatility regime (low/normal/high)
- Price trend regime (uptrend/downtrend/sideways)
- Abnormal volume detection
- Gap events (up/down gaps)
- Price-volume divergence
- Abnormal return events
- Relative performance vs benchmark (NIFTY 50)

**Output**: Extended `MarketObservation` with new fields

---

## Phase R3: Technical Research (Already Exists)

Technical indicators and observations already comprehensive. Will verify coverage and add any missing observations.

---

## Phase R4: Event Intelligence

### R4.1 Event Timeline with Subsequent Observations
**Extend**: `src/analysis/event_analysis.py`

Add:
- Event timeline construction
- Subsequent financial observations (where measurable)
- Subsequent market observations (where measurable)
- Event-market correlation (descriptive only)

**Output**: `EventTimeline` with linked observations

---

## Phase R5: Business Intelligence (Already Exists)

Business intelligence orchestrator exists. Will verify completeness.

---

## Phase R6: Research Gaps

### R6.1 Research Gap Detection
**New file**: `src/analysis/research_gaps.py`

For each company identify:
- Known information
- Partially known
- Unavailable
- Conflicting
- Stale
- Insufficient evidence

**Output**: `ResearchGap` dataclass with status and resolution path

---

## Phase R7: Cross-Domain Intelligence

### R7.1 Cross-Domain Observation Builder
**New file**: `src/analysis/cross_domain_observations.py`

Builds relationships between:
- Fundamentals + Market performance
- Events + Market reaction
- Technology investment + Business evidence
- Revenue growth + Margin compression
- Earnings growth + CFO deterioration

**Output**: `CrossDomainObservation` dataclass

---

## Phase R8: Research Report Data Contract

### R8.1 Report Data Contract
**New file**: `src/research/report_data_contract.py`

Defines the complete data contract for research reports:
- Company Overview
- Business Model
- Financials
- Financial Quality
- Cash Flow
- Balance Sheet
- Growth
- Market Behaviour
- Technical Observations
- Events
- Technology/Future Intelligence
- Sector Context
- Positive Evidence
- Negative Evidence
- Conflicting Evidence
- Risks
- Unknowns
- Research Gaps
- Data Quality
- Provenance

---

## Phase R9: Quality / Provenance

### R9.1 Enhanced Provenance Tracking
**Extend**: Existing provenance system

Ensure all new observations preserve:
- source/provenance
- as_of
- effective date
- calculation inputs
- methodology
- confidence/quality state
- missing-data semantics

---

## Phase R10: Testing

For each new module:
1. Unit tests
2. Edge cases
3. Missing-data cases
4. PIT cases
5. Provenance tests
6. API contract tests

---

## Implementation Order

1. **R1.1** Cash-Flow Quality Analysis (new module)
2. **R1.2** Balance Sheet Deep Analysis (new module)
3. **R1.3** Expanded Divergence Detection (extend existing)
4. **R2.1** Extended Market Observations (extend existing)
5. **R4.1** Event Timeline (extend existing)
6. **R6.1** Research Gap Detection (new module)
7. **R7.1** Cross-Domain Observations (new module)
8. **R8.1** Report Data Contract (new module)
9. **R9.1** Provenance verification
10. **R10** Tests for all new modules

---

## Files to Create

1. `src/analysis/cash_flow_quality.py`
2. `src/analysis/balance_sheet_deep.py`
3. `src/analysis/research_gaps.py`
4. `src/analysis/cross_domain_observations.py`
5. `src/research/report_data_contract.py`

## Files to Extend

1. `src/analysis/financial_anomalies.py` (R1.3)
2. `src/research/market_observations.py` (R2.1)
3. `src/analysis/event_analysis.py` (R4.1)
4. `src/analysis/fundamental_observations.py` (integrate new modules)
5. `src/analysis/deep_fundamental.py` (integrate new modules)

## Tests to Create

1. `tests/test_cash_flow_quality.py`
2. `tests/test_balance_sheet_deep.py`
3. `tests/test_research_gaps.py`
4. `tests/test_cross_domain_observations.py`
5. `tests/test_report_data_contract.py`
6. `tests/test_market_observations_extended.py`
7. `tests/test_event_timeline.py`

---

## Success Criteria

- All new observations are structured with provenance
- No scores, rankings, or recommendations
- PIT-safe (no look-ahead)
- Missing-data handled gracefully
- All tests pass
- PROJECT_PROGRESS.md updated
