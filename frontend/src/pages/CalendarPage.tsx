/**
 * CALENDAR — research calendar of recorded events.
 *
 * Shows upcoming and past recorded events chronologically.
 * Financial results, corporate actions, and significant dates.
 * Recorded only — no predictions or forecasts.
 */

import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { Calendar } from "lucide-react"
import { useDiscovery } from "../useDiscovery"
import { fetchTimeline, fetchCorporateActions } from "../api/client"
import { formatLabel, formatIsoShort, formatTitle, formatSourceName } from "../lib/format"
import { LoadingState, EmptyState, ErrorState } from "../components/States"
import { Tag } from "../components/ui"

interface CalendarRow {
  key: string
  symbol: string
  date: string
  title: string
  category: string
  source: string | null
  past: boolean
}

export default function CalendarPage() {
  const { items, loading: discoveryLoading } = useDiscovery()
  const [events, setEvents] = useState<CalendarRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const tracked = useMemo(() => items.filter((i) => i.research_available), [items])

  useEffect(() => {
    if (tracked.length === 0) return undefined
    let cancelled = false

    async function run() {
      setLoading(true)
      const symbols = tracked.map((i) => i.symbol)
      const now = new Date().toISOString().slice(0, 10)

      try {
        const [timelineResults, actionResults] = await Promise.all([
          Promise.allSettled(symbols.map((s) => fetchTimeline(s))),
          Promise.allSettled(symbols.map((s) => fetchCorporateActions(s))),
        ])

        if (cancelled) return

        const rows: CalendarRow[] = []

        for (const result of timelineResults) {
          if (result.status !== "fulfilled") continue
          for (const entry of result.value.timeline.entries) {
            const date = entry.timeline_at ?? entry.published_at ?? entry.effective_at
            if (!date) continue
            rows.push({
              key: entry.entry_id,
              symbol: entry.symbol,
              date,
              title: formatTitle(entry.title, entry.symbol),
              category: entry.event_type ?? "Event",
              source: formatSourceName(entry.source.source_name),
              past: date.slice(0, 10) <= now,
            })
          }
        }

        for (const result of actionResults) {
          if (result.status !== "fulfilled" || !result.value.corporate_actions) continue
          for (const item of result.value.corporate_actions.items) {
            const date = item.announcement_date
            if (!date) continue
            rows.push({
              key: item.action_id,
              symbol: item.symbol,
              date,
              title: formatTitle(item.title, item.symbol),
              category: item.action_type ?? "Corporate action",
              source: formatSourceName(item.source_name),
              past: date.slice(0, 10) <= now,
            })
          }
        }

        rows.sort((a, b) => a.date.localeCompare(b.date))
        setEvents(rows)
      } catch {
        if (!cancelled) setError("Calendar could not be loaded.")
      }

      if (!cancelled) setLoading(false)
    }

    void run()
    return () => { cancelled = true }
  }, [tracked])

  const pastEvents = useMemo(() => events.filter((e) => e.past), [events])
  const upcomingEvents = useMemo(() => events.filter((e) => !e.past), [events])

  return (
    <div className="page-calendar">
      <section className="page-hero">
        <p className="page-kicker">Calendar</p>
        <h1>Research Calendar</h1>
        <p className="page-subtitle">
          Recorded events and corporate actions chronologically ordered.
          Financial results, announcements, and significant dates.
          Recorded only — no forecasts.
        </p>
      </section>

      {(discoveryLoading || loading) && (
        <LoadingState label="Loading calendar" description="Scanning per-company timelines…" />
      )}

      {error && (
        <ErrorState error={error} />
      )}

      {!discoveryLoading && !loading && !error && events.length === 0 && (
        <EmptyState
          icon={Calendar}
          title="No recorded events"
          description="No events found in the current data window."
        />
      )}

      {!discoveryLoading && !loading && !error && events.length > 0 && (
        <>
          {upcomingEvents.length > 0 && (
            <section className="discover-section discover-primary" aria-label="Upcoming events">
              <Tag text={`${upcomingEvents.length} upcoming`} tone="blue" />
              <div className="table-scroll">
                <table className="feed-table">
                  <thead>
                    <tr>
                      <th scope="col">Date</th>
                      <th scope="col">Company</th>
                      <th scope="col">Event</th>
                      <th scope="col">Category</th>
                      <th scope="col">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {upcomingEvents.map((row) => (
                      <tr key={row.key}>
                        <td className="feed-date">{formatIsoShort(row.date)}</td>
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
                          <Tag text={formatLabel(row.category)} tone="slate" />
                        </td>
                        <td>{row.source ?? "\u2014"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {pastEvents.length > 0 && (
            <section className="discover-section discover-compact" aria-label="Past events">
              <Tag text={`${pastEvents.length} past`} tone="slate" />
              <div className="table-scroll">
                <table className="feed-table">
                  <thead>
                    <tr>
                      <th scope="col">Date</th>
                      <th scope="col">Company</th>
                      <th scope="col">Event</th>
                      <th scope="col">Category</th>
                      <th scope="col">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pastEvents.slice(0, 50).map((row) => (
                      <tr key={row.key}>
                        <td className="feed-date">{formatIsoShort(row.date)}</td>
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
                          <Tag text={formatLabel(row.category)} tone="slate" />
                        </td>
                        <td>{row.source ?? "\u2014"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
