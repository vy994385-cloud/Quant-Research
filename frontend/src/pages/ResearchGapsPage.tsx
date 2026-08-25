/**
 * RESEARCH COVERAGE — what is known, limited, stale, conflicting,
 * insufficient or missing.
 *
 *   header → context → status overview strip → grouped gap stream → limitations
 *
 * Gaps merge across selected companies so identical reasons render once.
 * Status is descriptive, never a score; missing evidence never reads as
 * negative evidence (slate, not red).
 */

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  FileSearch,
  HelpCircle,
  Search,
  Shield,
} from "lucide-react"
import { ApiError, fetchDiscovery, fetchResearchGaps } from "../api/client"
import type { DiscoveryItem, ResearchGap } from "../api/types"
import { formatIso, formatLabel, formatSourceName } from "../lib/format"
import type { Tone } from "../lib/signal"

/* ── Status language ──────────────────────────────────────────────────── */

type GapStatus = "KNOWN" | "PARTIALLY_KNOWN" | "UNAVAILABLE" | "CONFLICTING" | "STALE" | "INSUFFICIENT_EVIDENCE"

const STATUS_ORDER: GapStatus[] = [
  "KNOWN",
  "PARTIALLY_KNOWN",
  "STALE",
  "INSUFFICIENT_EVIDENCE",
  "CONFLICTING",
  "UNAVAILABLE",
]

const STATUS_META: Record<GapStatus, { label: string; blurb: string; tone: Tone }> = {
  KNOWN: { label: "Available", blurb: "recorded and in force", tone: "green" },
  PARTIALLY_KNOWN: { label: "Limited", blurb: "partial coverage", tone: "amber" },
  STALE: { label: "Stale", blurb: "dated observations", tone: "amber" },
  INSUFFICIENT_EVIDENCE: { label: "Insufficient", blurb: "not enough evidence", tone: "slate" },
  CONFLICTING: { label: "Conflicting", blurb: "sources disagree", tone: "amber" },
  UNAVAILABLE: { label: "Missing", blurb: "no recorded data", tone: "slate" },
}

function statusMeta(status: string) {
  const key = (status?.toUpperCase() ?? "") as GapStatus
  return STATUS_META[key] ?? { label: formatLabel(status), blurb: "", tone: "slate" as Tone }
}

function severityTone(severity: string): Tone {
  switch (severity?.toUpperCase()) {
    case "HIGH": return "red"
    case "MEDIUM": return "amber"
    default: return "slate"
  }
}

function statusIcon(status: string) {
  switch (status?.toUpperCase()) {
    case "KNOWN": return <CheckCircle2 size={12} />
    case "PARTIALLY_KNOWN": return <AlertTriangle size={12} />
    case "CONFLICTING": return <AlertTriangle size={12} />
    case "STALE": return <Clock size={12} />
    default: return <HelpCircle size={12} />
  }
}

/* ── Grouping ─────────────────────────────────────────────────────────── */

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
  research_gaps: ResearchGapsShape | null
  loading: boolean
  error: string | null
}

interface ResearchGapsShape {
  symbol: string
  as_of: string
  gap_count: number
  gaps: ResearchGap[]
  status_counts: Record<string, number>
  category_counts: Record<string, number>
  coverage_score: string | null
  coverage_explanation: string
  notes: string[]
}

/* ── Gap row with quiet expansion ─────────────────────────────────────── */

