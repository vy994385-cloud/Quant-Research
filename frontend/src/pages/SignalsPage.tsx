/**
 * Signals page: observed research developments by category.
 * Fetches actual signal data per company from CompanyResearch.
 * Each signal: WHAT HAPPENED, WHEN, EVIDENCE, WHY IT MAY MATTER.
 * Never a trading recommendation.
 */

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  Activity,
  FileSearch,
  Signal,
  Building2,
  Search,
} from "lucide-react"
import { fetchDiscovery, fetchResearch } from "../api/client"
import { ApiError } from "../api/client"
import type { CompanyResearch, ContractSignal, DiscoveryItem } from "../api/types"
import { formatConfidence, formatEvidenceObservation, formatLabel } from "../lib/format"
import { categoryTone, directionTone } from "../lib/signal"
import { Tag } from "../components/ui"

/* ── Signal Card ─────────────────────────────────────────────────────── */

function SignalCard({ signal }: { signal: ContractSignal }) {
  return (
    <article className="signal-card">
      <div className="signal-card-head">
        <strong>{signal.title}</strong>
        <span className="signal-card-tags">
          <Tag text={formatLabel(signal.category)} tone={categoryTone(signal.category)} />
          <Tag text={formatLabel(signal.direction)} tone={directionTone(signal.direction)} />
          {signal.severity && (
            <Tag text={`Severity: ${formatLabel(signal.severity)}`} tone="slate" />
          )}
        </span>
      </div>
      <p className="signal-card-explanation">{signal.explanation}</p>
      <div className="signal-card-backing">
        {signal.supporting_features.length > 0 && (
          <span className="signal-backing-item">
            <Tag text={`${signal.supporting_features.length} features`} tone="slate" />
            {signal.supporting_features.map(formatLabel).join(", ")}
          </span>
        )}
        {signal.supporting_metrics.length > 0 && (
          <span className="signal-backing-item">
            <Tag text={`${signal.supporting_metrics.length} metrics`} tone="slate" />
            {signal.supporting_metrics.map(formatLabel).join(", ")}
          </span>
        )}
        {signal.supporting_features.length === 0 && signal.supporting_metrics.length === 0 && (
          <span className="signal-backing-none">No data backing specified</span>
        )}
      </div>
      <div className="signal-card-meta">
        <span>Observed {formatEvidenceObservation(signal.observation_at)}</span>
        {signal.confidence && <span>Confidence: {formatConfidence(signal.confidence)}</span>}
      </div>
    </article>
  )
}

/* ── Main Component ──────────────────────────────────────────────────── */

