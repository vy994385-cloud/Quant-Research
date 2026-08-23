/**
 * COMPANY EVENTS — unified events workspace.
 *
 * Consolidates company news, corporate actions and the recorded evidence
 * timeline into ONE canonical table so an event appears exactly once.
 * Rows: Date | Event | Category | Verification | Source; details expand
 * below the row. Internal identifiers stay out of this view.
 */

import { Fragment, useEffect, useMemo, useState } from "react"
import { ChevronDown, ChevronRight } from "lucide-react"
import {
  fetchCompanyNews,
  fetchCorporateActions,
} from "../api/client"
import type { ApiError } from "../api/client"
import type { CorporateActionItem, TimelineEntry } from "../api/types"
import { formatIso, formatIsoShort, formatLabel, formatSourceName, formatTitle, humanizeNarrative } from "../lib/format"
import { EmptyCopy, FilterChips } from "./ui"

type Bucket =
  | "all"
  | "financial"
  | "business"
  | "management"
  | "technology"
  | "corporate-action"
  | "industry"
  | "market"

const BUCKET_ORDER: Array<{ value: Bucket; label: string }> = [
  { value: "all", label: "All" },
  { value: "financial", label: "Financial" },
  { value: "business", label: "Business" },
  { value: "management", label: "Management" },
  { value: "technology", label: "Technology" },
  { value: "corporate-action", label: "Corporate Action" },
  { value: "industry", label: "Industry" },
  { value: "market", label: "Market" },
]

function bucketize(category: string): Exclude<Bucket, "all"> {
  const c = category.toUpperCase()
  if (/\bFINANCIAL_DISCLOSURE\b|EARNINGS|RESULT|REVENUE|PROFIT|DIVIDEND|GUIDANCE|BALANCE|CASH_FLOW/.test(c)) {
    return "financial"
  }
  if (/MANAGEMENT_STATEMENT|\bCEO\b|\bCFO\b|BOARD|LEADERSHIP|EXECUT/.test(c)) return "management"
  if (/TECHNOLOGY|\bAI\b|DIGITAL|INNOVATION|R&D|SEMICONDUCTOR|PLATFORM/.test(c)) return "technology"
  if (/INDUSTRY|SECTOR|REGULAT|POLICY|COMPLIANCE/.test(c)) return "industry"
  if (/\bMARKET\b|MACRO|ECONOM|MONSOON|DEMAND_ENV/.test(c)) return "market"
  return "business"
}

interface UnifiedEvent {
  key: string
  date: string | null
  title: string
  description: string
  bucket: Exclude<Bucket, "all">
  typeLabel: string
  verification: string | null
  sourceName: string | null
  sourceUrl: string | null
  publishedAt: string | null
  availableAt: string | null
  effectiveAt: string | null
}

