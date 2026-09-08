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
import { fetchResearchChanges } from "../api/client"
import { formatLabel, formatIsoShort, formatTitle } from "../lib/format"
import { LoadingState, EmptyState, ErrorState } from "../components/States"
import { Tag } from "../components/ui"

/**
 * Recorded-window comparison. The archive is a single snapshot as of
 * DEFAULT_AS_OF (2026-08-10T12:00:00Z); the baseline opens the recorded
 * window (earlier baselines return research_data_unavailable, so 2026-
 * 01-01 is the earliest universally-usable window start). Advance both
 * when future data is appended.
 */
const CHANGES_BASELINE = "2026-01-01T00:00:00Z"
const CHANGES_CURRENT = "2026-08-10T12:00:00Z"

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
        const results = await Promise.allSettled(
          symbols.map((s) => fetchResearchChanges(s, CHANGES_BASELINE, CHANGES_CURRENT)),
        )

        if (cancelled) return

        const rows: ChangeRow[] = []

        for (const result of results) {
          if (result.status !== "fulfilled") continue
          for (const change of result.value.changes) {
            rows.push({
              key: change.change_id,
              symbol: change.symbol,
              date: change.effective_at ?? change.as_of,
              title: formatTitle(change.title, change.symbol),
              category: formatLabel(change.change_type),
              source: change.source ?? null,
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

  const visible = changes.slice(0, 100)

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
        <LoadingState label="Loading research changes" description="Comparing recorded windows per company…" />
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
                {visible.map((row) => (
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
