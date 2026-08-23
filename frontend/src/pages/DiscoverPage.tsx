/**
 * DISCOVER — full-page research discovery interface.
 *
 * Opens with one unified research-activity feed: the most recent recorded
 * items across the tracked universe (developments, news, corporate actions,
 * derived observations) in a single recency-sorted table. Supporting panels
 * follow: disclosures, technology activity, coverage gaps, industry spread.
 *
 * Every row carries date, company, event, kind, source/reliability and
 * verification where the record provides them. "Recent" means newest recorded
 * activity — never popularity. No scores, no rankings, no recommendations.
 */

import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { Activity, FileSearch, Search, XCircle } from "lucide-react"
import {
  fetchCompanyNews,
  fetchCorporateActions,
  fetchResearch,
  fetchResearchGaps,
  fetchTimeline,
} from "../api/client"
import type {
  CompanyNewsItem,
  CorporateActionItem,
  DiscoveryItem,
  ResearchGap,
  TimelineEntry,
} from "../api/types"
import { useDiscovery } from "../useDiscovery"
import {
  formatConfidence,
  formatIsoShort,
  formatLabel,
  formatSourceName,
  formatTitle,
} from "../lib/format"
import { EmptyCopy, FeedTable, SectionDivider, Tag } from "../components/ui"
import type { Tone } from "../lib/signal"

const ACTIVITY_CAP = 20
/** Per-kind cap inside the unified window so one ingestion batch cannot
 * crowd out the rest of the universe's activity. */
const KIND_CAP = 8
/** Per-company and per-company-kind caps so a single company's filing run
 * cannot dominate the window even within its kind budget. */
const COMPANY_CAP = 6
const COMPANY_KIND_CAP = 4
const FEED_CAP = 14

interface FeedRow {
  key: string
  symbol: string
  date: string | null
  event: string
  detail?: string
  type: string
  source: string | null
  verification: string | null
}

type ActivityKind = "Development" | "Corporate action" | "News" | "Observation"

interface ActivityRow {
  key: string
  symbol: string
  date: string | null
  title: string
  kind: ActivityKind
  /** Source name for recorded events; reliability band for observations. */
  origin: string | null
  /** Verification status for events; category for observations. */
  qualifier: string | null
}

function entryDate(entry: TimelineEntry): string | null {
  return entry.timeline_at ?? entry.published_at ?? entry.effective_at
}