/** One event appears once: later pools never override earlier ones. */
function dedupe(events: UnifiedEvent[]): UnifiedEvent[] {
  const seen = new Set<string>()
  return events.filter((event) => {
    const day = (event.date ?? "").slice(0, 10)
    const key = `${day}|${event.title.toLowerCase().replace(/\s+/g, " ").trim()}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function timelineToEvents(entries: TimelineEntry[]): UnifiedEvent[] {
  return entries.map((entry) => ({
    key: entry.entry_id,
    date: entry.timeline_at ?? entry.published_at ?? entry.effective_at,
    title: entry.title,
    description: entry.description,
    bucket: bucketize(entry.intel_category),
    typeLabel: formatLabel(entry.intel_category),
    verification: entry.verification_status || null,
    sourceName: formatSourceName(entry.source.source_name),
    sourceUrl: entry.source.source_url,
    publishedAt: entry.published_at,
    availableAt: entry.available_at,
    effectiveAt: entry.effective_at,
  }))
}

function actionsToEvents(items: CorporateActionItem[]): UnifiedEvent[] {
  return items.map((item) => {
    const details = [
      item.description,
      item.value !== null ? `Reported value: ${item.value}` : null,
      item.ratio !== null ? `Reported ratio: ${item.ratio}` : null,
    ]
      .filter((part): part is string => Boolean(part))
      .join(" · ")
    return {
      key: item.action_id,
      date: item.announcement_date ?? item.effective_date ?? item.record_date,
      title: item.title,
      description: details,
      bucket: "corporate-action" as const,
      typeLabel: formatLabel(item.action_type),
      verification: null,
      sourceName: formatSourceName(item.source_name),
      sourceUrl: item.source_url,
      publishedAt: item.published_at,
      availableAt: item.available_at,
      effectiveAt: item.effective_date,
    }
  })
}

export default function CompanyEventsPanel({
  symbol,
  asOf,
  timelineEntries,
}: {
  symbol: string
  asOf?: string
  timelineEntries: TimelineEntry[]
}) {
  const [newsItems, setNewsItems] = useState<Awaited<
    ReturnType<typeof fetchCompanyNews>
  >["news"]>(null)
  const [actions, setActions] = useState<CorporateActionItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | string | null>(null)
  const [bucket, setBucket] = useState<Bucket>("all")
  const [expanded, setExpanded] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function run() {
      setLoading(true)
      setError(null)
      try {
        const [newsResult, actionResult] = await Promise.allSettled([
          fetchCompanyNews(symbol, asOf),
          fetchCorporateActions(symbol, asOf),
        ])
        if (cancelled) return
        setNewsItems(newsResult.status === "fulfilled" ? newsResult.value.news : null)
        setActions(
          actionResult.status === "fulfilled"
            ? (actionResult.value.corporate_actions?.items ?? [])
            : [],
        )
        if (
          newsResult.status === "rejected" &&
          actionResult.status === "rejected"
        ) {
          const first = newsResult.reason
          setError(first instanceof Error ? first.message : String(first))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [symbol, asOf])

  const events = useMemo(() => {
    // Pool priority: timeline entries first (they carry verification), then
    // corporate actions, then news; dedupe keeps the first occurrence.
    const pooled = [
      ...timelineToEvents(timelineEntries),
      ...actionsToEvents(actions),
      ...(newsItems?.items ?? []).map((item) => ({
        key: item.news_id,
        date: item.published_at,
        title: item.headline,
        description: item.summary,
        bucket: bucketize(item.category),
        typeLabel: formatLabel(item.category),
        verification: null,
        sourceName: formatSourceName(item.source_name),
        sourceUrl: item.source_url || null,
        publishedAt: item.published_at,
        availableAt: item.available_at,
        effectiveAt: item.event_date,
      })),
    ]
    return dedupe(pooled).sort(
      (a, b) => (b.date ?? "").localeCompare(a.date ?? ""),
    )
  }, [timelineEntries, actions, newsItems])

  const countFor = (target: Bucket) =>
    target === "all"
      ? events.length
      : events.filter((event) => event.bucket === target).length

  const visible =
    bucket === "all" ? events : events.filter((event) => event.bucket === bucket)

  return (
    <div className="section-anchor" id="company-events">
      <div className="panel-head">
        <div>
          <h3>Events</h3>
          <span>
            News, disclosures and corporate actions in one record — each event appears once
          </span>
        </div>
      </div>

      <FilterChips
        ariaLabel="Filter events by category"
        options={BUCKET_ORDER.map((option) => ({
          ...option,
          count: countFor(option.value),
        }))}
        value={bucket}
        onChange={setBucket}
      />

      {error !== null ? (
        <EmptyCopy text={`Events could not be loaded: ${typeof error === "object" && error !== null && "message" in error ? error.message : error}`} />
      ) : loading ? (
        <p className="panel-loading">Loading events…</p>
      ) : visible.length === 0 ? (
        <EmptyCopy
          text={
            bucket === "all"
              ? "No events are recorded for this company."
              : "No events match the selected category."
          }
        />
      ) : (
        <div className="table-scroll">
          <table className="events-table">
            <caption className="visually-hidden">
              Company events: date, event, category, verification, source
            </caption>
            <thead>
              <tr>
                <th scope="col">Date</th>
                <th scope="col">Event</th>
                <th scope="col">Category</th>
                <th scope="col">Verification</th>
                <th scope="col">Source</th>
                <th scope="col" aria-label="Details" />
              </tr>
            </thead>
            <tbody>
              {visible.map((event) => {
                const open = expanded === event.key
                return (
                  <Fragment key={event.key}>
                    <tr className={open ? "event-row expanded" : "event-row"}>
                      <td className="events-date">
                        {event.date ? formatIsoShort(event.date) : "\u2014"}
                      </td>
                      <td className="events-title">{formatTitle(event.title, symbol)}</td>
                      <td>
                        <span className="feed-type">{event.typeLabel}</span>
                      </td>
                      <td>
                        {event.verification ? (
                          <span
                            className={
                              event.verification === "CONFIRMED"
                                ? "tag blue"
                                : "tag slate"
                            }
                          >
                            {formatLabel(event.verification)}
                          </span>
                        ) : (
                          "\u2014"
                        )}
                      </td>
                      <td className="events-source">{event.sourceName ?? "\u2014"}</td>
                      <td>
                        <button
                          type="button"
                          className="row-expand-btn"
                          onClick={() => setExpanded(open ? null : event.key)}
                          aria-expanded={open}
                          aria-controls={`event-detail-${event.key}`}
                          aria-label={open ? "Hide details" : "Show details"}
                        >
                          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        </button>
                      </td>
                    </tr>
                    {open && (
                      <tr className="event-detail-row">
                        <td colSpan={6} id={`event-detail-${event.key}`}>
                          <div className="event-detail">
                            {event.description && <p>{humanizeNarrative(event.description)}</p>}
                            <dl className="data-field-grid">
                              {event.publishedAt && (
                                <div className="data-field">
                                  <dt className="data-field-label">Published</dt>
                                  <dd className="data-field-value">{formatIso(event.publishedAt)}</dd>
                                </div>
                              )}
                              {event.availableAt && (
                                <div className="data-field">
                                  <dt className="data-field-label">Available</dt>
                                  <dd className="data-field-value">{formatIso(event.availableAt)}</dd>
                                </div>
                              )}
                              {event.effectiveAt && (
                                <div className="data-field">
                                  <dt className="data-field-label">Effective</dt>
                                  <dd className="data-field-value">{formatIso(event.effectiveAt)}</dd>
                                </div>
                              )}
                              <div className="data-field">
                                <dt className="data-field-label">Source</dt>
                                <dd className="data-field-value">
                                  {event.sourceUrl ? (
                                    <a href={event.sourceUrl} target="_blank" rel="noreferrer">
                                      {event.sourceName ?? "Source"}
                                    </a>
                                  ) : (
                                    (event.sourceName ?? "\u2014")
                                  )}
                                </dd>
                              </div>
                            </dl>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {newsItems?.notes?.length ? (
        <ul className="panel-notes">
          {newsItems.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
