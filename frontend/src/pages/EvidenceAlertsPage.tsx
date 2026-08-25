/**
 * EVIDENCE ALERTS — research-quality alerts from recorded evidence.
 *
 * Shows evidence items that require attention: new high-confidence signals,
 * gap changes, anomalies, and significant recorded events.
 * No fake alerts — only real recorded data.
 */

import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { Shield } from "lucide-react"
import { useDiscovery } from "../useDiscovery"
import { fetchResearch, fetchResearchGaps } from "../api/client"
import { formatLabel, formatConfidence, formatTitle } from "../lib/format"
import { LoadingState, EmptyState, ErrorState } from "../components/States"
import { Tag } from "../components/ui"

interface AlertRow {
  key: string
  symbol: string
  date: string | null
  title: string
  category: string
  severity: "info" | "attention" | "warning"
  source: string | null
}

export default function EvidenceAlertsPage() {
  const { items, loading: discoveryLoading } = useDiscovery()
  const [alerts, setAlerts] = useState<AlertRow[]>([])
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
        const [researchResults, gapResults] = await Promise.all([
          Promise.allSettled(symbols.map((s) => fetchResearch(s))),
          Promise.allSettled(symbols.map((s) => fetchResearchGaps(s))),
        ])

        if (cancelled) return

        const rows: AlertRow[] = []

        for (const result of researchResults) {
          if (result.status !== "fulfilled") continue
          const research = result.value
          if (!research || !Array.isArray(research.signals)) continue

          for (const signal of research.signals) {
            const severity: AlertRow["severity"] =
              signal.confidence === "HIGH" ? "attention" :
              signal.confidence === "MEDIUM" ? "info" : "info"

            rows.push({
              key: `${signal.symbol}-${signal.signal_id}`,
              symbol: signal.symbol,
              date: signal.observation_at,
              title: formatTitle(signal.title, signal.symbol),
              category: formatLabel(signal.category),
              severity,
              source: formatConfidence(signal.confidence),
            })
          }
        }

        for (const result of gapResults) {
          if (result.status !== "fulfilled") continue
          for (const gap of result.value.research_gaps?.gaps ?? []) {
            if (gap.status === "MISSING") {
              rows.push({
                key: `${gap.symbol}-${gap.gap_id}`,
                symbol: gap.symbol,
                date: null,
                title: gap.description,
                category: `Coverage gap: ${formatLabel(gap.category)}`,
                severity: "warning",
                source: formatLabel(gap.status),
              })
            }
          }
        }

        rows.sort((a, b) => {
          const sevOrder = { warning: 0, attention: 1, info: 2 }
          return sevOrder[a.severity] - sevOrder[b.severity]
        })

        setAlerts(rows)
      } catch {
        if (!cancelled) setError("Evidence alerts could not be loaded.")
      }

      if (!cancelled) setLoading(false)
    }

    void run()
    return () => { cancelled = true }
  }, [tracked])

  return (
    <div className="page-evidence-alerts">
      <section className="page-hero">
        <p className="page-kicker">Evidence alerts</p>
        <h1>Evidence Alerts</h1>
        <p className="page-subtitle">
          Research-quality alerts from recorded evidence.
          New high-confidence signals, coverage gaps, and significant observations.
          Only real recorded data — no synthetic alerts.
        </p>
      </section>

      {(discoveryLoading || loading) && (
        <LoadingState label="Loading evidence alerts" description="Scanning per-company evidence…" />
      )}

      {error && (
        <ErrorState error={error} />
      )}

      {!discoveryLoading && !loading && !error && alerts.length === 0 && (
        <EmptyState
          icon={Shield}
          title="No evidence alerts"
          description="No high-priority evidence items require attention at this time."
        />
      )}

      {!discoveryLoading && !loading && !error && alerts.length > 0 && (
        <section className="discover-section discover-primary" aria-label="Evidence alerts">
          <div className="table-scroll">
            <table className="feed-table">
              <thead>
                <tr>
                  <th scope="col">Priority</th>
                  <th scope="col">Company</th>
                  <th scope="col">Alert</th>
                  <th scope="col">Category</th>
                  <th scope="col">Source</th>
                </tr>
              </thead>
              <tbody>
                {alerts.slice(0, 30).map((row) => (
                  <tr key={row.key}>
                    <td>
                      <Tag
                        text={row.severity === "warning" ? "Warning" : row.severity === "attention" ? "Attention" : "Info"}
                        tone={row.severity === "warning" ? "amber" : row.severity === "attention" ? "blue" : "slate"}
                      />
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
