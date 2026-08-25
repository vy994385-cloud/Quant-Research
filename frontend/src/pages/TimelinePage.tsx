/**
 * Event Intelligence page: chronological company event timeline.
 *
 * Fetches timeline data per company via fetchTimeline.
 * Shows expandable events with category, direction, stance, verification status,
 * source/provenance, and fact-vs-derived distinction.
 * Events are clustered by month for readability.
 *
 * No rankings, no scores, no recommendations, no trade signals.
 */

import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Activity,
  Building2,
  Calendar,
  ChevronDown,
  ChevronRight,
  Clock,
  FileSearch,
  Filter,
  Search,
  Shield,
  Tag,
} from "lucide-react"
import { ApiError, fetchDiscovery, fetchTimeline } from "../api/client"
import type {
  CompanyTimelineResponse,
  DiscoveryItem,
  IntelCategory,
  TimelineEntry,
} from "../api/types"
import { LoadingState, ErrorState, EmptyState } from "../components/States"
import { formatIso, formatLabel, formatSourceName } from "../lib/format"
import { statusTone } from "../lib/signal"
import type { Tone } from "../lib/signal"

/* ── Helpers ──────────────────────────────────────────────────────────── */

function categoryTone(
  category: IntelCategory,
): "green" | "red" | "amber" | "blue" | "slate" {
  switch (category) {
    case "FINANCIAL_DISCLOSURE":
      return "blue"
    case "CORPORATE_ACTION":
    case "ORDER_CONTRACT":
    case "ACQUISITION_DIVESTMENT":
    case "CAPEX_EXPANSION":
      return "green"
    case "MANAGEMENT_STATEMENT":
    case "EXECUTIVE_CHANGE":
    case "CONFERENCE_CALL":
    case "INVESTOR_PRESENTATION":
    case "FORECAST_GUIDANCE":
      return "amber"
    case "REGULATORY_LEGAL":
    case "LEGAL_PROCEEDING":
    case "CREDIT_RATING_ACTION":
      return "red"
    case "BUSINESS_NEWS":
    case "PRODUCT_BUSINESS_UPDATE":
    case "SUBSIDIARY_UPDATE":
    case "SEGMENT_UPDATE":
      return "blue"
    case "OWNERSHIP_DISCLOSURE":
    case "INSIDER_ACTIVITY":
      return "amber"
    default:
      return "slate"
  }
}

function directionTone(direction: string): "green" | "red" | "amber" | "slate" {
  switch (direction?.toUpperCase()) {
    case "POSITIVE":
    case "SUPPORTIVE":
      return "green"
    case "NEGATIVE":
    case "CONTRADICTING":
      return "red"
    case "MIXED":
    case "NEUTRAL":
      return "slate"
    default:
      return "amber"
  }
}

function directionIcon(direction: string) {
  switch (direction?.toUpperCase()) {
    case "POSITIVE":
    case "SUPPORTIVE":
      return "\u2191"
    case "NEGATIVE":
    case "CONTRADICTING":
      return "\u2193"
    case "MIXED":
      return "\u21C5"
    default:
      return "\u2014"
  }
}

function semanticBadge(semantic: string): { label: string; tone: Tone } {
  switch (semantic?.toUpperCase()) {
    case "FACT":
      return { label: "Fact", tone: "green" }
    case "MANAGEMENT_COMMENTARY":
      return { label: "Commentary", tone: "amber" }
    case "DERIVED_METRIC":
      return { label: "Derived", tone: "blue" }
    case "OBSERVATION":
      return { label: "Observation", tone: "slate" }
    case "REPORTED_CLAIM":
      return { label: "Claim", tone: "amber" }
    case "ALLEGATION":
      return { label: "Allegation", tone: "red" }
    case "CONCLUSION":
      return { label: "Conclusion", tone: "blue" }
    default:
      return { label: formatLabel(semantic), tone: "slate" }
  }
}

function monthKey(dateStr: string | null): string {
  if (!dateStr) return "Unknown"
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return "Unknown"
  return d.toLocaleDateString(undefined, { year: "numeric", month: "long" })
}

