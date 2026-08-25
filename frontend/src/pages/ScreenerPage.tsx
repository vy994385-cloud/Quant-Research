/**
 * RESEARCH SCREENER — vertical research workspace.
 *
 *   header → universe context → filter builder → results
 *
 * Filters are composed FIELD · operator · VALUE and applied as tinted chips.
 * Results render as research objects (symbol, company, sector, coverage,
 * matched-filter context) rather than database rows. Planned-but-unwired
 * filter areas live behind one collapsed disclosure — unsupported filters
 * never present interactive controls. All filtering is client-side over
 * discovery data via lib/screener.ts. No scores, no rankings.
 */

import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  ArrowUpDown,
  ChevronRight,
  Plus,
  Search,
  X,
} from "lucide-react"
import { fetchDiscovery } from "../api/client"
import type { DiscoveryItem } from "../api/types"
import { formatLabel } from "../lib/format"
import { FilterChip } from "../components/ResearchPrimitives"
import { SegmentedControl } from "../components/ui"
import {
  ACTIVE_FILTER_DEFINITIONS,
  PLANNED_FILTER_CATEGORIES,
  evaluateFilters,
  type ActiveFilter,
} from "../lib/screener"

type SortKey = "symbol" | "company" | "sector" | "research"
type SortDir = "asc" | "desc"

const SORT_LABELS: Record<SortKey, string> = {
  symbol: "Symbol",
  company: "Company",
  sector: "Sector",
  research: "Coverage",
}

