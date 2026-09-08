/**
 * TrendingActivity — ranked research activity across the universe.
 *
 * Additive panel sourced from /api/v1/discovery/trending. Renders
 * nothing (silently) when the capability is unreachable, so the
 * Discover page never breaks if the trending endpoint is unavailable.
 */

import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { fetchDiscoveryTrending } from "../../api/client"
import type { TrendingResult } from "../../api/types"
import { Section, Tag } from "../ui"

const TRENDING_WINDOW_DAYS = 30

export function TrendingActivity() {
  const [data, setData] = useState<TrendingResult | null>(null)

  useEffect(() => {
    let cancelled = false

    fetchDiscoveryTrending({ window_days: TRENDING_WINDOW_DAYS })
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch(() => {
        if (!cancelled) setData(null)
      })

    return () => { cancelled = true }
  }, [])

  if (!data || data.ranked.length === 0) return null

  return (
    <Section
      id="rh-trending"
      title="Trending activity"
      subtitle={`Most-recorded research activity in the last ${TRENDING_WINDOW_DAYS} days`}
      meta={
        <span className="rh-coverage-count">
          {data.ranked.length} companies ranked · recency only
        </span>
      }
    >
      <ul className="rh-trend-list">
        {data.ranked.map((company, index) => (
          <li key={company.symbol} className="rh-trend-item">
            <span className="rh-trend-rank">{index + 1}</span>
            <Link
              to={`/companies/${encodeURIComponent(company.symbol)}`}
              className="rh-trend-symbol mono"
            >
              {company.symbol}
            </Link>
            <Tag text={`${company.recent_item_count} recent`} tone="blue" />
          </li>
        ))}
      </ul>
    </Section>
  )
}