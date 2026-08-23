/**
 * Tests for screener filter logic and evaluateFilters.
 */

import { describe, it, expect } from "vitest"
import {
  ACTIVE_FILTER_DEFINITIONS,
  PLANNED_FILTER_CATEGORIES,
  evaluateFilters,
  type ActiveFilter,
} from "./screener"
import type { DiscoveryItem } from "../api/types"

function makeItem(overrides: Partial<DiscoveryItem> = {}): DiscoveryItem {
  return {
    symbol: "TEST",
    company_name: "Test Corp",
    sector: "technology",
    research_available: true,
    ...overrides,
  }
}

describe("ACTIVE_FILTER_DEFINITIONS", () => {
  it("contains exactly 2 filters", () => {
    expect(ACTIVE_FILTER_DEFINITIONS).toHaveLength(2)
  })

  it("has sector and research_available", () => {
    const ids = ACTIVE_FILTER_DEFINITIONS.map((f) => f.id)
    expect(ids).toContain("sector")
    expect(ids).toContain("industry_research_available")
  })

  it("no filter has backendRequired property", () => {
    for (const f of ACTIVE_FILTER_DEFINITIONS) {
      expect(f).not.toHaveProperty("backendRequired")
    }
  })
})

describe("PLANNED_FILTER_CATEGORIES", () => {
  it("has 8 planned categories", () => {
    expect(PLANNED_FILTER_CATEGORIES).toHaveLength(8)
  })

  it("each category has requiredApi string", () => {
    for (const cat of PLANNED_FILTER_CATEGORIES) {
      expect(cat.requiredApi).toBeTruthy()
      expect(typeof cat.requiredApi).toBe("string")
    }
  })

  it("each category has at least 1 filter", () => {
    for (const cat of PLANNED_FILTER_CATEGORIES) {
      expect(cat.filters.length).toBeGreaterThanOrEqual(1)
    }
  })
})

describe("evaluateFilters", () => {
  const items = [
    makeItem({ symbol: "TCS", company_name: "Tata Consultancy", sector: "technology" }),
    makeItem({ symbol: "HDFCBANK", company_name: "HDFC Bank", sector: "financials" }),
    makeItem({ symbol: "RELIANCE", company_name: "Reliance Industries", sector: "energy" }),
    makeItem({ symbol: "SMALLCAP", company_name: "Small Co", sector: "technology", research_available: false }),
  ]

  it("returns the full tracked universe when no filters are active", () => {
    const results = evaluateFilters(items, [])
    expect(results).toHaveLength(4)
    expect(results.map((r) => r.symbol)).toContain("SMALLCAP")
  })

  it("sorts by symbol ascending", () => {
    const results = evaluateFilters(items, [])
    const symbols = results.map((r) => r.symbol)
    expect(symbols).toEqual([...symbols].sort())
  })

  it("filters by sector", () => {
    const filters: ActiveFilter[] = [
      { filterId: "sector", operator: "in_list", value: "technology" },
    ]
    const results = evaluateFilters(items, filters)
    expect(results).toHaveLength(2)
    expect(results.map((r) => r.symbol)).toContain("TCS")
    expect(results.map((r) => r.symbol)).toContain("SMALLCAP")
    const tcs = results.find((r) => r.symbol === "TCS")
    expect(tcs?.matchedFilters).toContain("Sector")
  })

  it("filters by research_available = true", () => {
    const filters: ActiveFilter[] = [
      { filterId: "industry_research_available", operator: "equals", value: "true" },
    ]
    const results = evaluateFilters(items, filters)
    expect(results).toHaveLength(3)
    expect(results.map((r) => r.symbol)).not.toContain("SMALLCAP")
  })

  it("filters by research_available = false", () => {
    const filters: ActiveFilter[] = [
      { filterId: "industry_research_available", operator: "equals", value: "false" },
    ]
    const results = evaluateFilters(items, filters)
    expect(results).toHaveLength(1)
    expect(results[0].symbol).toBe("SMALLCAP")
  })

  it("combines sector + research_available filters", () => {
    const filters: ActiveFilter[] = [
      { filterId: "sector", operator: "in_list", value: "technology" },
      { filterId: "industry_research_available", operator: "equals", value: "true" },
    ]
    const results = evaluateFilters(items, filters)
    expect(results).toHaveLength(1)
    expect(results[0].symbol).toBe("TCS")
    expect(results[0].matchedFilters).toHaveLength(2)
  })

  it("excludes all items when only unknown filter IDs are active", () => {
    const filters: ActiveFilter[] = [
      { filterId: "nonexistent", operator: "equals", value: "x" },
    ]
    const results = evaluateFilters(items, filters)
    expect(results).toHaveLength(0)
  })

  it("includes totalFilters count", () => {
    const filters: ActiveFilter[] = [
      { filterId: "sector", operator: "in_list", value: "technology" },
    ]
    const results = evaluateFilters(items, filters)
    expect(results[0].totalFilters).toBe(1)
  })

  it("handles empty items array", () => {
    const results = evaluateFilters([], [])
    expect(results).toHaveLength(0)
  })
})
