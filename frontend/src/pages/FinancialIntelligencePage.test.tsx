import { describe, expect, it } from "vitest"
import type { DeepMetricObservation } from "../api/types"
import { fmtObsValue } from "./FinancialIntelligencePage"

function observation(metric: string): DeepMetricObservation {
  return {
    observation_id: "obs-1",
    symbol: "HDFCBANK",
    metric,
    period_id: "HDFCBANK:2026-03-31:ANNUAL:UNKNOWN",
    period_end: "2026-03-31",
    period_type: "ANNUAL",
    consolidation: "CONSOLIDATED",
    observation_type: "REPORTED",
    value: null,
    previous_value: null,
    delta: null,
    delta_pct: null,
    derivation: null,
    published_at: null,
    available_at: null,
    provenance_id: null,
  }
}

describe("financial observation formatting", () => {
  it("formats total assets as a currency amount, not a percentage", () => {
    expect(fmtObsValue(observation("total_assets"), "52621193200000"))
      .toBe("52,62,119 crore")
  })

  it("formats known ratio metrics as percentages", () => {
    expect(fmtObsValue(observation("cash_conversion_ratio"), "0.73"))
      .toBe("73.0%")
  })

  it("does not assume an unknown metric is a percentage", () => {
    expect(fmtObsValue(observation("unclassified_metric"), "123456"))
      .toBe("1,23,456")
  })
})
