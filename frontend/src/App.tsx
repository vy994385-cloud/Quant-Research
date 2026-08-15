import { useMemo, useState } from "react"
import type { FormEvent, ReactNode } from "react"
import {
  Activity, AlertTriangle, BarChart3, Building2, ChevronDown,
  CircleHelp, Database, FileSearch, Landmark, RefreshCw, Search, ShieldCheck,
  Sparkles, TrendingDown, TrendingUp, TriangleAlert, XCircle,
} from "lucide-react"
import "./App.css"

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

type Evidence = { evidence_id: string; title: string; explanation: string; confidence: string; observation_at?: string; source_ids?: string[]; provenance_ids?: string[] }
type ResearchObservation = { observation_id: string; claim: string; explanation: string; observed_at: string; available_at?: string | null; confidence?: string | null; source_ids?: string[]; provenance_ids?: string[] }
type IntelligenceSection = { status: string; confidence: string; observations: ResearchObservation[]; positive_evidence: Evidence[]; negative_evidence: Evidence[]; unknown: string[]; as_of: string; source_ids: string[]; provenance_ids: string[] }
type ResearchIntelligence = { business_quality: IntelligenceSection; financial_quality: IntelligenceSection; transformation: IntelligenceSection; capital_allocation: IntelligenceSection; competitive_position: IntelligenceSection; innovation: IntelligenceSection; future_technology: IntelligenceSection; customer_intelligence: IntelligenceSection; management_intelligence: IntelligenceSection; market_intelligence: IntelligenceSection; risks_anomalies: IntelligenceSection; unknown_missing: string[] }
type Trend = { metric: string; direction: string; observations: number; average_change: string; positive_periods?: number; negative_periods?: number; stable_periods?: number; consistency?: string; explanation: string }
type Issue = { code: string; status: string; message: string }
type ResearchData = {
  company: { symbol: string; name: string | null; as_of: string; sector?: string | null }
  research_score: { total: string; signal: string; confidence: string; components: Record<string, string> }
  intelligence: { direction: string; signal_count: number; positive_signal_count: number; negative_signal_count: number }
  financial_trends?: Trend[]
  financial_records?: FinancialRecord[]
  observations: Record<string, string[]>
  is_trade_signal: boolean
  research_report?: { conclusion: string; confidence: string; thesis: string; positive_evidence: Evidence[]; negative_evidence: Evidence[]; evidence_narrative?: Record<string, unknown> | null; data_quality_notes?: string[]; research_intelligence?: ResearchIntelligence | null } | null
  provenance?: { as_of: string; market: Source; financials: Source } | null
  data_quality?: { market_validation_status: string; market_accepted_records: number; market_rejected_records: number; market_issues: Issue[]; financial_record_count: number; financial_data_missing: boolean; feature_statuses: Record<string, string>; provenance_completeness?: Record<string, boolean | number>; context: { accepted_observations: number; rejected_observations: number; rejected_missing_availability: number; rejected_not_known_at: number } } | null
}
type Source = { source: string; dataset_id: string | null; record_id: string | null; retrieved_at: string; available_at: string; archived_records?: number; market_as_of?: string }
type FinancialRecord = Record<string, string | null>

const navigation = ["Overview", "Financials", "Evidence", "Intelligence", "Risks", "Timeline", "Peers", "Sources"]
const financialMetrics = ["revenue", "net_profit", "operating_cash_flow", "free_cash_flow", "total_debt", "operating_profit"]

