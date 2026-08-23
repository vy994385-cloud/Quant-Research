/**
 * Research Gaps & Coverage Intelligence page.
 *
 * Structured workspace for understanding what is KNOWN, UNKNOWN,
 * PARTIALLY KNOWN, STALE, CONFLICTING, and PIT-LIMITED about a company.
 *
 * Sections: Coverage Summary, Attention Required, Domain Coverage,
 * Historical Gaps, Evidence Problems, Research Limitations, Gap Details.
 *
 * No scores, no rankings, no recommendations, no investment decisions.
 */

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  Activity,
  AlertTriangle,
  Building2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  FileSearch,
  HelpCircle,
  Search,
  Shield,
  XCircle,
} from "lucide-react"
import { ApiError, fetchDiscovery, fetchResearchGaps } from "../api/client"
import type { DiscoveryItem, ResearchGap } from "../api/types"
import { formatIso, formatLabel, formatSourceName } from "../lib/format"
import { Tag } from "../components/ui"
import type { Tone } from "../lib/signal"

/* ── Helpers ──────────────────────────────────────────────────────────── */

function statusTone(status: string): Tone {
  switch (status?.toUpperCase()) {
    case "KNOWN":
      return "green"
    case "PARTIALLY_KNOWN":
      return "amber"
    case "UNAVAILABLE":
      return "slate"
    case "CONFLICTING":
      return "amber"
    case "STALE":
      return "amber"
    case "INSUFFICIENT_EVIDENCE":
      return "amber"
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

function statusIcon(status: string) {
  switch (status?.toUpperCase()) {
    case "KNOWN":
      return <CheckCircle2 size={12} />
    case "PARTIALLY_KNOWN":
      return <AlertTriangle size={12} />
    case "UNAVAILABLE":
      return <XCircle size={12} />
    case "CONFLICTING":
      return <AlertTriangle size={12} />
    case "STALE":
      return <Clock size={12} />
    case "INSUFFICIENT_EVIDENCE":
      return <HelpCircle size={12} />
    default:
      return <HelpCircle size={12} />
  }
}

function statusLabel(status: string): string {
  switch (status?.toUpperCase()) {
    case "KNOWN":
      return "KNOWN"
    case "PARTIALLY_KNOWN":
      return "PARTIAL"
    case "UNAVAILABLE":
      return "MISSING"
    case "CONFLICTING":
      return "CONFLICT"
    case "STALE":
      return "STALE"
    case "INSUFFICIENT_EVIDENCE":
      return "INSUFFICIENT"
    default:
      return formatLabel(status)
  }
}

/* ── Interface ────────────────────────────────────────────────────────── */

/** A research gap merged across companies with identical content. */
type GroupedGap = ResearchGap & { symbols: string[] }

/**
 * Identical gaps repeat once per company ("No business profile available" × N).
 * Merging by description + category + status + severity keeps one row per
 * distinct gap; the affected companies travel as chips on the row.
 */
function groupGaps(gaps: Array<ResearchGap & { symbol: string }>): GroupedGap[] {
  const map = new Map<string, GroupedGap>()
  for (const gap of gaps) {
    const key = `${gap.description}|${gap.category}|${gap.status}|${gap.severity}`
    const existing = map.get(key)
    if (existing) {
      if (!existing.symbols.includes(gap.symbol)) existing.symbols.push(gap.symbol)
    } else {
      map.set(key, { ...gap, symbols: [gap.symbol] })
    }
  }
  return [...map.values()]
}

interface CompanyGapsData {
  symbol: string
  company_name: string | null
  research_gaps: {
    symbol: string
    as_of: string
    gap_count: number
    gaps: ResearchGap[]
    status_counts: Record<string, number>
    category_counts: Record<string, number>
    coverage_score: string | null
    coverage_explanation: string
    notes: string[]
  } | null
  loading: boolean
  error: string | null
}

/* ── Coverage Summary ─────────────────────────────────────────────────── */

function CoverageSummary({ gaps }: { gaps: ResearchGap[] }) {
  const total = gaps.length
  const byStatus: Record<string, number> = {}
  for (const g of gaps) {
    byStatus[g.status] = (byStatus[g.status] ?? 0) + 1
  }

  return (
    <div className="rg-summary">
      <div className="rg-stat">
        <strong>{total}</strong>
        <span>gaps</span>
      </div>
      {byStatus["UNAVAILABLE"] && (
        <div className="rg-stat rg-stat-slate">
          <strong>{byStatus["UNAVAILABLE"]}</strong>
          <span>missing</span>
        </div>
      )}
      {byStatus["INSUFFICIENT_EVIDENCE"] && (
        <div className="rg-stat rg-stat-warn">
          <strong>{byStatus["INSUFFICIENT_EVIDENCE"]}</strong>
          <span>insufficient</span>
        </div>
      )}
      {byStatus["STALE"] && (
        <div className="rg-stat rg-stat-warn">
          <strong>{byStatus["STALE"]}</strong>
          <span>stale</span>
        </div>
      )}
      {byStatus["CONFLICTING"] && (
        <div className="rg-stat rg-stat-warn">
          <strong>{byStatus["CONFLICTING"]}</strong>
          <span>conflicting</span>
        </div>
      )}
      {byStatus["PARTIALLY_KNOWN"] && (
        <div className="rg-stat rg-stat-warn">
          <strong>{byStatus["PARTIALLY_KNOWN"]}</strong>
          <span>partial</span>
        </div>
      )}
      {byStatus["KNOWN"] && (
        <div className="rg-stat rg-stat-pos">
          <strong>{byStatus["KNOWN"]}</strong>
          <span>known</span>
        </div>
      )}
    </div>
  )
}

/* ── Attention Required ───────────────────────────────────────────────── */

function AttentionRequired({ gaps }: { gaps: GroupedGap[] }) {
  const attention = gaps.filter(
    (g) =>
      g.severity.toUpperCase() === "HIGH" ||
      g.status.toUpperCase() === "UNAVAILABLE" ||
      g.status.toUpperCase() === "CONFLICTING" ||
      g.status.toUpperCase() === "INSUFFICIENT_EVIDENCE",
  )

  if (attention.length === 0) return null

  return (
    <div className="rg-section">
      <div className="rg-section-head">
        <AlertTriangle size={14} />
        <strong>Attention Required</strong>
        <span>{attention.length} gaps requiring research attention</span>
      </div>
      <div className="rg-attention-list">
        {attention.map((g) => (
          <div key={g.gap_id} className="rg-attention-item">
            <span className={`rg-attention-sev ${severityTone(g.severity)}`}>
              {formatLabel(g.severity)}
            </span>
            <div className="rg-attention-body">
              <strong>{g.description}</strong>
              {g.reason && <p>{g.reason}</p>}
              {g.suggested_action && (
                <span className="rg-attention-action">
                  {g.suggested_action}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Domain Coverage ──────────────────────────────────────────────────── */

function DomainCoverage({
  categoryCounts,
  totalGaps,
}: {
  categoryCounts: Record<string, number>
  totalGaps: number
}) {
  const entries = Object.entries(categoryCounts).sort((a, b) => b[1] - a[1])
  if (entries.length === 0) return null

  return (
    <div className="rg-section">
      <div className="rg-section-head">
        <Shield size={14} />
        <strong>Domain Coverage</strong>
        <span>{entries.length} domains with gaps</span>
      </div>
      <div className="rg-domain-grid">
        {entries.map(([cat, count]) => (
          <div key={cat} className="rg-domain-tile">
            <span className="rg-domain-label">{formatLabel(cat)}</span>
            <span className="rg-domain-count">
              {count} {count === 1 ? "gap" : "gaps"}
            </span>
            <div className="rg-domain-bar">
              <div
                className="rg-domain-bar-fill"
                style={{ width: `${Math.min((count / totalGaps) * 100, 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Evidence Problems ────────────────────────────────────────────────── */

function EvidenceProblems({
  gaps,
  filter,
}: {
  gaps: GroupedGap[]
  filter: "missing" | "stale" | "conflicting" | "insufficient"
}) {
  const filtered = gaps.filter((g) => {
    switch (filter) {
      case "missing":
        return g.status.toUpperCase() === "UNAVAILABLE"
      case "stale":
        return g.status.toUpperCase() === "STALE"
      case "conflicting":
        return g.status.toUpperCase() === "CONFLICTING"
      case "insufficient":
        return g.status.toUpperCase() === "INSUFFICIENT_EVIDENCE"
    }
  })

  if (filtered.length === 0) return null

  const config = {
    missing: { icon: XCircle, label: "Missing Evidence", tone: "red" as Tone },
    stale: { icon: Clock, label: "Stale Evidence", tone: "amber" as Tone },
    conflicting: { icon: AlertTriangle, label: "Conflicting Evidence", tone: "red" as Tone },
    insufficient: { icon: HelpCircle, label: "Insufficient Evidence", tone: "amber" as Tone },
  }
  const c = config[filter]
  const Icon = c.icon

  return (
    <div className="rg-section">
      <div className="rg-section-head">
        <Icon size={14} />
        <strong>{c.label}</strong>
        <Tag text={`${filtered.length}`} tone={c.tone} />
      </div>
      <div className="rg-gap-list">
        {filtered.map((g) => (
          <GapRow key={g.gap_id} gap={g} />
        ))}
      </div>
    </div>
  )
}

/* ── Gap Row ──────────────────────────────────────────────────────────── */

function GapRow({
  gap,
  expanded,
  onToggle,
}: {
  gap: GroupedGap
  expanded?: boolean
  onToggle?: () => void
}) {
  const supportingEntries = Object.entries(gap.supporting_data)

  return (
    <div className={`rg-gap-row ${expanded ? "expanded" : ""}`}>
      {onToggle && (
        <button
          className="rg-gap-toggle"
          onClick={onToggle}
          aria-label={expanded ? "Collapse" : "Expand"}
        >
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
      )}

      <div className="rg-gap-body">
        <div className="rg-gap-header">
          {statusIcon(gap.status)}
          <Tag text={statusLabel(gap.status)} tone={statusTone(gap.status)} />
          <Tag text={formatLabel(gap.severity)} tone={severityTone(gap.severity)} />
          <Tag text={formatLabel(gap.category)} tone="slate" />
          <span className="rg-gap-symbols">
            {gap.symbols.map((symbol) => (
              <span key={symbol} className="rg-gap-symbol">
                {symbol}
              </span>
            ))}
          </span>
        </div>

        <strong className="rg-gap-desc">{gap.description}</strong>

        {!expanded && gap.reason && (
          <p className="rg-gap-reason-preview">
            {gap.reason.length > 120 ? gap.reason.slice(0, 120) + "..." : gap.reason}
          </p>
        )}

        {expanded && (
          <div className="rg-gap-detail">
            {gap.reason && (
              <div className="rg-detail-section">
                <span className="rg-detail-label">Reason</span>
                <p className="rg-detail-text">{gap.reason}</p>
              </div>
            )}

            {gap.suggested_action && (
              <div className="rg-detail-section">
                <span className="rg-detail-label">What Would Resolve</span>
                <p className="rg-detail-text">{gap.suggested_action}</p>
              </div>
            )}

            {gap.related_metrics.length > 0 && (
              <div className="rg-detail-section">
                <span className="rg-detail-label">Related Metrics</span>
                <div className="rg-detail-tags">
                  {gap.related_metrics.map((m) => (
                    <Tag key={m} text={formatLabel(m)} tone="slate" />
                  ))}
                </div>
              </div>
            )}

            {gap.sources_checked.length > 0 && (
              <div className="rg-detail-section">
                <span className="rg-detail-label">Sources Checked</span>
                <div className="rg-detail-tags">
                  {gap.sources_checked.map((s) => (
                    <Tag key={s} text={formatSourceName(s)} tone="slate" />
                  ))}
                </div>
              </div>
            )}

            {gap.evidence_refs.length > 0 && (
              <div className="rg-detail-section">
                <span className="rg-detail-label">Evidence References</span>
                <div className="rg-detail-tags">
                  {gap.evidence_refs.map((e) => (
                    <Tag key={e} text={e} tone="slate" />
                  ))}
                </div>
              </div>
            )}

            {supportingEntries.length > 0 && (
              <div className="rg-detail-section">
                <span className="rg-detail-label">Supporting Data</span>
                <div className="rg-detail-kv">
                  {supportingEntries.map(([k, v]) => (
                    <div key={k} className="rg-detail-kv-row">
                      <span className="rg-detail-kv-key">{formatLabel(k)}</span>
                      <span className="rg-detail-kv-value mono">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="rg-detail-provenance">
              <span className="rg-detail-as-of">
                <Shield size={11} />
                As of {gap.as_of ? formatIso(gap.as_of) : "\u2014"}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Main Component ──────────────────────────────────────────────────── */

export default function ResearchGapsPage() {
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [companies, setCompanies] = useState<Map<string, CompanyGapsData>>(new Map())
  const [statusFilter, setStatusFilter] = useState<string | null>(null)
  const [severityFilter, setSeverityFilter] = useState<string | null>(null)
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [expandedGaps, setExpandedGaps] = useState<Set<string>>(new Set())

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

  const fetchCompanyGaps = useCallback(async (sym: string) => {
    setCompanies((prev) => {
      const next = new Map(prev)
      next.set(sym, { symbol: sym, company_name: null, research_gaps: null, loading: true, error: null })
      return next
    })

    try {
      const result = await fetchResearchGaps(sym)
      setCompanies((prev) => {
        const next = new Map(prev)
        next.set(sym, {
          symbol: sym,
          company_name: items.find((i) => i.symbol === sym)?.company_name ?? null,
          research_gaps: result.research_gaps,
          loading: false,
          error: null,
        })
        return next
      })
    } catch (err) {
      const message = err instanceof ApiError
        ? err.message
        : err instanceof Error ? err.message : "Failed to load research gaps"
      setCompanies((prev) => {
        const next = new Map(prev)
        next.set(sym, { symbol: sym, company_name: null, research_gaps: null, loading: false, error: message })
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
      if (!existing || (!existing.loading && existing.research_gaps === null && existing.error === null)) {
        void fetchCompanyGaps(sym)
      }
    }
  }

  function toggleExpand(gapId: string) {
    setExpandedGaps((prev) => {
      const next = new Set(prev)
      if (next.has(gapId)) {
        next.delete(gapId)
      } else {
        next.add(gapId)
      }
      return next
    })
  }

  const allGaps = useMemo(() => {
    const gaps: (ResearchGap & { symbol: string })[] = []
    for (const sym of selected) {
      const data = companies.get(sym)
      if (data?.research_gaps) {
        for (const g of data.research_gaps.gaps) {
          gaps.push({ ...g, symbol: sym })
        }
      }
    }
    return gaps
  }, [selected, companies])

  /** Attention-required view works on merged gaps so identical gaps across
   * companies render once with company chips. */
  const groupedAllGaps = useMemo(() => groupGaps(allGaps), [allGaps])

  const filteredGaps = useMemo(() => {
    let gaps = allGaps
    if (statusFilter) {
      gaps = gaps.filter((g) => g.status.toUpperCase() === statusFilter.toUpperCase())
    }
    if (severityFilter) {
      gaps = gaps.filter((g) => g.severity.toUpperCase() === severityFilter.toUpperCase())
    }
    if (categoryFilter) {
      gaps = gaps.filter((g) => g.category.toUpperCase() === categoryFilter.toUpperCase())
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      gaps = gaps.filter((g) =>
        g.description.toLowerCase().includes(q) ||
        g.category.toLowerCase().includes(q) ||
        g.symbol.toLowerCase().includes(q) ||
        (g.reason ?? "").toLowerCase().includes(q)
      )
    }
    return groupGaps(gaps)
  }, [allGaps, statusFilter, severityFilter, categoryFilter, searchQuery])

  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const g of allGaps) {
      counts[g.status] = (counts[g.status] ?? 0) + 1
    }
    return counts
  }, [allGaps])

  const severityCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const g of allGaps) {
      counts[g.severity] = (counts[g.severity] ?? 0) + 1
    }
    return counts
  }, [allGaps])

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const g of allGaps) {
      counts[g.category] = (counts[g.category] ?? 0) + 1
    }
    return counts
  }, [allGaps])

  const selectedCompanyNames = useMemo(() => {
    return selected.map((sym) => {
      const data = companies.get(sym)
      return {
        symbol: sym,
        name: data?.company_name ?? sym,
        gapCount: data?.research_gaps?.gap_count ?? 0,
      }
    })
  }, [selected, companies])

  return (
    <div className="page-research-gaps">
      <section className="page-hero">
        <h1>Research Gaps &amp; Coverage</h1>
        <p className="page-subtitle">
          What is known, unknown, partially known, stale, or conflicting about a company.
          Each gap explains why information is missing and what would resolve it.
          No scores, no rankings, no investment decisions.
        </p>
      </section>

      {loading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading research gap data</strong>
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
                  placeholder="Filter gaps..."
                  aria-label="Filter gaps"
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
                        {cd?.research_gaps && (
                          <span className="ei-entry-count">{cd.research_gaps.gap_count}</span>
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
                      <span className="ei-selected-chip-count">{c.gapCount}</span>
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

          {/* RIGHT: Gaps content */}
          <div className="ei-content">
            {selected.length === 0 ? (
              <div className="empty-state">
                <FileSearch size={28} />
                <strong>Select companies to view research gaps</strong>
                <p>Choose companies from the list to see their research gap analysis and coverage information.</p>
              </div>
            ) : (
              <>
                {/* Coverage Summary */}
                <CoverageSummary gaps={allGaps} />

                {/* Attention Required */}
                <AttentionRequired gaps={groupedAllGaps} />

                {/* Domain Coverage */}
                <DomainCoverage categoryCounts={categoryCounts} totalGaps={allGaps.length} />

                {/* Active Filters */}
                {(statusFilter || severityFilter || categoryFilter) && (
                  <div className="ei-active-filters">
                    <AlertTriangle size={13} />
                    {statusFilter && (
                      <span className="ei-active-filter">
                        <span>Status: {statusLabel(statusFilter)}</span>
                        <button onClick={() => setStatusFilter(null)}>&times;</button>
                      </span>
                    )}
                    {severityFilter && (
                      <span className="ei-active-filter">
                        <span>Severity: {formatLabel(severityFilter)}</span>
                        <button onClick={() => setSeverityFilter(null)}>&times;</button>
                      </span>
                    )}
                    {categoryFilter && (
                      <span className="ei-active-filter">
                        <span>Domain: {formatLabel(categoryFilter)}</span>
                        <button onClick={() => setCategoryFilter(null)}>&times;</button>
                      </span>
                    )}
                    <button
                      className="ei-clear-filters"
                      onClick={() => { setStatusFilter(null); setSeverityFilter(null); setCategoryFilter(null) }}
                    >
                      Clear all
                    </button>
                  </div>
                )}

                {/* Filter Bar */}
                <div className="ei-filter-bar">
                  {Object.keys(statusCounts).length > 0 && (
                    <div className="ei-filter-group">
                      <span className="ei-filter-label">Status</span>
                      <div className="ei-filter-chips">
                        <button
                          className={`ei-chip ${statusFilter === null ? "active" : ""}`}
                          onClick={() => setStatusFilter(null)}
                        >
                          All
                        </button>
                        {Object.keys(statusCounts).sort().map((s) => (
                          <button
                            key={s}
                            className={`ei-chip ${statusFilter === s ? "active" : ""}`}
                            onClick={() => setStatusFilter(statusFilter === s ? null : s)}
                          >
                            {statusLabel(s)}
                            <span className="ei-chip-count">{statusCounts[s]}</span>
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
                        {Object.keys(severityCounts).sort().map((s) => (
                          <button
                            key={s}
                            className={`ei-chip ${severityFilter === s ? "active" : ""}`}
                            onClick={() => setSeverityFilter(severityFilter === s ? null : s)}
                          >
                            {formatLabel(s)}
                            <span className="ei-chip-count">{severityCounts[s]}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {Object.keys(categoryCounts).length > 1 && (
                    <div className="ei-filter-group">
                      <span className="ei-filter-label">Domain</span>
                      <div className="ei-filter-chips">
                        <button
                          className={`ei-chip ${categoryFilter === null ? "active" : ""}`}
                          onClick={() => setCategoryFilter(null)}
                        >
                          All
                        </button>
                        {Object.keys(categoryCounts).sort().map((c) => (
                          <button
                            key={c}
                            className={`ei-chip ${categoryFilter === c ? "active" : ""}`}
                            onClick={() => setCategoryFilter(categoryFilter === c ? null : c)}
                          >
                            {formatLabel(c)}
                            <span className="ei-chip-count">{categoryCounts[c]}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Gap Count */}
                <div className="ei-event-count">
                  <span>
                    {filteredGaps.length} distinct gap{filteredGaps.length !== 1 ? "s" : ""}
                  </span>
                  {filteredGaps.length !== allGaps.length && (
                    <span className="ei-event-count-filtered">
                      (grouped from {allGaps.length} company ent{allGaps.length !== 1 ? "ries" : "ry"})
                    </span>
                  )}
                </div>

                {/* Evidence Problems: Missing */}
                <EvidenceProblems gaps={filteredGaps} filter="missing" />

                {/* Evidence Problems: Stale */}
                <EvidenceProblems gaps={filteredGaps} filter="stale" />

                {/* Evidence Problems: Conflicting */}
                <EvidenceProblems gaps={filteredGaps} filter="conflicting" />

                {/* Evidence Problems: Insufficient */}
                <EvidenceProblems gaps={filteredGaps} filter="insufficient" />

                {/* All Gaps (filtered) */}
                {filteredGaps.length === 0 ? (
                  <div className="empty-state">
                    <CheckCircle2 size={28} />
                    <strong>No matching gaps</strong>
                    <p>Try adjusting your filters or search query.</p>
                  </div>
                ) : (
                  <div className="rg-section">
                    <div className="rg-section-head">
                      <FileSearch size={14} />
                      <strong>Gap Details</strong>
                      <span>{filteredGaps.length} distinct gaps</span>
                    </div>
                    <div className="rg-gap-list">
                      {filteredGaps.map((g) => (
                        <GapRow
                          key={g.gap_id}
                          gap={g}
                          expanded={expandedGaps.has(g.gap_id)}
                          onToggle={() => toggleExpand(g.gap_id)}
                        />
                      ))}
                    </div>
                  </div>
                )}

                {/* Note */}
                <div className="ei-note">
                  <Shield size={13} />
                  <span>
                    Gaps are deterministic observations about missing, incomplete, stale,
                    or conflicting research evidence. Each gap explains why information
                    is unavailable and what would resolve it. Coverage is descriptive,
                    not evaluative. No single number represents company quality.
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
