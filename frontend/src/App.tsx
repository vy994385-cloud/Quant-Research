/**
 * Quant Research Dashboard — L4.
 *
 * Consumes the deterministic /api/v1 research contract:
 *   discovery -> company research -> rankings -> evidence -> risks ->
 *   trends -> signals -> intelligence -> provenance / point-in-time.
 *
 * Descriptive research only; never presents a trade instruction.
 */

import { useCallback, useState } from "react"
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Clock,
  Database,
  FileSearch,
  LineChart,
  Search,
  Sparkles,
  TrendingUp,
} from "lucide-react"
import { ApiError, fetchResearch } from "./api/client"
import type { CompanyResearch } from "./api/types"
import CompanyHeader from "./components/CompanyHeader"
import CompanySearch from "./components/CompanySearch"
import EvidencePanel from "./components/EvidencePanel"
import IntelligencePanel from "./components/IntelligencePanel"
import OverviewPanel from "./components/OverviewPanel"
import RankingsPanel from "./components/RankingsPanel"
import RisksPanel from "./components/RisksPanel"
import SignalsPanel from "./components/SignalsPanel"
import SourcesPanel from "./components/SourcesPanel"
import { DegradedAlerts, ErrorState, LoadingState } from "./components/States"
import TrendsPanel from "./components/TrendsPanel"
import TimelinePanel from "./components/TimelinePanel"
import "./App.css"

const navigation = [
  { id: "overview", label: "Overview", icon: BarChart3 },
  { id: "rankings", label: "Rankings", icon: TrendingUp },
  { id: "evidence", label: "Evidence", icon: FileSearch },
  { id: "trends", label: "Trends", icon: LineChart },
  { id: "signals", label: "Signals", icon: Activity },
  { id: "risks", label: "Risks", icon: AlertTriangle },
  { id: "intelligence", label: "Intelligence", icon: Sparkles },
  { id: "timeline", label: "Timeline", icon: Clock },
  { id: "sources", label: "Sources & PIT", icon: Database },
]

function App() {
  const [selected, setSelected] = useState<string | null>(null)
  const [research, setResearch] = useState<CompanyResearch | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<ApiError | string | null>(null)
  const [active, setActive] = useState("overview")
  const [asOf, setAsOf] = useState("")

  const loadResearch = useCallback(
    async (symbol: string, requestedAsOf?: string) => {
      setLoading(true)
      setError(null)

      try {
        const result = await fetchResearch(symbol, requestedAsOf)
        setResearch(result)
        setSelected(symbol)
        setAsOf("")
        setActive("overview")
      } catch (requestError) {
        setResearch(null)

        if (requestError instanceof ApiError) {
          setError(requestError)
        } else {
          setError(
            requestError instanceof Error
              ? requestError.message
              : String(requestError),
          )
        }
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  function handleSelect(symbol: string) {
    void loadResearch(symbol)
  }

  function handleApplyAsOf() {
    if (selected && asOf) {
      void loadResearch(selected, asOf)
    }
  }

  function handleRefresh() {
    if (selected) {
      void loadResearch(selected)
    }
  }

  function goTo(sectionId: string) {
    setActive(sectionId)
    document
      .getElementById(sectionId)
      ?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  const degradedAlerts = research
    ? buildDegradedAlerts(research)
    : []

  const degradedDanger =
    research !== null && research.point_in_time.pit_checks_passed === false

  return (
    <div className="terminal-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">Q</span>
          <span>
            <strong>Quant Research</strong>
            <small>RESEARCH DASHBOARD</small>
          </span>
        </div>
        <div className="sidebar-label">WORKSTATION</div>
        <nav>
          {navigation.map((item) => (
            <button
              key={item.id}
              className={active === item.id ? "nav-active" : ""}
              onClick={() => goTo(item.id)}
            >
              <item.icon size={16} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="live-dot" />
          Evidence-first research
          <br />
          <small>Descriptive. Not a trade signal.</small>
        </div>
      </aside>

      <main className="workspace">
        <header className="commandbar">
          <CompanySearch onSelect={handleSelect} disabled={loading} />
          <div className="api-status">
            <span className="live-dot" /> Research API
          </div>
        </header>

        <div className="research-workspace">
          {error !== null ? (
            <ErrorState
              error={error}
              onRetry={selected ? handleRefresh : undefined}
            />
          ) : research === null && loading ? (
            <LoadingState label="Retrieving, validating, and assembling the recorded evidence for this company." />
          ) : research === null ? (
            <EmptyState hasSearched={selected !== null} />
          ) : (
            <>
              <CompanyHeader
                data={research}
                asOf={asOf}
                onAsOfChange={setAsOf}
                onApplyAsOf={handleApplyAsOf}
                onRefresh={handleRefresh}
                refreshing={loading}
              />

              <DegradedAlerts
                alerts={degradedAlerts}
                danger={degradedDanger}
                label="Degraded research context"
              />

              <OverviewPanel data={research} />
              <RankingsPanel data={research} />
              <EvidencePanel data={research} />
              <TrendsPanel data={research} />
              <SignalsPanel data={research} />
              <RisksPanel data={research} />
              <IntelligencePanel data={research} />
              <TimelinePanel data={research} />
              <SourcesPanel data={research} />
            </>
          )}
        </div>
      </main>
    </div>
  )
}

function buildDegradedAlerts(research: CompanyResearch): string[] {
  const alerts: string[] = []
  const quality = research.data_quality

  if (!research.point_in_time.pit_checks_passed) {
    alerts.push(
      "Point-in-time checks did not all pass for this response. Evidence timestamps should be reviewed with extra caution.",
    )
  }

  if (quality.provider_failures.length > 0) {
    alerts.push(
      `${quality.provider_failures.length} research source provider(s) failed and were isolated from this report.`,
    )
  }

  if (quality.financial_data_missing) {
    alerts.push("Financial statement records are missing for this company.")
  }

  if (quality.market_rejected_records > 0) {
    alerts.push(
      `${quality.market_rejected_records} market record(s) were rejected during ingestion.`,
    )
  }

  return alerts
}

function EmptyState({ hasSearched }: { hasSearched: boolean }) {
  return (
    <div className="empty-state">
      {hasSearched ? (
        <FileSearch size={28} />
      ) : (
        <Search size={28} />
      )}
      <strong>
        {hasSearched
          ? "No research was returned"
          : "Start company research"}
      </strong>
      <p>
        {hasSearched
          ? "Select a supported company from the discovery list to assemble its evidence, rankings, and point-in-time context."
          : "Search an NSE company symbol above to assemble its available evidence, rankings, trends, signals, risks, and provenance."}
      </p>
    </div>
  )
}

export default App
