/**
 * MY RESEARCH — personal research context.
 *
 * Two capabilities genuinely work on this device today: the watchlist and
 * the recently-viewed trail (both stored locally; no backend account exists).
 * Capabilities that require backend support are listed explicitly as
 * unavailable rather than simulated.
 */

import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import {
  Activity,
  BellOff,
  Bookmark,
  Clock,
  FileSearch,
  MonitorPlay,
  Save,
  Settings2,
  X,
} from "lucide-react"
import {
  getRecentSymbols,
  getWatchlist,
  hydrateItems,
  removeFromWatchlist,
} from "../lib/localResearch"
import type { DiscoveryItem } from "../api/types"
import { useDiscovery } from "../useDiscovery"
import { formatLabel } from "../lib/format"
import { EmptyCopy, PanelHead, SectionDivider, Tag } from "../components/ui"

interface CompanyRow {
  symbol: string
  name: string
  sector: string
}

function CompanyRows({ rows }: { rows: CompanyRow[] }) {
  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Company</th>
            <th>Sector</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.symbol}>
              <td>
                <Link to={`/companies/${encodeURIComponent(row.symbol)}`}>
                  <strong>{row.symbol}</strong>
                </Link>
              </td>
              <td>
                <Link className="plain-link" to={`/companies/${encodeURIComponent(row.symbol)}`}>
                  {row.name}
                </Link>
              </td>
              <td>
                <Tag text={formatLabel(row.sector)} tone="slate" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

const UNAVAILABLE = [
  {
    icon: Save,
    title: "Saved screens",
    detail:
      "Screen definitions with persisted filters need a user-data API. The screener itself works today; only saving is unavailable.",
  },
  {
    icon: Bookmark,
    title: "Saved research contexts",
    detail:
      "Named research contexts (company sets + as-of dates) require saved server-side state that this beta does not include yet.",
  },
  {
    icon: BellOff,
    title: "Alerts",
    detail:
      "Evidence-driven alerts require server-side evaluation against new evidence. No alert API exists in the current contract.",
  },
  {
    icon: MonitorPlay,
    title: "Tracked assets beyond equities",
    detail:
      "ETF, mutual-fund and derivatives tracking activates with those datasets on the Asset Classes roadmap.",
  },
  {
    icon: Settings2,
    title: "Notification & display preferences",
    detail:
      "Account-level preferences need an authenticated profile API. Nothing is faked client-side.",
  },
]

export default function MyResearchPage() {
  const { items, loading, error } = useDiscovery()
  // localStorage is read lazily on mount; the page remounts on every visit,
  // so the context is always current without effect-driven state updates.
  const [watchlist, setWatchlist] = useState<string[]>(() => getWatchlist())
  const [recents] = useState<string[]>(() => getRecentSymbols())

  const universe = items as DiscoveryItem[]
  const watchRows = useMemo(
    () => hydrateItems(watchlist, universe),
    [watchlist, universe],
  )
  const recentRows = useMemo(
    () => hydrateItems(recents, universe),
    [recents, universe],
  )

  return (
    <div className="page-my-research">
      <section className="page-hero">
        <h1>My Research</h1>
        <p className="page-subtitle">
          Your working context. Watchlist and history live on this device only —
          there is no account sync yet, so nothing here pretends otherwise.
        </p>
      </section>

      {loading && (
        <div className="loading-state compact" role="status">
          <Activity className="spin" size={18} />
          <span>Loading your research context…</span>
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
          <section aria-label="Watchlist">
            <PanelHead
              title={`Watchlist (${watchRows.length})`}
              subtitle="Companies you follow — stored on this device"
            />
            {watchRows.length === 0 ? (
              <EmptyCopy text="No companies tracked yet. Use the Track button in any company workspace header." />
            ) : (
              <div className="panel">
                <CompanyRows rows={watchRows} />
              </div>
            )}
            {watchRows.length > 0 && (
              <ul className="watchlist-manage">
                {watchRows.map((row) => (
                  <li key={row.symbol}>
                    <button
                      type="button"
                      onClick={() => setWatchlist(removeFromWatchlist(row.symbol))}
                    >
                      <X size={12} aria-hidden />
                      Remove {row.symbol}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-label="Recently viewed">
            <PanelHead
              title="Recently viewed"
              subtitle="Your latest company visits on this device"
            />
            {recentRows.length === 0 ? (
              <EmptyCopy text="No visits recorded yet. Companies you open will appear here." />
            ) : (
              <ul className="recent-strip">
                {recentRows.map((row) => (
                  <li key={row.symbol}>
                    <Clock size={12} aria-hidden />
                    <Link to={`/companies/${encodeURIComponent(row.symbol)}`}>
                      <strong>{row.symbol}</strong> · {row.name}
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <SectionDivider label="NOT YET AVAILABLE" />

          <section aria-label="Capabilities not yet available" className="capability-grid">
            {UNAVAILABLE.map((item) => (
              <article key={item.title} className="capability-card">
                <header>
                  <item.icon size={15} aria-hidden />
                  <h3>{item.title}</h3>
                  <Tag text="Unavailable" tone="slate" />
                </header>
                <p>{item.detail}</p>
              </article>
            ))}
          </section>

          <p className="my-research-note">
            These surfaces activate without design changes once their APIs exist —
            availability is always stated plainly, never simulated.
          </p>
        </>
      )}
    </div>
  )
}
