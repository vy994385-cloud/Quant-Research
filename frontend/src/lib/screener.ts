/**
 * Screener filter types and client-side filtering logic.
 *
 * Only filters with validated client-side data are active:
 * - sector: filters by industry sector from discovery data
 * - industry_research_available: filters by research availability
 *
 * Financial, growth, valuation, technology, and competitive filters require
 * a backend screener API that does not yet exist. These are listed as
 * planned filters for transparency but have no interactive controls.
 */

import type { DiscoveryItem } from "../api/types"

/* ── Filter value types ─────────────────────────────────────────────── */

export type FilterOperator = "equals" | "in_list"

export interface FilterDefinition {
  id: string
  label: string
  operator: FilterOperator
  dataType: "string" | "boolean" | "enum"
  options?: Array<{ value: string; label: string }>
  description?: string
}

export interface ActiveFilter {
  filterId: string
  operator: FilterOperator
  value: string | string[]
}

export interface ScreenerResult {
  symbol: string
  companyName: string | null
  sector: string
  matchedFilters: string[]
  totalFilters: number
  researchAvailable: boolean
}

/* ── Active filter definitions ─────────────────────────────────────── */

export const ACTIVE_FILTER_DEFINITIONS: FilterDefinition[] = [
  {
    id: "sector",
    label: "Sector",
    operator: "in_list",
    dataType: "enum",
    description: "Filter by industry sector",
  },
  {
    id: "industry_research_available",
    label: "Research Available",
    operator: "equals",
    dataType: "boolean",
    description: "Only show companies with research data",
  },
]

/* ── Planned filter categories (for reference, no controls) ───────── */

export const PLANNED_FILTER_CATEGORIES = [
  {
    category: "Fundamentals",
    description: "Revenue, profit, margins, cash flow, returns",
    filters: ["Revenue", "Revenue Growth", "Gross Margin", "Operating Margin", "Net Margin", "EPS", "ROE", "ROCE", "Operating Cash Flow", "Free Cash Flow"],
    requiredApi: "Screener API with deep financial insights",
  },
  {
    category: "Growth",
    description: "Revenue acceleration, margin expansion, FCF growth",
    filters: ["Revenue Acceleration", "Margin Expansion", "FCF Growth"],
    requiredApi: "Screener API with multi-period trend analysis",
  },
  {
    category: "Financial Quality",
    description: "Debt, liquidity, working capital, cash conversion",
    filters: ["Debt/Equity", "Cash/Debt", "Working Capital", "Cash Conversion"],
    requiredApi: "Screener API with balance sheet metrics",
  },
  {
    category: "Valuation",
    description: "P/E, EV/EBITDA, P/B — only where market data exists",
    filters: ["P/E Ratio", "EV/EBITDA", "P/B Ratio"],
    requiredApi: "Screener API with market price data",
  },
  {
    category: "Technology",
    description: "AI, cloud, semiconductors, robotics, cybersecurity, energy",
    filters: ["AI Product", "AI Infrastructure", "Cloud Exposure", "Semiconductor Exposure", "Robotics/Automation", "Cybersecurity", "Energy Transition"],
    requiredApi: "Technology intelligence endpoint",
  },
  {
    category: "R&D / Innovation",
    description: "R&D spending, intensity, patents, innovation evidence",
    filters: ["R&D Spending", "R&D Intensity", "Innovation Evidence", "Patent Evidence"],
    requiredApi: "R&D expense and patent data endpoints",
  },
  {
    category: "Competitive",
    description: "Competitor data and market position",
    filters: ["Competitor Data Available"],
    requiredApi: "Competitors endpoint",
  },
  {
    category: "Technical / Market",
    description: "Timeline data, research observations, PIT checks",
    filters: ["Has Timeline Data", "Has Research Observations", "PIT Checks Passed"],
    requiredApi: "Timeline, signals, and PIT data from research store",
  },
]

/* ── Client-side filtering (discovery data only) ────────────────────── */

export function evaluateFilters(
  items: DiscoveryItem[],
  filters: ActiveFilter[],
): ScreenerResult[] {
  // With no active filters the full tracked universe is shown; the
  // "Research Available" filter narrows it explicitly when applied.
  return items
    .map((item) => {
      const matchedFilters: string[] = []

      for (const filter of filters) {
        const def = ACTIVE_FILTER_DEFINITIONS.find((f) => f.id === filter.filterId)
        if (!def) continue

        let matches = false

        if (def.id === "sector") {
          const values = Array.isArray(filter.value) ? filter.value : [filter.value]
          matches = values.includes(item.sector)
        } else if (def.id === "industry_research_available") {
          matches = filter.value === "true"
            ? item.research_available
            : filter.value === "false"
              ? !item.research_available
              : false
        }

        if (matches) {
          matchedFilters.push(def.label)
        }
      }

      return {
        symbol: item.symbol,
        companyName: item.company_name,
        sector: item.sector,
        matchedFilters,
        totalFilters: filters.length,
        researchAvailable: item.research_available,
      }
    })
    .filter((result) => {
      if (filters.length === 0) return true
      return result.matchedFilters.length === filters.length
    })
    .sort((a, b) => a.symbol.localeCompare(b.symbol))
}
