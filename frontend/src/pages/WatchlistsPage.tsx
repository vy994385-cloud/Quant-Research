/**
 * WATCHLISTS — personal research watchlists.
 *
 * Managed locally on this device. No server-side persistence.
 * Shows watched companies with research availability and freshness.
 */

import { useMemo } from "react"
import { Link } from "react-router-dom"
import { List, X } from "lucide-react"
import { useDiscovery } from "../useDiscovery"
import { formatLabel } from "../lib/format"
import { LoadingState, EmptyState, ErrorState } from "../components/States"
import { Tag } from "../components/ui"
import { getWatchlist, toggleWatch } from "../lib/localResearch"

export default function WatchlistsPage() {
  const { items, loading, error } = useDiscovery()

  const watched = useMemo(() => {
    const symbols = getWatchlist()
    return symbols
      .map((symbol) => items.find((i) => i.symbol === symbol))
      .filter(Boolean)
  }, [items])

  return (
    <div className="page-watchlists">
      <section className="page-hero">
        <p className="page-kicker">Monitor</p>
        <h1>Watchlists</h1>
        <p className="page-subtitle">
          Companies you are tracking. Managed locally on this device —
          no server-side persistence. Changes stay on this browser only.
        </p>
      </section>

      {loading && (
        <LoadingState label="Loading watchlists" />
      )}

      {error && (
        <ErrorState error={error} />
      )}

      {!loading && !error && watched.length === 0 && (
        <EmptyState
          icon={List}
          title="No companies on your watchlist"
          description="Visit a company workspace and add it to your watchlist to track it here. Watchlists are stored locally on this device."
        />
      )}

      {!loading && !error && watched.length > 0 && (
        <section className="discover-section discover-primary" aria-label="Watched companies">
          <div className="company-table">
            <div className="company-table-head">
              <span className="col-symbol">Symbol</span>
              <span className="col-name">Company</span>
              <span className="col-sector">Sector</span>
              <span className="col-status">Research</span>
              <span className="col-actions">Action</span>
            </div>
            {watched.map((item) => item && (
              <div key={item.symbol} className="company-table-row">
                <span className="col-symbol mono">
                  <Link to={`/companies/${encodeURIComponent(item.symbol)}`}>
                    {item.symbol}
                  </Link>
                </span>
                <span className="col-name">
                  <Link to={`/companies/${encodeURIComponent(item.symbol)}`}>
                    {item.company_name ?? item.symbol}
                  </Link>
                </span>
                <span className="col-sector">
                  <Tag text={formatLabel(item.sector)} tone="slate" />
                </span>
                <span className="col-status">
                  <Tag
                    text={item.research_available ? "Available" : "Not available"}
                    tone={item.research_available ? "blue" : "slate"}
                  />
                </span>
                <span className="col-actions">
                  <button
                    type="button"
                    className="icon-btn"
                    onClick={() => toggleWatch(item.symbol)}
                    aria-label={`Remove ${item.symbol} from watchlist`}
                  >
                    <X size={14} />
                  </button>
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
