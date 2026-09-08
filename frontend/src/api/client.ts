/**
 * Minimal typed client for the /api/v1 production research contract.
 *
 * Every non-2xx response is normalized into an ApiError carrying the
 * structured contract error code, message, and details so the UI can render
 * errors (unknown company, invalid as_of, unavailable research data) without
 * leaking raw server internals.
 */

import type {
  CalendarResponse,
  CompanyComparison,
  CompanyCorporateActionsResponse,
  CompanyCrossDomainResponse,
  CompanyDeepTechnicalResponse,
  CompanyEvidenceResponse,
  CompanyNewsResponse,
  CompanyProfessionalReportResponse,
  CompanyResearch,
  CompanyResearchGapsResponse,
  CompanyTimelineResponse,
  DiscoveryFeed,
  DiscoveryResponse,
  EvidenceDeltaReport,
  EvidenceSearchResponse,
  ExportPackage,
  ResearchChangesResponse,
  ScreenDefinitionPayload,
  ScreenExecutionOutput,
  ScreenerFieldCatalog,
  TrendingResult,
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

/**
 * Cheap reachability probe used after a request fails at the network level.
 * CORS-blocked 5xx responses and offline servers are indistinguishable from
 * the rejected fetch alone; one lightweight GET to a known-good endpoint
 * separates "API down" from "this data area failed server-side".
 */
async function probeApiReachable(): Promise<boolean> {
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 5000)
    const response = await fetch(`${API_URL}/api/v1/companies`, {
      cache: "no-store",
      signal: controller.signal,
    })
    clearTimeout(timer)
    // Any HTTP answer — even an error status — proves the API is reachable.
    return response.status > 0
  } catch {
    return false
  }
}