function App() {
  const [data, setData] = useState<ResearchData | null>(null)
  const [symbol, setSymbol] = useState("")
  const [active, setActive] = useState("Overview")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [hasSearched, setHasSearched] = useState(false)

  async function loadResearch(requestedSymbol: string) {
    const normalized = requestedSymbol.trim().toUpperCase()
    if (!normalized) { setData(null); setError("Enter an NSE company symbol to start research."); setHasSearched(true); return }
    try {
      setLoading(true); setError(""); setHasSearched(true)
      const response = await fetch(`${API_URL}/api/stocks/${encodeURIComponent(normalized)}/research`)
      if (!response.ok) throw new Error(response.status === 404 ? `No research is currently available for ${normalized}.` : "Research API is unavailable. Please try again.")
      setData(await response.json())
      setActive("Overview")
    } catch (requestError) {
      setData(null); setError(requestError instanceof Error ? requestError.message : "Unable to connect to the Quant Research API.")
    } finally { setLoading(false) }
  }
  function handleSearch(event: FormEvent<HTMLFormElement>) { event.preventDefault(); void loadResearch(symbol) }
  function goTo(section: string) { setActive(section); document.getElementById(section.toLowerCase())?.scrollIntoView({ behavior: "smooth", block: "start" }) }

  const report = data?.research_report
  const quality = data?.data_quality
  const invalidFeatures = useMemo(() => Object.entries(quality?.feature_statuses ?? {}).filter(([, status]) => status !== "VALID"), [quality])
  const unknownCount = invalidFeatures.length + (quality?.financial_data_missing ? 1 : 0) + (quality?.context.rejected_observations ? 1 : 0)
  const trends = data?.financial_trends ?? []

  return <div className="terminal-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">Q</span><span><strong>Quant Research</strong><small>RESEARCH TERMINAL</small></span></div>
      <div className="sidebar-label">WORKSTATION</div>
      <nav>{navigation.map((item) => <button className={active === item ? "nav-active" : ""} onClick={() => goTo(item)} key={item}>{navIcon(item)}<span>{item}</span></button>)}</nav>
      <div className="sidebar-footer"><span className="live-dot" /> Evidence-first research<br /><small>Descriptive. Not a trade signal.</small></div>
    </aside>
    <main className="workspace">
      <header className="commandbar">
        <form onSubmit={handleSearch} className="command-search"><Search size={17} /><input value={symbol} onChange={(event) => setSymbol(event.target.value)} placeholder="Search company — TCS, INFY, HDFCBANK" aria-label="Company symbol" disabled={loading} /><kbd>⌘ K</kbd><button type="submit" disabled={loading}>{loading ? <Activity className="spin" size={16} /> : "Research"}</button></form>
        <div className="api-status"><span className="live-dot" /> Research API</div>
      </header>
      <div className="research-workspace">
        {!data && !loading && <EmptyState error={error} hasSearched={hasSearched} />}
        {loading && <div className="loading-state"><Activity className="spin" size={26} /><strong>Building research context</strong><span>Retrieving, validating, and assembling available evidence.</span></div>}
        {data && <>
          <CompanyHeader data={data} report={report} loading={loading} onRefresh={() => void loadResearch(data.company.symbol)} />
          <section id="overview" className="section-anchor"><SectionTitle eyebrow="RESEARCH OVERVIEW" title="Evidence before conclusion" detail="A descriptive research view; unavailable evidence is kept distinct from contradicting evidence." />
            <div className="metric-grid">
              <Metric label="Research Score" value={formatNumber(data.research_score.total)} detail="Composite research context" icon={<BarChart3 />} />
              <Metric label="Evidence Confidence" value={`${formatConfidence(report?.confidence ?? data.research_score.confidence)}%`} detail="Confidence in available evidence" icon={<ShieldCheck />} />
              <Metric label="Supporting Evidence" value={String(report?.positive_evidence.length ?? data.intelligence.positive_signal_count)} detail="Validated positive observations" tone="positive" icon={<TrendingUp />} />
              <Metric label="Contradicting Evidence" value={String(report?.negative_evidence.length ?? data.intelligence.negative_signal_count)} detail="Validated negative observations" tone="negative" icon={<TrendingDown />} />
              <Metric label="Unknown / Missing" value={String(unknownCount)} detail="Neither positive nor negative" tone="neutral" icon={<CircleHelp />} />
            </div>
            <div className="overview-grid">
              <article className="panel conclusion-panel"><div className="panel-kicker">OVERALL CONCLUSION</div><h2>{formatLabel(report?.conclusion ?? data.research_score.signal)}</h2><p>{report?.thesis || "A report thesis is not available for this company."}</p><div className="score-line"><span>Research score</span><strong>{formatNumber(data.research_score.total)} / 100</strong></div></article>
              <article className="panel"><PanelHead title="What the evidence says" subtitle="Evidence is classified without inferring missing data." /><div className="evidence-summary"><SummaryCard type="positive" title="Supporting evidence" count={report?.positive_evidence.length ?? 0} text="Evidence consistent with the research conclusion." /><SummaryCard type="negative" title="Contradicting evidence" count={report?.negative_evidence.length ?? 0} text="Evidence that qualifies or challenges the conclusion." /><SummaryCard type="neutral" title="Unknown / insufficient" count={unknownCount} text="Missing, rejected, or unavailable evidence; not a negative signal." /></div></article>
            </div>
          </section>
          <section id="financials" className="section-anchor"><SectionTitle eyebrow="FINANCIALS" title="Available financial context" detail={data.financial_records?.length ? "Validated annual records with compact trend context." : "Raw financial statement values are not available from the current provider response."} /><div className="panel"><div className="financial-grid">{financialMetrics.map((metric) => <FinancialMetric key={metric} metric={metric} trend={trends.find((item) => item.metric === metric)} record={latestRecord(data.financial_records)} />)}</div></div></section>
          <section id="evidence" className="section-anchor"><SectionTitle eyebrow="EVIDENCE" title="Evidence ledger" detail="Every item carries its confidence and available lineage." /><div className="evidence-columns"><EvidenceList tone="positive" title="Supporting evidence" icon={<TrendingUp />} items={report?.positive_evidence ?? []} empty="No supporting evidence was included in this report." /><EvidenceList tone="negative" title="Contradicting evidence" icon={<TrendingDown />} items={report?.negative_evidence ?? []} empty="No contradicting evidence was included in this report." /><UnknownEvidence quality={quality} invalidFeatures={invalidFeatures} /></div></section>
          <section id="intelligence" className="section-anchor"><SectionTitle eyebrow="INTELLIGENCE" title="Company intelligence" detail="Each category shows what is supported, contradicted, and still unknown." /><IntelligenceDashboard intelligence={report?.research_intelligence} fallback={data.observations} /></section>
          <section id="risks" className="section-anchor"><SectionTitle eyebrow="RISKS & ANOMALIES" title="Exceptions requiring context" detail="Warnings remain visible; they are not translated into trade instructions." /><div className="risk-grid"><div className="panel"><PanelHead title="Negative evidence & anomalies" subtitle="Validated adverse or anomalous observations" />{(report?.negative_evidence.length || data.observations.risk?.length || quality?.market_issues.length) ? <div className="risk-list">{[...(data.observations.risk ?? []), ...(quality?.market_issues.map((issue) => `${formatLabel(issue.code)} — ${issue.message}`) ?? [])].map((item) => <RiskRow key={item} text={item} />)}{(report?.negative_evidence ?? []).map((item) => <RiskRow key={item.evidence_id} text={`${readableEvidenceTitle(item.title)} — ${item.explanation}`} />)}</div> : <EmptyCopy text="No risk observations or market anomalies are currently available." />}</div><DataQuality quality={quality} invalidFeatures={invalidFeatures} /></div></section>
          <section id="timeline" className="section-anchor"><SectionTitle eyebrow="TIMELINE" title="Dated research evidence" detail="Only timestamps actually returned by the API are included." /><Timeline report={report} /></section>
          <section id="peers" className="section-anchor"><SectionTitle eyebrow="PEERS" title="Peer comparison" detail="Peer scores and comparisons are not inferred." /><div className="panel peer-empty"><Landmark size={22} /><strong>Peer intelligence is coming from the research engine. No peer dataset is currently available.</strong></div></section>
          <section id="sources" className="section-anchor"><SectionTitle eyebrow="SOURCES & PROVENANCE" title="Data lineage" detail="Retrieval and availability timestamps make evidence freshness inspectable." /><Sources data={data} report={report} /></section>
        </>}
      </div>
    </main>
  </div>
}

