/**
 * Minimal typed client for the /api/v1 production research contract.
 *
 * Every non-2xx response is normalized into an ApiError carrying the
 * structured contract error code, message, and details so the UI can render
 * errors (unknown company, invalid as_of, unavailable research data) without
 * leaking raw server internals.
 */

import type {
  CompanyRankings,
  CompanyResearch,
  CompanyTimelineResponse,
  DiscoveryResponse,
  UniverseRankings,
} from "./types"
import type { ApiErrorBody } from "./types"

export const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

export const HORIZONS = [
  "INTRADAY",
  "SWING",
  "LONG_TERM",
] as const

export type Horizon = (typeof HORIZONS)[number]

export class ApiError extends Error {
  code: string
  status: number
  details: Record<string, unknown>

  constructor(
    message: string,
    code: string,
    status: number,
    details: Record<string, unknown> = {},
  ) {
    super(message)
    this.name = "ApiError"
    this.code = code
    this.status = status
    this.details = details
  }
}

async function request<T>(
  path: string,
  query: Record<string, string | undefined> = {},
): Promise<T> {
  const url = new URL(`${API_URL}${path}`)

  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") {
      url.searchParams.set(key, value)
    }
  }

  let response: Response

  try {
    response = await fetch(url)
  } catch {
    throw new ApiError(
      "Unable to connect to the Quant Research API.",
      "network_error",
      0,
    )
  }

  if (!response.ok) {
    let body: ApiErrorBody | null = null

    try {
      body = (await response.json()) as ApiErrorBody
    } catch {
      // Non-JSON failure body; fall back to the status text.
    }

    throw new ApiError(
      body?.error?.message ??
        `Request failed with status ${response.status}.`,
      body?.error?.code ?? "request_failed",
      response.status,
      body?.error?.details ?? {},
    )
  }

  return (await response.json()) as T
}

export function fetchDiscovery(): Promise<DiscoveryResponse> {
  return request<DiscoveryResponse>("/api/v1/companies")
}

export function fetchResearch(
  symbol: string,
  asOf?: string,
): Promise<CompanyResearch> {
  return request<CompanyResearch>(
    `/api/v1/companies/${encodeURIComponent(symbol)}/research`,
    { as_of: asOf },
  )
}

export function fetchTimeline(
  symbol: string,
  asOf?: string,
): Promise<CompanyTimelineResponse> {
  return request<CompanyTimelineResponse>(
    `/api/v1/companies/${encodeURIComponent(symbol)}/timeline`,
    { as_of: asOf },
  )
}

export function fetchCompanyRankings(
  symbol: string,
  asOf?: string,
): Promise<CompanyRankings> {
  return request<CompanyRankings>(
    `/api/v1/companies/${encodeURIComponent(symbol)}/rankings`,
    { as_of: asOf },
  )
}

export function fetchUniverseRankings(
  horizon: string,
  asOf?: string,
  symbols?: string,
): Promise<UniverseRankings> {
  return request<UniverseRankings>(
    `/api/v1/rankings/${encodeURIComponent(horizon)}`,
    { as_of: asOf, symbols },
  )
}