function GapRow({
  gap,
  expanded,
  onToggle,
}: {
  gap: GroupedGap
  expanded: boolean
  onToggle: () => void
}) {
  const meta = statusMeta(gap.status)

  return (
    <div className={`rgx-row${expanded ? " expanded" : ""}`}>
      <button
        type="button"
        className="rgx-row-head"
        onClick={onToggle}
        aria-expanded={expanded}
      >
        <span className="rgx-domain">{formatLabel(gap.category)}</span>
        <span className="rgx-title">{gap.description}</span>
        <span className="rgx-badges">
          <span className={`status-badge ${meta.tone}`}>
            {statusIcon(gap.status)}
            {meta.label}
          </span>
          <span className={`tag ${severityTone(gap.severity)}`}>
            {formatLabel(gap.severity)}
          </span>
        </span>
        <ChevronRight size={14} className="rgx-chevron" />
      </button>

      {expanded && (
        <div className="rgx-detail">
          {gap.reason && (
            <section className="evx-drawer-block">
              <span className="evx-drawer-label">Why this gap exists</span>
              <p>{gap.reason}</p>
            </section>
          )}

          {gap.suggested_action && (
            <section className="evx-drawer-block">
              <span className="evx-drawer-label">What would resolve it</span>
              <p>{gap.suggested_action}</p>
            </section>
          )}

          <div className="rgx-detail-cols">
            {gap.related_metrics.length > 0 && (
              <section className="evx-drawer-block">
                <span className="evx-drawer-label">Affected research</span>
                <div className="evx-drawer-tags">
                  {gap.related_metrics.map((m) => (
                    <span key={m} className="tag slate">{formatLabel(m)}</span>
                  ))}
                </div>
              </section>
            )}

            {gap.sources_checked.length > 0 && (
              <section className="evx-drawer-block">
                <span className="evx-drawer-label">Source availability</span>
                <div className="evx-drawer-tags">
                  {gap.sources_checked.map((s) => (
                    <span key={s} className="tag slate">{formatSourceName(s)}</span>
                  ))}
                </div>
              </section>
            )}
          </div>

          {Object.keys(gap.supporting_data).length > 0 && (
            <section className="evx-drawer-block">
              <span className="evx-drawer-label">Recorded context</span>
              <dl className="evx-kv">
                {Object.entries(gap.supporting_data).map(([k, v]) => (
                  <div key={k}>
                    <dt>{formatLabel(k)}</dt>
                    <dd className="mono">{v}</dd>
                  </div>
                ))}
              </dl>
            </section>
          )}

          <div className="rgx-detail-foot">
            <Shield size={11} />
            <span>
              Affected: {gap.symbols.join(" · ")} · As of{" "}
              {gap.as_of ? formatIso(gap.as_of) : "—"}
            </span>
          </div>
        </div>
      )}
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

  /** Open with the first tracked company so the page shows content immediately. */
  useEffect(() => {
    if (items.length > 0) {
      const first = items.find((i) => i.research_available)
      if (first) void selectCompany(first.symbol, false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items])

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

  function selectCompany(sym: string, toggle = true) {
    setSelected((prev) => {
      const has = prev.includes(sym)
      if (toggle && has) return prev.filter((s) => s !== sym)
      return toggle ? [...prev, sym] : prev.includes(sym) ? prev : [...prev, sym]
    })
    setCompanies((prev) => {
      if (prev.get(sym)?.research_gaps || prev.get(sym)?.loading) return prev
      void fetchCompanyGaps(sym)
      return prev
    })
  }

  function toggleExpand(gapId: string) {
    setExpandedGaps((prev) => {
      const next = new Set(prev)
      if (next.has(gapId)) next.delete(gapId)
      else next.add(gapId)
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

  const groupedGaps = useMemo(() => groupGaps(allGaps), [allGaps])

  const filteredGaps = useMemo(() => {
    if (!searchQuery.trim()) return groupedGaps
    const q = searchQuery.toLowerCase()
    return groupedGaps.filter(
      (g) =>
        g.description.toLowerCase().includes(q) ||
        g.category.toLowerCase().includes(q) ||
        g.symbols.some((s) => s.toLowerCase().includes(q)) ||
        (g.reason ?? "").toLowerCase().includes(q),
    )
  }, [groupedGaps, searchQuery])

  /** Group the stream by status so related gaps read together. */
  const streamGroups = useMemo(() => {
    const byStatus = new Map<GapStatus, GroupedGap[]>()
    for (const gap of filteredGaps) {
      const key = (gap.status.toUpperCase()) as GapStatus
      if (!byStatus.has(key)) byStatus.set(key, [])
      byStatus.get(key)!.push(gap)
    }
    return STATUS_ORDER.filter((s) => byStatus.has(s)).map((s) => ({
      status: s,
      gaps: byStatus.get(s)!,
    }))
  }, [filteredGaps])

  const statusCounts = useMemo(() => {
    const counts = new Map<string, number>()
    for (const g of allGaps) counts.set(g.status, (counts.get(g.status) ?? 0) + 1)
    return counts
  }, [allGaps])

  /** Context: as-of window across selected companies. */
  const asOfWindow = useMemo(() => {
    const dates = [...companies.values()]
      .map((c) => c.research_gaps?.as_of)
      .filter((d): d is string => Boolean(d))
      .sort()
    if (dates.length === 0) return null
    const first = formatIso(dates[0])
    const last = formatIso(dates[dates.length - 1])
    return first === last ? first : `${first} → ${last}`
  }, [companies])

  const anyLoading = [...companies.values()].some((c) => c.loading)

  if (loading || error) {
    return (
      <div className="page-research-gaps">
        <header className="scr-header">
          <span className="eyebrow">Coverage intelligence</span>
          <h1>Research Coverage</h1>
        </header>
        {loading && (
          <div className="loading-state" role="status">
            <Activity className="spin" size={26} />
            <strong>Loading coverage data</strong>
          </div>
        )}
        {error && (
          <div className="empty-state error" role="alert">
            <FileSearch size={28} />
            <strong>Discovery unavailable</strong>
            <p>{error}</p>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="page-research-gaps page-gaps--workflow">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="scr-header">
        <span className="eyebrow">Coverage intelligence</span>
        <h1>Research Coverage</h1>
        <p className="scr-subtitle">
          What is known, limited, stale, conflicting, insufficient or missing.
          Each gap explains why information is absent and what would resolve it.
        </p>
      </header>

      {/* ── Company picker + context ──────────────────────────────── */}
      <section className="rgx-context scr-section mt-5">
        <div className="rgx-picker" role="group" aria-label="Select companies">
          {researchable.map((item) => (
            <button
              key={item.symbol}
              type="button"
              className={`rgx-pick${selected.includes(item.symbol) ? " active" : ""}`}
              onClick={() => selectCompany(item.symbol)}
              aria-pressed={selected.includes(item.symbol)}
            >
              {item.symbol}
            </button>
          ))}
        </div>
        <div className="scr-context rgx-context-strip">
          <span className="scr-context-item">
            <strong>{selected.length}</strong> of {researchable.length} companies
          </span>
          <span className="scr-context-sep" />
          <span className="scr-context-item">
            <strong>{filteredGaps.length}</strong> distinct gaps
          </span>
          {asOfWindow && (
            <>
              <span className="scr-context-sep" />
              <span className="scr-context-item">as of <strong>{asOfWindow}</strong></span>
            </>
          )}
          {anyLoading && <Activity className="spin" size={13} />}
        </div>
      </section>

      {selected.length === 0 ? (
        <div className="empty-state">
          <FileSearch size={28} />
          <strong>Select companies to view coverage</strong>
          <p>Choose one or more companies above to see their research gaps.</p>
        </div>
      ) : (
        <>
          {/* ── Status overview strip ───────────────────────────────── */}
          <section className="rgx-status-strip" aria-label="Coverage status overview">
            {STATUS_ORDER.map((status) => {
              const count = statusCounts.get(status) ?? 0
              const meta = STATUS_META[status]
              return (
                <div key={status} className={`rgx-status-cell ${meta.tone}${count === 0 ? " empty" : ""}`}>
                  <span className="rgx-status-count mono">{count}</span>
                  <span className="rgx-status-name">{meta.label}</span>
                  <span className="rgx-status-blurb">{meta.blurb}</span>
                </div>
              )
            })}
          </section>

          {/* ── Search within gaps ──────────────────────────────────── */}
          <div className="rgx-searchbar">
            <Search size={14} />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter gaps by keyword, domain, or company…"
              aria-label="Filter gaps"
            />
          </div>

          {/* ── Grouped gap stream ──────────────────────────────────── */}
          {streamGroups.length === 0 ? (
            <div className="empty-state">
              <CheckCircle2 size={28} />
              <strong>No matching gaps</strong>
              <p>Adjust the filter query to widen the view.</p>
            </div>
          ) : (
            <div className="rgx-stream">
              {streamGroups.map((group) => {
                const meta = STATUS_META[group.status]
                return (
                  <details key={group.status} className="rgx-group" open>
                    <summary>
                      <ChevronDown size={13} />
                      <span className={`status-badge ${meta.tone}`}>
                        {statusIcon(group.status)}
                        {meta.label}
                      </span>
                      <span className="rgx-group-count mono">{group.gaps.length}</span>
                      <span className="rgx-group-blurb">{meta.blurb}</span>
                    </summary>
                    <div className="rgx-group-body">
                      {group.gaps.map((g) => (
                        <GapRow
                          key={`${g.gap_id}-${g.symbols.join("_")}`}
                          gap={g}
                          expanded={expandedGaps.has(g.gap_id)}
                          onToggle={() => toggleExpand(g.gap_id)}
                        />
                      ))}
                    </div>
                  </details>
                )
              })}
            </div>
          )}

          {/* ── Limitations ─────────────────────────────────────────── */}
          <footer className="evx-footnote">
            <Shield size={12} />
            <span>
              Coverage is descriptive, not evaluative. Missing evidence is an observation about
              recorded data — it is not negative evidence. No single number represents company
              quality. Gaps are deterministic outputs of documented checks against available sources.
            </span>
          </footer>
        </>
      )}
    </div>
  )
}
