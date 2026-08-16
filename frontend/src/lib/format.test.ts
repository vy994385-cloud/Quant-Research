import { describe, expect, it } from "vitest"
import {
  formatConfidence,
  formatEvidenceObservation,
  formatIso,
  formatLabel,
  formatNumber,
  formatScore,
  formatTitle,
} from "./format"

describe("formatNumber", () => {
  it("renders one decimal place", () => {
    expect(formatNumber("66.928")).toBe("66.9")
  })

  it("renders an em dash for non-finite values", () => {
    expect(formatNumber("not-a-number")).toBe("—")
  })
})

describe("formatScore", () => {
  it("renders a score over 100", () => {
    expect(formatScore("66.9")).toBe("66.9 / 100")
  })
})

describe("formatConfidence", () => {
  it("scales 0..1 confidences to percentages", () => {
    expect(formatConfidence("0.8")).toBe("80%")
  })

  it("passes through 0..100 confidences unchanged", () => {
    expect(formatConfidence("81.1")).toBe("81%")
  })

  it("renders an em dash for non-finite values", () => {
    expect(formatConfidence("nope")).toBe("—")
  })
})

describe("formatLabel", () => {
  it("turns snake_case into title case", () => {
    expect(formatLabel("future_readiness")).toBe("Future Readiness")
  })
})

describe("formatTitle", () => {
  it("strips validated-feature prefixes", () => {
    expect(formatTitle("Validated feature: revenue_growth")).toBe(
      "Revenue Growth",
    )
  })
})

describe("formatIso", () => {
  it("renders date-only strings without timezone drift", () => {
    expect(formatIso("2026-08-07")).toMatch(/Aug/)
  })

  it("renders full timestamps as locale strings", () => {
    expect(formatIso("2026-08-10T12:00:00+00:00")).toMatch(/2026/)
  })

  it("falls back to the raw value when unparseable", () => {
    expect(formatIso("not-a-date")).toBe("not-a-date")
  })
})

describe("formatEvidenceObservation", () => {
  it("renders observation timestamps", () => {
    expect(formatEvidenceObservation("2026-08-10T12:00:00+00:00")).toMatch(
      /2026/,
    )
  })
})
