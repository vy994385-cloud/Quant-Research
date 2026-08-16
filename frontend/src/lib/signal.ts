export type Tone =
  | "green"
  | "red"
  | "amber"
  | "blue"
  | "slate"

export const SIGNAL_COLORS: Record<string, string> = {
  POSITIVE: "#2aad7c",
  NEGATIVE: "#d66267",
  NEUTRAL: "#7b8aa0",
  MIXED: "#d9a23f",
  INSUFFICIENT_EVIDENCE: "#7b8aa0",
}

export function signalColor(signal: string): string {
  return SIGNAL_COLORS[signal] ?? "#7b8aa0"
}

export function signalTone(signal: string): Tone {
  switch (signal) {
    case "POSITIVE":
      return "green"
    case "NEGATIVE":
      return "red"
    case "MIXED":
    case "INSUFFICIENT_EVIDENCE":
      return "amber"
    default:
      return "slate"
  }
}
