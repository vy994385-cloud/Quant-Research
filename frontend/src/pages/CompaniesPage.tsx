/**
 * COMPANIES — the research directory.
 *
 * One dense, sortable table of every tracked company: symbol, name, sector,
 * research state, latest activity, and freshness, with quick access into
 * each company workspace. Filter by text or sector; sort by any column.
 *
 * Factual metadata only — no scores, no rankings.
 */

import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { Activity, ArrowUpRight, Building2, FileSearch } from "lucide-react"
import { useDiscovery } from "../useDiscovery"
import type { DiscoveryItem } from "../api/types"
import { fetchTimeline } from "../api/client"
import { formatLabel, formatIsoShort } from "../lib/format"
import { Tag } from "../components/ui"

type SortKey = "symbol" | "company" | "sector" | "research" | "freshness"
type SortDir = "asc" | "desc"

const SECTOR_ALL = "__all__"

interface CompanyMeta {
  latestDate: string | null
  eventCount: number
}

export default function CompaniesPage() {
  const { items, loading, error } = useDiscovery()
  const [query, setQuery] = useState("")
  const [sector, setSector] = useState<string>(SECTOR_ALL)
  const [sortKey, setSortKey] = useState<SortKey>("symbol")
  const [sortDir, setSortDir] = useState<SortDir>("asc")
  const [meta, setMeta] = useState<Map<string, CompanyMeta>>(new Map())
  const [metaLoading, setMetaLoading] = useState(false)
  const [now] = useState(() => Date.now())

  const sectors = useMemo(() => {
    const set = new Set<string>()
    for (const item of items) set.add(item.sector)
    return [...set].sort()
  }, [items])

  useEffect(() => {
    const tracked = items.filter((i) => i.research_available)
    if (tracked.length === 0) return undefined
    let cancelled = false

    async function run() {
      setMetaLoading(true)
      const results = await Promise.allSettled(
        tracked.map((i) => fetchTimeline(i.symbol)),
      )
      if (cancelled) return

      const next = new Map<string, CompanyMeta>()
      for (const result of results) {
        if (result.status !== "fulfilled") continue
        const { timeline } = result.value
        const entries = timeline.entries
        if (entries.length === 0) continue

        let latestDate: string | null = null
        for (const entry of entries) {
          const date = entry.timeline_at ?? entry.published_at ?? entry.effective_at
          if (date && (!latestDate || date > latestDate)) latestDate = date
        }
        next.set(timeline.company, { latestDate, eventCount: entries.length })
      }
      setMeta(next)
      setMetaLoading(false)
    }

    void run()
    return () => { cancelled = true }
  }, [items])

  function freshness(date: string | null): { label: string; tone: "green" | "amber" | "slate" } {
    if (!date) return { label: "No activity", tone: "slate" }
    const daysSince = (now - new Date(date).getTime()) / (1000 * 60 * 60 * 24)
    if (daysSince <= 7) return { label: "Fresh", tone: "green" }
    if (daysSince <= 30) return { label: "Recent", tone: "amber" }
    return { label: "Stale", tone: "slate" }
  }

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    let next = items
    if (q) {
      next = next.filter(
        (item) =>
          item.symbol.toLowerCase().includes(q) ||
          (item.company_name ?? "").toLowerCase().includes(q) ||
          item.sector.toLowerCase().includes(q),
      )
    }
    if (sector !== SECTOR_ALL) next = next.filter((item) => item.sector === sector)

    const dir = sortDir === "asc" ? 1 : -1
    return [...next].sort((a: DiscoveryItem, b: DiscoveryItem) => {
      switch (sortKey) {
        case "company":
          return dir * (a.company_name ?? a.symbol).localeCompare(b.company_name ?? b.symbol)
        case "sector":
          return dir * a.sector.localeCompare(b.sector)
        case "research":
          return dir * (Number(b.research_available) - Number(a.research_available))
        case "freshness": {
          const aDate = meta.get(a.symbol)?.latestDate ?? ""
          const bDate = meta.get(b.symbol)?.latestDate ?? ""
          return dir * bDate.localeCompare(aDate)
        }
        default:
          return dir * a.symbol.localeCompare(b.symbol)
      }
    })
  }, [items, query, sector, sortKey, sortDir, meta])

  const availableCount = rows.filter((item) => item.research_available).length

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((dir) => (dir === "asc" ? "desc" : "asc"))
    } else {
      setSortKey(key)
      setSortDir("asc")
    }
  }

  function sortIndicator(key: SortKey): string {
    if (key !== sortKey) return ""
    return sortDir === "asc" ? " ▲" : " ▼"
  }

  return (
    <div className="page-companies">
      <header className="page-hero">
        <p className="page-kicker">Research</p>
        <h1>Companies</h1>
        <p className="page-subtitle">
          The tracked research universe as one directory. Open any company to enter its
          full research workspace — financials, business, market, technology, events,
          evidence and coverage.
        </p>
        <div className="page-hero-meta">
          <dl className="directory-stats">
            <div>
              <dd>{items.length}</dd>
              <dt>Companies</dt>
            </div>
            <div>
              <dd>{items.filter((item) => item.research_available).length}</dd>
              <dt>With research</dt>
            </div>
            <div>
              <dd>{sectors.length}</dd>
              <dt>Sectors</dt>
            </div>
          </dl>
        </div>
      </header>

      {loading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading companies</strong>
        </div>
      )}

      {error && (
        <div className="empty-state error" role="alert">
          <FileSearch size={28} />
          <strong>Discovery unavailable</strong>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && (
        <>
          <section className="directory-controls" aria-label="Directory filters">
            <div className="directory-search">
              <Building2 size={15} />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Filter by name, symbol, or sector…"
                aria-label="Filter companies"
              />
            </div>
            <label className="directory-sector">
              <span>Sector</span>
              <select
                value={sector}
                onChange={(event) => setSector(event.target.value)}
                aria-label="Filter by sector"
              >
                <option value={SECTOR_ALL}>All sectors</option>
                {sectors.map((entry) => (
                  <option key={entry} value={entry}>{formatLabel(entry)}</option>
                ))}
              </select>
            </label>
          </section>

          <section className="directory-table-section">
            <div className="table-scroll">
              <table className="directory-table">
                <caption className="visually-hidden">
                  Company research directory: symbol, company, sector, research state, latest activity, freshness
                </caption>
                <thead>
                  <tr>
                    <th scope="col" aria-sort={sortKey === "symbol" ? "ascending" : undefined}>
                      <button type="button" onClick={() => toggleSort("symbol")}>
                        Symbol{sortIndicator("symbol")}
                      </button>
                    </th>
                    <th scope="col" aria-sort={sortKey === "company" ? "ascending" : undefined}>
                      <button type="button" onClick={() => toggleSort("company")}>
                        Company{sortIndicator("company")}
                      </button>
                    </th>
                    <th scope="col" aria-sort={sortKey === "sector" ? "ascending" : undefined}>
                      <button type="button" onClick={() => toggleSort("sector")}>
                        Sector{sortIndicator("sector")}
                      </button>
                    </th>
                    <th scope="col" aria-sort={sortKey === "research" ? "descending" : undefined}>
                      <button type="button" onClick={() => toggleSort("research")}>
                        Research State{sortIndicator("research")}
                      </button>
                    </th>
                    <th scope="col">
                      <span>Latest Activity</span>
                    </th>
                    <th scope="col" aria-sort={sortKey === "freshness" ? "descending" : undefined}>
                      <button type="button" onClick={() => toggleSort("freshness")}>
                        Freshness{sortIndicator("freshness")}
                      </button>
                    </th>
                    <th scope="col" aria-label="Open workspace" />
                  </tr>
                </thead>
                <tbody>
                  {rows.map((item) => {
                    const companyMeta = meta.get(item.symbol)
                    const fresh = freshness(companyMeta?.latestDate ?? null)
                    return (
                      <tr key={item.symbol} className="directory-row">
                        <td><Link className="mono directory-symbol" to={`/companies/${encodeURIComponent(item.symbol)}`}>{item.symbol}</Link></td>
                        <td>{item.company_name ?? "\u2014"}</td>
                        <td><Tag text={formatLabel(item.sector)} tone="slate" /></td>
                        <td>
                          <span className={`status-badge ${item.research_available ? "green" : "slate"}`}>
                            <span className="status-badge-dot" />
                            {item.research_available ? "Research available" : "Directory only"}
                          </span>
                        </td>
                        <td className="directory-activity">
                          {companyMeta?.latestDate ? (
                            <span className="mono">{formatIsoShort(companyMeta.latestDate)}</span>
                          ) : (
                            <span className="text-muted">—</span>
                          )}
                        </td>
                        <td>
                          <Tag text={fresh.label} tone={fresh.tone} />
                        </td>
                        <td className="directory-action">
                          <Link
                            to={`/companies/${encodeURIComponent(item.symbol)}`}
                            className="directory-open"
                            aria-label={`Open ${item.symbol} workspace`}
                          >
                            <ArrowUpRight size={13} />
                            Open
                          </Link>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            <p className="directory-footnote">
              Showing {rows.length} of {items.length} companies · {availableCount} with full
              research · companies marked "Directory only" are listed without a generated
              research snapshot yet.
              {metaLoading && " Loading freshness data…"}
            </p>
          </section>
        </>
      )}
    </div>
  )
}
