/**
 * GLOBAL SEARCH — research discovery workspace.
 *
 * Second entrance into the same research platform as Research Home.
 * Searches companies by symbol, name, and sector; derives industry
 * groupings from the tracked universe. Results open directly into
 * the appropriate research workspace.
 */

import { useMemo, useState, useCallback, useRef, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Building2, ChevronRight, Globe, Search, X } from "lucide-react"
import { useDiscovery } from "../useDiscovery"
import { formatLabel } from "../lib/format"
import { trackRecentVisit } from "../lib/localResearch"
import { LoadingState, ErrorState } from "../components/States"

type ResultType = "company" | "sector"

interface SearchResult {
  type: ResultType
  title: string
  symbol: string
  context: string
  to: string
  sector: string
  researchAvailable: boolean
}

const EXAMPLES = [
  { label: "TCS", query: "TCS" },
  { label: "Infosys", query: "Infosys" },
  { label: "Banking", query: "Banking" },
  { label: "Pharma", query: "Pharma" },
  { label: "Reliance", query: "Reliance" },
]

function buildResults(
  items: Array<{
    symbol: string
    company_name: string | null
    sector: string
    research_available: boolean
  }>,
  query: string,
): { companies: SearchResult[]; sectors: SearchResult[] } {
  if (!query) return { companies: [], sectors: [] }
  const q = query.toLowerCase()

  const companies: SearchResult[] = []
  const sectorMatches = new Map<string, number>()

  for (const item of items) {
    const nameMatch =
      item.symbol.toLowerCase().includes(q) ||
      (item.company_name ?? "").toLowerCase().includes(q) ||
      item.sector.toLowerCase().includes(q)

    if (nameMatch) {
      companies.push({
        type: "company",
        title: item.company_name ?? item.symbol,
        symbol: item.symbol,
        context: item.research_available
          ? "Full research"
          : "Limited data",
        to: `/companies/${encodeURIComponent(item.symbol)}`,
        sector: item.sector,
        researchAvailable: item.research_available,
      })
    }

    if (item.sector.toLowerCase().includes(q)) {
      sectorMatches.set(
        item.sector,
        (sectorMatches.get(item.sector) ?? 0) + 1,
      )
    }
  }

  const sectors: SearchResult[] = []
  for (const [sector, count] of sectorMatches) {
    sectors.push({
      type: "sector",
      title: formatLabel(sector),
      symbol: "",
      context: `${count} tracked ${count === 1 ? "company" : "companies"}`,
      to: "/industries",
      sector,
      researchAvailable: true,
    })
  }

  return { companies, sectors }
}

