/**
 * Neutral presentation tones for data statuses and categories.
 *
 * No judgment-based colouring — these map factual statuses to
 * consistent visual palettes for readability.
 */

export type Tone = "green" | "red" | "amber" | "blue" | "slate"

export function statusTone(status: string): Tone {
  switch (status) {
    case "SUPPORTED":
    case "CONFIRMED":
    case "VALID":
      return "green"
    case "MISSING":
    case "INVALID":
    case "STALE":
    case "HIGH":
      return "red"
    case "MIXED":
    case "PARTIAL":
    case "UNKNOWN":
    case "MEDIUM":
      return "amber"
    default:
      return "slate"
  }
}

export function categoryTone(category: string): Tone {
  switch (category) {
    case "FUNDING":
    case "REGULATORY":
    case "IP_FILING":
      return "blue"
    case "GOVERNANCE":
    case "LEADERSHIP":
      return "amber"
    case "FINANCIAL":
    case "EARNINGS":
      return "green"
    default:
      return "slate"
  }
}

export function observationTypeTone(type: string): Tone {
  switch (type) {
    case "REPORTED":
      return "blue"
    case "DERIVED":
      return "amber"
    case "UNAVAILABLE":
      return "red"
    default:
      return "slate"
  }
}

export function directionTone(direction: string): Tone {
  switch (direction.toUpperCase()) {
    case "POSITIVE":
      return "green"
    case "NEGATIVE":
      return "red"
    case "MIXED":
      return "amber"
    default:
      return "slate"
  }
}
