/**
 * ResearchHomeHeader — editorial page header with integrated search.
 *
 * Communicates: RESEARCH UNIVERSE → entry point for discovering what changed.
 *
 * Uses PageHeader from VISUAL SYSTEM 5.0 for consistent editorial treatment.
 */

import { Link } from "react-router-dom"
import {
  ArrowUpRight,
  BarChart3,
  Compass,
  Filter,
  GitCompareArrows,
  Lightbulb,
  Search,
  XCircle,
} from "lucide-react"
import type { DiscoveryItem } from "../../api/types"
import { EmptyCopy, PageHeader } from "../ui"
import { formatLabel } from "../../lib/format"

const DESTINATIONS = [
  { to: "/themes", icon: Lightbulb, label: "Themes" },
  { to: "/industries", icon: BarChart3, label: "Industries" },
  { to: "/screener", icon: Filter, label: "Screener" },
  { to: "/compare", icon: GitCompareArrows, label: "Compare" },
  { to: "/companies", icon: Compass, label: "All Companies" },
]

export function ResearchHomeHeader({
  query,
  onQueryChange,
  matchedCompanies,
  items,
}: {
  query: string
  onQueryChange: (q: string) => void
  matchedCompanies: DiscoveryItem[]
  items: DiscoveryItem[]
}) {
  const q = query.trim().toLowerCase()

  return (
    <header className="rh-header" aria-label="Research home">
      <PageHeader
        kicker="Research home"
        title="What's new in the research universe"
        subtitle={`${items.length} tracked companies · evidence-first research`}
      />

      <div className="rh-search" role="search" aria-label="Search companies">
        <Search size={16} className="rh-search-icon" aria-hidden />
        <input
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          placeholder="Search by company, symbol, or sector"
          aria-label="Search companies, symbols, or sectors"
        />
        {query && (
          <button
            type="button"
            className="rh-search-clear"
            onClick={() => onQueryChange("")}
            aria-label="Clear search"
          >
            <XCircle size={14} />
          </button>
        )}
      </div>

      {q && (
        <div className="rh-search-results" role="listbox" aria-label="Search results">
          {matchedCompanies.length === 0 ? (
            <EmptyCopy text="No tracked companies match this search." />
          ) : (
            <ul className="rh-search-hits">
              {matchedCompanies.slice(0, 6).map((item) => (
                <li key={item.symbol} role="option">
                  <Link to={`/companies/${encodeURIComponent(item.symbol)}`}>
                    <span className="rh-hit-name">{item.company_name ?? item.symbol}</span>
                    <span className="rh-hit-symbol mono">{item.symbol}</span>
                    <span className="rh-hit-sector">{formatLabel(item.sector)}</span>
                    <ArrowUpRight size={12} className="rh-hit-arrow" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <nav className="rh-destinations" aria-label="Research destinations">
        {DESTINATIONS.map((dest) => {
          const Icon = dest.icon
          return (
            <Link key={dest.to} to={dest.to} className="rh-dest-link">
              <Icon size={14} />
              <span>{dest.label}</span>
            </Link>
          )
        })}
      </nav>
    </header>
  )
}
