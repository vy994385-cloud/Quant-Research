/**
 * HOME — institutional landing for the research terminal.
 *
 * Compact entry point: brand statement, primary search hand-off,
 * coverage summary and navigation into the workspaces. Activity feeds
 * live on /discover; this page never duplicates them.
 *
 * No scores, no rankings, no recommendations.
 */

import { Link, useNavigate } from "react-router-dom"
import {
  Activity,
  ArrowRight,
  Building2,
  CheckCircle2,
  FileSearch,
  GitCompareArrows,
  Layers,
  Search,
} from "lucide-react"
import { useDiscovery } from "../useDiscovery"
import { SectionDivider } from "../components/ui"

export default function ResearchHome() {
  const navigate = useNavigate()
  const { items, loading, error } = useDiscovery()

  const tracked = items.filter((item) => item.research_available)
  const sectors = new Set(tracked.map((item) => item.sector))

  return (
    <div className="page-home-landing">
      <section className="page-hero">
        <h1>Research Home</h1>
        <p className="page-subtitle">
          An evidence-first research terminal. Facts, data, sources and provenance are
          presented as recorded — no scores, no rankings, no recommendations. The
          researcher makes the judgment.
        </p>
      </section>

      <section className="home-entry-search" aria-label="Open company research">
        <button type="button" onClick={() => navigate("/discover")} className="home-search-handoff">
          <Search size={17} aria-hidden />
          <span>Search companies, symbols and sectors in Discover…</span>
          <ArrowRight size={14} aria-hidden />
        </button>
      </section>

      {loading && (
        <div className="loading-state compact" role="status">
          <Activity className="spin" size={18} />
          <span>Loading coverage summary…</span>
        </div>
      )}

      {error && (
        <div className="empty-state error" role="alert">
          <FileSearch size={28} />
          <strong>Discovery unavailable</strong>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && (
        <>
          <section className="home-summary" aria-label="Coverage summary">
            <div className="summary-stat">
              <strong>{tracked.length}</strong>
              <span>Companies under coverage</span>
            </div>
            <div className="summary-stat">
              <strong>{sectors.size}</strong>
              <span>Sectors</span>
            </div>
            <div className="summary-stat summary-note">
              <CheckCircle2 size={13} aria-hidden />
              <span>Every figure links back to dated evidence</span>
            </div>
          </section>

          {tracked.length > 0 && (
            <section className="home-companies" aria-label="Companies under coverage">
              <SectionDivider label="COMPANIES UNDER COVERAGE" />
              <ul className="home-company-list">
                {tracked.map((item) => (
                  <li key={item.symbol}>
                    <Link to={`/companies/${encodeURIComponent(item.symbol)}`}>
                      <strong>{item.company_name ?? item.symbol}</strong>
                      <span className="mono">{item.symbol}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <SectionDivider label="ENTER THE TERMINAL" />
          <nav className="home-entry-grid" aria-label="Terminal sections">
            <Link className="home-entry-card" to="/discover">
              <FileSearch size={16} aria-hidden />
              <strong>Discover</strong>
              <span>Latest developments, disclosures, actions and gaps across the universe.</span>
            </Link>
            <Link className="home-entry-card" to="/companies">
              <Building2 size={16} aria-hidden />
              <strong>Companies</strong>
              <span>The tracked index; open any company workspace.</span>
            </Link>
            <Link className="home-entry-card" to="/financial-intelligence">
              <Activity size={16} aria-hidden />
              <strong>Financial Intelligence</strong>
              <span>Cross-company financial observations from reported filings.</span>
            </Link>
            <Link className="home-entry-card" to="/evidence">
              <FileSearch size={16} aria-hidden />
              <strong>Evidence Record</strong>
              <span>Every claim with source, verification and point-in-time context.</span>
            </Link>
            <Link className="home-entry-card" to="/reports">
              <Layers size={16} aria-hidden />
              <strong>Reports</strong>
              <span>Document output: dossiers and the professional report.</span>
            </Link>
            <Link className="home-entry-card" to="/compare">
              <GitCompareArrows size={16} aria-hidden />
              <strong>Compare</strong>
              <span>Side-by-side evidence tables across companies. No winners.</span>
            </Link>
          </nav>

          <p className="home-principle">
            Missing is shown as missing, unavailable as unavailable, conflict as conflict.
            None of these is treated as an error or a judgment.
          </p>
        </>
      )}
    </div>
  )
}
