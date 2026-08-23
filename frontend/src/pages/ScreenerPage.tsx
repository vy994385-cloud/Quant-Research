/**
 * Research Screener page: filter companies by observable conditions.
 *
 * Active filters (client-side, backed by discovery data):
 * - Sector: filter by industry sector
 * - Research Available: show only companies with research data
 *
 * Planned filters (require backend screener API):
 * Fundamentals, Growth, Financial Quality, Valuation, Technology,
 * R&D/Innovation, Competitive, Technical/Market — listed for
 * transparency but not interactive until the backend API exists.
 *
 * No scores, no rankings, no recommendations.
 */

import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Activity,
  Filter,
  Search,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  Beaker,
} from "lucide-react"
import { fetchDiscovery } from "../api/client"
import type { DiscoveryItem } from "../api/types"
import { formatLabel } from "../lib/format"
import { Tag } from "../components/ui"
import { FilterChip } from "../components/ResearchPrimitives"
import {
  ACTIVE_FILTER_DEFINITIONS,
  PLANNED_FILTER_CATEGORIES,
  evaluateFilters,
  type ActiveFilter,
} from "../lib/screener"

export default function ScreenerPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [showPlanned, setShowPlanned] = useState(false)

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
    for (const item of items) {
      set.add(item.sector)
    }
    return [...set].sort()
  }, [items])

  const results = useMemo(() => {
    let filtered = evaluateFilters(items, activeFilters)

    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      filtered = filtered.filter(
        (r) =>
          r.symbol.toLowerCase().includes(q) ||
          (r.companyName ?? "").toLowerCase().includes(q) ||
          r.sector.toLowerCase().includes(q),
      )
    }

    return filtered
  }, [items, activeFilters, searchQuery])

  function addFilter(filterId: string, value: string | string[]) {
    setActiveFilters((prev) => {
      const existing = prev.find((f) => f.filterId === filterId)
      if (existing) {
        return prev.map((f) => (f.filterId === filterId ? { ...f, value } : f))
      }
      const def = ACTIVE_FILTER_DEFINITIONS.find((f) => f.id === filterId)
      if (!def) return prev
      return [...prev, { filterId, operator: def.operator, value }]
    })
  }

  function removeFilter(filterId: string) {
    setActiveFilters((prev) => prev.filter((f) => f.filterId !== filterId))
  }

  function clearAllFilters() {
    setActiveFilters([])
    setSearchQuery("")
  }

  return (
    <div className="page-screener">
      <section className="page-hero">
        <h1>Research Screener</h1>
        <p className="page-subtitle">
          Filter companies by observable conditions. Every match explains what
          data was used. No scores, no rankings, no recommendations.
        </p>
      </section>

      {loading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading screener data</strong>
          <span>Fetching supported companies...</span>
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
        <div className="screener-layout">
          <div className="screener-filters">
            <div className="screener-filters-head">
              <Filter size={14} />
              <strong>Filters</strong>
              {activeFilters.length > 0 && (
                <button className="screener-clear" onClick={clearAllFilters}>
                  Clear all ({activeFilters.length})
                </button>
              )}
            </div>

            <div className="screener-search">
              <Search size={14} />
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by name or symbol..."
                aria-label="Search companies"
              />
            </div>

            {activeFilters.length > 0 && (
              <div className="screener-active-filters">
                {activeFilters.map((f) => {
                  const def = ACTIVE_FILTER_DEFINITIONS.find((d) => d.id === f.filterId)
                  if (!def) return null
                  return (
                    <FilterChip
                      key={f.filterId}
                      label={def.label}
                      value={f.value === "true" ? "Yes" : f.value === "false" ? "No" : String(f.value)}
                      onRemove={() => removeFilter(f.filterId)}
                    />
                  )
                })}
              </div>
            )}

            <ScreenerFilterSection
              label="Sector"
              activeFilters={activeFilters}
              onAddFilter={addFilter}
              onRemoveFilter={removeFilter}
              sectors={sectors}
            />

            <ScreenerFilterSection
              label="Research Available"
              activeFilters={activeFilters}
              onAddFilter={addFilter}
              onRemoveFilter={removeFilter}
            />

            <button
              className="screener-planned-toggle"
              onClick={() => setShowPlanned(!showPlanned)}
              aria-expanded={showPlanned}
            >
              {showPlanned ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <Beaker size={14} />
              <span>More filters</span>
              <span className="screener-planned-count">
                {PLANNED_FILTER_CATEGORIES.reduce((n, c) => n + c.filters.length, 0)} planned across {PLANNED_FILTER_CATEGORIES.length} categories
              </span>
            </button>

            {showPlanned && (
              <div className="screener-planned-list">
                {PLANNED_FILTER_CATEGORIES.map((cat) => (
                  <div key={cat.category} className="screener-planned-category">
                    <strong>{cat.category}</strong>
                    <span>{cat.description}</span>
                    <div className="screener-planned-filters">
                      {cat.filters.map((f) => (
                        <Tag key={f} text={formatLabel(f)} tone="slate" />
                      ))}
                    </div>
                  </div>
                ))}
                <p className="screener-planned-note">
                  These filters are not wired up yet — the screener currently runs on
                  sector and research availability. Each additional filter will be
                  evaluated against recorded financial, technology, and competitive
                  data with full provenance before it ships.
                </p>
              </div>
            )}
          </div>

          <div className="screener-results">
            <div className="screener-results-head">
              <strong>{results.length} companies</strong>
              <span>
                {activeFilters.length > 0
                  ? `matching ${activeFilters.length} filter${activeFilters.length !== 1 ? "s" : ""}`
                  : "— showing the full tracked universe; apply a filter to narrow it"}
              </span>
            </div>

            {results.length === 0 ? (
              <div className="empty-state">
                <Search size={24} />
                <strong>No matching companies</strong>
                <p>Try adjusting your filters.</p>
              </div>
            ) : (
              <div className="screener-results-table">
                <div className="screener-results-head-row">
                  <span className="col-symbol">Symbol</span>
                  <span className="col-name">Company</span>
                  <span className="col-sector">Sector</span>
                </div>
                {results.map((result) => (
                  <button
                    key={result.symbol}
                    className="screener-result-row"
                    onClick={() => navigate(`/companies/${result.symbol}`)}
                  >
                    <span className="col-symbol mono">{result.symbol}</span>
                    <span className="col-name">{result.companyName ?? result.symbol}</span>
                    <span className="col-sector">
                      <Tag text={formatLabel(result.sector)} tone="slate" />
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Filter sections ──────────────────────────────────────────────── */

function ScreenerFilterSection({
  label,
  activeFilters,
  onAddFilter,
  onRemoveFilter,
  sectors,
}: {
  label: string
  activeFilters: ActiveFilter[]
  onAddFilter: (id: string, value: string | string[]) => void
  onRemoveFilter: (id: string) => void
  sectors?: string[]
}) {
  const filterDef = ACTIVE_FILTER_DEFINITIONS.find((f) => f.label === label)
  if (!filterDef) return null
  const active = activeFilters.find((f) => f.filterId === filterDef.id)

  if (filterDef.id === "sector" && sectors) {
    return (
      <div className="filter-row">
        <span className="filter-row-label">{label}</span>
        <select
          className="filter-select"
          value={active ? String(active.value) : ""}
          onChange={(e) => {
            if (e.target.value) {
              onAddFilter(filterDef.id, e.target.value)
            } else {
              onRemoveFilter(filterDef.id)
            }
          }}
        >
          <option value="">All sectors</option>
          {sectors.map((s) => (
            <option key={s} value={s}>{formatLabel(s)}</option>
          ))}
        </select>
      </div>
    )
  }

  if (filterDef.id === "industry_research_available") {
    return (
      <div className="filter-row">
        <span className="filter-row-label">{label}</span>
        <div className="filter-toggle-group">
          <button
            className={`filter-toggle ${active?.value === "true" ? "active" : ""}`}
            onClick={() => onAddFilter(filterDef.id, "true")}
            aria-pressed={active?.value === "true"}
          >
            Yes
          </button>
          <button
            className={`filter-toggle ${active?.value === "false" ? "active" : ""}`}
            onClick={() => onAddFilter(filterDef.id, "false")}
            aria-pressed={active?.value === "false"}
          >
            No
          </button>
          {active && (
            <button className="filter-toggle-clear" onClick={() => onRemoveFilter(filterDef.id)}>
              Clear
            </button>
          )}
        </div>
      </div>
    )
  }

  return null
}
