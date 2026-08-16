/**
 * Presentation helpers for the research contract.
 *
 * Scores and confidences arrive from the API as decimal strings and are
 * rendered without inventing precision that the engine did not produce.
 */

export function formatNumber(value: string): string {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(1) : "—"
}

export function formatScore(value: string): string {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${numeric.toFixed(1)} / 100` : "—"
}

export function formatConfidence(value: string): string {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return "—"
  return `${(numeric <= 1 ? numeric * 100 : numeric).toFixed(0)}%`
}

export function formatLabel(value: string): string {
  if (!value) return value
  return value
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

export function formatTitle(value: string): string {
  return formatLabel(value.replace(/^Validated feature:\s*/i, ""))
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