export default function ScreenerPage() {
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [showPlanned, setShowPlanned] = useState(false)
  const [sortKey, setSortKey] = useState<SortKey>("symbol")
  const [sortDir, setSortDir] = useState<SortDir>("asc")
  const [builderField, setBuilderField] = useState("sector")
  const [builderSector, setBuilderSector] = useState("")
  const [builderAvailable, setBuilderAvailable] = useState<"true" | "false">("true")

  useEffect(() => {
    let cancelled = false
    fetchDiscovery()
      .then((res) => {
        if (!cancelled) {
          setItems(res.results)
          setLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Discovery unavailable")
          setLoading(false)
        }
      })
    return () => { cancelled = true }
  }, [])

  const sectors = useMemo(() => {
    const set = new Set<string>()
    for (const item of items) set.add(item.sector)
    return [...set].sort()
  }, [items])

  /** Rows after filter evaluation + free-text search. */
  const matched = useMemo(() => {
    let filtered = evaluateFilters(items, activeFilters)
    const q = searchQuery.trim().toLowerCase()
    if (q) {
      filtered = filtered.filter(
        (item) =>
          item.symbol.toLowerCase().includes(q) ||
          (item.companyName ?? "").toLowerCase().includes(q) ||
          item.sector.toLowerCase().includes(q),
      )
    }
    return filtered
  }, [items, activeFilters, searchQuery])

  const results = useMemo(() => {
    const dir = sortDir === "asc" ? 1 : -1
    return [...matched].sort((a, b) => {
      switch (sortKey) {
        case "company":
          return dir * (a.companyName ?? a.symbol).localeCompare(b.companyName ?? b.symbol)
        case "sector":
          return dir * a.sector.localeCompare(b.sector)
        case "research":
          return dir * (Number(b.researchAvailable) - Number(a.researchAvailable))
        default:
          return dir * a.symbol.localeCompare(b.symbol)
      }
    })
  }, [matched, sortKey, sortDir])

  function applyBuilder() {
    if (builderField === "sector") {
      if (!builderSector) return
      upsertFilter("sector", builderSector)
    } else {
      upsertFilter("industry_research_available", builderAvailable)
    }
  }

  function upsertFilter(filterId: string, value: string) {
    setActiveFilters((prev) => {
      const existing = prev.find((f) => f.filterId === filterId)
      if (existing) {
        return prev.map((f) => (f.filterId === filterId ? { ...f, value } : f))
      }
      return [...prev, { filterId, operator: "equals", value }]
    })
  }

  function removeFilter(filterId: string) {
    setActiveFilters((prev) => prev.filter((f) => f.filterId !== filterId))
  }

  function clearAllFilters() {
    setActiveFilters([])
    setSearchQuery("")
  }

  const hasConstraints = activeFilters.length > 0 || searchQuery.trim() !== ""

  return (
    <div className="page-screener">
      {/* ── Page header ─────────────────────────────────────────── */}
      <section className="page-hero">
        <p className="page-kicker">Screen</p>
        <h1>Research Screener</h1>
        <p className="page-subtitle">
          Search the tracked universe, compose evidence-backed filters, and inspect what
          matches. Every result states which conditions it satisfied. No scores, no rankings.
        </p>
      </section>

      {loading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading screener data</strong>
        </div>
      )}

      {error && (
        <div className="empty-state error" role="alert">
          <AlertTriangle size={28} />
          <strong>Screener unavailable</strong>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && (
        <>
          {/* ── Universe context ──────────────────────────────────── */}
          <div className="scr-context scr-section mt-5">
            <span className="scr-context-item">
              <strong>{items.length}</strong> tracked companies
            </span>
            <span className="scr-context-sep" />
            <span className="scr-context-item">
              <strong>{activeFilters.length}</strong>{" "}
              filter{activeFilters.length === 1 ? "" : "s"} active
            </span>
            <span className="scr-context-sep" />
            <span className="scr-context-item">
              evaluation on recorded universe data · client-side
            </span>
          </div>

          {/* ── Filter builder ────────────────────────────────────── */}
          <section className="scr-builder scr-section" aria-label="Filter builder">
            <div className="scr-builder-head">
              <strong className="scr-builder-title">Filters</strong>
              <span className={`scr-filter-count${activeFilters.length === 0 ? " zero" : ""}`}>
                {activeFilters.length}
              </span>
            </div>

            <div className="scr-search">
              <Search size={15} />
              <input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search by name, symbol, sector…"
                aria-label="Search companies"
              />
              {searchQuery && (
                <button
                  className="filter-chip-remove"
                  onClick={() => setSearchQuery("")}
                  aria-label="Clear search"
                >
                  <X size={13} />
                </button>
              )}
            </div>

            <div className="scr-builder-grid">
              <div>
                <label className="scr-field-label" htmlFor="scr-field">
                  Field
                </label>
                <select
                  id="scr-field"
                  className="scr-select"
                  value={builderField}
                  onChange={(event) => setBuilderField(event.target.value)}
                >
                  {ACTIVE_FILTER_DEFINITIONS.map((def) => (
                    <option key={def.id} value={def.id}>
                      {def.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <span className="scr-field-label">Operator</span>
                <span className="scr-operator">is</span>
              </div>

              <div>
                <label className="scr-field-label" htmlFor="scr-value">
                  Value
                </label>
                {builderField === "sector" ? (
                  <select
                    id="scr-value"
                    className="scr-select"
                    value={builderSector}
                    onChange={(event) => setBuilderSector(event.target.value)}
                  >
                    <option value="">Select sector…</option>
                    {sectors.map((sector) => (
                      <option key={sector} value={sector}>
                        {formatLabel(sector)}
                      </option>
                    ))}
                  </select>
                ) : (
                  <SegmentedControl
                    size="md"
                    ariaLabel="Research availability value"
                    options={[
                      { value: "true" as const, label: "Yes" },
                      { value: "false" as const, label: "No" },
                    ]}
                    value={builderAvailable}
                    onChange={(next) => setBuilderAvailable(next)}
                  />
                )}
              </div>

              <button
                className="scr-add-btn"
                onClick={applyBuilder}
                disabled={builderField === "sector" && !builderSector}
              >
                <Plus size={14} />
                Add filter
              </button>
            </div>

            {/* Active filters as chips */}
            <div className="scr-chips" role="list" aria-label="Active filters">
              {searchQuery.trim() !== "" && (
                <FilterChip
                  label="Search"
                  value={`“${searchQuery.trim()}”`}
                  onRemove={() => setSearchQuery("")}
                />
              )}
              {activeFilters.map((filter) => {
                const def = ACTIVE_FILTER_DEFINITIONS.find((d) => d.id === filter.filterId)
                if (!def) return null
                return (
                  <FilterChip
                    key={filter.filterId}
                    label={def.label}
                    value={
                      filter.value === "true"
                        ? "Yes"
                        : filter.value === "false"
                          ? "No"
                          : formatLabel(String(filter.value))
                    }
                    onRemove={() => removeFilter(filter.filterId)}
                  />
                )
              })}
            </div>

            {/* Compact placeholder disclosure */}
            <div className="scr-more">
              <button
                className="scr-more-toggle"
                onClick={() => setShowPlanned(!showPlanned)}
                aria-expanded={showPlanned}
              >
                <ChevronRight size={14} />
                View planned filter areas
              </button>
              {showPlanned && (
                <div className="scr-more-body">
                  <p className="scr-more-note">
                    More filters coming — additional evidence-backed filters will appear here as
                    their recorded data coverage is validated. Planned areas:{" "}
                    {PLANNED_FILTER_CATEGORIES.map((cat) => cat.category).join(" · ")}. Each will
                    be evaluated against recorded data with full provenance before it ships.
                  </p>
                </div>
              )}
            </div>
          </section>

          {/* ── Results ────────────────────────────────────────────── */}
          <section className="scr-section" aria-label="Screener results">
            <div className="scr-results-head">
              <span className="scr-results-label">Matching companies</span>
              <span className="scr-results-count">
                {results.length} <small>of {items.length}</small>
              </span>
              <div className="scr-results-tools">
                <ArrowUpDown size={13} className="icon-muted" />
                <select
                  className="scr-sort"
                  value={sortKey}
                  onChange={(event) => setSortKey(event.target.value as SortKey)}
                  aria-label="Sort results by"
                >
                  {(Object.keys(SORT_LABELS) as SortKey[]).map((key) => (
                    <option key={key} value={key}>
                      Sort: {SORT_LABELS[key]}
                    </option>
                  ))}
                </select>
                <button
                  className="scr-sort"
                  onClick={() => setSortDir((d) => (d === "asc" ? "desc" : "asc"))}
                  aria-label={`Sort direction ${sortDir === "asc" ? "ascending" : "descending"}`}
                >
                  {sortDir === "asc" ? "↑ Asc" : "↓ Desc"}
                </button>
                {hasConstraints && (
                  <button className="scr-clear" onClick={clearAllFilters}>
                    Clear all
                  </button>
                )}
              </div>
            </div>

            {results.length === 0 ? (
              <div className="empty-state">
                <Search size={24} />
                <strong>No matching companies</strong>
                <p>
                  {hasConstraints
                    ? "Loosen or clear the current filters to widen the match."
                    : "The tracked universe is empty right now."}
                </p>
                {hasConstraints && (
                  <button className="refresh-button retry-button" onClick={clearAllFilters}>
                    Clear all filters
                  </button>
                )}
              </div>
            ) : (
              <div className="scr-results-list">
                {results.map((result) => (
                  <article key={result.symbol} className="result-card">
                    <div className="result-card-id">
                      <Link
                        to={`/companies/${encodeURIComponent(result.symbol)}`}
                        className="result-symbol"
                      >
                        {result.symbol}
                      </Link>
                      <span className="result-company">{result.companyName ?? "\u2014"}</span>
                      <span className="result-sector">{formatLabel(result.sector)}</span>
                    </div>

                    <div className="result-card-main">
                      <span
                        className={`status-badge ${result.researchAvailable ? "green" : "slate"}`}
                      >
                        <span className="status-badge-dot" />
                        {result.researchAvailable ? "Research available" : "Directory only"}
                      </span>
                      <span className="result-context">
                        {result.matchedFilters.length > 0
                          ? `Matches: ${result.matchedFilters.join(" · ")}`
                          : hasConstraints
                            ? "Passes search only"
                            : "Full tracked universe"}
                      </span>
                    </div>

                    <div className="result-actions">
                      <Link
                        to={`/companies/${encodeURIComponent(result.symbol)}`}
                        className="result-open"
                      >
                        Open Research
                        <ArrowRight size={14} />
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