export default function GlobalSearchPage() {
  const { items, loading, error } = useDiscovery()
  const navigate = useNavigate()
  const [query, setQuery] = useState("")
  const [activeFilter, setActiveFilter] = useState<ResultType | "all">("all")
  const inputRef = useRef<HTMLInputElement | null>(null)
  const q = query.trim()

  const { companies, sectors } = useMemo(
    () => buildResults(items, q),
    [items, q],
  )

  const filteredCompanies =
    activeFilter === "all" || activeFilter === "company" ? companies : []
  const filteredSectors =
    activeFilter === "all" || activeFilter === "sector" ? sectors : []

  const totalResults = filteredCompanies.length + filteredSectors.length
  const hasQuery = q.length > 0

  const handleSelect = useCallback(
    (result: SearchResult) => {
      if (result.type === "company" && result.symbol) {
        trackRecentVisit(result.symbol)
      }
      navigate(result.to)
    },
    [navigate],
  )

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  return (
    <div className="page-global-search">
      {/* ── Header ──────────────────────────────────────────── */}
      <header className="gs-header">
        <p className="page-kicker">Global search</p>
        <h1>Search the research universe</h1>
        <p className="gs-scope">
          Companies by name, ticker, or sector — results open directly into the
          research workspace.
        </p>
      </header>

      {/* ── Search Input ────────────────────────────────────── */}
      <div className="gs-input-area">
        <div className="gs-input-wrap">
          <Search size={17} className="gs-input-icon" aria-hidden />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setActiveFilter("all")
            }}
            placeholder="Company, ticker, or sector…"
            aria-label="Search companies, sectors, and industries"
            autoComplete="off"
            className="gs-input"
          />
          {hasQuery && (
            <button
              type="button"
              className="gs-clear"
              onClick={() => {
                setQuery("")
                setActiveFilter("all")
                inputRef.current?.focus()
              }}
              aria-label="Clear search"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {!hasQuery && (
          <div className="gs-examples">
            <span className="gs-examples-label">Try:</span>
            {EXAMPLES.map((ex) => (
              <button
                key={ex.label}
                type="button"
                className="gs-example"
                onClick={() => {
                  setQuery(ex.query)
                  inputRef.current?.focus()
                }}
              >
                {ex.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── Loading / Error ─────────────────────────────────── */}
      {loading && <LoadingState label="Loading research universe…" />}
      {error && <ErrorState error={error} />}

      {/* ── Results ─────────────────────────────────────────── */}
      {!loading && !error && hasQuery && (
        <div className="gs-results">
          <div className="gs-results-bar">
            <div className="gs-scope-pills" role="radiogroup" aria-label="Filter by type">
              {(
                [
                  { value: "all", label: "All" },
                  { value: "company", label: "Companies" },
                  { value: "sector", label: "Sectors" },
                ] as const
              ).map((opt) => {
                const count =
                  opt.value === "all"
                    ? companies.length + sectors.length
                    : opt.value === "company"
                      ? companies.length
                      : sectors.length
                return (
                  <button
                    key={opt.value}
                    type="button"
                    role="radio"
                    aria-checked={activeFilter === opt.value}
                    className={`gs-pill ${activeFilter === opt.value ? "gs-pill--active" : ""}`}
                    onClick={() => setActiveFilter(opt.value)}
                  >
                    {opt.label}
                    {count > 0 && (
                      <span className="gs-pill-count">{count}</span>
                    )}
                  </button>
                )
              })}
            </div>
          </div>

          {totalResults === 0 ? (
            <div className="gs-no-results">
              <p className="gs-no-results-title">
                No results for &ldquo;{q}&rdquo;
              </p>
              <p className="gs-no-results-desc">
                Try a different name, ticker, or sector. The tracked universe
                includes {items.length} companies.
              </p>
              <div className="gs-no-results-actions">
                <button
                  type="button"
                  className="gs-action-link"
                  onClick={() => {
                    setQuery("")
                    setActiveFilter("all")
                    inputRef.current?.focus()
                  }}
                >
                  Clear search
                </button>
                <span className="gs-no-results-sep">·</span>
                {EXAMPLES.slice(0, 3).map((ex) => (
                  <button
                    key={ex.label}
                    type="button"
                    className="gs-action-link"
                    onClick={() => {
                      setQuery(ex.query)
                      setActiveFilter("all")
                    }}
                  >
                    {ex.label}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="gs-result-groups">
              {filteredCompanies.length > 0 && (
                <section className="gs-group" aria-label="Company results">
                  <h2 className="gs-group-heading">
                    Companies
                    <span className="gs-group-count">
                      {filteredCompanies.length}
                    </span>
                  </h2>
                  <ul className="gs-group-list" role="listbox">
                    {filteredCompanies.map((r) => (
                      <li key={r.to}>
                        <SearchRow result={r} onSelect={handleSelect} />
                      </li>
                    ))}
                  </ul>
                </section>
              )}

              {filteredSectors.length > 0 && (
                <section className="gs-group" aria-label="Sector results">
                  <h2 className="gs-group-heading">
                    Sectors &amp; Industries
                    <span className="gs-group-count">
                      {filteredSectors.length}
                    </span>
                  </h2>
                  <ul className="gs-group-list" role="listbox">
                    {filteredSectors.map((r) => (
                      <li key={r.to}>
                        <SearchRow result={r} onSelect={handleSelect} />
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Empty State (no query) ──────────────────────────── */}
      {!loading && !error && !hasQuery && (
        <div className="gs-welcome">
          <p className="gs-welcome-hint">
            Search across {items.length} tracked companies to open their full
            research workspace — evidence, financials, coverage, and
            provenance.
          </p>
        </div>
      )}
    </div>
  )
}

/* ── Search Row ──────────────────────────────────────────────── */

function SearchRow({
  result,
  onSelect,
}: {
  result: SearchResult
  onSelect: (r: SearchResult) => void
}) {
  const Icon = result.type === "company" ? Building2 : Globe

  return (
    <a
      href={result.to}
      className={`gs-row gs-row--${result.type}`}
      onClick={(e) => {
        e.preventDefault()
        onSelect(result)
      }}
      role="option"
    >
      <span className={`gs-row-icon gs-row-icon--${result.type}`}>
        <Icon size={15} />
      </span>
      <div className="gs-row-body">
        <div className="gs-row-title-line">
          <span className="gs-row-title">{result.title}</span>
          {result.symbol && (
            <span className="gs-row-symbol">{result.symbol}</span>
          )}
        </div>
        <div className="gs-row-meta">
          <span>{result.context}</span>
          <span className="gs-row-dot">·</span>
          <span>{formatLabel(result.sector)}</span>
        </div>
      </div>
      <ChevronRight size={15} className="gs-row-arrow" />
    </a>
  )
}
