/**
 * Research Reports page: structured research combining all dimensions.
 * Serves as a useful research entry point with report structure overview
 * and company selection. Links to full CompanyResearch pages.
 */

import { useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  FileSearch,
  Layers,
  Search,
} from "lucide-react"
import { useDiscovery } from "../useDiscovery"
import { LoadingState, ErrorState } from "../components/States"
import { formatLabel } from "../lib/format"
import { Tag } from "../components/ui"

/* ── Report Structure Definition ─────────────────────────────────────── */

const REPORT_SECTIONS = [
  { section: "Executive Research Summary", type: "FACT + ANALYSIS", desc: "Thesis, direction, conflict detection, intelligence coverage" },
  { section: "Business Overview", type: "FACT", desc: "Business model, competitive position, market intelligence" },
  { section: "Financial Trajectory", type: "FACT + DERIVED", desc: "Revenue, margins, cash flow, debt, capital allocation" },
  { section: "Technology & AI", type: "FACT + INFERENCE", desc: "Technology exposure, AI adoption, innovation indicators" },
  { section: "R&D / Innovation", type: "FACT", desc: "Research initiatives, patent activity, innovation programs" },
  { section: "Competitive Position", type: "FACT + ANALYSIS", desc: "Market position, industry dynamics, customer intelligence" },
  { section: "Recent Developments", type: "FACT", desc: "Timeline of observed changes and developments" },
  { section: "Positive Evidence", type: "FACT", desc: "Evidence items with positive direction" },
  { section: "Negative Evidence", type: "FACT", desc: "Evidence items with negative direction" },
  { section: "Conflicting Evidence", type: "FACT", desc: "Evidence items with conflicting signals" },
  { section: "Risks & Anomalies", type: "FACT + ANALYSIS", desc: "Risk observations, anomaly detection" },
  { section: "Uncertainties", type: "UNKNOWN", desc: "Knowledge gaps, unknown categories" },
  { section: "Signals", type: "FACT", desc: "Research observations with data backing" },
  { section: "Historical Changes", type: "FACT", desc: "Timeline of changes over time" },
  { section: "Provenance", type: "FACT", desc: "Source health, PIT validation, data lineage" },
] as const

/* ── Main Component ──────────────────────────────────────────────────── */

export default function ReportsPage() {
  const navigate = useNavigate()
  const { items, loading, error } = useDiscovery()
  const [query, setQuery] = useState("")

  const researchable = useMemo(
    () => items.filter((i) => i.research_available),
    [items],
  )

  const filteredCompanies = useMemo(() => {
    const q = query.toLowerCase()
    if (!q) return researchable
    return researchable.filter(
      (i) =>
        i.symbol.toLowerCase().includes(q) ||
        (i.company_name ?? "").toLowerCase().includes(q) ||
        i.sector.toLowerCase().includes(q),
    )
  }, [researchable, query])

  return (
    <div className="page-reports">
      <section className="page-hero">
        <p className="page-kicker">Output</p>
        <h1>Research Reports</h1>
        <p className="page-subtitle">
          Structured research reports combining evidence, provenance, and
          point-in-time context. Each section is explicitly labeled as FACT,
          ANALYSIS, INFERENCE, or UNKNOWN.
        </p>
      </section>

      {loading && (
        <LoadingState label="Loading reports" />
      )}

      {error && (
        <ErrorState error={error} />
      )}

      {!loading && !error && (
        <div className="reports-layout">
          {/* LEFT: Report structure */}
          <div className="reports-sidebar">
            <div className="panel">
              <div className="panel-head">
                <h3>Report Structure</h3>
                <span>{REPORT_SECTIONS.length} sections</span>
              </div>
              <div className="reports-structure-list">
                {REPORT_SECTIONS.map((item) => (
                  <div className="report-structure-row" key={item.section}>
                    <div className="report-structure-info">
                      <strong>{item.section}</strong>
                      <small>{item.desc}</small>
                    </div>
                    <Tag text={item.type} tone="slate" />
                  </div>
                ))}
              </div>
            </div>

            <div className="panel">
              <div className="panel-head">
                <h3>Report Principles</h3>
              </div>
              <div className="reports-principles">
                <div className="reports-principle">
                  <span className="reports-principle-label">Evidence-first</span>
                  <span className="reports-principle-text">Every claim is backed by evidence with source provenance</span>
                </div>
                <div className="reports-principle">
                  <span className="reports-principle-label">Point-in-time</span>
                  <span className="reports-principle-text">Evidence is validated against the requested as-of date</span>
                </div>
                <div className="reports-principle">
                  <span className="reports-principle-label">No scores</span>
                  <span className="reports-principle-text">No rankings, scores, or investment recommendations</span>
                </div>
                <div className="reports-principle">
                  <span className="reports-principle-label">Transparent</span>
                  <span className="reports-principle-text">Unknown data is shown, never inferred or fabricated</span>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT: Company list */}
          <div className="reports-content">
            <div className="panel">
              <div className="panel-head">
                <h3>Available Reports</h3>
                <span>{filteredCompanies.length} companies with research</span>
              </div>
              <div className="reports-search">
                <Search size={14} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Filter by name, symbol, or sector..."
                  aria-label="Filter companies"
                />
              </div>
              <div className="reports-company-list">
                {filteredCompanies.map((item) => (
                  <div className="reports-company-group" key={item.symbol}>
                  <button
                    className="reports-company-item"
                    onClick={() => navigate(`/companies/${item.symbol}`)}
                  >
                    <div className="reports-company-info">
                      <Layers size={14} />
                      <div>
                        <strong>{item.symbol}</strong>
                        <small>{item.company_name ?? item.symbol}</small>
                      </div>
                    </div>
                    <div className="reports-company-meta">
                      <Tag text={formatLabel(item.sector)} tone="slate" />
                      <span className="reports-cta">View Report →</span>
                    </div>
                  </button>
                  <button
                    className="reports-company-item reports-professional"
                    onClick={() => navigate(`/professional-report?company=${item.symbol}`)}
                  >
                    <div className="reports-company-info">
                      <FileSearch size={14} />
                      <div>
                        <strong>{item.symbol}</strong>
                        <small>Professional 22-section report</small>
                      </div>
                    </div>
                    <div className="reports-company-meta">
                      <Tag text="22 sections" tone="slate" />
                      <span className="reports-cta">Professional Report →</span>
                    </div>
                  </button>
                  </div>
                ))}
                {filteredCompanies.length === 0 && (
                  <div className="reports-empty">
                    <Search size={16} />
                    <span>No matching companies</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
