/**
 * Company Research page — professional research-terminal layout.
 *
 * Information architecture (top → bottom):
 *   1. Company identity / research context + point-in-time controls
 *   2. Research overview (context, changes, evidence balance, tensions)
 *   3. Financial terminal (reported vs derived table, charts)
 *   4. Research observations (derived register)
 *   5. Business & operating context
 *   6. Market context
 *   7. Technology & innovation (only when evidence supports it)
 *   8. Events — one canonical record across news / disclosures / actions
 *   9. Evidence record
 *  10. Data coverage & gaps
 *  11. Sources + provenance & point-in-time methodology
 *
 * Flow: identity → overview → financials → observations → business → market
 * → technology → events → evidence → coverage → sources/PIT. A single
 * horizontal contextual navigation bar anchors the sections.
 */

import { useCallback, useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { Building2 } from "lucide-react"
import { ApiError, fetchResearch } from "../api/client"
import type { CompanyResearch } from "../api/types"
import { trackRecentVisit } from "../lib/localResearch"
import CompanyHeader from "../components/CompanyHeader"
import { ErrorState, LoadingState } from "../components/States"
import ResearchOverviewPanel from "../components/ResearchOverviewPanel"
import BusinessDataPanel from "../components/BusinessDataPanel"
import MarketContextPanel from "../components/MarketContextPanel"
import FinancialDataPanel from "../components/FinancialDataPanel"
import TechInnovationPanel from "../components/TechInnovationPanel"
import EvidenceTablePanel from "../components/EvidenceTablePanel"
import SignalRegisterPanel from "../components/SignalRegisterPanel"
import CompanyEventsPanel from "../components/CompanyEventsPanel"
import DataCoveragePanel from "../components/DataCoveragePanel"
import SourceHealthPanel from "../components/SourceHealthPanel"
import ProvenancePITPanel from "../components/ProvenancePITPanel"

/**
 * Sticky section navigation. "Provenance" is one anchor covering the two
 * adjacent record sections (source coverage + provenance/PIT) so the bar
 * stays compact; both sections still own their DOM ids for deep links.
 */
const SECTION_NAV: Array<{ id: string; label: string; aliases?: string[] }> = [
  { id: "research-overview", label: "Overview" },
  { id: "financial-data", label: "Financials" },
  { id: "signals", label: "Observations" },
  { id: "business-data", label: "Business" },
  { id: "market-context", label: "Market" },
  { id: "tech-innovation", label: "Technology" },
  { id: "company-events", label: "Events" },
  { id: "evidence", label: "Evidence" },
  { id: "data-coverage", label: "Coverage" },
  { id: "source-health", label: "Provenance", aliases: ["provenance-pit"] },
]

export default function CompanyResearchPage() {
  const { symbol } = useParams<{ symbol: string }>()
  const [research, setResearch] = useState<CompanyResearch | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | string | null>(null)
  const [asOf, setAsOf] = useState("")

  useEffect(() => {
    if (!symbol) return
    trackRecentVisit(symbol)
    const sym = symbol
    let cancelled = false
    async function run() {
      setLoading(true)
      setError(null)
      try {
        const result = await fetchResearch(sym)
        if (!cancelled) {
          setResearch(result)
          setAsOf("")
        }
      } catch (err) {
        if (!cancelled) {
          setResearch(null)
          setError(err instanceof ApiError ? err : err instanceof Error ? err.message : String(err))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void run()
    return () => { cancelled = true }
  }, [symbol])

  const loadResearch = useCallback(async (sym: string, requestedAsOf?: string) => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchResearch(sym, requestedAsOf)
      setResearch(result)
      setAsOf("")
    } catch (err) {
      setResearch(null)
      setError(err instanceof ApiError ? err : err instanceof Error ? err.message : String(err))
    } finally {
      setLoading(false)
    }
  }, [])

  function handleRefresh() {
    if (symbol) void loadResearch(symbol)
  }

  function handleApplyAsOf() {
    if (symbol && asOf) void loadResearch(symbol, asOf)
  }

  return (
    <div className="page-company-research">
      {error !== null ? (
        <ErrorState
          error={error}
          onRetry={symbol ? handleRefresh : undefined}
        />
      ) : research === null && loading ? (
        <LoadingState label={`Retrieving research data for ${symbol ?? "this company"}...`} />
      ) : research === null ? (
        <div className="empty-state">
          <Building2 size={28} aria-hidden />
          <strong>No research data</strong>
          <p>Select a company from the Companies page to view its research.</p>
        </div>
      ) : (
        <>
          {/* 1. Research context */}
          <CompanyHeader
            data={research}
            asOf={asOf}
            onAsOfChange={setAsOf}
            onApplyAsOf={handleApplyAsOf}
            onRefresh={handleRefresh}
            refreshing={loading}
          />
          <SectionNav />          <ResearchOverviewPanel data={research} />

          {/* 2. Financial performance: table + trend charts */}
          <FinancialDataPanel data={research} />

          {/* 3. Research observations (derived register) */}
          <SignalRegisterPanel data={research} />

          {/* 4. Business & operating context */}
          <BusinessDataPanel data={research} />

          {/* 5. Market context */}
          <MarketContextPanel data={research} />

          {/* 6. Technology & innovation (renders only when supported) */}
          <TechInnovationPanel data={research} />

          {/* 7. Events — one canonical record across news/actions/timeline */}
          <CompanyEventsPanel
            symbol={symbol!}
            asOf={asOf || undefined}
            timelineEntries={research.timeline?.entries ?? []}
          />

          {/* 8. Evidence record */}
          <EvidenceTablePanel data={research} />

          {/* 9. Data coverage & gaps */}
          <DataCoveragePanel data={research} />

          {/* 10. Sources + provenance & point-in-time methodology */}
          <SourceHealthPanel data={research} />
          <ProvenancePITPanel data={research} />
        </>
      )}
    </div>
  )
}

function SectionNav() {
  const [activeId, setActiveId] = useState<string | null>(null)

  useEffect(() => {
    // Scroll-spy: highlight the anchor whose section crosses the upper
    // viewport band. Alias sections (e.g. provenance/PIT under one anchor)
    // highlight their parent nav item too. Gracefully no-ops where
    // IntersectionObserver is absent.
    if (typeof IntersectionObserver === "undefined") return
    const sectionToNav = new Map<string, string>()
    const sections: HTMLElement[] = []
    for (const item of SECTION_NAV) {
      const ids = [item.id, ...(item.aliases ?? [])]
      for (const id of ids) {
        const el = document.getElementById(id)
        if (el) {
          sections.push(el)
          sectionToNav.set(id, item.id)
        }
      }
    }
    if (sections.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)
        if (visible.length > 0) setActiveId(sectionToNav.get(visible[0].target.id) ?? null)
      },
      { rootMargin: "-15% 0px -70% 0px" },
    )
    for (const section of sections) observer.observe(section)
    return () => observer.disconnect()
  }, [])

  return (
    <nav className="section-nav" aria-label="Report sections">
      <ul>
        {SECTION_NAV.map((item) => (
          <li key={item.id}>
            <a
              href={`#${item.id}`}
              className={activeId === item.id ? "active" : undefined}
              aria-current={activeId === item.id ? "location" : undefined}
            >
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}
