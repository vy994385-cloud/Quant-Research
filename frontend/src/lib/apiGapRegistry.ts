/**
 * API Gap Registry: machine-readable list of all backend API requirements.
 *
 * This register documents backend endpoints that the frontend needs
 * but is not (yet) available. Entries that are now served by the
 * capability layer are marked "implemented" so the list reflects the
 * live contract surface. Each entry specifies:
 * - Endpoint path and method
 * - Required query/path parameters
 * - Response shape requirements
 * - Frontend page/feature that depends on it
 * - Priority (critical / high / medium / low)
 * - Status (planned / in-progress / implemented / blocked)
 *
 * This file is the single source of truth for backend API requirements.
 * Update this file whenever a new feature is added to the frontend that
 * requires backend data.
 */

export interface ApiGap {
  id: string
  endpoint: string
  method: "GET" | "POST" | "PUT" | "DELETE"
  description: string
  requiredParams?: string[]
  responseShape: string
  frontendDependency: string
  priority: "critical" | "high" | "medium" | "low"
  status: "planned" | "in-progress" | "implemented" | "blocked"
  notes?: string
}

export const API_GAP_REGISTRY: ApiGap[] = [
  // ── Critical ──
  {
    id: "screener-filter",
    endpoint: "/api/v1/screener",
    method: "POST",
    description: "Filter companies by financial, growth, valuation, technology, and competitive criteria",
    requiredParams: ["definition (ScreenDefinition)", "columns (optional)"],
    responseShape: "ScreenExecutionOutput { name, description, definition_hash, selected_filters, selected_columns, rows: ScreenResultRow[], matched_count, universe_size, notes }",
    frontendDependency: "ScreenerPage — backend screen builder (fields loaded from /screener/fields)",
    priority: "critical",
    status: "implemented",
    notes: "Implemented. Field catalog: GET /api/v1/screener/fields. Operators by value_type (eq/ne/gt/gte/lt/lte/between/contains/is_true/is_false/has/missing).",
  },
  {
    id: "sector-intelligence",
    endpoint: "/api/v1/industries/{sector}/intelligence",
    method: "GET",
    description: "Sector-level intelligence: competitive dynamics, regulation, demand drivers, technology disruption, KPIs",
    requiredParams: ["sector"],
    responseShape: "{ sector: string, companies: CompanySummary[], competitive_dynamics: {...}, regulation: {...}, trends: {...}, kpis: {...} }",
    frontendDependency: "IndustriesPage — sector detail view",
    priority: "critical",
    status: "planned",
  },
  {
    id: "theme-intelligence",
    endpoint: "/api/v1/themes/{themeId}/intelligence",
    method: "GET",
    description: "Cross-company theme aggregation: metrics, trends, regulation, market sizing",
    requiredParams: ["themeId"],
    responseShape: "{ theme: string, companies: ThemeExposure[], metrics: {...}, trends: {...}, regulation: {...} }",
    frontendDependency: "ThemesPage — theme detail view",
    priority: "critical",
    status: "planned",
  },
  {
    id: "technology-companies",
    endpoint: "/api/v1/technologies/{themeId}/companies",
    method: "GET",
    description: "List companies with exposure to a specific technology theme, with evidence types",
    requiredParams: ["themeId"],
    responseShape: "{ companies: TechnologyExposure[], evidence_types: string[] }",
    frontendDependency: "ThemesPage — companies exposed to a theme",
    priority: "critical",
    status: "planned",
  },

  // ── High ──
  {
    id: "screener-financials",
    endpoint: "/api/v1/screener/fields",
    method: "GET",
    description: "Per-company financial/growth/profitability metrics exposed as screener fields for filtering",
    requiredParams: [],
    responseShape: "ScreenerFieldCatalog { fields: ScreenerFieldSpec[], available_count, unavailable_count }",
    frontendDependency: "ScreenerPage — fundamentals, growth, financial quality, valuation filters",
    priority: "high",
    status: "implemented",
    notes: "Implemented. Field catalog covers FUNDAMENTALS/GROWTH/PROFITABILITY/CASH_FLOW/BALANCE_SHEET/MARKET/TECHNICAL/OWNERSHIP categories; per-company deep-financial endpoints remain for the company page.",
  },
  {
    id: "technology-intelligence",
    endpoint: "/api/v1/companies/{symbol}/technology-intelligence",
    method: "GET",
    description: "Per-company technology exposure: AI product, AI adoption, cloud, semiconductors, robotics, cybersecurity, energy",
    requiredParams: ["symbol"],
    responseShape: "{ exposures: TechnologyExposure[], evidence: TechnologyEvidence[] }",
    frontendDependency: "ScreenerPage — technology filters; ThemesPage — per-company exposure",
    priority: "high",
    status: "planned",
    notes: "Technology data currently only available as part of company research notes. Needs structured endpoint.",
  },
  {
    id: "competitors",
    endpoint: "/api/v1/companies/{symbol}/competitors",
    method: "GET",
    description: "Competitor landscape for a company",
    requiredParams: ["symbol"],
    responseShape: "{ competitors: CompetitorInfo[], market_position: {...} }",
    frontendDependency: "ScreenerPage — competitive filters; CompanyResearchPage — competitive intelligence",
    priority: "high",
    status: "planned",
  },
  {
    id: "market-data",
    endpoint: "/api/v1/screener/fields",
    method: "GET",
    description: "Market/valuation data surfaced as screener fields (MARKET + TECHNICAL categories)",
    requiredParams: [],
    responseShape: "ScreenerFieldCatalog (MARKET/TECHNICAL categories)",
    frontendDependency: "ScreenerPage — valuation filters",
    priority: "high",
    status: "implemented",
    notes: "Implemented as screener fields. Finite snapshot-only market data; live market feed (price/volume streaming) is out of scope.",
  },
  {
    id: "rd-data",
    endpoint: "/api/v1/companies/{symbol}/rnd-data",
    method: "GET",
    description: "R&D spending, intensity, patent data",
    requiredParams: ["symbol"],
    responseShape: "{ rnd_spending: number, rnd_intensity: number, patents: PatentInfo[] }",
    frontendDependency: "ScreenerPage — R&D/innovation filters",
    priority: "high",
    status: "planned",
  },

  // ── Medium ──
  {
    id: "batch-research",
    endpoint: "/api/v1/companies/compare",
    method: "GET",
    description: "Side-by-side research comparison for multiple companies",
    requiredParams: ["symbols (comma-separated)", "as_of (optional)"],
    responseShape: "CompanyComparison { comparison_context, as_of, companies, rows: ComparisonRow[], row_count, coverage_summary, conflict_summary, notes }",
    frontendDependency: "ComparePage — single canonical compare call",
    priority: "medium",
    status: "implemented",
    notes: "Implemented. Replaces the per-company fetchResearch loop.",
  },
  {
    id: "company-search",
    endpoint: "/api/v1/companies/search",
    method: "GET",
    description: "Search companies by name, symbol, sector, or technology exposure",
    requiredParams: ["q (query string)"],
    responseShape: "{ results: CompanySearchResult[] }",
    frontendDependency: "ResearchHome — universal search; ScreenerPage — search",
    priority: "medium",
    status: "planned",
  },
  {
    id: "industry-list",
    endpoint: "/api/v1/industries",
    method: "GET",
    description: "List all industries with company counts and research availability",
    requiredParams: [],
    responseShape: "{ industries: IndustrySummary[] }",
    frontendDependency: "IndustriesPage — industry list",
    priority: "medium",
    status: "planned",
    notes: "Currently derived from discovery data. Dedicated endpoint would provide richer metadata.",
  },
  {
    id: "theme-list",
    endpoint: "/api/v1/themes",
    method: "GET",
    description: "List all technology themes with company counts and evidence types",
    requiredParams: [],
    responseShape: "{ themes: ThemeSummary[] }",
    frontendDependency: "ThemesPage — theme list",
    priority: "medium",
    status: "planned",
    notes: "Currently hardcoded in frontend. Dedicated endpoint would provide dynamic theme definitions.",
  },
  {
    id: "evidence-bulk",
    endpoint: "/api/v1/evidence/search",
    method: "GET",
    description: "Universe-wide evidence search (deterministic lexical, source + PIT filters)",
    requiredParams: ["q", "symbol (optional)", "as_of (optional)"],
    responseShape: "EvidenceSearchResponse { query, items: EvidenceSearchHit[], hit_count, searched_count, symbols_searched, notes }",
    frontendDependency: "EvidencePage — universe search across all companies",
    priority: "medium",
    status: "implemented",
    notes: "Implemented. Per-canonical-record bulk export via /api/v1/companies/{symbol}/export.",
  },

  // ── Low ──
  {
    id: "report-generate",
    endpoint: "/api/v1/reports/generate",
    method: "POST",
    description: "Generate a research report for a company",
    requiredParams: ["symbol", "report_type"],
    responseShape: "{ report: ResearchReport }",
    frontendDependency: "ReportsPage — report generation",
    priority: "low",
    status: "planned",
  },
  {
    id: "export-screener",
    endpoint: "/api/v1/companies/{symbol}/export",
    method: "GET",
    description: "Canonical export package per company (research, evidence, screener fields, manifest, sha256)",
    requiredParams: ["symbol"],
    responseShape: "ExportPackage { schema_version, as_of, files, manifest, package_sha256 }",
    frontendDependency: "EvidencePage — Export Package download",
    priority: "low",
    status: "implemented",
    notes: "Implemented. Schema v2.0.0; JSON payload downloaded as a browser file.",
  },
]

/* ── Registry utilities ─────────────────────────────────────────────── */

export function getGapsByPriority(priority: ApiGap["priority"]): ApiGap[] {
  return API_GAP_REGISTRY.filter((g) => g.priority === priority)
}

export function getGapsByStatus(status: ApiGap["status"]): ApiGap[] {
  return API_GAP_REGISTRY.filter((g) => g.status === status)
}

export function getGapsByDependency(page: string): ApiGap[] {
  return API_GAP_REGISTRY.filter((g) =>
    g.frontendDependency.toLowerCase().includes(page.toLowerCase()),
  )
}

export function getCriticalGaps(): ApiGap[] {
  return getGapsByPriority("critical")
}

export function getRegistryStats() {
  return {
    total: API_GAP_REGISTRY.length,
    byPriority: {
      critical: getGapsByPriority("critical").length,
      high: getGapsByPriority("high").length,
      medium: getGapsByPriority("medium").length,
      low: getGapsByPriority("low").length,
    },
    byStatus: {
      planned: getGapsByStatus("planned").length,
      "in-progress": getGapsByStatus("in-progress").length,
      implemented: getGapsByStatus("implemented").length,
      blocked: getGapsByStatus("blocked").length,
    },
  }
}
