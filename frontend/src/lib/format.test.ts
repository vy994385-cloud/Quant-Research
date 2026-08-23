import { describe, expect, it } from "vitest"
import {
  formatAxisCompact,
  formatCrore,
  formatCroreNumber,
  formatDeltaPct,
  formatEvidenceObservation,
  formatFiscalYear,
  formatIso,
  formatIsoShort,
  formatLabel,
  formatNumber,
  formatPeriodDelta,
  formatPitNote,
  formatSourceName,
  formatSourceNote,
  formatTitle,
  humanizeNarrative,
  indianCommas,
  splitMeasureUncertainty,
  toCrore,
} from "./format"

describe("formatNumber", () => {
  it("renders one decimal place", () => {
    expect(formatNumber("66.928")).toBe("66.9")
  })

  it("renders an em dash for non-finite values", () => {
    expect(formatNumber("not-a-number")).toBe("\u2014")
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

  it("keeps natural sentence wording and casing", () => {
    expect(formatTitle("TCS reported Q1 FY27 net profit of Rs 17,728 crore")).toBe(
      "TCS reported Q1 FY27 net profit of Rs 17,728 crore",
    )
  })

  it("softens shouty period tokens and compacts period boilerplate to a fiscal year", () => {
    expect(
      formatTitle("HDFCBANK ANNUAL financials for the period ending 2023-03-31", "HDFCBANK"),
    ).toBe("Annual financials, FY23")
  })

  it("does not strip a ticker that is part of a real company phrase", () => {
    expect(
      formatTitle(
        "Reliance Industries AGM: chairman's address on leadership",
        "RELIANCE",
      ),
    ).toBe("Reliance Industries AGM: chairman's address on leadership")
  })
})

describe("formatSourceName", () => {
  it("humanises internal source slugs", () => {
    expect(formatSourceName("recorded_financials")).toBe("Recorded Financials")
    expect(formatSourceName("hdfcbank-capital-bonds")).toBe("Hdfcbank Capital Bonds")
  })

  it("passes readable names through untouched", () => {
    expect(formatSourceName("Recorded Sector Review")).toBe("Recorded Sector Review")
    expect(formatSourceName(null)).toBe("\u2014")
  })

  it("softens shouting ALL-CAPS labels to title case", () => {
    expect(formatSourceName("YAHOO FINANCE FINANCIALS")).toBe("Yahoo Finance Financials")
    expect(formatSourceName("RECORDED EARNINGS CALL NOTES")).toBe(
      "Recorded Earnings Call Notes",
    )
  })

  it("keeps short acronyms uppercase", () => {
    expect(formatSourceName("NSE")).toBe("NSE")
  })
})

describe("formatSourceNote", () => {
  it("condenses boilerplate review sentences to source and outlet", () => {
    expect(
      formatSourceNote(
        "Reliance Industries AGM: chairman's address on leadership: Recorded source 'reliance-agm-management' (Mint) was reviewed for evidence relevant to this research question.",
      ),
    ).toBe("Reliance Agm Management (Mint)")
  })

  it("passes non-boilerplate text through", () => {
    expect(formatSourceNote("A plain recorded note.")).toBe("A plain recorded note.")
  })
})

describe("splitMeasureUncertainty", () => {
  it("extracts uniform limited-reliability measures into names", () => {
    const { measures, other } = splitMeasureUncertainty([
      "Validated research measure: Cash conversion ratio has limited evidence reliability.",
      "Debt to revenue has limited evidence reliability.",
      "AI-partnership pipeline is unquantified.",
    ])
    expect(measures).toEqual(["Cash conversion ratio", "Debt to revenue"])
    expect(other).toEqual(["AI-partnership pipeline is unquantified."])
  })
})

describe("formatAxisCompact", () => {
  it("renders chart ticks on compact Indian scales", () => {
    expect(formatAxisCompact(300000)).toMatch(/3/)
    expect(formatAxisCompact(-65000)).toMatch(/65/)
    expect(formatAxisCompact(Number.NaN)).toBe("\u2014")
  })
})

describe("humanizeNarrative", () => {
  it("reads metric keys as words", () => {
    expect(humanizeNarrative("net_profit increased across 4 observations")).toBe(
      "net profit increased across 4 observations",
    )
  })

  it("compacts raw INR-scale figures onto the crore scale", () => {
    expect(
      humanizeNarrative("revenue increased by an average of 240097600000.0 per interval"),
    ).toBe("revenue increased by an average of 24,010 Cr per interval")
    expect(humanizeNarrative("cash position of 45237933333.3 units")).toBe(
      "cash position of 4,524 Cr units",
    )
  })

  it("rounds runaway percentages to one decimal", () => {
    expect(humanizeNarrative("with 66.66666666666666667% directional consistency")).toBe(
      "with 66.7% directional consistency",
    )
  })
})

describe("formatPitNote", () => {
  it("reads internal as_of field names as plain English", () => {
    expect(
      formatPitNote(
        "No evidence in this response has an observation timestamp after the effective as_of.",
      ),
    ).toBe(
      "No evidence in this response has an observation timestamp after the as-of date.",
    )
    expect(
      formatPitNote(
        "Acquired evidence is included only when its availability timestamp is known, timezone-aware, and on or before the effective as_of.",
      ),
    ).toContain("on or before the as-of date.")
    expect(formatPitNote("Evidence newer than as_of is excluded.")).toBe(
      "Evidence newer than as-of date is excluded.",
    )
  })

  it("leaves notes without field jargon unchanged", () => {
    expect(formatPitNote("Comparability is limited to reported figures.")).toBe(
      "Comparability is limited to reported figures.",
    )
  })
})

describe("formatIsoShort", () => {
  it("renders timestamps without the time-of-day", () => {
    expect(formatIsoShort("2026-08-10T12:00:00+00:00")).not.toMatch(/PM|AM|:/)
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

describe("indianCommas", () => {
  it("groups digits in the lakh/crore pattern (3 then 2s)", () => {
    expect(indianCommas("54449")).toBe("54,449")
    expect(indianCommas("120538")).toBe("1,20,538")
    expect(indianCommas("5262119")).toBe("52,62,119")
    expect(indianCommas("2054")).toBe("2,054")
    expect(indianCommas("999")).toBe("999")
  })
})

describe("toCrore / formatCroreNumber", () => {
  it("converts raw INR-scale values to crore", () => {
    expect(toCrore("1205375000000")).toBeCloseTo(120537.5, 5)
    expect(toCrore(null)).toBeNull()
    expect(toCrore("not-a-number")).toBeNull()
  })

  it("formats crore numbers with Indian grouping and no decimals", () => {
    expect(formatCroreNumber(120537.5)).toBe("1,20,538")
  })
})

describe("formatCrore", () => {
  it("renders one consistent crore convention for INR-scale figures", () => {
    expect(formatCrore("1205375000000")).toBe("\u20B91,20,538 crore")
    expect(formatCrore("1604968500000")).toBe("\u20B91,60,497 crore")
    expect(formatCrore("52621193200000")).toBe("\u20B952,62,119 crore")
  })

  it("keeps one decimal for values below 100 crore", () => {
    expect(formatCrore("500000000")).toMatch(/50\.0 crore$/)
  })

  it("renders an em dash for missing or invalid input", () => {
    expect(formatCrore(null)).toBe("\u2014")
    expect(formatCrore("junk")).toBe("\u2014")
  })
})

describe("formatDeltaPct", () => {
  it("treats backend fractions as ratios of the previous value", () => {
    expect(formatDeltaPct("0.3315096961526495903764388676")).toBe("+33.2%")
    expect(formatDeltaPct("-0.09482190149860158434020582879")).toBe("-9.5%")
    expect(formatDeltaPct(0)).toBe("0.0%")
    expect(formatDeltaPct("junk")).toBe("\u2014")
  })
})

describe("formatFiscalYear", () => {
  it("maps Apr–Mar period ends to the Indian fiscal year label", () => {
    expect(formatFiscalYear("2023-03-31")).toBe("FY23")
    expect(formatFiscalYear("2024-03-31")).toBe("FY24")
    expect(formatFiscalYear("2023-12-31")).toBe("FY24")
    expect(formatFiscalYear("unknown")).toBe("unknown")
  })
})

describe("formatPeriodDelta", () => {
  it("returns a fraction-based percentage and crore absolute", () => {
    const { absolute, percentage } = formatPeriodDelta("1065776300000", "1129220100000")
    expect(percentage).toBe("-5.6%")
    expect(absolute).toContain("crore")
  })
})
