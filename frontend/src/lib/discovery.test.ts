import { describe, expect, it } from "vitest"
import { filterDiscovery, matchesQuery, normalizeSymbol } from "./discovery"
import { DISCOVERY } from "../test/fixtures"

describe("normalizeSymbol", () => {
  it("trims and uppercases", () => {
    expect(normalizeSymbol("  tcs ")).toBe("TCS")
  })
})

describe("matchesQuery", () => {
  const [tcs] = DISCOVERY.results

  it("matches by symbol", () => {
    expect(matchesQuery(tcs, "tcs")).toBe(true)
  })

  it("matches by company name", () => {
    expect(matchesQuery(tcs, "consultancy")).toBe(true)
  })

  it("matches by sector", () => {
    expect(matchesQuery(tcs, "information")).toBe(true)
  })

  it("matches everything on an empty query", () => {
    expect(matchesQuery(tcs, "   ")).toBe(true)
  })

  it("rejects unrelated queries", () => {
    expect(matchesQuery(tcs, "bank")).toBe(false)
  })
})

describe("filterDiscovery", () => {
  it("only returns researchable companies", () => {
    const items = [
      ...DISCOVERY.results,
      {
        symbol: "XX",
        company_name: null,
        sector: "other",
        research_available: false,
      },
    ]

    const filtered = filterDiscovery(items, "")

    expect(filtered.map((item) => item.symbol)).not.toContain("XX")
  })

  it("sorts results by symbol", () => {
    const filtered = filterDiscovery(DISCOVERY.results, "")

    expect(filtered.map((item) => item.symbol)).toEqual(["INFY", "TCS"])
  })
})
