/**
 * Companies page: company discovery and listing.
 * Factual metadata only — no scores, no rankings.
 */

import { useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Activity, Building2, FileSearch } from "lucide-react"
import { useDiscovery } from "../useDiscovery"
import { formatLabel } from "../lib/format"
import { Tag } from "../components/ui"

export default function CompaniesPage() {
  const navigate = useNavigate()
  const { items, loading, error } = useDiscovery()
  const [query, setQuery] = useState("")

  const filtered = useMemo(() => {
    const q = query.toLowerCase()
    if (!q) return items
    return items.filter((item) => {
      return (
        item.symbol.toLowerCase().includes(q) ||
        (item.company_name ?? "").toLowerCase().includes(q) ||
        item.sector.toLowerCase().includes(q)
      )
    })
  }, [items, query])

  return (
    <div className="page-companies">
      <section className="page-hero">
        <h1>Companies</h1>
        <p className="page-subtitle">
          Company discovery with factual research metadata. No scores, no rankings.
        </p>
      </section>

      <section className="page-search-section">
        <div className="home-search">
          <Building2 size={17} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter by name, symbol, or sector..."
            aria-label="Filter companies"
          />
        </div>
      </section>

      {loading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading companies</strong>
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
        <section className="companies-table-section">
          <div className="panel">
            <div className="panel-head">
              <h3>All Companies</h3>
              <span>{filtered.length} of {items.length} companies</span>
            </div>
            <div className="data-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Symbol</th>
                    <th>Company Name</th>
                    <th>Sector</th>
                    <th>Research</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((item) => (
                    <tr
                      key={item.symbol}
                      className="clickable-row"
                      onClick={() => navigate(`/companies/${item.symbol}`)}
                      onKeyDown={(e) => { if (e.key === "Enter") navigate(`/companies/${item.symbol}`) }}
                      tabIndex={0}
                      role="link"
                    >
                      <td><strong>{item.symbol}</strong></td>
                      <td>{item.company_name ?? "—"}</td>
                      <td><Tag text={formatLabel(item.sector)} tone="slate" /></td>
                      <td>
                        <span className={`status-badge ${item.research_available ? "green" : "slate"}`}>
                          <span className="status-badge-dot" />
                          {item.research_available ? "Available" : "Unavailable"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
