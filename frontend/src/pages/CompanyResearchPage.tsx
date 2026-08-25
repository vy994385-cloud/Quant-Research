/**
 * COMPANY WORKSPACE — the primary investigation surface.
 *
 * Structure:
 *   COMPANY HEADER      identity · sector · research context · as-of controls
 *   CONTEXT STRIP       evidence count · freshness · PIT status · coverage
 *   PRIMARY TABS        Overview | Financials | Business | Market | Technology
 *                       | Events | Evidence | Coverage | Provenance
 *
 * One contextual navigation row. The active tab owns the canvas; Overview is
 * the analyst dashboard, every other tab is a full investigation workspace.
 * The selected tab is mirrored to `?tab=` so workspaces are linkable.
 */

import { useCallback, useEffect, useState } from "react"
import { useParams, useSearchParams } from "react-router-dom"
import { Building2 } from "lucide-react"
import { ApiError, fetchResearch } from "../api/client"
import type { CompanyResearch } from "../api/types"
import { trackRecentVisit } from "../lib/localResearch"
import CompanyHeader from "../components/CompanyHeader"
import { ErrorState, LoadingState } from "../components/States"
import OverviewTab from "../components/company/OverviewTab"
import FinancialDataPanel from "../components/FinancialDataPanel"
import SignalRegisterPanel from "../components/SignalRegisterPanel"
import BusinessDataPanel from "../components/BusinessDataPanel"
import MarketContextPanel from "../components/MarketContextPanel"
import TechInnovationPanel from "../components/TechInnovationPanel"
import CompanyEventsPanel from "../components/CompanyEventsPanel"
import EvidenceTablePanel from "../components/EvidenceTablePanel"
import DataCoveragePanel from "../components/DataCoveragePanel"
import SourceHealthPanel from "../components/SourceHealthPanel"
import ProvenancePITPanel from "../components/ProvenancePITPanel"

const TABS = [
  { id: "overview", label: "Overview" },
  { id: "financials", label: "Financials" },
  { id: "business", label: "Business" },
  { id: "market", label: "Market" },
  { id: "technology", label: "Technology" },
  { id: "events", label: "Events" },
  { id: "evidence", label: "Evidence" },
  { id: "coverage", label: "Coverage" },
  { id: "provenance", label: "Provenance" },
] as const

type TabId = (typeof TABS)[number]["id"]

const VALID_TABS = new Set<string>(TABS.map((tab) => tab.id))

function readTab(param: string | null): TabId {
  return param && VALID_TABS.has(param) ? (param as TabId) : "overview"
}

export default function CompanyResearchPage() {
  const { symbol } = useParams<{ symbol: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const [research, setResearch] = useState<CompanyResearch | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | string | null>(null)
  const [asOf, setAsOf] = useState("")

  const activeTab = readTab(searchParams.get("tab"))

  const openTab = useCallback(
    (tab: string) => {
      const next = new URLSearchParams(searchParams)
      next.set("tab", tab)
      setSearchParams(next, { replace: true })
    },
    [searchParams, setSearchParams],
  )

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

  async function loadResearch(sym: string, requestedAsOf?: string) {
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
  }

  function handleRefresh() {
    if (symbol) void loadResearch(symbol)
  }

  function handleApplyAsOf() {
    if (symbol && asOf) void loadResearch(symbol, asOf)
  }

  if (error !== null) {
    return (
      <div className="page-company-research">
        <ErrorState error={error} onRetry={symbol ? handleRefresh : undefined} />
      </div>
    )
  }

  if (research === null && loading) {
    return (
      <div className="page-company-research">
        <LoadingState label={`Retrieving research data for ${symbol ?? "this company"}...`} />
      </div>
    )
  }

  if (research === null) {
    return (
      <div className="page-company-research">
        <div className="empty-state">
          <Building2 size={28} aria-hidden />
          <strong>No research data</strong>
          <p>Select a company from the Companies directory to view its research.</p>
        </div>
      </div>
    )
  }

  const pit = research.point_in_time
  const freshness = research.research_status?.freshness

  return (
    <div className="page-company-research">
      <CompanyHeader
        data={research}
        asOf={asOf}
        onAsOfChange={setAsOf}
        onApplyAsOf={handleApplyAsOf}
        onRefresh={handleRefresh}
        refreshing={loading}
      />

      {/* Context strip — orientation facts only; details live in their tabs */}
      <div className="context-strip" role="group" aria-label="Research context">
        <span className="context-item">
          <strong>{pit.evidence_included}</strong> evidence items
        </span>
        <span className="context-item">
          {freshness?.days_since_latest_published !== null &&
          freshness?.days_since_latest_published !== undefined ? (
            <>
              latest publication <strong>{freshness.days_since_latest_published}d ago</strong>
              {freshness.stale && <em className="context-flag">stale</em>}
            </>
          ) : (
            <>freshness not available</>
          )}
        </span>
        <span className="context-item">
          PIT{" "}
          <strong className={pit.pit_checks_passed ? "ok" : "bad"}>
            {pit.pit_checks_passed ? "verified" : "checks failed"}
          </strong>
        </span>
        <span className="context-item">
          <strong>{research.data_quality.financial_record_count}</strong> financial records
        </span>
        <span className="context-item">
          <strong>{research.source_statuses.length}</strong> sources
        </span>
        <span className="context-item">
          <strong>{research.research_status?.coverage.item_count ?? 0}</strong> coverage entries
        </span>
      </div>

      {/* ONE contextual tab bar */}
      <nav className="workspace-tabs" aria-label="Company workspace sections">
        <div className="workspace-tabs-track" role="tablist">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              role="tab"
              id={`workspace-tab-${tab.id}`}
              aria-selected={activeTab === tab.id}
              aria-controls="workspace-tab-panel"
              className={activeTab === tab.id ? "workspace-tab active" : "workspace-tab"}
              onClick={() => openTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </nav>

      <div
        id="workspace-tab-panel"
        role="tabpanel"
        aria-labelledby={`workspace-tab-${activeTab}`}
        className="workspace-tab-panel"
      >
        {activeTab === "overview" && <OverviewTab data={research} onOpenTab={openTab} />}
        {activeTab === "financials" && <FinancialDataPanel data={research} />}
        {activeTab === "business" && (
          <>
            <BusinessDataPanel data={research} />
            <SignalRegisterPanel data={research} />
          </>
        )}
        {activeTab === "market" && (
          <>
            <MarketContextPanel data={research} />
          </>
        )}
        {activeTab === "technology" && <TechInnovationPanel data={research} />}
        {activeTab === "events" && (
          <CompanyEventsPanel
            symbol={research.company.symbol}
            timelineEntries={research.timeline?.entries ?? []}
          />
        )}
        {activeTab === "evidence" && <EvidenceTablePanel data={research} />}
        {activeTab === "coverage" && <DataCoveragePanel data={research} />}
        {activeTab === "provenance" && (
          <>
            <SourceHealthPanel data={research} />
            <ProvenancePITPanel data={research} />
          </>
        )}
      </div>
    </div>
  )
}
