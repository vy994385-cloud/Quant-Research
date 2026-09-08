/**
 * CoverageSummary — research gaps and data completeness across the universe.
 *
 * Communicates: HOW TO VERIFY → what's missing, what's stale, what to trust.
 *
 * Fetches research gaps per tracked company and presents them as
 * actionable coverage intelligence: grouped by category, sorted by impact.
 */

import { useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { ArrowUpRight } from "lucide-react"
import { fetchResearchGaps } from "../../api/client"
import type { DiscoveryItem, ResearchGap } from "../../api/types"
import { formatLabel } from "../../lib/format"
import { EmptyCopy, Section, Tag } from "../ui"

const GAP_CAP = 8

interface GapGroup {
  key: string
  category: string
  statuses: string[]
  description: string
  symbols: string[]
}

export function CoverageSummary({
  tracked,
}: {
  tracked: DiscoveryItem[]
}) {
  const [gaps, setGaps] = useState<ResearchGap[]>([])
  const [fetched, setFetched] = useState(false)

  const loading = tracked.length > 0 && !fetched

  useEffect(() => {
    if (tracked.length === 0) return undefined
    let cancelled = false

    async function run() {
      const results = await Promise.allSettled(
        tracked.map((i) => fetchResearchGaps(i.symbol)),
      )
      if (cancelled) return

      const pooled: ResearchGap[] = []
      for (const result of results) {
        if (result.status === "fulfilled" && result.value.research_gaps) {
          pooled.push(...result.value.research_gaps.gaps)
        }
      }
      setGaps(pooled)
      setFetched(true)
    }

    void run()
    return () => { cancelled = true }
  }, [tracked])

  const gapGroups = useMemo<GapGroup[]>(() => {
    const map = new Map<string, GapGroup>()
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
    return [...map.values()]
      .sort((a, b) => b.symbols.length - a.symbols.length || a.category.localeCompare(b.category))
      .slice(0, GAP_CAP)
  }, [gaps])

  const totalGaps = gaps.length
  const uniqueCategories = useMemo(() => {
    const cats = new Set(gaps.map((g) => g.category))
    return cats.size
  }, [gaps])

  return (
    <Section
      id="rh-coverage"
      title="Coverage intelligence"
      subtitle="Research gaps across the tracked universe"
      meta={
        loading ? (
          <span className="rh-coverage-loading">Loading</span>
        ) : (
          <span className="rh-coverage-count">
            {totalGaps} gaps · {uniqueCategories} categories
          </span>
        )
      }
    >
      {loading ? (
        <div className="loading-state compact" role="status">
          <span>Fetching research gaps</span>
        </div>
      ) : gapGroups.length === 0 ? (
        <EmptyCopy text="No research gaps identified. All tracked companies have complete coverage." />
      ) : (
        <>
          <ul className="rh-gap-list">
            {gapGroups.map((group) => (
              <li key={group.key} className="rh-gap-item">
                <div className="rh-gap-companies">
                  {group.symbols.map((symbol) => (
                    <Link
                      key={symbol}
                      to={`/companies/${encodeURIComponent(symbol)}`}
                      className="rh-gap-company"
                    >
                      {symbol}
                    </Link>
                  ))}
                </div>
                <div className="rh-gap-body">
                  <div className="rh-gap-head">
                    <span className="rh-gap-category">{group.category}</span>
                    {group.statuses.map((status) => (
                      <Tag key={status} text={formatLabel(status)} tone="amber" />
                    ))}
                  </div>
                  <p className="rh-gap-description">{group.description}</p>
                </div>
              </li>
            ))}
          </ul>
          <Link to="/research-gaps" className="rh-gap-more">
            View all gaps
            <ArrowUpRight size={12} />
          </Link>
        </>
      )}
    </Section>
  )
}