function CompanyHeader({ data, report, loading, onRefresh }: { data: ResearchData; report: ResearchData["research_report"]; loading: boolean; onRefresh: () => void }) { const quality = data.data_quality; return <section className="company-header"><div className="company-identity"><div className="company-icon"><Building2 size={25} /></div><div><div className="ticker">NSE:{data.company.symbol}</div><h1>{data.company.name || data.company.symbol}</h1><div className="company-meta"><span>{data.company.sector || "Sector not available"}</span><span>As of {formatDate(data.provenance?.as_of || data.company.as_of)}</span></div></div></div><div className="header-tags"><Tag text="DESCRIPTIVE RESEARCH" tone="blue" /><Tag text={quality?.market_validation_status || "QUALITY UNKNOWN"} tone={quality?.market_validation_status === "VALID" ? "green" : "amber"} /><Tag text={`${formatConfidence(report?.confidence ?? data.research_score.confidence)}% confidence`} tone="slate" /><button className="refresh-button" onClick={onRefresh} disabled={loading}><RefreshCw className={loading ? "spin" : ""} size={15} /> Refresh</button></div></section> }
function Metric({ label, value, detail, icon, tone = "" }: { label: string; value: string; detail: string; icon: ReactNode; tone?: string }) { return <article className={`metric ${tone}`}><div>{icon}<span>{label}</span></div><strong>{value}</strong><small>{detail}</small></article> }
function SummaryCard({ type, title, count, text }: { type: string; title: string; count: number; text: string }) { return <div className={`summary-card ${type}`}><strong>{title}<span>{count}</span></strong><p>{text}</p></div> }
function FinancialMetric({ metric, trend, record }: { metric: string; trend?: Trend; record?: FinancialRecord }) { const total = Math.max(1, (trend?.positive_periods ?? 0) + (trend?.negative_periods ?? 0) + (trend?.stable_periods ?? 0)); const positive = ((trend?.positive_periods ?? 0) / total) * 100; const negative = ((trend?.negative_periods ?? 0) / total) * 100; const raw = record?.[metric]; return <article className="financial-metric"><div><span>{formatMetric(metric)}</span><strong>{raw ? formatCurrency(raw) : "Not available"}</strong></div>{trend ? <><div className="trend-detail"><span className={trend.direction === "INCREASING" ? "up" : trend.direction === "DECREASING" ? "down" : "flat"}>{formatLabel(trend.direction)}</span><small>{trend.observations} observations</small></div><div className="trend-bar"><i style={{ width: `${positive}%` }} /><b style={{ width: `${negative}%` }} /></div><p>{trend.explanation}</p></> : <p>{raw ? "Latest validated reported value." : "No validated trend is available."}</p>}</article> }

