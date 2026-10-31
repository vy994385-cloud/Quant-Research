import "./DiscoverLanding.css"
/**
 * RESEARCH HOME — the daily entry point of the evidence-first research terminal.
 *
 * Layout order:
 *   1. Research context — universe overview with freshness
 *   2. Global research search — one search across the tracked universe
 *   3. What changed — recent changes summary
 *   4. Research activity — everything recorded, recency-ordered
 *      Financial disclosures · Company developments · Technology · Corporate actions
 *   5. Coverage changes — gap status changes across the universe
 *   6. Recently researched — your latest company visits
 *   7. Themes & Industries — quick navigation to research domains
 *   8. Research gaps — what's missing across the universe
 *   9. Company index — the full tracked universe
 *
 * Recency only — nothing here is ranked or scored.
 */

import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { Activity, ArrowRight, BarChart3, FileSearch, Filter, GitCompareArrows, Search, XCircle } from "lucide-react"
import {
  fetchCompanyNews,
  fetchCorporateActions,
  fetchResearch,
  fetchResearchGaps,
  fetchTimeline,
} from "../api/client"
import type {
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
import { getRecentSymbols } from "../lib/localResearch"
import { EmptyCopy, SectionDivider, SegmentedControl, Tag } from "../components/ui"
import type { Tone } from "../lib/signal"

/** Per-kind cap inside the unified window so one ingestion batch cannot
 * crowd out the rest of the universe's activity. */
const KIND_CAP = 8
/** Per-company and per-company-kind caps so a single company's filing run
 * cannot dominate the window even within its kind budget. */
const COMPANY_CAP = 6
const COMPANY_KIND_CAP = 4
const SECTION_CAP = 12

type ActivityKind = "Development" | "Corporate action" | "News" | "Observation"

interface ActivityRow {
  key: string
  symbol: string
  date: string | null
  title: string
  detail?: string
  kind: ActivityKind
  /** Source name for recorded events; reliability band for observations. */
  origin: string | null
  /** Verification status for events; category for observations. */
  qualifier: string | null
}

function entryDate(entry: TimelineEntry): string | null {
  return entry.timeline_at ?? entry.published_at ?? entry.effective_at
}

function companyCell(symbol: string): React.ReactNode {
  return (
    <Link className="feed-company mono" to={`/companies/${encodeURIComponent(symbol)}`}>
      {symbol}
    </Link>
  )
}

function verificationTag(status: string | null): React.ReactNode {
  if (!status) return "\u2014"
  const tone: Tone = status === "CONFIRMED" ? "blue" : "slate"
  return <Tag text={formatLabel(status)} tone={tone} />
}

export default function DiscoverPage() {
  const { items, loading: discoveryLoading, error: discoveryError } = useDiscovery()
  const [query, setQuery] = useState("")
  const [kind, setKind] = useState<"all" | ActivityKind>("all")
  const [days, setDays] = useState<"all" | "7" | "30">("all")
  // Reference point for the time-window filter, captured when feed data
  // loads (never during render) so filtering stays pure and stable.
  const [now, setNow] = useState<number | null>(null)

  const [activity, setActivity] = useState<ActivityRow[]>([])
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

      /* Pool every recorded item into ONE activity stream. The same event can
       * surface through several feeds; a fingerprint keeps it once. Per-kind /
       * per-company caps keep a single ingestion batch from filling the window;
       * counts stay honest. */
      interface Pooled extends ActivityRow {
        fingerprint: string
      }
      const pooled: Pooled[] = []

      for (const result of timelines) {
        if (result.status !== "fulfilled") continue
        for (const entry of result.value.timeline.entries) {
          const title = formatTitle(entry.title, entry.symbol)
          pooled.push({
            key: entry.entry_id,
            fingerprint: `${entry.symbol}|${(entryDate(entry) ?? "").slice(0, 10)}|${title.toLowerCase()}`,
            symbol: entry.symbol,
            date: entryDate(entry),
            title,
            kind: "Development",
            origin: formatSourceName(entry.source.source_name),
            qualifier: entry.verification_status || null,
          })
        }
      }

      for (const result of actionResults) {
        if (result.status !== "fulfilled" || !result.value.corporate_actions) continue
        for (const item of result.value.corporate_actions.items) {
          const title = formatTitle(item.title, item.symbol)
          pooled.push({
            key: item.action_id,
            fingerprint: `${item.symbol}|${(item.announcement_date ?? "").slice(0, 10)}|${title.toLowerCase()}`,
            symbol: item.symbol,
            date: item.announcement_date,
            title,
            detail:
              item.action_type === "DIVIDEND" && item.value !== null
                ? `Per-share value as reported: ${formatLabel(String(item.value))}`
                : undefined,
            kind: "Corporate action",
            origin: formatSourceName(item.source_name),
            qualifier: null,
          })
        }
      }

      for (const result of newsResults) {
        if (result.status !== "fulfilled" || !result.value.news) continue
        for (const item of result.value.news.items) {
          pooled.push({
            key: item.news_id,
            fingerprint: `${item.symbol}|${(item.published_at ?? "").slice(0, 10)}|${item.headline.toLowerCase()}`,
            symbol: item.symbol,
            date: item.published_at,
            title: item.headline,
            kind: "News",
            origin: formatSourceName(item.source_name),
            qualifier: null,
          })
        }
      }

      const techPooled: Array<{ key: string; symbol: string; group: string; text: string }> = []
      for (const result of researches) {
        if (result.status !== "fulfilled") continue
        const research = result.value
        // A malformed research payload contributes nothing to the stream
        // rather than breaking discovery for every other company.
        if (!research || !Array.isArray(research.signals)) continue
        for (const signal of research.signals) {
          pooled.push({
            key: signal.signal_id,
            fingerprint: `${signal.symbol}|signal|${signal.signal_id}`,
            symbol: signal.symbol,
            date: signal.observation_at,
            title: formatTitle(signal.title, signal.symbol),
            kind: "Observation",
            origin: formatConfidence(signal.confidence),
            qualifier: formatLabel(signal.category),
          })
        }
        const techSections: Array<[string, typeof research.intelligence.innovation]> = research.intelligence
          ? [
              ["Innovation", research.intelligence.innovation],
              ["Future technology", research.intelligence.future_technology],
            ]
          : []
        for (const [group, section] of techSections) {
          if (!section || !research.company) continue
          for (const text of section.observations) {
            techPooled.push({
              key: `${research.company.symbol}-${group}-${text}`,
              symbol: research.company.symbol,
              group,
              text,
            })
          }
        }
      }
      setTechActivity(techPooled)

      // Dedupe + budget, then newest first.
      const seen = new Set<string>()
      const perKind = new Map<ActivityKind, number>()
      const perCompany = new Map<string, number>()
      const perCompanyKind = new Map<string, number>()
      const picked: ActivityRow[] = []
      pooled.sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""))
      for (const row of pooled) {
        if (seen.has(row.fingerprint)) continue
        if ((perKind.get(row.kind) ?? 0) >= KIND_CAP) continue
        if ((perCompany.get(row.symbol) ?? 0) >= COMPANY_CAP) continue
        const companyKindKey = `${row.symbol}|${row.kind}`
        if ((perCompanyKind.get(companyKindKey) ?? 0) >= COMPANY_KIND_CAP) continue
        seen.add(row.fingerprint)
        perKind.set(row.kind, (perKind.get(row.kind) ?? 0) + 1)
        perCompany.set(row.symbol, (perCompany.get(row.symbol) ?? 0) + 1)
        perCompanyKind.set(companyKindKey, (perCompanyKind.get(companyKindKey) ?? 0) + 1)
        picked.push({
          key: row.key,
          symbol: row.symbol,
          date: row.date,
          title: row.title,
          detail: row.detail,
          kind: row.kind,
          origin: row.origin,
          qualifier: row.qualifier,
        })
      }
      setActivity(picked)

      const gapPooled: ResearchGap[] = []
      for (const result of gapResults) {
        if (result.status === "fulfilled" && result.value.research_gaps) {
          gapPooled.push(...result.value.research_gaps.gaps)
        }
      }
      setGaps(gapPooled)
      setNow(Date.now())
      setFeedsLoading(false)
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [tracked])

  /* ── Derived views ──────────────────────────────────────────── */

  const q = query.trim().toLowerCase()
  const matchedCompanies = useMemo(() => {
    if (!q) return []
    return items.filter(
      (item) =>
        item.symbol.toLowerCase().includes(q) ||
        (item.company_name ?? "").toLowerCase().includes(q) ||
        item.sector.toLowerCase().includes(q),
    )
  }, [items, q])

  // Use the actual tracked universe for quick starts; never imply these are
  // ranked or recommended companies.
  const suggestedCompanies = useMemo(() => tracked.slice(0, 4), [tracked])

  const sectorActivity = useMemo(() => {
    const counts = new Map<string, number>()
    for (const item of items) counts.set(item.sector, (counts.get(item.sector) ?? 0) + 1)
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [items])

  const stream = useMemo(() => {
    let rows = activity
    if (kind !== "all") rows = rows.filter((row) => row.kind === kind)
    if (days !== "all" && now !== null) {
      const cutoff = now - Number(days) * 24 * 60 * 60 * 1000
      rows = rows.filter((row) => row.date !== null && new Date(row.date).getTime() >= cutoff)
    }
    return rows
  }, [activity, kind, days, now])

  const disclosures = useMemo(
    () =>
      activity
        .filter((row) => row.kind === "Development" && /disclosure|filing|result/i.test(`${row.qualifier ?? ""} ${row.title}`))
        .slice(0, SECTION_CAP),
    [activity],
  )

  const businessDevelopments = useMemo(
    () =>
      activity
        .filter((row) => row.kind === "Development" && !/disclosure|filing|result/i.test(`${row.qualifier ?? ""} ${row.title}`))
        .slice(0, SECTION_CAP),
    [activity],
  )

  const actionsFeed = useMemo(
    () => activity.filter((row) => row.kind === "Corporate action").slice(0, SECTION_CAP),
    [activity],
  )

  const techRows = techActivity.slice(0, SECTION_CAP)

  /* Identical gaps repeat once per company; grouping collapses the repetition
   * into one row per distinct gap with affected companies as chips. */
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

  const KIND_OPTIONS: Array<{ value: "all" | ActivityKind; label: string }> = [
    { value: "all", label: "All activity" },
    { value: "Development", label: "Developments" },
    { value: "Corporate action", label: "Corporate actions" },
    { value: "News", label: "News" },
    { value: "Observation", label: "Observations" },
  ]

  const WINDOW_OPTIONS: Array<{ value: "all" | "7" | "30"; label: string }> = [
    { value: "all", label: "All time" },
    { value: "7", label: "Last 7 days" },
    { value: "30", label: "Last 30 days" },
  ]

  function renderStreamTable(rows: ActivityRow[], headers: string[]) {
    if (rows.length === 0) {
      return <EmptyCopy text="No recorded activity matches this view." />
    }
    return (
      <div className="table-scroll">
        <table className="feed-table discover-stream-table">
          <thead>
            <tr>
              {headers.map((header) => (
                <th scope="col" key={header}>{header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.kind}-${row.symbol}-${row.key}`}>
                <td className="feed-date">
                  {row.date ? formatIsoShort(row.date) : "\u2014"}
                </td>
                <td>{companyCell(row.symbol)}</td>
                <td className="feed-event" title={row.title}>
                  {formatTitle(row.title, row.symbol)}
                  {row.detail ? <small className="feed-event-detail">{row.detail}</small> : null}
                </td>
                <td>
                  <Tag text={row.kind} tone={row.kind === "Observation" ? "blue" : "slate"} />
                </td>
                <td className="feed-meta-cell">
                  <small>{row.kind === "Observation" ? "Reliability" : "Source"}</small>
                  <span>{row.origin ?? "\u2014"}</span>
                </td>
                <td className="feed-meta-cell">
                  <small>{row.kind === "Observation" ? "Basis" : "Verification"}</small>
                  <span>{row.qualifier ? row.kind === "Observation" ? row.qualifier : verificationTag(row.qualifier) : "\u2014"}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  const STREAM_HEADERS = ["Event date", "Company", "Event / observation", "Kind", "Provenance", "Validation context"]

  /* ── Render ─────────────────────────────────────────────────── */

  const recentVisits = useMemo(() => {
    const symbols = getRecentSymbols()
    if (symbols.length === 0) return []
    return symbols
      .slice(0, 8)
      .map((symbol) => items.find((i) => i.symbol === symbol))
      .filter((item): item is DiscoveryItem => item !== undefined)
  }, [items])

  return (
    <div className="page-discover discover-landing">
      {/* 1. Research Home hero — global search */}
      <section className="discover-hero discover-hero-compact" aria-label="Research Home">
        <div className="discover-hero-heading">
          <div>
            <p className="page-kicker">RESEARCH WORKSPACE</p>
            <h1>Research Home</h1>
            <p className="page-subtitle">Your tracked universe, recent activity and coverage status in one place.</p>
          </div>
          <Link className="discover-open-search" to="/discover/search">Open global search <ArrowRight size={15} aria-hidden /></Link>
        </div>
        <div className="discover-hero-search">
          <Search size={18} aria-hidden />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search a company, symbol or sector…"
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
        {q && (
          <div className="discover-hero-results" role="region" aria-label="Company search results" aria-live="polite">
            {matchedCompanies.length === 0 ? (
              <EmptyCopy text="No tracked companies match this search. Try a ticker, company name, or sector." />
            ) : (
              <ul className="discover-hero-hits">
                {matchedCompanies.slice(0, 8).map((item: DiscoveryItem) => (
                  <li key={item.symbol}>
                    <Link to={`/companies/${encodeURIComponent(item.symbol)}`}>
                      <strong>{item.company_name ?? item.symbol}</strong>
                      <span className="mono">{item.symbol}</span>
                      <span className="hit-sector">{formatLabel(item.sector)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        {!q && suggestedCompanies.length > 0 && (
          <div className="discover-search-suggestions" role="group" aria-label="Start with a tracked company">
            <span>Start with a company</span>
            {suggestedCompanies.map((item) => (
              <Link key={item.symbol} to={`/companies/${encodeURIComponent(item.symbol)}`}>
                <span className="mono">{item.symbol}</span>
                <small>{item.company_name ?? item.symbol}</small>
              </Link>
            ))}
          </div>
        )}
      </section>

      <div className="landing-section-intro landing-section-intro-compact">
        <div><span className="landing-eyebrow">YOUR RESEARCH DESK</span><h2>Latest research activity</h2><p>Recent recorded developments across the tracked universe.</p></div>
      </div>

      {discoveryLoading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading research data</strong>
          <span>Fetching the tracked universe…</span>
        </div>
      )}

      {discoveryError && (
        <div className="empty-state error" role="alert">
          <FileSearch size={28} />
          <strong>Research home unavailable</strong>
          <p>{discoveryError}</p>
        </div>
      )}

      {!discoveryLoading && !discoveryError && (
        <>
          {/* Universe summary strip */}
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
              <strong>{feedsLoading ? "…" : activity.length}</strong>
              <span>Recent items in stream</span>
            </div>
            <div className="summary-stat summary-note">
              <span>Feeds show the latest recorded evidence, not popularity.</span>
            </div>
          </section>

          {/* 2. What changed — recent changes across the universe */}
          {!feedsLoading && activity.length > 0 && (
            <section className="discover-section discover-compact" aria-label="What changed">
              <SectionDivider label="What changed" />
              <div className="what-changed-grid">
                {disclosures.length > 0 && <div className="what-changed-stat"><strong>{disclosures.length}</strong><span>Financial disclosures</span></div>}
                {businessDevelopments.length > 0 && <div className="what-changed-stat"><strong>{businessDevelopments.length}</strong><span>Business developments</span></div>}
                {actionsFeed.length > 0 && <div className="what-changed-stat"><strong>{actionsFeed.length}</strong><span>Corporate actions</span></div>}
                {techRows.length > 0 && <div className="what-changed-stat"><strong>{techRows.length}</strong><span>Technology activity</span></div>}
                {disclosures.length + businessDevelopments.length + actionsFeed.length + techRows.length === 0 && <p className="what-changed-empty">No recorded changes in the current research feed.</p>}
              </div>
            </section>
          )}

          {/* 3. Research activity stream — the visual primary */}
          <section className="discover-section discover-primary" aria-label="Research activity">
            <SectionDivider label="Research activity" />
            <div className="stream-controls">
              <SegmentedControl
                options={KIND_OPTIONS}
                value={kind}
                onChange={setKind}
                ariaLabel="Filter by activity kind"
              />
              <SegmentedControl
                options={WINDOW_OPTIONS}
                value={days}
                onChange={setDays}
                ariaLabel="Filter by time window"
                size="sm"
              />
            </div>
            {feedsLoading ? (
              <div className="loading-state compact" role="status">
                <Activity className="spin" size={18} />
                <span>Assembling feeds from per-company records…</span>
              </div>
            ) : (
              renderStreamTable(stream, STREAM_HEADERS)
            )}
          </section>

          {/* One activity stream only. Detailed category feeds live on their own pages. */}

          {/* Coverage summary belongs on the home page; the full gap register stays in Coverage & Gaps. */}
          {!feedsLoading && (
            <section className="discover-section discover-coverage-summary" aria-label="Coverage overview">
              <div className="discover-section-heading">
                <div><span className="landing-eyebrow">DATA COVERAGE</span><h2>Coverage overview</h2><p>Reported gaps across the currently tracked universe—not a measure of company quality.</p></div>
                <Link to="/research-gaps">Open Coverage &amp; Gaps <ArrowRight size={15} aria-hidden /></Link>
              </div>
              {gapGroups.length === 0 ? (
                <EmptyCopy text="No coverage gaps were returned for this universe. This does not mean every data domain is complete." />
              ) : (
                <div className="coverage-summary-grid">
                  <div><strong>{gapGroups.length}</strong><span>Research areas with reported gaps</span></div>
                  <div><strong>{new Set(gaps.map((gap) => gap.symbol)).size}</strong><span>Companies affected</span></div>
                  <div><strong>{gaps.length}</strong><span>Gap records returned</span></div>
                </div>
              )}
              <div className="coverage-area-list">
                {gapGroups.slice(0, 6).map((group) => (
                  <div className="coverage-area-row" key={group.key}>
                    <span>{group.category}</span>
                    <span className="coverage-area-companies">{group.symbols.slice(0, 6).map((symbol) => <Link key={symbol} to={`/companies/${encodeURIComponent(symbol)}`} className="mono">{symbol}</Link>)}{group.symbols.length > 6 ? <small>+{group.symbols.length - 6} more</small> : null}</span>
                    <Tag text={`${group.symbols.length} affected`} tone="amber" />
                  </div>
                ))}
              </div>
            </section>
          )}


          {/* 5. Recently researched — quick return to recent work */}
          {recentVisits.length > 0 && (
            <section className="discover-section" aria-label="Recently researched">
              <SectionDivider label="Recently researched" />
              <div className="company-table">
                {recentVisits.map((item) => (
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

          {/* Only expose research domains that have a real destination; no unsupported theme claims. */}
          <section className="discover-section" aria-label="Research tools">
            <SectionDivider label="Research tools" />
            <div className="discover-domains">
              <Link to="/industries" className="discover-domain-card">
                <BarChart3 size={16} />
                <span>Industries</span>
                <small>Browse the currently tracked sector universe</small>
              </Link>
              <Link to="/screener" className="discover-domain-card">
                <Filter size={16} />
                <span>Screener</span>
                <small>Explore supported company filters</small>
              </Link>
              <Link to="/compare" className="discover-domain-card">
                <GitCompareArrows size={16} />
                <span>Compare</span>
                <small>Compare available company research side by side</small>
              </Link>
            </div>
          </section>

          {/* Full company directory is secondary; keep the home page focused on current work. */}
          <section className="discover-section discover-index" aria-label="Company index">
            <details className="discover-index-details">
              <summary>Company index <span>{tracked.length} tracked companies</span></summary>
              <div className="company-table">
                <div className="company-table-head">
                  <span className="col-symbol">Symbol</span>
                  <span className="col-name">Company</span>
                  <span className="col-sector">Sector</span>
                </div>
                {tracked.map((item: DiscoveryItem) => (
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
              <p className="feed-more">Open the full directory in <Link to="/companies">Companies</Link>.</p>
            </details>
          </section>
        </>
      )}
    </div>
  )
}
