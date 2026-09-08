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
import { fetchCalendar } from "../api/client"
import { formatIsoShort, formatLabel, formatTitle } from "../lib/format"
import { LoadingState, EmptyState, ErrorState } from "../components/States"
import { Tag } from "../components/ui"

/** Recorded archive window mirrored from the backend (DEFAULT_AS_OF). */
const CALENDAR_RANGE_FROM = "2025-01-01T00:00:00Z"
const CALENDAR_RANGE_TO = "2026-12-31T23:59:59Z"

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
  const [events, setEvents] = useState<CalendarRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function run() {
      setLoading(true)
      try {
        const result = await fetchCalendar(
          "all",
          CALENDAR_RANGE_FROM,
          CALENDAR_RANGE_TO,
        )
        if (cancelled) return

        const rows: CalendarRow[] = result.events.map((event) => ({
          key: event.event_id,
          symbol: event.symbol,
          date: event.event_date,
          title: formatTitle(event.title, event.symbol),
          category: event.category ?? "Event",
          source: event.source ?? null,
          past: event.state !== "ANNOUNCED",
        }))

        rows.sort((a, b) => a.date.localeCompare(b.date))
        setEvents(rows)
      } catch {
        if (!cancelled) setError("Calendar could not be loaded.")
      }

      if (!cancelled) setLoading(false)
    }

    void run()
    return () => { cancelled = true }
  }, [])

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

      {loading && (
        <LoadingState label="Loading calendar" description="Reading the recorded-event calendar…" />
      )}

      {error && (
        <ErrorState error={error} />
      )}

      {!loading && !error && events.length === 0 && (
        <EmptyState
          icon={Calendar}
          title="No recorded events"
          description="No events found in the recorded data window."
        />
      )}

      {!loading && !error && events.length > 0 && (
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
                          <Tag text={formatLabel(row.category ?? "Event")} tone="slate" />
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
                          <Tag text={formatLabel(row.category ?? "Event")} tone="slate" />
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
