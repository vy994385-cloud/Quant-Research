/**
 * Presentation helpers for the research contract.
 *
 * Pure data formatting — no scores, confidences, or investment judgments.
 */

export function formatNumber(value: string): string {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(1) : "—"
}

export function formatLabel(value: string): string {
  if (!value) return value
  return value
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

/** "1 item" / "3 items" — avoids the "1 items" class of copy bugs. */
export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`
}

/**
 * Human display form for backend event/evidence titles.
 *
 * Identifier-like inputs (snake_case feature names) become Title Case;
 * natural-language titles keep their wording but read as prose: embedded
 * metric keys ("Increasing net_profit") gain spaces, shouty period tokens
 * soften, and only the first letter is capitalised. When the ticker is known,
 * a leading symbol prefix ("HDFCBANK ANNUAL …") is dropped so rows read
 * naturally inside that company's workspace.
 */
/** Words that continue a real company name after its first token. */
const COMPANY_NAME_WORD_RE =
  /^(industries|bank|banks|limited|ltd|llp|motors|consultancy|consulting|services|systems|pharmaceuticals?|laboratories|petroleum|steel|group|holdings|technologies|capital|finance)\b/i

export function formatTitle(value: string, symbol?: string): string {
  let text = value.replace(/^Validated (?:research measure|feature):\s*/i, "").trim()
  if (symbol) {
    // Strip a leading bare ticker unless what follows continues a real
    // company name ("Reliance Industries AGM: …"), where stripping would
    // leave a dangling fragment of the name.
    const prefix = new RegExp(`^${escapeRegExp(symbol)}[\\s:-]+`, "i")
    const match = prefix.exec(text)
    if (match && !COMPANY_NAME_WORD_RE.test(text.slice(match[0].length))) {
      text = text.slice(match[0].length).trim()
    }
  }
  if (/^[a-z0-9]+(_[a-z0-9]+)+$/i.test(text)) {
    return formatLabel(text)
  }
  text = text.replace(/\b(ANNUAL|QUARTERLY|MONTHLY)\b/g, (token) =>
    token.charAt(0) + token.slice(1).toLowerCase(),
  )
  // Embedded metric keys read as words ("Increasing net_profit" -> "…net profit").
  text = text.replace(/\b([a-z]+(?:_[a-z0-9]+)+)\b/g, (key) =>
    /^\d/.test(key) ? key : key.replaceAll("_", " "),
  )
  // Period boilerplate compacts to the Indian fiscal year:
  // "Annual financials for the period ending 2023-03-31" -> "Annual financials, FY23".
  text = text.replace(
    /,?\s+for the period ending (\d{4}-\d{2}-\d{2})/gi,
    (_match, date: string) => `, ${formatFiscalYear(date)}`,
  )
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text
}

/** Title-case words in an already-lowercase or uppercase label. */
function titleCaseWords(text: string): string {
  return text
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ")
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

/**
 * Display form for recorded source names. Internal slugs ("recorded_financials",
 * "hdfcbank-capital-bonds") render as readable labels; names that already read
 * like prose pass through untouched.
 */
export function formatSourceName(value: string | null | undefined): string {
  if (!value) return "\u2014"
  const restoreFiscal = (text: string) =>
    text.replace(/\bq[1-4]fy\d{2,4}\b/gi, (m) => m.toUpperCase()).replace(/\bfy\d{2,4}\b/gi, (m) => m.toUpperCase())
  if (!/^[\w][\w -]*$/.test(value) || !/[_-]|\s{2,}/.test(value)) {
    // Shouting ALL-CAPS labels ("RECORDED EARNINGS CALL NOTES") soften to
    // title case; short acronyms ("NSE") and mixed-case names pass through.
    if (value === value.toUpperCase() && /[A-Z]/.test(value) && value.trim().length > 5) {
      return titleCaseWords(value)
    }
    return value
  }
  return restoreFiscal(
    value
      .split(/[-_]+/)
      .filter(Boolean)
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(" "),
  )
}

/**
 * Condensed rendering of boilerplate source-note sentences composed by the
 * research engine: "Recorded source 'reliance-agm-management' (Mint) was
 * reviewed for evidence relevant to this research question." becomes
 * "Reliance Agm Management (Mint)". Non-matching text passes through.
 */
export function formatSourceNote(text: string): string {
  const match = /^.*?[Rr]ecorded source '([^']+)' \(([^)]+)\)[^.]*\.?$/.exec(text)
  if (!match) return text
  const name = formatSourceName(match[1])
  return `${name} (${match[2]})`
}

/**
 * Presentation cleanup for recorded PIT / comparability notes: internal field
 * names read as plain English ("after the effective as_of" -> "after the
 * as-of date"). Purely presentational — sentence meaning is unchanged.
 */
export function formatPitNote(text: string): string {
  return text
    .replace(/\bthe effective as_of\b/gi, "the as-of date")
    .replace(/\beffective as_of\b/gi, "as-of date")
    .replace(/\bas_of\b/g, "as-of date")
}

/**
 * Presentation cleanup for narrative sentences composed by the research
 * engine: snake_case metric keys read as words, oversized raw figures render
 * compactly on the Indian crore scale, and runaway decimals round sensibly.
 * Purely presentational — no values change meaning.
 */
export function humanizeNarrative(text: string): string {
  // 1. Round runaway percentages ("66.66666666666666667%" -> "66.7%").
  let out = text.replace(/(\d+(?:\.\d+)?)%/g, (_match, digits: string) =>
    Number(digits) >= 1000 || !digits.includes(".")
      ? `${Number(digits)}%`
      : `${Number(digits).toFixed(1)}%`,
  )
  // 2. Compact oversized raw figures onto readable scales.
  out = out.replace(/\d{7,}(?:\.\d+)?/g, (raw) => {
    const numeric = Number(raw)
    return Number.isFinite(numeric) ? formatCompactFigure(numeric) : raw
  })
  // 3. Metric keys read as words ("net_profit" -> "net profit").
  out = out.replace(/\b([a-z]+(?:_[a-z0-9]+)+)\b/g, (key) =>
    /^\d/.test(key) ? key : key.replaceAll("_", " "),
  )
  return out
}

/** Compact figure: INR-scale magnitudes render in crore; others group digits. */
function formatCompactFigure(numeric: number): string {
  if (Math.abs(numeric) >= 1e7) {
    const crore = numeric / 1e7
    const digits = Math.abs(crore) >= 100 ? 0 : 1
    return `${crore.toLocaleString("en-IN", {
      minimumFractionDigits: 0,
      maximumFractionDigits: digits,
    })} Cr`
  }
  return numeric.toLocaleString("en-IN", { maximumFractionDigits: 1 })
}

/**
 * Compact timestamp for dense table cells: date only. Full precision stays
 * available in detail views via formatIso.
 */
export function formatIsoShort(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (match) {
    return formatIso(value)
  }
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })
}

export function formatIso(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)

  if (match) {
    const year = Number(match[1])
    const month = Number(match[2])
    const day = Number(match[3])
    const date = new Date(year, month - 1, day)
    return Number.isNaN(date.getTime())
      ? value
      : date.toLocaleDateString(undefined, {
          dateStyle: "medium",
        })
  }

  const date = new Date(value)

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      })
}

export function formatEvidenceObservation(value: string): string {
  return formatIso(value)
}

/**
 * Correct Indian digit grouping: rightmost group of 3, then groups of 2
 * (e.g. 1253790 -> "12,53,790"). The previous implementation produced
 * malformed output such as "544,49"; this is the standard lakh/crore split.
 */
export function indianCommas(integerPart: string): string {
  if (!/^\d+$/.test(integerPart)) return integerPart
  if (integerPart.length <= 3) return integerPart
  const last3 = integerPart.slice(-3)
  const rest = integerPart.slice(0, -3)
  const groups: string[] = []
  for (let i = rest.length; i > 0; i -= 2) {
    groups.push(rest.slice(Math.max(0, i - 2), i))
  }
  return `${groups.reverse().join(",")},${last3}`
}

const CRORE = 1e7

const croreFormatter = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 0,
})

/**
 * Numeric crore value from a raw INR-scale figure ("1205375000000" ->
 * 120538). Returns null for missing/non-finite input.
 */
export function toCrore(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null
  const numeric = typeof value === "string" ? Number(value) : value
  if (!Number.isFinite(numeric)) return null
  return numeric / CRORE
}

/** Grouped integer rendering of a crore-scale number (en-IN grouping). */
export function formatCroreNumber(croreValue: number): string {
  return croreFormatter.format(Math.round(croreValue))
}

/**
 * Single consistent financial display convention: raw INR-scale figures are
 * converted to crore and rendered as "₹1,20,538 crore". Values below 100
 * crore keep one decimal so small figures stay meaningful.
 */
export function formatCrore(
  value: string | number | null | undefined,
  options: { withSymbol?: boolean } = {},
): string {
  const croreValue = toCrore(value)
  if (croreValue === null) return "\u2014"
  const { withSymbol = true } = options
  const prefix = withSymbol ? "\u20B9" : ""
  if (Math.abs(croreValue) < 100) {
    const text = croreValue.toLocaleString("en-IN", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })
    return `${prefix}${text} crore`
  }
  return `${prefix}${formatCroreNumber(croreValue)} crore`
}

export function formatDelta(value: string | number): string {
  const numeric = typeof value === "string" ? Number(value) : value
  if (!Number.isFinite(numeric)) return "\u2014"
  return formatCrore(numeric)
}

/**
 * Percent formatting for change ratios. Backend delta_pct values arrive as
 * fractions of the previous value (0.3315 = "+33.2%"); they must never be
 * rendered as raw decimals ("+0.33%").
 */
export function formatDeltaPct(value: string | number): string {
  const numeric = typeof value === "string" ? Number(value) : value
  if (!Number.isFinite(numeric)) return "\u2014"
  const pct = numeric * 100
  const sign = pct > 0 ? "+" : ""
  return `${sign}${pct.toFixed(1)}%`
}

/**
 * Human-readable confidence: numeric decimals become percentages
 * ("0.8" -> "80%"); qualitative labels pass through in title case.
 */
export function formatConfidence(value: string | null | undefined): string {
  if (!value) return "\u2014"
  const numeric = Number(value)
  if (Number.isFinite(numeric) && value.trim() !== "") {
    return `${Math.round(numeric * 100)}%`
  }
  return formatLabel(value)
}

/**
 * Short period label for table columns: month + year of the period end
 * (e.g. "Mar 2026"). Falls back to the raw value when unparseable.
 */
export function formatPeriodColumn(periodEnd: string): string {
  const match = /^(\d{4})-(\d{2})/.exec(periodEnd)
  if (!match) return periodEnd
  const months = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ]
  return `${months[Number(match[2]) - 1] ?? match[2]} ${match[1]}`
}

/**
 * Indian fiscal-year label for a period end (Apr–Mar fiscal calendar):
 * "2024-03-31" -> "FY24", "2023-12-31" -> "FY24". Falls back to the raw
 * value when the period cannot be parsed as an annual date.
 */
export function formatFiscalYear(periodEnd: string): string {
  const match = /^(\d{4})-(\d{2})/.exec(periodEnd)
  if (!match) return periodEnd
  const year = Number(match[1])
  const month = Number(match[2])
  const fiscalYear = month >= 4 ? year + 1 : year
  return `FY${String(fiscalYear).slice(-2)}`
}

export function formatPeriodDelta(
  current: string | number,
  previous: string | number,
): { absolute: string; percentage: string } {
  const curr = typeof current === "string" ? Number(current) : current
  const prev = typeof previous === "string" ? Number(previous) : previous

  if (!Number.isFinite(curr) || !Number.isFinite(prev)) {
    return { absolute: "\u2014", percentage: "\u2014" }
  }

  const absolute = curr - prev
  // Fraction of the previous value; formatDeltaPct scales by 100.
  const ratio = prev !== 0 ? absolute / Math.abs(prev) : null

  return {
    absolute: formatDelta(absolute),
    percentage: ratio === null ? "\u2014" : formatDeltaPct(ratio),
  }
}

/**
 * Compact human axis scale for chart tick labels: Indian compact notation
 * renders 300000 as "3L" and -65000 as "-65K" instead of "300,000".
 */
const axisFormatter = new Intl.NumberFormat("en-IN", {
  notation: "compact",
  maximumFractionDigits: 1,
})

export function formatAxisCompact(value: number): string {
  if (!Number.isFinite(value)) return "\u2014"
  return axisFormatter.format(value)
}

const MEASURE_UNCERTAINTY_RE =
  /^(?:validated (?:research measure|feature):\s*)?(.+?)\s+has limited evidence reliability\.?$/i

/**
 * Splits a narrative uncertainty list into uniform "measure has limited
 * evidence reliability" items (rendered once as a compact chip group) and
 * everything else (kept as individual sentences).
 */
export function splitMeasureUncertainty(items: string[]): {
  measures: string[]
  other: string[]
} {
  const measures: string[] = []
  const other: string[] = []
  for (const item of items) {
    const match = MEASURE_UNCERTAINTY_RE.exec(item.trim())
    if (match) {
      const name = match[1]
      // Metric keys read as words ("cash_conversion_ratio" -> "Cash conversion ratio").
      measures.push(/^[a-z0-9]+(_[a-z0-9]+)+$/i.test(name) ? formatLabel(name) : name)
    } else {
      other.push(item)
    }
  }
  return { measures, other }
}
