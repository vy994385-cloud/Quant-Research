/**
 * Cross-Domain Research page: fundamental vs. market, growth vs. margin,
 * earnings vs. cash flow, debt vs. cash generation divergences.
 *
 * Fetches cross-domain observations per company via fetchCrossDomain.
 * Each observation exposes domain-1/domain-2 context, relationship,
 * direction, severity, explanation, supporting_data, limitations,
 * as_of, and source provenance.
 *
 * No scores, no rankings, no recommendations, no trade signals.
 */

import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Activity,
  Building2,
  ChevronDown,
  ChevronRight,
  Database,
  FileSearch,
  GitBranch,
  Search,
  Shield,
  Tag,
  Zap,
} from "lucide-react"
import { ApiError, fetchCrossDomain, fetchDiscovery } from "../api/client"
import type { CrossDomainObservation, DiscoveryItem } from "../api/types"
import { formatConfidence, formatIso, formatLabel, formatSourceName } from "../lib/format"
import { Tag as UiTag } from "../components/ui"
import type { Tone } from "../lib/signal"

/* ── Helpers ──────────────────────────────────────────────────────────── */

function directionTone(direction: string): Tone {
  switch (direction?.toUpperCase()) {
    case "POSITIVE":
      return "green"
    case "NEGATIVE":
      return "red"
    case "MIXED":
      return "amber"
    case "NEUTRAL":
    default:
      return "slate"
  }
}

function severityTone(severity: string): Tone {
  switch (severity?.toUpperCase()) {
    case "HIGH":
      return "red"
    case "MEDIUM":
      return "amber"
    case "LOW":
    default:
      return "slate"
  }
}

function directionIcon(direction: string) {
  switch (direction?.toUpperCase()) {
    case "POSITIVE":
      return "\u2191"
    case "NEGATIVE":
      return "\u2193"
    case "MIXED":
      return "\u21C5"
    default:
      return "\u2014"
  }
}

function domainLabel(name: string): string {
  const n = name.toUpperCase()
  if (n.includes("FUNDAMENTAL")) return "Fundamentals"
  if (n.includes("MARKET")) return "Market"
  if (n.includes("GROWTH")) return "Growth"
  if (n.includes("MARGIN")) return "Margins"
  if (n.includes("EARNINGS")) return "Earnings"
  if (n.includes("CFO") || n.includes("CASH")) return "Cash Flow"
  if (n.includes("DEBT")) return "Debt"
  return formatLabel(name)
}

function relationshipLabel(rel: string): string {
  const r = rel.toUpperCase()
  if (r.includes("DIVERGENC")) return "Divergence"
  if (r.includes("CONVERGENC")) return "Convergence"
  if (r.includes("MISMATCH")) return "Mismatch"
  if (r.includes("CORRELAT")) return "Correlation"
  return formatLabel(rel)
}

/* ── Interface ────────────────────────────────────────────────────────── */

interface CompanyCrossDomainData {
  symbol: string
  company_name: string | null
  cross_domain: {
    symbol: string
    as_of: string
    observation_count: number
    observations: CrossDomainObservation[]
    positive_count: number
    negative_count: number
    mixed_count: number
    neutral_count: number
    notes: string[]
  } | null
  loading: boolean
  error: string | null
}

/* ── Summary Stats ────────────────────────────────────────────────────── */

function CrossDomainSummaryStats({
  observations,
  companyCount,
}: {
  observations: (CrossDomainObservation & { symbol: string })[]
  companyCount: number
}) {
  const total = observations.length
  const positive = observations.filter((o) => o.direction.toUpperCase() === "POSITIVE").length
  const negative = observations.filter((o) => o.direction.toUpperCase() === "NEGATIVE").length
  const mixed = observations.filter((o) => o.direction.toUpperCase() === "MIXED").length
  const high = observations.filter((o) => o.severity.toUpperCase() === "HIGH").length
  const domains = new Set(
    observations.flatMap((o) => [o.domain_1_name, o.domain_2_name]),
  ).size

  return (
    <div className="ei-summary">
      <div className="ei-stat">
        <strong>{total}</strong>
        <span>observations</span>
      </div>
      <div className="ei-stat">
        <strong>{companyCount}</strong>
        <span>companies</span>
      </div>
      <div className="ei-stat">
        <strong>{domains}</strong>
        <span>domains</span>
      </div>
      {positive > 0 && (
        <div className="ei-stat ei-stat-pos">
          <strong>{positive}</strong>
          <span>positive</span>
        </div>
      )}
      {negative > 0 && (
        <div className="ei-stat ei-stat-neg">
          <strong>{negative}</strong>
          <span>negative</span>
        </div>
      )}
      {mixed > 0 && (
        <div className="ei-stat ei-stat-warn">
          <strong>{mixed}</strong>
          <span>mixed</span>
        </div>
      )}
      {high > 0 && (
        <div className="ei-stat ei-stat-neg">
          <strong>{high}</strong>
          <span>high severity</span>
        </div>
      )}
    </div>
  )
}