const intelligenceCategories: Array<[keyof Omit<ResearchIntelligence, "unknown_missing">, string]> = [
  ["business_quality", "Business quality"],
  ["financial_quality", "Financial quality"],
  ["transformation", "Transformation"],
  ["innovation", "Innovation"],
  ["future_technology", "Future technology"],
  ["customer_intelligence", "Customers"],
  ["management_intelligence", "Management"],
  ["capital_allocation", "Capital allocation"],
  ["competitive_position", "Competitive position"],
  ["market_intelligence", "Market intelligence"],
]

function IntelligenceDashboard({ intelligence, fallback }: { intelligence?: ResearchIntelligence | null; fallback: Record<string, string[]> }) { return <div className="intelligence-dashboard">{intelligence ? intelligenceCategories.map(([key, title]) => <IntelligenceCard key={key} title={title} section={intelligence[key]} />) : <><ObservationPanel title="Business signals" items={fallback.events ?? []} /><ObservationPanel title="Financial signals" items={fallback.financial ?? []} /><ObservationPanel title="Market signals" items={fallback.market ?? []} /><ObservationPanel title="Ownership" items={fallback.ownership ?? []} /><ObservationPanel title="Management / strategic" items={[...(fallback.management ?? []), ...(fallback.related_parties ?? [])]} /></>}</div> }
function IntelligenceCard({ title, section }: { title: string; section: IntelligenceSection }) { const evidence = [...section.positive_evidence, ...section.negative_evidence]; return <article className={`intelligence-card status-${section.status.toLowerCase()}`}><div className="intelligence-card-head"><h3>{title}</h3><Tag text={section.status} tone={section.status === "SUPPORTED" ? "green" : section.status === "CONTRADICTED" ? "red" : section.status === "UNKNOWN" ? "slate" : "amber"} /></div><div className="intelligence-state"><span>Confidence</span><strong>{section.confidence}</strong></div>{section.observations.slice(0, 3).map((item) => <p className="intel-observation" key={item.observation_id}>{item.claim}</p>)}{evidence.slice(0, 2).map((item) => <p className="intel-evidence" key={item.evidence_id}><b>{section.positive_evidence.includes(item) ? "Supporting" : "Contradicting"}</b> {readableEvidenceTitle(item.title)}</p>)}{section.unknown.length ? <p className="intel-unknown"><CircleHelp size={13} />{section.unknown[0]}</p> : null}{!section.observations.length && !evidence.length && !section.unknown.length ? <EmptyCopy text="No section data returned." /> : null}</article> }
function EvidenceList({ tone, title, icon, items, empty }: { tone: string; title: string; icon: ReactNode; items: Evidence[]; empty: string }) { return <div className={`panel evidence-panel ${tone}`}><div className="evidence-panel-title">{icon}<div><h3>{title}</h3><span>{items.length} item{items.length === 1 ? "" : "s"}</span></div></div>{items.length ? items.map((item) => <EvidenceCard key={item.evidence_id} item={item} />) : <EmptyCopy text={empty} />}</div> }
function EvidenceCard({ item }: { item: Evidence }) { return <details className="evidence-card"><summary><div><strong>{readableEvidenceTitle(item.title)}</strong><p>{readableExplanation(item)}</p></div><ChevronDown size={16} /></summary><div className="evidence-detail"><span>Confidence <b>{formatConfidence(item.confidence)}%</b></span>{item.observation_at && <span>Observed {formatDate(item.observation_at)}</span>}{item.source_ids?.length ? <span>Source ID: {item.source_ids.join(", ")}</span> : <span>Source ID: Not available</span>}{item.provenance_ids?.length ? <span>Provenance ID: {item.provenance_ids.join(", ")}</span> : <span>Provenance ID: Not available</span>}</div></details> }
function UnknownEvidence({ quality, invalidFeatures }: { quality?: ResearchData["data_quality"]; invalidFeatures: [string, string][] }) { const items = [quality?.financial_data_missing ? "Financial records are not available from the provider." : "", ...invalidFeatures.map(([feature, status]) => `${formatMetric(feature)} — ${formatLabel(status)}`), quality?.context.rejected_observations ? `${quality.context.rejected_observations} observations were excluded by point-in-time controls.` : ""].filter(Boolean); return <div className="panel evidence-panel neutral"><div className="evidence-panel-title"><CircleHelp /><div><h3>Unknown / insufficient evidence</h3><span>{items.length} item{items.length === 1 ? "" : "s"}</span></div></div>{items.length ? items.map((item) => <div className="unknown-row" key={item}>{item}</div>) : <EmptyCopy text="No missing or insufficient evidence flags were returned." />}</div> }
function ObservationPanel({ title, items }: { title: string; items: string[] }) { return <article className="panel observation-panel"><h3>{title}</h3>{items.length ? <div>{items.map((item) => <p key={item}>{item}</p>)}</div> : <EmptyCopy text="Not available from the current research response." />}</article> }
function DataQuality({ quality, invalidFeatures }: { quality?: ResearchData["data_quality"]; invalidFeatures: [string, string][] }) { return <div className="panel quality-panel"><PanelHead title="Data quality" subtitle="Validation and point-in-time controls" />{quality ? <div className="quality-list"><QualityRow label="Validation status" value={quality.market_validation_status} /><QualityRow label="Accepted / rejected records" value={`${quality.market_accepted_records} / ${quality.market_rejected_records}`} /><QualityRow label="Missing financial records" value={quality.financial_data_missing ? "Yes" : "No"} /><QualityRow label="Missing / invalid features" value={String(invalidFeatures.length)} /><QualityRow label="PIT rejected observations" value={String(quality.context.rejected_observations)} /><QualityRow label="Missing availability" value={String(quality.context.rejected_missing_availability)} /><QualityRow label="Not known at cutoff" value={String(quality.context.rejected_not_known_at)} /></div> : <EmptyCopy text="Data-quality details are not available." />}</div> }
function Timeline({ report }: { report?: ResearchData["research_report"] }) { const dated = [...(report?.positive_evidence ?? []), ...(report?.negative_evidence ?? [])].filter((item) => item.observation_at).sort((a, b) => String(b.observation_at).localeCompare(String(a.observation_at))); return <div className="panel timeline">{dated.length ? dated.map((item) => <div className="timeline-row" key={item.evidence_id}><time>{formatDate(item.observation_at!)}</time><div><strong>{readableEvidenceTitle(item.title)}</strong><p>{readableExplanation(item)}</p></div></div>) : <EmptyCopy text="Timeline data is not yet available for this company." />}</div> }
function Sources({ data, report }: { data: ResearchData; report?: ResearchData["research_report"] }) { const sourceIds = [...(report?.positive_evidence ?? []), ...(report?.negative_evidence ?? [])].flatMap((item) => item.source_ids ?? []); const provenanceIds = [...(report?.positive_evidence ?? []), ...(report?.negative_evidence ?? [])].flatMap((item) => item.provenance_ids ?? []); return <div className="source-grid"><SourcePanel title="Market source" source={data.provenance?.market} /><SourcePanel title="Financial source" source={data.provenance?.financials} /><div className="panel source-panel"><h3>Evidence references</h3><SourceLine label="Evidence source IDs" value={sourceIds.length ? [...new Set(sourceIds)].join(", ") : "Not available"} /><SourceLine label="Provenance IDs" value={provenanceIds.length ? [...new Set(provenanceIds)].join(", ") : "Not available"} /></div></div> }
function SourcePanel({ title, source }: { title: string; source?: Source }) { return <div className="panel source-panel"><h3>{title}</h3>{source ? <><SourceLine label="Source" value={source.source} /><SourceLine label="Dataset" value={source.dataset_id || "Not available"} /><SourceLine label="Record" value={source.record_id || "Not available"} /><SourceLine label="Retrieved at" value={formatDate(source.retrieved_at)} /><SourceLine label="Available at" value={formatDate(source.available_at)} />{source.market_as_of && <SourceLine label="Market as-of" value={formatDate(source.market_as_of)} />}{typeof source.archived_records === "number" && <SourceLine label="Archived records" value={String(source.archived_records)} />}</> : <EmptyCopy text="Source metadata is not available." />}</div> }
function SourceLine({ label, value }: { label: string; value: string }) { return <div className="source-line"><span>{label}</span><strong>{value}</strong></div> }
function RiskRow({ text }: { text: string }) { return <div className="risk-row"><TriangleAlert size={16} /><span>{text}</span></div> }
function QualityRow({ label, value }: { label: string; value: string }) { return <div><span>{label}</span><strong>{value}</strong></div> }
function PanelHead({ title, subtitle }: { title: string; subtitle: string }) { return <div className="panel-head"><div><h3>{title}</h3><span>{subtitle}</span></div></div> }
function SectionTitle({ eyebrow, title, detail }: { eyebrow: string; title: string; detail: string }) { return <header className="section-title"><span>{eyebrow}</span><h2>{title}</h2><p>{detail}</p></header> }
function Tag({ text, tone }: { text: string; tone: string }) { return <span className={`tag ${tone}`}>{text}</span> }
function EmptyCopy({ text }: { text: string }) { return <p className="empty-copy">{text}</p> }
function EmptyState({ error, hasSearched }: { error: string; hasSearched: boolean }) { return <div className={`empty-state ${error ? "error" : ""}`}>{error ? <XCircle size={28} /> : <FileSearch size={28} />}<strong>{error ? "Research could not be generated" : hasSearched ? "No research available" : "Start company research"}</strong><p>{error || "Search an NSE company symbol to assemble its available evidence, data quality, and provenance."}</p></div> }
function navIcon(item: string) { const icons: Record<string, ReactNode> = { Overview: <BarChart3 />, Financials: <Landmark />, Evidence: <FileSearch />, Intelligence: <Sparkles />, Risks: <AlertTriangle />, Timeline: <Activity />, Peers: <Building2 />, Sources: <Database /> }; return icons[item] }
function readableEvidenceTitle(title: string) { const cleaned = title.replace(/^Validated feature:\s*/i, ""); return formatMetric(cleaned) }
function readableExplanation(item: Evidence) { if (/^Validated feature:/i.test(item.title)) return `Validated financial evidence supporting ${formatMetric(item.title.replace(/^Validated feature:\s*/i, "")).toLowerCase()}.`; return item.explanation }
function formatMetric(value: string) { const replacements: Record<string, string> = { revenue: "Revenue", net_profit: "Net Profit", operating_cash_flow: "Operating Cash Flow", free_cash_flow: "Free Cash Flow", total_debt: "Debt", operating_profit: "Operating Profit", cash_conversion_ratio: "Cash Conversion", market_close: "Market Close" }; return replacements[value] || formatLabel(value) }
function formatLabel(value: string) { return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase()) }
function formatConfidence(value: string) { const numeric = Number(value); return Number.isFinite(numeric) ? (numeric <= 1 ? numeric * 100 : numeric).toFixed(1) : "—" }
function formatNumber(value: string) { const numeric = Number(value); return Number.isFinite(numeric) ? numeric.toFixed(1) : "—" }
function latestRecord(records?: FinancialRecord[]) { return records?.length ? records[records.length - 1] : undefined }
function formatCurrency(value: string) { const numeric = Number(value); if (!Number.isFinite(numeric)) return "Not available"; const absolute = Math.abs(numeric); const sign = numeric < 0 ? "-" : ""; if (absolute >= 1e12) return `${sign}₹${(absolute / 1e12).toFixed(2)}T`; if (absolute >= 1e9) return `${sign}₹${(absolute / 1e9).toFixed(2)}B`; if (absolute >= 1e6) return `${sign}₹${(absolute / 1e6).toFixed(2)}M`; return `${sign}₹${absolute.toLocaleString("en-IN")}` }
function formatDate(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) }
export default App
