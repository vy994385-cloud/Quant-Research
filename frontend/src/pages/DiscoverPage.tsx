/**
 * DISCOVER — research home: the evidence-first entry point.
 *
 * Information architecture:
 *   RESEARCH UNIVERSE → WHAT MATTERS NOW → WHAT CHANGED → WHERE TO INVESTIGATE → HOW TO VERIFY
 *
 * This page is a thin orchestrator that composes focused sub-components:
 *   - ResearchHomeHeader: editorial greeting + search + destinations
 *   - ResearchContext: watchlist + universe summary
 *   - ResearchChangeStream: chronological change evidence
 *   - CoverageSummary: research gaps and data completeness
 *   - RecentlyResearched: resume previous sessions
 */

import { useMemo, useState } from "react"
import { useDiscovery } from "../useDiscovery"
import { ResearchHomeHeader } from "../components/discover/ResearchHomeHeader"
import { ResearchContext } from "../components/discover/ResearchContext"
import { ResearchChangeStream } from "../components/discover/ResearchChangeStream"
import { TrendingActivity } from "../components/discover/TrendingActivity"
import { CoverageSummary } from "../components/discover/CoverageSummary"
import { RecentlyResearched } from "../components/discover/RecentlyResearched"

export default function DiscoverPage() {
  const { items, loading, error } = useDiscovery()
  const [query, setQuery] = useState("")

  const tracked = useMemo(
    () => items.filter((i) => i.research_available),
    [items],
  )

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

  if (loading) {
    return (
      <div className="page-discover" role="status">
        <div className="loading-state">
          <span className="spinner" aria-hidden />
          <strong>Loading research data</strong>
          <span>Fetching the tracked universe</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-discover" role="alert">
        <div className="empty-state error">
          <strong>Research home unavailable</strong>
          <p>{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page-discover">
      <ResearchHomeHeader
        query={query}
        onQueryChange={setQuery}
        matchedCompanies={matchedCompanies}
        items={items}
      />

      <div className="rh-body">
        <aside className="rh-sidebar">
          <ResearchContext items={items} />
        </aside>

        <main className="rh-main">
          <ResearchChangeStream tracked={tracked} />
          <TrendingActivity />
          <CoverageSummary tracked={tracked} />
          <RecentlyResearched items={items} />
        </main>
      </div>
    </div>
  )
}