/* ── Observation Card ─────────────────────────────────────────────────── */

function ObservationRow({
  obs,
  expanded,
  onToggle,
  navigate,
}: {
  obs: CrossDomainObservation & { symbol: string }
  expanded: boolean
  onToggle: () => void
  navigate: ReturnType<typeof useNavigate>
}) {
  const dirTone = directionTone(obs.direction)
  const sevTone = severityTone(obs.severity)
  const supportingEntries = Object.entries(obs.supporting_data)
  const limitationList = Array.isArray(obs.limitations) ? obs.limitations : []
  const relatedMetrics = Array.isArray(obs.related_metrics) ? obs.related_metrics : []
  const calcInputs = obs.calculation_inputs ? Object.entries(obs.calculation_inputs) : []

  return (
    <div className={`cd-obs-row ${expanded ? "expanded" : ""}`}>
      <button
        className="cd-obs-toggle"
        onClick={onToggle}
        aria-label={expanded ? "Collapse" : "Expand"}
      >
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>

      <div className="cd-obs-body">
        {/* Header row */}
        <div className="cd-obs-header">
          <button
            className="cd-obs-symbol"
            onClick={(e) => {
              e.stopPropagation()
              navigate(`/companies/${obs.symbol}`)
            }}
          >
            {obs.symbol}
          </button>
          <span className={`cd-obs-direction cd-obs-direction-${dirTone}`}>
            {directionIcon(obs.direction)} {formatLabel(obs.direction)}
          </span>
          <UiTag text={formatLabel(obs.severity)} tone={sevTone} />
          <UiTag text={formatLabel(obs.semantic_category)} tone="slate" />
          <span className="cd-obs-rel">{relationshipLabel(obs.relationship)}</span>
        </div>

        {/* Label + description */}
        <strong className="cd-obs-label">{obs.label}</strong>
        <p className="cd-obs-desc">{obs.description}</p>

        {/* Domain pair */}
        <div className="cd-obs-domains">
          <div className="cd-obs-domain cd-obs-domain-1">
            <span className="cd-obs-domain-label">{domainLabel(obs.domain_1_name)}</span>
            <span className="cd-obs-domain-metric">{obs.domain_1_metric}</span>
            {obs.domain_1_value !== null && (
              <span className="cd-obs-domain-value mono">{obs.domain_1_value}</span>
            )}
            {obs.domain_1_direction && obs.domain_1_direction !== "UNKNOWN" && (
              <span className={`cd-obs-domain-dir ${directionTone(obs.domain_1_direction)}`}>
                {directionIcon(obs.domain_1_direction)} {formatLabel(obs.domain_1_direction)}
              </span>
            )}
          </div>
          <div className="cd-obs-domain-arrow">
            <Zap size={14} />
          </div>
          <div className="cd-obs-domain cd-obs-domain-2">
            <span className="cd-obs-domain-label">{domainLabel(obs.domain_2_name)}</span>
            <span className="cd-obs-domain-metric">{obs.domain_2_metric}</span>
            {obs.domain_2_value !== null && (
              <span className="cd-obs-domain-value mono">{obs.domain_2_value}</span>
            )}
            {obs.domain_2_direction && obs.domain_2_direction !== "UNKNOWN" && (
              <span className={`cd-obs-domain-dir ${directionTone(obs.domain_2_direction)}`}>
                {directionIcon(obs.domain_2_direction)} {formatLabel(obs.domain_2_direction)}
              </span>
            )}
          </div>
        </div>

        {/* Expanded detail */}
        {expanded && (
          <div className="cd-obs-detail">
            {obs.methodology && (
              <div className="cd-detail-section">
                <span className="cd-detail-label">Methodology</span>
                <p className="cd-detail-text">{obs.methodology}</p>
              </div>
            )}

            {obs.confidence && (
              <div className="cd-detail-section">
                <span className="cd-detail-label">Confidence</span>
                <span className="cd-detail-value">{formatConfidence(obs.confidence)}</span>
              </div>
            )}

            {calcInputs.length > 0 && (
              <div className="cd-detail-section">
                <span className="cd-detail-label">Calculation Inputs</span>
                <div className="cd-detail-kv">
                  {calcInputs.map(([k, v]) => (
                    <div key={k} className="cd-detail-kv-row">
                      <span className="cd-detail-kv-key">{formatLabel(k)}</span>
                      <span className="cd-detail-kv-value mono">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {supportingEntries.length > 0 && (
              <div className="cd-detail-section">
                <span className="cd-detail-label">Supporting Data</span>
                <div className="cd-detail-kv">
                  {supportingEntries.map(([k, v]) => (
                    <div key={k} className="cd-detail-kv-row">
                      <span className="cd-detail-kv-key">{formatLabel(k)}</span>
                      <span className="cd-detail-kv-value mono">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {relatedMetrics.length > 0 && (
              <div className="cd-detail-section">
                <span className="cd-detail-label">Related Metrics</span>
                <div className="cd-detail-tags">
                  {relatedMetrics.map((m) => (
                    <UiTag key={m} text={formatLabel(m)} tone="slate" />
                  ))}
                </div>
              </div>
            )}

            {limitationList.length > 0 && (
              <div className="cd-detail-section cd-detail-limitations">
                <span className="cd-detail-label">Limitations</span>
                <ul className="cd-detail-list">
                  {limitationList.map((l, i) => (
                    <li key={i}>{l}</li>
                  ))}
                </ul>
              </div>
            )}

            {obs.source_name && (
              <div className="cd-detail-source">
                <FileSearch size={12} />
                <span className="cd-detail-source-name">{formatSourceName(obs.source_name)}</span>
              </div>
            )}

            <div className="cd-detail-provenance">
              <span className="cd-detail-as-of">
                <Shield size={11} />
                As of {obs.as_of ? formatIso(obs.as_of) : "\u2014"}
              </span>
            </div>
          </div>
        )}

        {/* Collapsed supporting-data hint */}
        {!expanded && supportingEntries.length > 0 && (
          <span className="cd-obs-hint">
            <Database size={11} />
            {supportingEntries.length} supporting data points
          </span>
        )}
      </div>
    </div>
  )
}

/* ── Main Component ──────────────────────────────────────────────────── */

export default function CrossDomainPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [companies, setCompanies] = useState<Map<string, CompanyCrossDomainData>>(new Map())
  const [directionFilter, setDirectionFilter] = useState<string | null>(null)
  const [severityFilter, setSeverityFilter] = useState<string | null>(null)
  const [relationshipFilter, setRelationshipFilter] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [expandedObs, setExpandedObs] = useState<Set<string>>(new Set())

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

  const researchable = useMemo(() => items.filter((i) => i.research_available), [items])

  const fetchCompanyCrossDomain = useCallback(async (sym: string) => {
    setCompanies((prev) => {
      const next = new Map(prev)
      next.set(sym, { symbol: sym, company_name: null, cross_domain: null, loading: true, error: null })
      return next
    })

    try {
      const result = await fetchCrossDomain(sym)
      setCompanies((prev) => {
        const next = new Map(prev)
        next.set(sym, {
          symbol: sym,
          company_name: items.find((i) => i.symbol === sym)?.company_name ?? null,
          cross_domain: result.cross_domain,
          loading: false,
          error: null,
        })
        return next
      })
    } catch (err) {
      const message = err instanceof ApiError
        ? err.message
        : err instanceof Error ? err.message : "Failed to load cross-domain data"
      setCompanies((prev) => {
        const next = new Map(prev)
        next.set(sym, { symbol: sym, company_name: null, cross_domain: null, loading: false, error: message })
        return next
      })
    }
  }, [items])

  function toggleCompany(sym: string) {
    const isRemoving = selected.includes(sym)
    setSelected((prev) =>
      prev.includes(sym) ? prev.filter((s) => s !== sym) : [...prev, sym],
    )
    if (!isRemoving) {
      const existing = companies.get(sym)
      if (!existing || (!existing.loading && existing.cross_domain === null && existing.error === null)) {
        void fetchCompanyCrossDomain(sym)
      }
    }
  }

  function toggleExpand(obsId: string) {
    setExpandedObs((prev) => {
      const next = new Set(prev)
      if (next.has(obsId)) {
        next.delete(obsId)
      } else {
        next.add(obsId)
      }
      return next
    })
  }

  const allObservations = useMemo(() => {
    const obs: (CrossDomainObservation & { symbol: string })[] = []
    for (const sym of selected) {
      const data = companies.get(sym)
      if (data?.cross_domain) {
        for (const o of data.cross_domain.observations) {
          obs.push({ ...o, symbol: sym })
        }
      }
    }
    return obs
  }, [selected, companies])

  const filteredObservations = useMemo(() => {
    let obs = allObservations
    if (directionFilter) {
      obs = obs.filter((o) => o.direction.toUpperCase() === directionFilter.toUpperCase())
    }
    if (severityFilter) {
      obs = obs.filter((o) => o.severity.toUpperCase() === severityFilter.toUpperCase())
    }
    if (relationshipFilter) {
      obs = obs.filter((o) => o.relationship.toUpperCase().includes(relationshipFilter.toUpperCase()))
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      obs = obs.filter((o) =>
        o.label.toLowerCase().includes(q) ||
        o.description.toLowerCase().includes(q) ||
        o.symbol.toLowerCase().includes(q) ||
        o.domain_1_name.toLowerCase().includes(q) ||
        o.domain_2_name.toLowerCase().includes(q)
      )
    }
    return obs
  }, [allObservations, directionFilter, severityFilter, relationshipFilter, searchQuery])

  const directionCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const o of allObservations) {
      const d = o.direction.toUpperCase()
      counts[d] = (counts[d] ?? 0) + 1
    }
    return counts
  }, [allObservations])

  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const o of allObservations) {
      const s = o.severity.toUpperCase()
      counts[s] = (counts[s] ?? 0) + 1
    }
    return counts
  }, [allObservations])

  const relationshipCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const o of allObservations) {
      const r = o.relationship.toUpperCase()
      counts[r] = (counts[r] ?? 0) + 1
    }
    return counts
  }, [allObservations])

  const selectedCompanyNames = useMemo(() => {
    return selected.map((sym) => {
      const data = companies.get(sym)
      return {
        symbol: sym,
        name: data?.company_name ?? sym,
        obsCount: data?.cross_domain?.observation_count ?? 0,
      }
    })
  }, [selected, companies])

  return (
    <div className="page-cross-domain">
      <section className="page-hero">
        <h1>Cross-Domain Research</h1>
        <p className="page-subtitle">
          Observations spanning multiple research domains: fundamental vs. market,
          growth vs. margin, earnings vs. cash flow, debt vs. cash generation.
          Each divergence exposes both sides with relationship, severity, explanation,
          supporting data, and limitations. No scores, no recommendations.
        </p>
      </section>

      {loading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading cross-domain data</strong>
          <span>Fetching supported companies...</span>
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
        <div className="ei-layout">
          {/* LEFT: Company selector */}
          <div className="ei-sidebar">
            <div className="panel">
              <div className="panel-head">
                <h3>Select Companies</h3>
                <span>{selected.length} selected</span>
              </div>
              <div className="ei-search">
                <Search size={14} />
                <input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter observations..."
                  aria-label="Filter observations"
                />
              </div>
              <div className="ei-company-list">
                {researchable.map((item) => {
                  const cd = companies.get(item.symbol)
                  return (
                    <button
                      key={item.symbol}
                      className={`ei-company-item ${selected.includes(item.symbol) ? "active" : ""}`}
                      onClick={() => toggleCompany(item.symbol)}
                    >
                      <span className="ei-company-info">
                        <Building2 size={14} />
                        <div>
                          <b>{item.symbol}</b>
                          <small>{item.company_name ?? item.symbol}</small>
                        </div>
                      </span>
                      <span className="ei-company-meta">
                        {cd?.loading && <Activity className="spin" size={12} />}
                        {cd?.cross_domain && (
                          <span className="ei-entry-count">{cd.cross_domain.observation_count}</span>
                        )}
                        {cd?.error && (
                          <span className="ei-entry-error" title={cd.error}>!</span>
                        )}
                      </span>
                    </button>
                  )
                })}
              </div>

              {selectedCompanyNames.length > 0 && (
                <div className="ei-selected-chips">
                  {selectedCompanyNames.map((c) => (
                    <span key={c.symbol} className="ei-selected-chip">
                      <span>{c.symbol}</span>
                      <span className="ei-selected-chip-count">{c.obsCount}</span>
                      <button
                        onClick={() => toggleCompany(c.symbol)}
                        aria-label={`Remove ${c.symbol}`}
                      >
                        &times;
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* RIGHT: Observations content */}
          <div className="ei-content">
            {selected.length === 0 ? (
              <div className="empty-state">
                <GitBranch size={28} />
                <strong>Select companies to view cross-domain observations</strong>
                <p>Choose companies from the list to see their cross-domain divergence analysis.</p>
              </div>
            ) : (
              <>
                {/* Summary Stats */}
                <CrossDomainSummaryStats observations={allObservations} companyCount={selected.length} />

                {/* Active Filters */}
                {(directionFilter || severityFilter || relationshipFilter) && (
                  <div className="ei-active-filters">
                    <Tag size={13} />
                    {directionFilter && (
                      <span className="ei-active-filter">
                        <span>Direction: {formatLabel(directionFilter)}</span>
                        <button onClick={() => setDirectionFilter(null)}>&times;</button>
                      </span>
                    )}
                    {severityFilter && (
                      <span className="ei-active-filter">
                        <span>Severity: {formatLabel(severityFilter)}</span>
                        <button onClick={() => setSeverityFilter(null)}>&times;</button>
                      </span>
                    )}
                    {relationshipFilter && (
                      <span className="ei-active-filter">
                        <span>Relationship: {relationshipLabel(relationshipFilter)}</span>
                        <button onClick={() => setRelationshipFilter(null)}>&times;</button>
                      </span>
                    )}
                    <button
                      className="ei-clear-filters"
                      onClick={() => { setDirectionFilter(null); setSeverityFilter(null); setRelationshipFilter(null) }}
                    >
                      Clear all
                    </button>
                  </div>
                )}

                {/* Filter Bar */}
                <div className="ei-filter-bar">
                  {Object.keys(directionCounts).length > 0 && (
                    <div className="ei-filter-group">
                      <span className="ei-filter-label">Direction</span>
                      <div className="ei-filter-chips">
                        <button
                          className={`ei-chip ${directionFilter === null ? "active" : ""}`}
                          onClick={() => setDirectionFilter(null)}
                        >
                          All
                        </button>
                        {Object.keys(directionCounts).sort().map((dir) => (
                          <button
                            key={dir}
                            className={`ei-chip ${directionFilter === dir ? "active" : ""}`}
                            onClick={() => setDirectionFilter(directionFilter === dir ? null : dir)}
                          >
                            {directionIcon(dir)} {formatLabel(dir)}
                            <span className="ei-chip-count">{directionCounts[dir]}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {Object.keys(severityCounts).length > 1 && (
                    <div className="ei-filter-group">
                      <span className="ei-filter-label">Severity</span>
                      <div className="ei-filter-chips">
                        <button
                          className={`ei-chip ${severityFilter === null ? "active" : ""}`}
                          onClick={() => setSeverityFilter(null)}
                        >
                          All
                        </button>
                        {Object.keys(severityCounts).sort().map((sev) => (
                          <button
                            key={sev}
                            className={`ei-chip ${severityFilter === sev ? "active" : ""}`}
                            onClick={() => setSeverityFilter(severityFilter === sev ? null : sev)}
                          >
                            {formatLabel(sev)}
                            <span className="ei-chip-count">{severityCounts[sev]}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {Object.keys(relationshipCounts).length > 1 && (
                    <div className="ei-filter-group">
                      <span className="ei-filter-label">Relationship</span>
                      <div className="ei-filter-chips">
                        <button
                          className={`ei-chip ${relationshipFilter === null ? "active" : ""}`}
                          onClick={() => setRelationshipFilter(null)}
                        >
                          All
                        </button>
                        {Object.keys(relationshipCounts).sort().map((rel) => (
                          <button
                            key={rel}
                            className={`ei-chip ${relationshipFilter === rel ? "active" : ""}`}
                            onClick={() => setRelationshipFilter(relationshipFilter === rel ? null : rel)}
                          >
                            {relationshipLabel(rel)}
                            <span className="ei-chip-count">{relationshipCounts[rel]}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Observation Count */}
                <div className="ei-event-count">
                  <span>{filteredObservations.length} observations</span>
                  {filteredObservations.length !== allObservations.length && (
                    <span className="ei-event-count-filtered">
                      (of {allObservations.length} total)
                    </span>
                  )}
                </div>

                {/* Observation List */}
                {filteredObservations.length === 0 ? (
                  <div className="empty-state">
                    <Search size={28} />
                    <strong>No matching observations</strong>
                    <p>Try adjusting your filters or search query.</p>
                  </div>
                ) : (
                  <div className="cd-obs-list">
                    {filteredObservations.map((obs) => (
                      <ObservationRow
                        key={obs.observation_id}
                        obs={obs}
                        expanded={expandedObs.has(obs.observation_id)}
                        onToggle={() => toggleExpand(obs.observation_id)}
                        navigate={navigate}
                      />
                    ))}
                  </div>
                )}

                {/* Notes */}
                {selected.some((sym) => {
                  const cd = companies.get(sym)
                  return cd?.cross_domain?.notes && cd.cross_domain.notes.length > 0
                }) && (
                  <div className="ei-note">
                    <Tag size={13} />
                    <span>
                      Observations are deterministic divergences between research domains.
                      Each exposes both sides, their relationship, and explicit limitations.
                      No claim is automatically resolved.
                    </span>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