export default function SignalsPage() {
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)
  const [research, setResearch] = useState<CompanyResearch | null>(null)
  const [researchLoading, setResearchLoading] = useState(false)
  const [researchError, setResearchError] = useState<string | null>(null)
  const [activeCategory, setActiveCategory] = useState("all")
  const [activeDirection, setActiveDirection] = useState("all")

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

  const loadResearch = useCallback(async (sym: string) => {
    setSelectedSymbol(sym)
    setResearch(null)
    setResearchLoading(true)
    setResearchError(null)
    setActiveCategory("all")
    setActiveDirection("all")
    try {
      const result = await fetchResearch(sym)
      setResearch(result)
    } catch (err) {
      setResearchError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error ? err.message : "Failed to load research",
      )
    } finally {
      setResearchLoading(false)
    }
  }, [])

  const signals = useMemo(() => research?.signals ?? [], [research])

  const categories = useMemo(() => {
    const set = new Set<string>()
    for (const s of signals) set.add(s.category)
    return [...set].sort()
  }, [signals])

  const directions = useMemo(() => {
    const set = new Set<string>()
    for (const s of signals) set.add(s.direction)
    return [...set].sort()
  }, [signals])

  const filtered = useMemo(() => {
    return signals.filter((s) => {
      if (activeCategory !== "all" && s.category !== activeCategory) return false
      if (activeDirection !== "all" && s.direction !== activeDirection) return false
      return true
    })
  }, [signals, activeCategory, activeDirection])

  const byCategory = useMemo(() => {
    const map = new Map<string, ContractSignal[]>()
    for (const signal of filtered) {
      const bucket = map.get(signal.category) ?? []
      bucket.push(signal)
      map.set(signal.category, bucket)
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b))
  }, [filtered])

  const totalSignals = signals.length
  const matchedSignals = filtered.length

  return (
    <div className="page-signals">
      <section className="page-hero">
        <h1>Signals</h1>
        <p className="page-subtitle">
          Observed research developments. Each signal documents what happened, when,
          the evidence backing, and related data points. Not a trading recommendation.
        </p>
      </section>

      {loading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading signals</strong>
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
        <div className="signals-layout">
          {/* LEFT: Company selector */}
          <div className="signals-sidebar">
            <div className="panel">
              <div className="panel-head">
                <h3>Select Company</h3>
                <span>{researchable.length} companies</span>
              </div>
              <div className="signals-search">
                <Search size={14} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Filter companies..."
                  aria-label="Filter companies"
                />
              </div>
              <div className="signals-company-list">
                {filteredCompanies.map((item) => (
                  <button
                    key={item.symbol}
                    className={`signals-company-item ${selectedSymbol === item.symbol ? "active" : ""}`}
                    onClick={() => void loadResearch(item.symbol)}
                  >
                    <Building2 size={13} />
                    <div>
                      <strong>{item.symbol}</strong>
                      <small>{item.company_name ?? item.symbol}</small>
                    </div>
                  </button>
                ))}
                {filteredCompanies.length === 0 && (
                  <div className="signals-empty-list">
                    <Search size={14} />
                    <span>No matching companies</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* RIGHT: Signals content */}
          <div className="signals-content">
            {!selectedSymbol && (
              <div className="empty-state">
                <Signal size={28} />
                <strong>Select a company</strong>
                <p>Choose a company from the list to view its observed research developments.</p>
              </div>
            )}

            {selectedSymbol && researchLoading && (
              <div className="loading-state" role="status">
                <Activity className="spin" size={26} />
                <strong>Loading research</strong>
                <span>Fetching signal data for {selectedSymbol}...</span>
              </div>
            )}

            {selectedSymbol && researchError && (
              <div className="empty-state error" role="alert">
                <FileSearch size={28} />
                <strong>Could not load research</strong>
                <p>{researchError}</p>
              </div>
            )}

            {selectedSymbol && research && !researchLoading && (
              <>
                {/* Summary stats */}
                <div className="signals-summary">
                  <div className="signals-stat">
                    <strong>{totalSignals}</strong>
                    <span>total signals</span>
                  </div>
                  <div className="signals-stat">
                    <strong>{categories.length}</strong>
                    <span>categories</span>
                  </div>
                  <div className="signals-stat">
                    <strong>{directions.length}</strong>
                    <span>directions</span>
                  </div>
                  {matchedSignals < totalSignals && (
                    <div className="signals-stat signals-stat-filtered">
                      <strong>{matchedSignals}</strong>
                      <span>matching filters</span>
                    </div>
                  )}
                </div>

                {/* Filters */}
                {categories.length > 0 && (
                  <div className="signals-filters">
                    <div className="signals-filter-group">
                      <span className="signals-filter-label">Category:</span>
                      <button
                        className={`signals-filter-btn ${activeCategory === "all" ? "active" : ""}`}
                        onClick={() => setActiveCategory("all")}
                      >
                        All
                      </button>
                      {categories.map((cat) => (
                        <button
                          key={cat}
                          className={`signals-filter-btn ${activeCategory === cat ? "active" : ""}`}
                          onClick={() => setActiveCategory(cat)}
                        >
                          {formatLabel(cat)}
                        </button>
                      ))}
                    </div>
                    {directions.length > 0 && (
                      <div className="signals-filter-group">
                        <span className="signals-filter-label">Direction:</span>
                        <button
                          className={`signals-filter-btn ${activeDirection === "all" ? "active" : ""}`}
                          onClick={() => setActiveDirection("all")}
                        >
                          All
                        </button>
                        {directions.map((dir) => (
                          <button
                            key={dir}
                            className={`signals-filter-btn ${activeDirection === dir ? "active" : ""}`}
                            onClick={() => setActiveDirection(dir)}
                          >
                            {formatLabel(dir)}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Signals list */}
                {signals.length === 0 ? (
                  <div className="empty-state">
                    <Signal size={28} />
                    <strong>No signals</strong>
                    <p>No research observations were produced for {selectedSymbol}.</p>
                  </div>
                ) : filtered.length === 0 ? (
                  <div className="empty-state">
                    <Search size={24} />
                    <strong>No matching signals</strong>
                    <p>Try adjusting the category or direction filters.</p>
                  </div>
                ) : (
                  <div className="signals-groups">
                    {byCategory.map(([category, items]) => (
                      <div className="signals-group" key={category}>
                        <div className="signals-group-head">
                          <Tag text={formatLabel(category)} tone={categoryTone(category)} />
                          <span>{items.length} signal{items.length === 1 ? "" : "s"}</span>
                        </div>
                        <div className="signals-list">
                          {items.map((signal) => (
                            <SignalCard key={signal.signal_id} signal={signal} />
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Nota bene */}
                <div className="signals-nb">
                  <Signal size={13} />
                  <span>
                    Signals document observed developments with evidence backing.
                    Each category shows WHAT HAPPENED, WHEN, and the DATA BACKING.
                    This is not an investment recommendation.
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
