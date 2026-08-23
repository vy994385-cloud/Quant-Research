/**
 * API Gap Registry: machine-readable list of all backend API requirements.
 *
 * This registry documents every backend endpoint that the frontend needs
 * but is not yet available. Each entry specifies:
 * - Endpoint path and method
 * - Required query/path parameters
 * - Response shape requirements
 * - Frontend page/feature that depends on it
 * - Priority (critical / high / medium / low)
 * - Status (planned / in-progress / blocked)
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
  status: "planned" | "in-progress" | "blocked"
  notes?: string
}

export const API_GAP_REGISTRY: ApiGap[] = [
  // ── Critical ──
  {
    id: "screener-filter",
    endpoint: "/api/v1/screener",
    method: "GET",
    description: "Filter companies by financial, growth, valuation, technology, and competitive criteria",
    requiredParams: ["filters (JSON array)", "page", "limit"],
    responseShape: "{ results: ScreenerResult[], total: number, page: number }",
    frontendDependency: "ScreenerPage — composable filter architecture",
    priority: "critical",
    status: "planned",
    notes: "Backend currently only supports /api/v1/rankings/{horizon}. Screener needs per-company financial, growth, valuation, technology data with filter evaluation.",
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
    endpoint: "/api/v1/companies/{symbol}/deep-financial-insights",
    method: "GET",
    description: "Per-company financial data for screener filtering: revenue, margins, EPS, ROE, ROCE, OCF, FCF",
    requiredParams: ["symbol"],
    responseShape: "{ metrics: DeepMetricObservation[], series: DeepFinancialSeries[] }",
    frontendDependency: "ScreenerPage — fundamentals, growth, financial quality, valuation filters",
    priority: "high",
    status: "planned",
    notes: "Endpoint exists but not designed for bulk filtering. Needs batch/bulk variant for screener.",
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
    endpoint: "/api/v1/companies/{symbol}/market-data",
    method: "GET",
    description: "Market price, volume, P/E, EV/EBITDA, P/B for valuation filters",
    requiredParams: ["symbol"],
    responseShape: "{ price: {...}, valuation: {...}, volume: {...} }",
    frontendDependency: "ScreenerPage — valuation filters",
    priority: "high",
    status: "planned",
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
    endpoint: "/api/v1/companies/batch-research",
    method: "POST",
    description: "Batch fetch research data for multiple companies (screener results, compare)",
    requiredParams: ["symbols (array)"],
    responseShape: "{ companies: CompanyResearch[] }",
    frontendDependency: "ScreenerPage — displaying research data for results; ComparePage",
    priority: "medium",
    status: "planned",
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
    endpoint: "/api/v1/evidence/bulk",
    method: "POST",
    description: "Bulk fetch evidence for multiple source IDs",
    requiredParams: ["source_ids (array)"],
    responseShape: "{ evidence: EvidenceRecord[] }",
    frontendDependency: "EvidencePage — bulk evidence traceability",
    priority: "medium",
    status: "planned",
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
    endpoint: "/api/v1/screener/export",
    method: "POST",
    description: "Export screener results as CSV/Excel",
    requiredParams: ["filters (JSON array)", "format"],
    responseShape: "{ download_url: string }",
    frontendDependency: "ScreenerPage — export functionality",
    priority: "low",
    status: "planned",
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
      blocked: getGapsByStatus("blocked").length,
    },
  }
}
