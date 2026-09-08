/**
 * RecentlyResearched — resume previous research sessions.
 *
 * Communicates: WHERE TO INVESTIGATE → continue where you left off.
 *
 * Reads recently visited companies from localStorage and presents them
 * as quick-access links with company metadata from the discovery universe.
 */

import { useMemo } from "react"
import { Link } from "react-router-dom"
import { Clock } from "lucide-react"
import type { DiscoveryItem } from "../../api/types"
import { getRecentSymbols } from "../../lib/localResearch"
import { formatLabel } from "../../lib/format"
import { Section } from "../ui"

export function RecentlyResearched({
  items,
}: {
  items: DiscoveryItem[]
}) {
  const recent = useMemo(() => {
    const symbols = getRecentSymbols()
    return symbols
      .slice(0, 6)
      .map((symbol) => items.find((i) => i.symbol === symbol))
      .filter((i): i is DiscoveryItem => i !== undefined)
  }, [items])

  if (recent.length === 0) return null

  return (
    <Section
      id="rh-recent"
      title="Recently researched"
      subtitle="Continue where you left off"
    >
      <div className="rh-recent-grid">
        {recent.map((item) => (
          <Link
            key={item.symbol}
            to={`/companies/${encodeURIComponent(item.symbol)}`}
            className="rh-recent-card"
          >
            <div className="rh-recent-card-top">
              <span className="rh-recent-card-symbol mono">{item.symbol}</span>
              <Clock size={11} className="rh-recent-card-icon" />
            </div>
            <span className="rh-recent-card-name">
              {item.company_name ?? item.symbol}
            </span>
            <span className="rh-recent-card-sector">
              {formatLabel(item.sector)}
            </span>
          </Link>
        ))}
      </div>
    </Section>
  )
}
