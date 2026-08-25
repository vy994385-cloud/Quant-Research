/**
 * GLOBAL SEARCH — cross-domain research search.
 *
 * Searches across companies, evidence, events, themes, and industries.
 * Each result clearly identifies its type. No ranking, no scoring —
 * just matching results from recorded research data.
 */

import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { Building2, Clock, Globe, Lightbulb, Search, Shield, XCircle } from "lucide-react"
import { useDiscovery } from "../useDiscovery"
import { formatLabel } from "../lib/format"
import { Tag } from "../components/ui"
import { LoadingState, EmptyState, ErrorState } from "../components/States"

type ResultType = "company" | "evidence" | "event" | "theme" | "industry"

interface SearchResult {
  type: ResultType
  title: string
  subtitle: string
  to: string
  icon: React.ComponentType<{ size?: number }>
  tone: "slate" | "blue" | "amber"
}

const TYPE_LABELS: Record<ResultType, string> = {
  company: "Company",
  evidence: "Evidence",
  event: "Event",
  theme: "Theme",
  industry: "Industry",
}

export default function GlobalSearchPage() {
  const { items, loading, error } = useDiscovery()
  const [query, setQuery] = useState("")
  const [activeFilter, setActiveFilter] = useState<ResultType | "all">("all")

  const q = query.trim().toLowerCase()

  const results = useMemo<SearchResult[]>(() => {
    if (!q) return []

    const matched: SearchResult[] = []

    for (const item of items) {
      const nameMatch =
        item.symbol.toLowerCase().includes(q) ||
        (item.company_name ?? "").toLowerCase().includes(q) ||
        item.sector.toLowerCase().includes(q)

      if (nameMatch) {
        matched.push({
          type: "company",
          title: item.company_name ?? item.symbol,
          subtitle: `${item.symbol} · ${formatLabel(item.sector)}`,
          to: `/companies/${encodeURIComponent(item.symbol)}`,
          icon: Building2,
          tone: "blue",
        })

        if (item.research_available) {
          matched.push({
            type: "evidence",
            title: `Evidence for ${item.company_name ?? item.symbol}`,
            subtitle: `${item.symbol} · Research evidence and provenance`,
            to: `/companies/${encodeURIComponent(item.symbol)}?tab=evidence`,
            icon: Shield,
            tone: "blue",
          })

          matched.push({
            type: "event",
            title: `Events for ${item.company_name ?? item.symbol}`,
            subtitle: `${item.symbol} · Recorded timeline`,
            to: `/companies/${encodeURIComponent(item.symbol)}?tab=events`,
            icon: Clock,
            tone: "slate",
          })
        }
      }
    }

    const themes = [
      "artificial-intelligence",
      "cloud",
      "semiconductor",
      "fintech",
      "edtech",
      "pharma",
      "ev",
      "renewable",
      "banking",
      "insurance",
    ]
    for (const theme of themes) {
      if (theme.includes(q)) {
        matched.push({
          type: "theme",
          title: formatLabel(theme),
          subtitle: "Technology and market theme",
          to: "/themes",
          icon: Lightbulb,
          tone: "amber",
        })
      }
    }

    const industries = [...new Set(items.map((i) => i.sector))]
    for (const industry of industries) {
      if (industry.toLowerCase().includes(q)) {
        matched.push({
          type: "industry",
          title: formatLabel(industry),
          subtitle: `${items.filter((i) => i.sector === industry).length} tracked companies`,
          to: "/industries",
          icon: Globe,
          tone: "slate",
        })
      }
    }

    return matched
  }, [q, items])

  const filteredResults = useMemo(() => {
    if (activeFilter === "all") return results
    return results.filter((r) => r.type === activeFilter)
  }, [results, activeFilter])

  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const r of results) {
      counts[r.type] = (counts[r.type] ?? 0) + 1
    }
    return counts
  }, [results])

  return (
    <div className="page-global-search">
      <section className="discover-hero" aria-label="Global research search">
        <p className="page-kicker">Global search</p>
        <h1>Search the research universe</h1>
        <p className="page-subtitle">
          Cross-domain search across companies, evidence, events, themes, and industries.
          Each result identifies its type clearly.
        </p>
        <div className="discover-hero-search">
          <Search size={18} aria-hidden />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search companies, sectors, evidence, events — TCS, Pharma, AI…"
            aria-label="Global research search"
            autoFocus
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
      </section>

      {loading && <LoadingState label="Fetching tracked universe…" />}

      {error && <ErrorState error={error} />}

      {!loading && !error && q && (
        <section className="discover-section discover-primary" aria-label="Search results">
          <div className="stream-controls">
            <SegmentedFilter
              activeFilter={activeFilter}
              onChange={setActiveFilter}
              typeCounts={typeCounts}
            />
            <span className="search-result-count">
              {filteredResults.length} result{filteredResults.length !== 1 ? "s" : ""}
            </span>
          </div>

          {filteredResults.length === 0 ? (
            <EmptyState
              icon={Search}
              title="No results match this search"
              description="Try a different query or broaden the type filter."
            />
          ) : (
            <ul className="search-results-list">
              {filteredResults.map((result, index) => {
                const Icon = result.icon
                return (
                  <li key={`${result.type}-${result.to}-${index}`}>
                    <Link to={result.to} className={`search-result-item search-result-${result.type}`}>
                      <span className={`search-result-icon ${result.type}`}>
                        <Icon size={16} />
                      </span>
                      <div className="search-result-body">
                        <span className="search-result-title">{result.title}</span>
                        <span className="search-result-subtitle">{result.subtitle}</span>
                      </div>
                      <Tag text={TYPE_LABELS[result.type]} tone={result.tone} />
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      )}

      {!loading && !error && !q && (
        <section className="discover-section" aria-label="Search guidance">
          <EmptyState
            icon={Search}
            title="Enter a search query"
            description="Search by company name, symbol, sector, theme, or industry. Results include companies, evidence records, events, themes, and industries."
          />
        </section>
      )}
    </div>
  )
}

function SegmentedFilter({
  activeFilter,
  onChange,
  typeCounts,
}: {
  activeFilter: ResultType | "all"
  onChange: (value: ResultType | "all") => void
  typeCounts: Record<string, number>
}) {
  const options: Array<{ value: ResultType | "all"; label: string }> = [
    { value: "all", label: "All" },
    { value: "company", label: "Companies" },
    { value: "evidence", label: "Evidence" },
    { value: "event", label: "Events" },
    { value: "theme", label: "Themes" },
    { value: "industry", label: "Industries" },
  ]

  return (
    <div className="segmented-control" role="radiogroup" aria-label="Filter by result type">
      {options.map((option) => {
        const count = option.value === "all"
          ? Object.values(typeCounts).reduce((a, b) => a + b, 0)
          : (typeCounts[option.value] ?? 0)
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={activeFilter === option.value}
            className={activeFilter === option.value ? "segmented-active" : ""}
            onClick={() => onChange(option.value)}
          >
            {option.label}
            {count > 0 && <span className="segmented-count">{count}</span>}
          </button>
        )
      })}
    </div>
  )
}