/** One event appears once: collapse repeated titles within a company+day. */
function dedupeRows(rows: FeedRow[]): FeedRow[] {
  const seen = new Set<string>()
  return rows.filter((row) => {
    const day = (row.date ?? "").slice(0, 10)
    const key = `${row.symbol}|${day}|${row.event.toLowerCase().replace(/\s+/g, " ").trim()}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function byRecency(a: FeedRow, b: FeedRow): number {
  return (b.date ?? "").localeCompare(a.date ?? "")
}

const COMPANY_CELL_CLASS = "feed-company mono"

function companyCell(symbol: string): React.ReactNode {
  return (
    <Link className={COMPANY_CELL_CLASS} to={`/companies/${encodeURIComponent(symbol)}`}>
      {symbol}
    </Link>
  )
}

function verificationTag(status: string | null): React.ReactNode {
  if (!status) return "\u2014"
  const tone: Tone = status === "CONFIRMED" ? "blue" : "slate"
  return <Tag text={formatLabel(status)} tone={tone} />
}

function timelineRows(entries: TimelineEntry[]): FeedRow[] {
  return dedupeRows(
    entries.map((entry) => ({
      key: entry.entry_id,
      symbol: entry.symbol,
      date: entryDate(entry),
      event: entry.title,
      type: formatLabel(entry.intel_category),
      source: formatSourceName(entry.source.source_name),
      verification: entry.verification_status || null,
    })),
  ).sort(byRecency)
}

function newsRows(items: CompanyNewsItem[]): FeedRow[] {
  return items
    .map((item) => ({
      key: item.news_id,
      symbol: item.symbol,
      date: item.published_at,
      event: item.headline,
      type: formatLabel(item.category),
      source: formatSourceName(item.source_name),
      verification: null,
    }))
    .sort(byRecency)
}

function actionRows(items: CorporateActionItem[]): FeedRow[] {
  return dedupeRows(
    items.map((item) => ({
      key: item.action_id,
      symbol: item.symbol,
      date: item.announcement_date,
      event: item.title,
      detail:
        item.action_type === "DIVIDEND" && item.value !== null
          ? `Per-share value as reported: ${item.value}`
          : undefined,
      type: formatLabel(item.action_type),
      source: formatSourceName(item.source_name),
      verification: null,
    })),
  ).sort(byRecency)
}

function feedToTableRows(rows: FeedRow[]): Array<{ key: string; cells: React.ReactNode[] }> {
  return rows.map((row) => ({
    key: row.key,
    cells: [
      row.date ? <span className="feed-date">{formatIsoShort(row.date)}</span> : "\u2014",
      companyCell(row.symbol),
      <span className="feed-event" title={row.event}>
        {formatTitle(row.event, row.symbol)}
        {row.detail ? <small className="feed-event-detail">{row.detail}</small> : null}
      </span>,
      <span className="feed-type">{row.type}</span>,
      row.source ?? "\u2014",
      verificationTag(row.verification),
    ],
  }))
}

const FEED_HEADERS = ["Date", "Company", "Event", "Type", "Source", "Verification"]

const ACTIVITY_HEADERS = [
  "Date",
  "Company",
  "Event / observation",
  "Kind",
  "Source · reliability",
  "Verification · basis",
]

function kindTag(kind: ActivityKind): React.ReactNode {
  const tone: Tone = kind === "Observation" ? "blue" : "slate"
  return <Tag text={kind} tone={tone} />
}

export default function DiscoverPage() {
  const { items, loading: discoveryLoading, error: discoveryError } = useDiscovery()
  const [query, setQuery] = useState("")

  const [developments, setDevelopments] = useState<FeedRow[]>([])
  const [actions, setActions] = useState<FeedRow[]>([])
  const [news, setNews] = useState<FeedRow[]>([])
  const [observations, setObservations] = useState<
    Array<{ key: string; symbol: string; date: string; title: string; category: string; confidence: string }>
  >([])
  const [techActivity, setTechActivity] = useState<
    Array<{ key: string; symbol: string; group: string; text: string }>
  >([])
  const [gaps, setGaps] = useState<ResearchGap[]>([])
  const [feedsLoading, setFeedsLoading] = useState(true)

  const tracked = useMemo(() => items.filter((item) => item.research_available), [items])

  useEffect(() => {
    if (tracked.length === 0) return undefined
    let cancelled = false

    async function run() {
      setFeedsLoading(true)
      const symbols = tracked.map((item) => item.symbol)
      const [timelines, newsResults, actionResults, researches, gapResults] =
        await Promise.all([
          Promise.allSettled(symbols.map((symbol) => fetchTimeline(symbol))),
          Promise.allSettled(symbols.map((symbol) => fetchCompanyNews(symbol))),
          Promise.allSettled(symbols.map((symbol) => fetchCorporateActions(symbol))),
          Promise.allSettled(symbols.map((symbol) => fetchResearch(symbol))),
          Promise.allSettled(symbols.map((symbol) => fetchResearchGaps(symbol))),
        ])
      if (cancelled) return

      const pooledEntries: TimelineEntry[] = []
      for (const result of timelines) {
        if (result.status === "fulfilled") {
          pooledEntries.push(...result.value.timeline.entries)
        }
      }
      setDevelopments(timelineRows(pooledEntries))

      const pooledNews: CompanyNewsItem[] = []
      for (const result of newsResults) {
        if (result.status === "fulfilled" && result.value.news) {
          pooledNews.push(...result.value.news.items)
        }
      }
      setNews(newsRows(pooledNews))

      const pooledActions: CorporateActionItem[] = []
      for (const result of actionResults) {
        if (result.status === "fulfilled" && result.value.corporate_actions) {
          pooledActions.push(...result.value.corporate_actions.items)
        }
      }
      setActions(actionRows(pooledActions))

      const pooledObservations: Array<{
        key: string
        symbol: string
        date: string
        title: string
        category: string
        confidence: string
      }> = []
      const pooledTech: Array<{ key: string; symbol: string; group: string; text: string }> = []
      const pooledGaps: ResearchGap[] = []
      for (const result of researches) {
        if (result.status !== "fulfilled") continue
        const research = result.value
        for (const signal of research.signals) {
          pooledObservations.push({
            key: `${signal.symbol}-${signal.signal_id}`,
            symbol: signal.symbol,
            date: signal.observation_at,
            title: signal.title,
            category: formatLabel(signal.category),
            confidence: signal.confidence,
          })
        }
        const techSections: Array<[string, typeof research.intelligence.innovation]> = [
          ["Innovation", research.intelligence.innovation],
          ["Future technology", research.intelligence.future_technology],
        ]
        for (const [group, section] of techSections) {
          if (!section) continue
          for (const text of section.observations) {
            pooledTech.push({ key: `${research.company.symbol}-${group}-${text}`, symbol: research.company.symbol, group, text })
          }
        }
      }
      pooledObservations.sort((a, b) => b.date.localeCompare(a.date))
      setObservations(pooledObservations)
      setTechActivity(pooledTech)

      for (const result of gapResults) {
        if (result.status === "fulfilled" && result.value.research_gaps) {
          pooledGaps.push(...result.value.research_gaps.gaps)
        }
      }
      setGaps(pooledGaps)
      setFeedsLoading(false)
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [tracked])

  /* ── Derived views ──────────────────────────────────────────────── */

  const q = query.trim().toLowerCase()
  const matchedCompanies = useMemo(() => {
    if (!q) return tracked
    return tracked.filter(
      (item) =>
        item.symbol.toLowerCase().includes(q) ||
        (item.company_name ?? "").toLowerCase().includes(q) ||
        item.sector.toLowerCase().includes(q),
    )
  }, [tracked, q])

  const sectorActivity = useMemo(() => {
    const counts = new Map<string, number>()
    for (const item of items) {
      counts.set(item.sector, (counts.get(item.sector) ?? 0) + 1)
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [items])

  const disclosureRows = useMemo(
    () =>
      developments
        .filter((row) => row.type === "Financial Disclosure")
        .slice(0, FEED_CAP),
    [developments],
  )

  /* Unified research-activity feed: everything recorded, one recency order.
    * Per-kind, per-company and per-company-kind caps keep a single ingestion
    * batch (e.g. one filing run across the universe) from filling the whole
    * window; counts stay honest. */
  const activityFeed = useMemo<ActivityRow[]>(() => {
    const rows: ActivityRow[] = [
      ...developments.map((row) => ({
        key: row.key,
        symbol: row.symbol,
        date: row.date,
        title: row.event,
        kind: "Development" as const,
        origin: row.source,
        qualifier: row.verification,
      })),
      ...news.map((row) => ({
        key: row.key,
        symbol: row.symbol,
        date: row.date,
        title: row.event,
        kind: "News" as const,
        origin: row.source,
        qualifier: null,
      })),
      ...actions.map((row) => ({
        key: row.key,
        symbol: row.symbol,
        date: row.date,
        title: row.event,
        kind: "Corporate action" as const,
        origin: row.source,
        qualifier: row.detail ?? null,
      })),
      ...observations.map((observation) => ({
        key: observation.key,
        symbol: observation.symbol,
        date: observation.date,
        title: observation.title,
        kind: "Observation" as const,
        origin: formatConfidence(observation.confidence),
        qualifier: observation.category,
      })),
    ]
    rows.sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""))
    /* The same recorded event can surface through several feeds; keep the
     * first occurrence so the unified window never shows it twice. */
    const seen = new Set<string>()
    const perKind = new Map<ActivityKind, number>()
    const perCompany = new Map<string, number>()
    const perCompanyKind = new Map<string, number>()
    const picked: ActivityRow[] = []
    for (const row of rows) {
      if (picked.length >= ACTIVITY_CAP) break
      const fingerprint = `${row.symbol}|${row.date ?? ""}|${row.title.toLowerCase()}`
      if (seen.has(fingerprint)) continue
      if ((perKind.get(row.kind) ?? 0) >= KIND_CAP) continue
      if ((perCompany.get(row.symbol) ?? 0) >= COMPANY_CAP) continue
      const companyKindKey = `${row.symbol}|${row.kind}`
      if ((perCompanyKind.get(companyKindKey) ?? 0) >= COMPANY_KIND_CAP) continue
      seen.add(fingerprint)
      perKind.set(row.kind, (perKind.get(row.kind) ?? 0) + 1)
      perCompany.set(row.symbol, (perCompany.get(row.symbol) ?? 0) + 1)
      perCompanyKind.set(companyKindKey, (perCompanyKind.get(companyKindKey) ?? 0) + 1)
      picked.push(row)
    }
    return picked
  }, [developments, news, actions, observations])

  const techRows = techActivity.slice(0, FEED_CAP)

  /* Identical gaps repeat once per company ("No segment/business breakdown
   * available" × 6). Grouping by area + description collapses the repetition:
   * one row per distinct gap, with the affected companies as chips. */
  interface GapGroupRow {
    key: string
    category: string
    statuses: string[]
    description: string
    symbols: string[]
  }
  const gapGroups = useMemo<GapGroupRow[]>(() => {
    const map = new Map<string, GapGroupRow>()
    for (const gap of gaps) {
      const key = `${gap.category}|${gap.description}`
      let entry = map.get(key)
      if (!entry) {
        entry = {
          key,
          category: formatLabel(gap.category),
          statuses: [],
          description: gap.description,
          symbols: [],
        }
        map.set(key, entry)
      }
      if (!entry.statuses.includes(gap.status)) entry.statuses.push(gap.status)
      if (!entry.symbols.includes(gap.symbol)) entry.symbols.push(gap.symbol)
    }
    return [...map.values()].sort(
      (a, b) => b.symbols.length - a.symbols.length || a.category.localeCompare(b.category),
    )
  }, [gaps])

  const feedCount = developments.length + actions.length + news.length + observations.length

  /* ── Render ─────────────────────────────────────────────────────── */

  return (
    <div className="page-discover">
      <section className="page-hero">
        <h1>Discover</h1>
        <p className="page-subtitle">
          The most recent recorded activity across the tracked universe — developments,
          disclosures, corporate actions, observations and coverage gaps. Recency only;
          nothing here is ranked or scored.
        </p>
      </section>

      <section className="discover-search-section">
        <div className="discover-search">
          <Search size={18} aria-hidden />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search companies, symbols, or sectors…"
            aria-label="Search companies, symbols, or sectors"
          />
          {query && (
            <button
              type="button"
              className="search-clear"
              onClick={() => setQuery("")}
              aria-label="Clear search"
            >
              <XCircle size={15} />
            </button>
          )}
        </div>
      </section>

      {discoveryLoading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading discovery data</strong>
          <span>Fetching the tracked universe…</span>
        </div>
      )}

      {discoveryError && (
        <div className="empty-state error" role="alert">
          <FileSearch size={28} />
          <strong>Discovery unavailable</strong>
          <p>{discoveryError}</p>
        </div>
      )}

      {!discoveryLoading && !discoveryError && (
        <>
          <section className="home-summary" aria-label="Universe summary">
            <div className="summary-stat">
              <strong>{tracked.length}</strong>
              <span>Tracked companies</span>
            </div>
            <div className="summary-stat">
              <strong>{sectorActivity.length}</strong>
              <span>Sectors</span>
            </div>
            <div className="summary-stat">
              <strong>{feedsLoading ? "…" : feedCount}</strong>
              <span>Feed items recorded</span>
            </div>
            <div className="summary-stat summary-note">
              <span>Feeds show the latest recorded evidence, not popularity.</span>
            </div>
          </section>

          <section className="discover-feeds">
            <SectionDivider label="RESEARCH ACTIVITY ACROSS THE UNIVERSE" />

            {feedsLoading && (
              <div className="loading-state compact" role="status">
                <Activity className="spin" size={18} />
                <span>Assembling feeds from per-company records…</span>
              </div>
            )}

            {!feedsLoading && (
              <>
                <article className="feed-block">
                  <h3>
                    Unified research activity
                    <small>
                      Latest {activityFeed.length} of {feedCount} recorded items — events and
                      observations in one recency order
                    </small>
                  </h3>
                  <FeedTable
                    headers={ACTIVITY_HEADERS}
                    caption="Most recent recorded activity across tracked companies"
                    emptyText="No activity has been recorded yet."
                    rows={activityFeed.map((row) => ({
                      key: `${row.kind}-${row.key}`,
      cells: [
        row.date ? <span className="feed-date">{formatIsoShort(row.date)}</span> : "\u2014",
        companyCell(row.symbol),
        <span className="feed-event" title={row.title}>{formatTitle(row.title, row.symbol)}</span>,
                        kindTag(row.kind),
                        row.origin ?? "\u2014",
                        row.qualifier ? (
                          row.kind === "Observation" ? (
                            <span className="feed-type">{row.qualifier}</span>
                          ) : (
                            verificationTag(row.qualifier)
                          )
                        ) : (
                          "\u2014"
                        ),
                      ],
                    }))}
                  />
                  <p className="feed-more">
                    Full history in <Link to="/timeline">Events</Link> · derived records in{" "}
                    <Link to="/signals">Signals</Link>.
                  </p>
                </article>

                <SectionDivider label="SUPPORTING FEEDS" />

                {disclosureRows.length > 0 && (
                  <article className="feed-block">
                    <h3>
                      Financial disclosures
                      <small>Latest {disclosureRows.length} recorded filings</small>
                    </h3>
                    <FeedTable
                      headers={FEED_HEADERS}
                      caption="Recent financial disclosures across tracked companies"
                      emptyText="No financial disclosures have been recorded."
                      rows={feedToTableRows(disclosureRows)}
                    />
                  </article>
                )}

                {techRows.length > 0 && (
                  <article className="feed-block">
                    <h3>
                      Technology activity
                      <small>{techActivity.length} evidence-backed items</small>
                    </h3>
                    <FeedTable
                      headers={["Company", "Development", "Group"]}
                      caption="Technology activity recorded from evidence"
                      emptyText="No technology activity is supported by evidence yet."
                      rows={techRows.map((item) => ({
                        key: item.key,
                        cells: [
                          companyCell(item.symbol),
                          <span className="feed-event">{item.text}</span>,
                          <span className="feed-type">{item.group}</span>,
                        ],
                      }))}
                    />
                  </article>
                )}

                {gapGroups.length > 0 && (
                  <article className="feed-block">
                    <h3>
                      Research gaps
                      <small>
                        {gaps.length} open coverage items · {gapGroups.length} distinct
                      </small>
                    </h3>
                    <FeedTable
                      headers={["Companies", "Area", "Status", "Missing / limited information"]}
                      caption="Open research gaps across tracked companies, grouped by gap"
                      emptyText="No research gaps are currently recorded."
                      rows={gapGroups.slice(0, FEED_CAP).map((group) => ({
                        key: group.key,
                        cells: [
                          <span className="gap-company-chips">
                            {group.symbols.map((symbol) => (
                              <span key={symbol} className="gap-company-cell">
                                {companyCell(symbol)}
                              </span>
                            ))}
                          </span>,
                          <span className="feed-type">{group.category}</span>,
                          group.statuses.map((status) => (
                            <Tag key={status} text={formatLabel(status)} tone="amber" />
                          )),
                          <span className="feed-event">{group.description}</span>,
                        ],
                      }))}
                    />
                    <p className="feed-more">
                      Full control center in <Link to="/research-gaps">Coverage &amp; Gaps</Link>.
                    </p>
                  </article>
                )}
              </>
            )}
          </section>

          {matchedCompanies.length > 0 && (
            <section className="discover-companies" aria-label="Matching companies">
              <SectionDivider label={q ? "MATCHING COMPANIES" : "COMPANY INDEX"} />
              <div className="company-table">
                <div className="company-table-head">
                  <span className="col-symbol">Symbol</span>
                  <span className="col-name">Company</span>
                  <span className="col-sector">Sector</span>
                </div>
                {matchedCompanies.map((item: DiscoveryItem) => (
                  <Link
                    key={item.symbol}
                    className="company-table-row"
                    to={`/companies/${encodeURIComponent(item.symbol)}`}
                  >
                    <span className="col-symbol mono">{item.symbol}</span>
                    <span className="col-name">{item.company_name ?? item.symbol}</span>
                    <span className="col-sector">
                      <Tag text={formatLabel(item.sector)} tone="slate" />
                    </span>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {matchedCompanies.length === 0 && (
            <EmptyCopy text="No tracked companies match this search." />
          )}

          <section className="discover-industry" aria-label="Industry activity">
            <SectionDivider label="INDUSTRY COVERAGE" />
            <ul className="industry-activity-list">
              {sectorActivity.map(([sector, count]) => (
                <li key={sector}>
                  <Link to="/industries">{formatLabel(sector)}</Link>
                  <span className="chip-count">{count}</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  )
}