/* ── Interface ────────────────────────────────────────────────────────── */

interface CompanyTimelineData {
  symbol: string
  company_name: string | null
  timeline: CompanyTimelineResponse["timeline"] | null
  loading: boolean
  error: string | null
}

/* ── Summary Stats ────────────────────────────────────────────────────── */

function TimelineSummaryStats({
  entries,
  companyCount,
}: {
  entries: (TimelineEntry & { symbol: string })[]
  companyCount: number
}) {
  const totalEvents = entries.length
  const positive = entries.filter(
    (e) => e.direction?.toUpperCase() === "POSITIVE" || e.direction?.toUpperCase() === "SUPPORTIVE",
  ).length
  const negative = entries.filter(
    (e) => e.direction?.toUpperCase() === "NEGATIVE" || e.direction?.toUpperCase() === "CONTRADICTING",
  ).length
  const categories = new Set(entries.map((e) => e.intel_category)).size
  const sources = new Set(entries.map((e) => e.source.source_name)).size

  return (
    <div className="ei-summary">
      <div className="ei-stat">
        <strong>{totalEvents}</strong>
        <span>events</span>
      </div>
      <div className="ei-stat">
        <strong>{companyCount}</strong>
        <span>companies</span>
      </div>
      <div className="ei-stat">
        <strong>{categories}</strong>
        <span>categories</span>
      </div>
      <div className="ei-stat">
        <strong>{sources}</strong>
        <span>sources</span>
      </div>
      {positive > 0 && (
        <div className="ei-stat ei-stat-pos">
          <strong>{positive}</strong>
          <span>supportive</span>
        </div>
      )}
      {negative > 0 && (
        <div className="ei-stat ei-stat-neg">
          <strong>{negative}</strong>
          <span>contradicting</span>
        </div>
      )}
    </div>
  )
}

/* ── Date Cluster Group ───────────────────────────────────────────────── */

function DateClusterGroup({
  label,
  entries,
  expandedEntries,
  onToggle,
  navigate,
}: {
  label: string
  entries: (TimelineEntry & { symbol: string })[]
  expandedEntries: Set<string>
  onToggle: (id: string) => void
  navigate: ReturnType<typeof useNavigate>
}) {
  return (
    <div className="ei-cluster">
      <div className="ei-cluster-header">
        <Calendar size={13} />
        <span>{label}</span>
        <span className="ei-cluster-count">{entries.length}</span>
      </div>
      <div className="ei-cluster-entries">
        {entries.map((entry, i) => (
          <EventRow
            key={`${entry.symbol}-${entry.entry_id}-${i}`}
            entry={entry}
            expanded={expandedEntries.has(entry.entry_id)}
            onToggle={() => onToggle(entry.entry_id)}
            navigate={navigate}
          />
        ))}
      </div>
    </div>
  )
}

/* ── Event Row ────────────────────────────────────────────────────────── */

