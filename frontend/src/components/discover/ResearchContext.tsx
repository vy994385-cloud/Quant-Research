/**
 * ResearchContext — current research context at a glance.
 *
 * Communicates: WHAT MATTERS NOW → watchlist, sector distribution, freshness.
 *
 * Shows the user's watchlist and a compact universe summary so they can
 * orient themselves before diving into activity or search.
 */

import { useMemo } from "react"
import { Link } from "react-router-dom"
import { Clock, Target } from "lucide-react"
import type { DiscoveryItem } from "../../api/types"
import {
  getRecentSymbols,
  getWatchlist,
} from "../../lib/localResearch"
import { formatLabel } from "../../lib/format"
import { Section, Tag } from "../ui"

export function ResearchContext({
  items,
}: {
  items: DiscoveryItem[]
}) {
  const watchlist = useMemo(() => {
    const symbols = getWatchlist()
    return symbols
      .map((s) => items.find((i) => i.symbol === s))
      .filter((i): i is DiscoveryItem => i !== undefined)
  }, [items])

  const recentSymbols = useMemo(() => getRecentSymbols().slice(0, 5), [])

  const sectorCounts = useMemo(() => {
    const map = new Map<string, number>()
    for (const item of items) {
      map.set(item.sector, (map.get(item.sector) ?? 0) + 1)
    }
    return [...map.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
  }, [items])

  const tracked = useMemo(
    () => items.filter((i) => i.research_available).length,
    [items],
  )

  return (
    <div className="rh-context">
      {/* Watchlist */}
      <Section
        id="rh-watchlist"
        title="Watchlist"
        subtitle="Your followed companies"
        meta={<Tag text={`${watchlist.length}`} tone="slate" />}
      >
        {watchlist.length === 0 ? (
          <p className="rh-context-empty">
            <Target size={14} />
            No companies watched yet. Use the search above or visit a company page to start tracking.
          </p>
        ) : (
          <div className="rh-watchlist-grid">
            {watchlist.map((item) => (
              <Link
                key={item.symbol}
                to={`/companies/${encodeURIComponent(item.symbol)}`}
                className="rh-watchlist-card"
              >
                <span className="rh-watchlist-symbol mono">{item.symbol}</span>
                <span className="rh-watchlist-name">
                  {item.company_name ?? item.symbol}
                </span>
                <span className="rh-watchlist-sector">
                  {formatLabel(item.sector)}
                </span>
              </Link>
            ))}
          </div>
        )}
      </Section>

      {/* Universe summary */}
      <Section
        id="rh-universe"
        title="Research Universe"
        subtitle="Coverage at a glance"
        meta={<Tag text={`${tracked} tracked`} tone="slate" />}
      >
        <div className="rh-universe-stats">
          <div className="rh-stat">
            <span className="rh-stat-value">{items.length}</span>
            <span className="rh-stat-label">Total companies</span>
          </div>
          <div className="rh-stat">
            <span className="rh-stat-value">{tracked}</span>
            <span className="rh-stat-label">With research</span>
          </div>
          <div className="rh-stat">
            <span className="rh-stat-value">{items.length - tracked}</span>
            <span className="rh-stat-label">Discovery only</span>
          </div>
        </div>

        <div className="rh-sector-list">
          <h4 className="rh-sector-title">
            Top sectors
          </h4>
          {sectorCounts.map(([sector, count]) => (
            <div key={sector} className="rh-sector-row">
              <span className="rh-sector-name">{formatLabel(sector)}</span>
              <span className="rh-sector-count">{count}</span>
            </div>
          ))}
        </div>
      </Section>

      {/* Recent context */}
      {recentSymbols.length > 0 && (
        <Section
          id="rh-recent-context"
          title="Recent"
          subtitle="Previously visited"
        >
          <div className="rh-recent-list">
            {recentSymbols.map((symbol) => {
              const item = items.find((i) => i.symbol === symbol)
              return (
                <Link
                  key={symbol}
                  to={`/companies/${encodeURIComponent(symbol)}`}
                  className="rh-recent-row"
                >
                  <Clock size={12} className="rh-recent-icon" />
                  <span className="rh-recent-symbol mono">{symbol}</span>
                  <span className="rh-recent-name">
                    {item?.company_name ?? symbol}
                  </span>
                </Link>
              )
            })}
          </div>
        </Section>
      )}
    </div>
  )
}
