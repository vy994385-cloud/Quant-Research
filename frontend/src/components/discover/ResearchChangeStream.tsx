/**
 * ResearchChangeStream — timeline of recent changes across the universe.
 *
 * Communicates: WHAT CHANGED → chronological evidence of what happened.
 *
 * Fetches timeline, news, corporate actions, and signals per tracked company.
 * Deduplicates by fingerprint, caps per kind/company, sorts by date.
 */

import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  FileSearch,
  Compass,
} from "lucide-react"
import {
  fetchCompanyNews,
  fetchCorporateActions,
  fetchResearch,
  fetchTimeline,
} from "../../api/client"
import type {
  DiscoveryItem,
  TimelineEntry,
} from "../../api/types"
import {
  formatConfidence,
  formatIsoShort,
  formatLabel,
  formatSourceName,
  formatTitle,
} from "../../lib/format"
import { EmptyCopy, Section, Tag, SegmentedControl } from "../ui"
import type { Tone } from "../../lib/signal"

const KIND_CAP = 8
const COMPANY_CAP = 6
const COMPANY_KIND_CAP = 4
const STREAM_CAP = 20

type ActivityKind = "Development" | "Corporate action" | "News" | "Observation"

interface ActivityRow {
  key: string
  symbol: string
  date: string | null
  title: string
  detail?: string
  kind: ActivityKind
  origin: string | null
  qualifier: string | null
  fingerprint: string
}

const KIND_ICON: Record<ActivityKind, React.ReactNode> = {
  Development: <FileSearch size={13} />,
  "Corporate action": <BarChart3 size={13} />,
  News: <ArrowUpRight size={13} />,
  Observation: <Compass size={13} />,
}

const KIND_OPTIONS: Array<{ value: "all" | ActivityKind; label: string }> = [
  { value: "all", label: "All" },
  { value: "Development", label: "Developments" },
  { value: "Corporate action", label: "Actions" },
  { value: "News", label: "News" },
  { value: "Observation", label: "Observations" },
]

const WINDOW_OPTIONS: Array<{ value: "all" | "7" | "30"; label: string }> = [
  { value: "all", label: "All time" },
  { value: "7", label: "7 days" },
  { value: "30", label: "30 days" },
]

function entryDate(entry: TimelineEntry): string | null {
  return entry.timeline_at ?? entry.published_at ?? entry.effective_at
}

function CompanyLink({ symbol }: { symbol: string }) {
  return (
    <Link className="rh-activity-company" to={`/companies/${encodeURIComponent(symbol)}`}>
      {symbol}
    </Link>
  )
}

function VerificationDot({ status }: { status: string | null }) {
  if (!status) return null
  const tone: Tone = status === "CONFIRMED" ? "blue" : "slate"
  return <Tag text={formatLabel(status)} tone={tone} />
}

export function ResearchChangeStream({
  tracked,
}: {
  tracked: DiscoveryItem[]
}) {
  const [activity, setActivity] = useState<ActivityRow[]>([])
  const [fetched, setFetched] = useState(false)
  const [kind, setKind] = useState<"all" | ActivityKind>("all")
  const [days, setDays] = useState<"all" | "7" | "30">("all")
  const [now, setNow] = useState<number | null>(null)

  const loading = tracked.length > 0 && !fetched

  useEffect(() => {
    if (tracked.length === 0) return undefined
    let cancelled = false

    async function run() {
      const symbols = tracked.map((i) => i.symbol)
      const [timelines, newsResults, actionResults, researches] =
        await Promise.all([
          Promise.allSettled(symbols.map((s) => fetchTimeline(s))),
          Promise.allSettled(symbols.map((s) => fetchCompanyNews(s))),
          Promise.allSettled(symbols.map((s) => fetchCorporateActions(s))),
          Promise.allSettled(symbols.map((s) => fetchResearch(s))),
        ])
      if (cancelled) return

      const pooled: ActivityRow[] = []

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
                ? `Per-share value: ${formatLabel(String(item.value))}`
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

      for (const result of researches) {
        if (result.status !== "fulfilled") continue
        const research = result.value
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
      }

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
        picked.push(row)
      }
      setActivity(picked)
      setNow(Date.now())
      setFetched(true)
    }

    void run()
    return () => { cancelled = true }
  }, [tracked])

  const stream = useMemo(() => {
    let rows = activity
    if (kind !== "all") rows = rows.filter((r) => r.kind === kind)
    if (days !== "all" && now !== null) {
      const cutoff = now - Number(days) * 24 * 60 * 60 * 1000
      rows = rows.filter((r) => r.date !== null && new Date(r.date).getTime() >= cutoff)
    }
    return rows.slice(0, STREAM_CAP)
  }, [activity, kind, days, now])

  return (
    <Section
      id="rh-changes"
      title="What changed"
      subtitle="Recent evidence across tracked companies"
      meta={
        <span className="rh-stream-count">
          {loading ? "Loading" : `${activity.length} items`}
        </span>
      }
    >
      <div className="rh-filters">
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

      {loading ? (
        <div className="loading-state compact" role="status">
          <Activity className="spin" size={16} />
          <span>Assembling activity from per-company records</span>
        </div>
      ) : stream.length === 0 ? (
        <EmptyCopy text="No recorded activity matches this view." />
      ) : (
        <div className="rh-activity-list" role="list">
          {stream.map((row) => (
            <article
              key={`${row.kind}-${row.symbol}-${row.key}`}
              className="rh-activity-item"
              role="listitem"
            >
              <div className="rh-activity-date">
                <time>{row.date ? formatIsoShort(row.date) : "\u2014"}</time>
              </div>
              <div className="rh-activity-body">
                <div className="rh-activity-title-row">
                  <CompanyLink symbol={row.symbol} />
                  <h3 className="rh-activity-title">{row.title}</h3>
                </div>
                {row.detail && (
                  <p className="rh-activity-detail">{row.detail}</p>
                )}
                <div className="rh-activity-meta">
                  <span className={`rh-activity-kind kind-${row.kind.toLowerCase().replace(" ", "-")}`}>
                    {KIND_ICON[row.kind]}
                    {row.kind}
                  </span>
                  {row.origin && (
                    <span className="rh-activity-source">{row.origin}</span>
                  )}
                  {row.qualifier && (
                    row.kind === "Observation"
                      ? <span className="rh-activity-qualifier">{row.qualifier}</span>
                      : <VerificationDot status={row.qualifier} />
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </Section>
  )
}