function EventRow({
  entry,
  expanded,
  onToggle,
  navigate,
}: {
  entry: TimelineEntry & { symbol: string }
  expanded: boolean
  onToggle: () => void
  navigate: ReturnType<typeof useNavigate>
}) {
  const date = entry.timeline_at ?? entry.published_at ?? entry.effective_at
  const sem = semanticBadge(entry.semantic_category)
  const dirTone = directionTone(entry.direction)
  const catTone = categoryTone(entry.intel_category)

  return (
    <div className={`ei-event-row ${expanded ? "expanded" : ""}`}>
      <button className="ei-event-toggle" onClick={onToggle} aria-label={expanded ? "Collapse" : "Expand"}>
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>

      <div className="ei-event-timeline">
        <div className="ei-event-dot" />
        <div className="ei-event-line" />
      </div>

      <div className="ei-event-body">
        <div className="ei-event-header">
          <button
            className="ei-event-symbol"
            onClick={(e) => {
              e.stopPropagation()
              navigate(`/companies/${entry.symbol}`)
            }}
          >
            {entry.symbol}
          </button>
          <span className="ei-event-date">
            <Clock size={11} />
            {date ? formatIso(date) : "\u2014"}
          </span>
          {entry.direction && entry.direction !== "UNKNOWN" && (
            <span className={`ei-event-direction ${dirTone}`}>
              {directionIcon(entry.direction)} {formatLabel(entry.direction)}
            </span>
          )}
          <span className={`ei-tag ei-tag-${catTone}`}>
            {formatLabel(entry.intel_category)}
          </span>
          {entry.verification_status && (
            <span className={`ei-tag ei-tag-${statusTone(entry.verification_status)}`}>
              {formatLabel(entry.verification_status)}
            </span>
          )}
          <span className={`ei-tag ei-tag-${sem.tone}`}>{sem.label}</span>
        </div>

        <strong className="ei-event-title">{entry.title}</strong>

        {!expanded && entry.description && (
          <p className="ei-event-desc-preview">
            {entry.description.length > 120
              ? entry.description.slice(0, 120) + "..."
              : entry.description}
          </p>
        )}

        {expanded && (
          <div className="ei-event-detail">
            {entry.description && (
              <div className="ei-detail-section">
                <span className="ei-detail-label">Description</span>
                <p className="ei-detail-text">{entry.description}</p>
              </div>
            )}

            <div className="ei-detail-grid">
              {entry.stance && entry.stance !== "NEUTRAL" && (
                <div className="ei-detail-item">
                  <span className="ei-detail-label">Stance</span>
                  <span className={`ei-tag ei-tag-${directionTone(entry.stance)}`}>
                    {formatLabel(entry.stance)}
                  </span>
                </div>
              )}
              {entry.event_type && (
                <div className="ei-detail-item">
                  <span className="ei-detail-label">Event Type</span>
                  <span className="ei-detail-value">{formatLabel(entry.event_type)}</span>
                </div>
              )}
              {entry.topic && (
                <div className="ei-detail-item">
                  <span className="ei-detail-label">Topic</span>
                  <span className="ei-detail-value">{formatLabel(entry.topic)}</span>
                </div>
              )}
              {entry.kind && (
                <div className="ei-detail-item">
                  <span className="ei-detail-label">Kind</span>
                  <span className="ei-detail-value">{formatLabel(entry.kind)}</span>
                </div>
              )}
            </div>

            <div className="ei-detail-source">
              <FileSearch size={12} />
              <span className="ei-detail-source-name">
                {formatSourceName(entry.source.source_name) || "Unknown source"}
              </span>
              {entry.source.source_type && (
                <span className="ei-tag ei-tag-slate">
                  {formatLabel(entry.source.source_type)}
                </span>
              )}
              {entry.source.reliability_tier && (
                <span className="ei-detail-reliability">
                  <Shield size={11} />
                  Tier {entry.source.reliability_tier}
                </span>
              )}
              {entry.source.source_url && (
                <a
                  href={entry.source.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="ei-detail-link"
                >
                  source link
                </a>
              )}
            </div>

            {/* Raw lineage identifiers (provenance id, checksum) stay in the
                API payload and the Evidence explorer; they are noise here. */}

            {entry.published_at && (
              <div className="ei-detail-timestamps">
                {entry.published_at && (
                  <span>Published: {formatIso(entry.published_at)}</span>
                )}
                {entry.available_at && (
                  <span>Available: {formatIso(entry.available_at)}</span>
                )}
                {entry.effective_at && (
                  <span>Effective: {formatIso(entry.effective_at)}</span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/* ── Main Component ──────────────────────────────────────────────────── */

export default function TimelinePage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [timelines, setTimelines] = useState<Map<string, CompanyTimelineData>>(new Map())
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null)
  const [directionFilter, setDirectionFilter] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [expandedEntries, setExpandedEntries] = useState<Set<string>>(new Set())

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

  const fetchCompanyTimeline = useCallback(async (sym: string) => {
    setTimelines((prev) => {
      const next = new Map(prev)
      next.set(sym, { symbol: sym, company_name: null, timeline: null, loading: true, error: null })
      return next
    })

    try {
      const result = await fetchTimeline(sym)
      setTimelines((prev) => {
        const next = new Map(prev)
        next.set(sym, {
          symbol: sym,
          company_name: items.find((i) => i.symbol === sym)?.company_name ?? null,
          timeline: result.timeline,
          loading: false,
          error: null,
        })
        return next
      })
    } catch (err) {
      const message = err instanceof ApiError
        ? err.message
        : err instanceof Error ? err.message : "Failed to load timeline"
      setTimelines((prev) => {
        const next = new Map(prev)
        next.set(sym, { symbol: sym, company_name: null, timeline: null, loading: false, error: message })
        return next
      })
    }
  }, [items])

  function toggleCompany(sym: string) {
    const isRemoving = selected.includes(sym)
    setSelected((prev) =>
      prev.includes(sym) ? prev.filter((s) => s !== sym) : [...prev, sym]
    )
    if (!isRemoving) {
      const existing = timelines.get(sym)
      if (!existing || (!existing.loading && existing.timeline === null && existing.error === null)) {
        void fetchCompanyTimeline(sym)
      }
    }
  }

  function toggleExpand(entryId: string) {
    setExpandedEntries((prev) => {
      const next = new Set(prev)
      if (next.has(entryId)) {
        next.delete(entryId)
      } else {
        next.add(entryId)
      }
      return next
    })
  }

  const allEntries = useMemo(() => {
    const entries: (TimelineEntry & { symbol: string })[] = []
    for (const sym of selected) {
      const data = timelines.get(sym)
      if (data?.timeline) {
        for (const entry of data.timeline.entries) {
          entries.push({ ...entry, symbol: sym })
        }
      }
    }
    entries.sort((a, b) => {
      const da = a.timeline_at ?? a.published_at ?? ""
      const db = b.timeline_at ?? b.published_at ?? ""
      return db.localeCompare(da)
    })
    return entries
  }, [selected, timelines])

  const filteredEntries = useMemo(() => {
    let entries = allEntries
    if (categoryFilter) {
      entries = entries.filter((e) => e.intel_category === categoryFilter)
    }
    if (directionFilter) {
      const dir = directionFilter.toUpperCase()
      entries = entries.filter((e) => e.direction?.toUpperCase() === dir)
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      entries = entries.filter((e) =>
        e.title.toLowerCase().includes(q) ||
        e.description.toLowerCase().includes(q) ||
        e.symbol.toLowerCase().includes(q) ||
        (e.topic ?? "").toLowerCase().includes(q)
      )
    }
    return entries
  }, [allEntries, categoryFilter, directionFilter, searchQuery])

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const entry of allEntries) {
      counts[entry.intel_category] = (counts[entry.intel_category] ?? 0) + 1
    }
    return counts
  }, [allEntries])

  const directionCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const entry of allEntries) {
      const d = entry.direction?.toUpperCase() ?? "UNKNOWN"
      counts[d] = (counts[d] ?? 0) + 1
    }
    return counts
  }, [allEntries])

  const clusteredEntries = useMemo(() => {
    const clusters = new Map<string, (TimelineEntry & { symbol: string })[]>()
    for (const entry of filteredEntries) {
      const key = monthKey(entry.timeline_at ?? entry.published_at ?? entry.effective_at)
      const list = clusters.get(key) ?? []
      list.push(entry)
      clusters.set(key, list)
    }
    return clusters
  }, [filteredEntries])

  const selectedCompanyNames = useMemo(() => {
    return selected.map((sym) => {
      const data = timelines.get(sym)
      return {
        symbol: sym,
        name: data?.company_name ?? sym,
        entryCount: data?.timeline?.entries.length ?? 0,
      }
    })
  }, [selected, timelines])

  return (
    <div className="page-event-intelligence">
      <section className="page-hero">
        <p className="page-kicker">Research</p>
        <h1>Event Intelligence</h1>
        <p className="page-subtitle">
          Chronological company events: what happened, when, from which source, and its verification status.
          Events are facts from recorded sources. No interpretation, no scores, no recommendations.
        </p>
      </section>

      {loading && (
        <LoadingState label="Loading event data" description="Fetching supported companies..." />
      )}

      {error && (
        <ErrorState error={error} />
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
                  placeholder="Filter companies..."
                  aria-label="Filter companies"
                />
              </div>
              <div className="ei-company-list">
                {researchable.map((item) => {
                  const tl = timelines.get(item.symbol)
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
                        {tl?.loading && <Activity className="spin" size={12} />}
                        {tl?.timeline && (
                          <span className="ei-entry-count">{tl.timeline.entries.length}</span>
                        )}
                        {tl?.error && (
                          <span className="ei-entry-error" title={tl.error}>!</span>
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
                      <span className="ei-selected-chip-count">{c.entryCount}</span>
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

          {/* RIGHT: Timeline content */}
          <div className="ei-content">
            {selected.length === 0 ? (
              <EmptyState
                title="Select companies to view events"
                description="Choose companies from the list to see their event timelines."
              />
            ) : (
              <>
                {/* Summary Stats */}
                <TimelineSummaryStats entries={allEntries} companyCount={selected.length} />

                {/* Active Filters */}
                {(categoryFilter || directionFilter) && (
                  <div className="ei-active-filters">
                    <Filter size={13} />
                    {categoryFilter && (
                      <span className="ei-active-filter">
                        <span>Category: {formatLabel(categoryFilter)}</span>
                        <button onClick={() => setCategoryFilter(null)}>&times;</button>
                      </span>
                    )}
                    {directionFilter && (
                      <span className="ei-active-filter">
                        <span>Direction: {formatLabel(directionFilter)}</span>
                        <button onClick={() => setDirectionFilter(null)}>&times;</button>
                      </span>
                    )}
                    <button className="ei-clear-filters" onClick={() => { setCategoryFilter(null); setDirectionFilter(null) }}>
                      Clear all
                    </button>
                  </div>
                )}

                {/* Filter Bar */}
                <div className="ei-filter-bar">
                  <div className="ei-filter-group">
                    <Filter size={13} />
                    <span className="ei-filter-label">Category</span>
                    <div className="ei-filter-chips">
                      <button
                        className={`ei-chip ${categoryFilter === null ? "active" : ""}`}
                        onClick={() => setCategoryFilter(null)}
                      >
                        All
                      </button>
                      {Object.keys(categoryCounts).sort().map((cat) => (
                        <button
                          key={cat}
                          className={`ei-chip ${categoryFilter === cat ? "active" : ""}`}
                          onClick={() => setCategoryFilter(categoryFilter === cat ? null : cat)}
                        >
                          {formatLabel(cat)}
                          <span className="ei-chip-count">{categoryCounts[cat]}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {Object.keys(directionCounts).length > 1 && (
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
                            className={`ei-chip ei-chip-dir-${directionTone(dir)} ${directionFilter === dir ? "active" : ""}`}
                            onClick={() => setDirectionFilter(directionFilter === dir ? null : dir)}
                          >
                            {directionIcon(dir)} {formatLabel(dir)}
                            <span className="ei-chip-count">{directionCounts[dir]}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Event Count */}
                <div className="ei-event-count">
                  <span>{filteredEntries.length} events</span>
                  {filteredEntries.length !== allEntries.length && (
                    <span className="ei-event-count-filtered">
                      (of {allEntries.length} total)
                    </span>
                  )}
                </div>

                {/* Clustered Event List */}
                {filteredEntries.length === 0 ? (
                  <EmptyState
                    title="No matching events"
                    description="Try adjusting your filters or search query."
                  />
                ) : (
                  <div className="ei-clusters">
                    {[...clusteredEntries.entries()].map(([month, entries]) => (
                      <DateClusterGroup
                        key={month}
                        label={month}
                        entries={entries}
                        expandedEntries={expandedEntries}
                        onToggle={toggleExpand}
                        navigate={navigate}
                      />
                    ))}
                  </div>
                )}

                {/* Note */}
                <div className="ei-note">
                  <Tag size={13} />
                  <span>
                    Events are sourced facts from recorded company disclosures, financial filings,
                    and management statements. Each entry shows what was reported, when, from which
                    source, and its verification status. Semantic labels (FACT, COMMENTARY, etc.)
                    distinguish sourced facts from management commentary or derived observations.
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