async function request<T>(
  path: string,
  query: Record<string, string | undefined> = {},
  init?: { method?: string; body?: unknown },
): Promise<T> {
  const url = new URL(`${API_URL}${path}`)

  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") {
      url.searchParams.set(key, value)
    }
  }

  let response: Response

  try {
    response = await fetch(url, {
      method: init?.method ?? "GET",
      headers:
        init?.body !== undefined
          ? { "Content-Type": "application/json" }
          : undefined,
      body:
        init?.body !== undefined ? JSON.stringify(init.body) : undefined,
    })
  } catch {
    // The fetch itself failed. Distinguish an unreachable API from a
    // server-side failure on this specific research area (e.g. a 5xx whose
    // error body is blocked by CORS) so the UI never claims a connectivity
    // outage that did not happen.
    const reachable = await probeApiReachable()
    throw reachable
      ? new ApiError(
          "The server could not produce this research area right now.",
          "server_unavailable",
          0,
        )
      : new ApiError(
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

export function fetchCompanyNews(
  symbol: string,
  asOf?: string,
): Promise<CompanyNewsResponse> {
  return request<CompanyNewsResponse>(
    `/api/v1/companies/${encodeURIComponent(symbol)}/news`,
    { as_of: asOf },
  )
}

export function fetchCorporateActions(
  symbol: string,
  asOf?: string,
): Promise<CompanyCorporateActionsResponse> {
  return request<CompanyCorporateActionsResponse>(
    `/api/v1/companies/${encodeURIComponent(symbol)}/corporate-actions`,
    { as_of: asOf },
  )
}

export function fetchDeepTechnicals(
  symbol: string,
  asOf?: string,
): Promise<CompanyDeepTechnicalResponse> {
  return request<CompanyDeepTechnicalResponse>(
    `/api/v1/companies/${encodeURIComponent(symbol)}/deep-technicals`,
    { as_of: asOf },
  )
}

export function fetchCrossDomain(
  symbol: string,
  asOf?: string,
): Promise<CompanyCrossDomainResponse> {
  return request<CompanyCrossDomainResponse>(
    `/api/v1/companies/${encodeURIComponent(symbol)}/cross-domain`,
    { as_of: asOf },
  )
}

export function fetchResearchGaps(
  symbol: string,
  asOf?: string,
): Promise<CompanyResearchGapsResponse> {
  return request<CompanyResearchGapsResponse>(
    `/api/v1/companies/${encodeURIComponent(symbol)}/research-gaps`,
    { as_of: asOf },
  )
}

export function fetchEvidenceLineage(
  symbol: string,
  asOf?: string,
): Promise<CompanyEvidenceResponse> {
  return request<CompanyEvidenceResponse>(
    `/api/v1/companies/${encodeURIComponent(symbol)}/evidence`,
    { as_of: asOf },
  )
}

export function fetchProfessionalReport(
  symbol: string,
  asOf?: string,
): Promise<CompanyProfessionalReportResponse> {
  return request<CompanyProfessionalReportResponse>(
    `/api/v1/companies/${encodeURIComponent(symbol)}/research-report`,
    { as_of: asOf },
  )
}

/* ── Capability layer: screener ──────────────────────────────────── */

export function fetchScreenerFields(): Promise<ScreenerFieldCatalog> {
  return request<ScreenerFieldCatalog>("/api/v1/screener/fields")
}

export function runScreen(
  definition: ScreenDefinitionPayload,
  columns?: string[],
): Promise<ScreenExecutionOutput> {
  return request<ScreenExecutionOutput>(
    "/api/v1/screener",
    {},
    { method: "POST", body: { definition, columns: columns ?? null } },
  )
}

/* ── Capability layer: evidence search ───────────────────────────── */

export function searchEvidence(params: {
  q?: string
  exact_phrase?: string
  symbol?: string
  category?: string
  source_id?: string
  as_of?: string
}): Promise<EvidenceSearchResponse> {
  return request<EvidenceSearchResponse>("/api/v1/evidence/search", {
    q: params.q,
    exact_phrase: params.exact_phrase,
    symbol: params.symbol,
    category: params.category,
    source_id: params.source_id,
    as_of: params.as_of,
  })
}

/* ── Research change radar ───────────────────────────────────────── */

export function fetchResearchChanges(
  symbol: string,
  baselineAsOf: string,
  currentAsOf: string,
): Promise<ResearchChangesResponse> {
  return request<ResearchChangesResponse>("/api/v1/research-changes", {
    symbol,
    baseline_as_of: baselineAsOf,
    current_as_of: currentAsOf,
  })
}

export function fetchResearchDelta(
  symbol: string,
  baselineAsOf: string,
  currentAsOf: string,
): Promise<EvidenceDeltaReport> {
  return request<EvidenceDeltaReport>("/api/v1/research-delta", {
    symbol,
    baseline_as_of: baselineAsOf,
    current_as_of: currentAsOf,
  })
}

export function fetchCalendar(
  symbols: string,
  rangeFrom: string,
  rangeTo: string,
): Promise<CalendarResponse> {
  return request<CalendarResponse>("/api/v1/calendar", {
    symbols,
    range_from: rangeFrom,
    range_to: rangeTo,
  })
}

/* ── Capability layer: discovery feed / trending ─────────────────── */

export function fetchDiscoveryFeed(params?: {
  as_of?: string
  item_types?: string[]
  limit_per_symbol?: number
}): Promise<DiscoveryFeed> {
  return request<DiscoveryFeed>("/api/v1/discovery", {
    as_of: params?.as_of,
    item_types: params?.item_types?.length
      ? params.item_types.join(",")
      : undefined,
    limit_per_symbol:
      params?.limit_per_symbol !== undefined
        ? String(params.limit_per_symbol)
        : undefined,
  })
}

export function fetchDiscoveryTrending(params?: {
  as_of?: string
  window_days?: number
}): Promise<TrendingResult> {
  return request<TrendingResult>("/api/v1/discovery/trending", {
    as_of: params?.as_of,
    window_days:
      params?.window_days !== undefined
        ? String(params.window_days)
        : undefined,
  })
}

/* ── Capability layer: comparison ────────────────────────────────── */

export function fetchCompare(
  symbols: string[],
  asOf?: string,
): Promise<CompanyComparison> {
  return request<CompanyComparison>("/api/v1/companies/compare", {
    symbols: symbols.join(","),
    as_of: asOf,
  })
}

/* ── Capability layer: export package ────────────────────────────── */

export function fetchExportPackage(
  symbol: string,
  asOf?: string,
): Promise<ExportPackage> {
  return request<ExportPackage>(
    `/api/v1/companies/${encodeURIComponent(symbol)}/export`,
    { as_of: asOf },
  )
}

export function downloadExportPackage(pkg: ExportPackage): void {
  const blob = new Blob([JSON.stringify(pkg, null, 2)], {
    type: "application/json",
  })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = `quant-research-export-${pkg.as_of.slice(0, 10)}.json`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
