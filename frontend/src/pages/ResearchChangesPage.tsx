/**
 * RESEARCH CHANGES — track what has changed in recorded research.
 *
 * Shows recent changes to research data across the tracked universe:
 * new evidence, updated financials, new events, gap closures.
 * Recency only — no scoring or ranking.
 */

import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { ArrowUpRight } from "lucide-react"
import { useDiscovery } from "../useDiscovery"
import { fetchTimeline, fetchResearch, fetchResearchGaps } from "../api/client"
import { formatLabel, formatIsoShort, formatTitle, formatSourceName, formatConfidence } from "../lib/format"
import { LoadingState, EmptyState, ErrorState } from "../components/States"
import { Tag } from "../components/ui"

interface ChangeRow {
  key: string
  symbol: string
  date: string | null
  title: string
  category: string
  source: string | null
}

export default function ResearchChangesPage() {
  const { items, loading: discoveryLoading } = useDiscovery()
  const [changes, setChanges] = useState<ChangeRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const tracked = useMemo(() => items.filter((i) => i.research_available), [items])

  useEffect(() => {
    if (tracked.length === 0) return undefined
    let cancelled = false

    async function run() {
      setLoading(true)
      const symbols = tracked.map((i) => i.symbol)

      try {
        const [timelineResults, researchResults, gapResults] = await Promise.all([
          Promise.allSettled(symbols.map((s) => fetchTimeline(s))),
          Promise.allSettled(symbols.map((s) => fetchResearch(s))),
          Promise.allSettled(symbols.map((s) => fetchResearchGaps(s))),
        ])

        if (cancelled) return

        const rows: ChangeRow[] = []

        for (const result of timelineResults) {
          if (result.status !== "fulfilled") continue
          for (const entry of result.value.timeline.entries) {
            rows.push({
              key: entry.entry_id,
              symbol: entry.symbol,
              date: entry.timeline_at ?? entry.published_at ?? entry.effective_at,
              title: formatTitle(entry.title, entry.symbol),
              category: entry.event_type ?? "Event",
              source: formatSourceName(entry.source.source_name),
            })
          }
        }

        for (const result of researchResults) {
          if (result.status !== "fulfilled") continue
          const research = result.value
          if (!research || !Array.isArray(research.signals)) continue
          for (const signal of research.signals) {
            rows.push({
              key: signal.signal_id,
              symbol: signal.symbol,
              date: signal.observation_at,
              title: formatTitle(signal.title, signal.symbol),
              category: formatLabel(signal.category),
              source: formatConfidence(signal.confidence),
            })
          }
        }

        for (const result of gapResults) {
          if (result.status !== "fulfilled") continue
          for (const gap of result.value.research_gaps?.gaps ?? []) {
            rows.push({
              key: gap.gap_id,
              symbol: gap.symbol,
              date: null,
              title: gap.description,
              category: `Gap: ${formatLabel(gap.category)}`,
              source: formatLabel(gap.status),
            })
          }
        }

        rows.sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""))
        setChanges(rows)
      } catch {
        if (!cancelled) setError("Research changes could not be loaded.")
      }

      if (!cancelled) setLoading(false)
    }

    void run()
    return () => { cancelled = true }
  }, [tracked])

  return (
    <div className="page-research-changes">
      <section className="page-hero">
        <p className="page-kicker">Research changes</p>
        <h1>Research Changes</h1>
        <p className="page-subtitle">
          Recent changes to recorded research across the tracked universe.
          New evidence, updated financials, new events, gap closures.
          Recency only — no scoring.
        </p>
      </section>

      {(discoveryLoading || loading) && (
        <LoadingState label="Loading research changes" description="Scanning per-company records…" />
      )}

      {error && (
        <ErrorState error={error} />
      )}

      {!discoveryLoading && !loading && !error && changes.length === 0 && (
        <EmptyState
          icon={ArrowUpRight}
          title="No recent changes"
          description="No recorded research changes in the current data window."
        />
      )}

      {!discoveryLoading && !loading && !error && changes.length > 0 && (
        <section className="discover-section discover-primary" aria-label="Recent changes">
          <div className="table-scroll">
            <table className="feed-table">
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Company</th>
                  <th scope="col">Change</th>
                  <th scope="col">Category</th>
                  <th scope="col">Source</th>
                </tr>
              </thead>
              <tbody>
                {changes.slice(0, 50).map((row) => (
                  <tr key={row.key}>
                    <td className="feed-date">
                      {row.date ? formatIsoShort(row.date) : "\u2014"}
                    </td>
                    <td>
                      <Link
                        className="feed-company mono"
                        to={`/companies/${encodeURIComponent(row.symbol)}`}
                      >
                        {row.symbol}
                      </Link>
                    </td>
                    <td className="feed-event" title={row.title}>
                      {formatTitle(row.title, row.symbol)}
                    </td>
                    <td>
                      <Tag text={row.category} tone="slate" />
                    </td>
                    <td>{row.source ?? "\u2014"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}
