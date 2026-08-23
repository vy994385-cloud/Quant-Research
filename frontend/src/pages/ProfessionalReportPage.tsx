/**
 * Professional Research Report page: 22-section canonical report from F8.
 * Fetches from the dedicated F8 professional report endpoint.
 * Evidence-first: no scores, no rankings, no recommendations.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useSearchParams } from "react-router-dom"
import {
  Activity,
  Building2,
  FileSearch,
  ChevronDown,
  Search,
  AlertTriangle,
  CheckCircle,
  XCircle,
  MinusCircle,
} from "lucide-react"
import { fetchDiscovery, fetchProfessionalReport } from "../api/client"
import { ApiError } from "../api/client"
import type {
  CompanyProfessionalReportResponse,
  DiscoveryItem,
  F8ConflictDetail,
  F8EvidenceItemSimple,
  F8EvidenceSection,
  F8ExecutiveOverview,
  F8Methodology,
  F8PITIntegrity,
  F8ProfessionalReport,
  F8QualityLayer,
  F8ReportItem,
  F8ReportSection,
  F8SourceHealth,
} from "../api/types"
import { formatConfidence, formatIso, formatLabel, formatSourceName, pluralize } from "../lib/format"
import { Tag } from "../components/ui"

/* ── Helpers ────────────────────────────────────────────────────── */

function epistemicBadge(ep: string): "green" | "red" | "slate" {
  if (ep === "REPORTED") return "green"
  if (ep === "DERIVED") return "slate"
  if (ep === "INFERRED") return "red"
  return "slate"
}

/* ── Sub-components ──────────────────────────────────────────── */

function ReportItemCard({ item }: { item: F8ReportItem }) {
  return (
    <div className="pr-item">
      <div className="pr-item-head">
        <Tag text={formatLabel(item.epistemic_type)} tone={epistemicBadge(item.epistemic_type)} />
        {item.confidence !== "0" && item.confidence !== "" && (
          <span className="pr-item-conf">Reliability {formatConfidence(item.confidence)}</span>
        )}
        {item.observation_at && (
          <span className="pr-item-date">{formatIso(item.observation_at)}</span>
        )}
      </div>
      <p>{item.text}</p>
      {item.metadata && Object.keys(item.metadata).length > 0 && (
        <div className="pr-item-meta">
          {Object.entries(item.metadata).map(([k, v]) => (
            <span key={k}><strong>{formatLabel(k)}:</strong> {v}</span>
          ))}
        </div>
      )}
    </div>
  )
}

function ReportSection({
  section,
  defaultOpen = false,
}: {
  section: F8ReportSection
  defaultOpen?: boolean
}) {
  if (!section || section.status === "MISSING" || section.total_items === 0) return null

  return (
    <details className="pr-section" open={defaultOpen}>
      <summary>
        <div className="pr-section-head">
          <Tag text={formatLabel(section.epistemic_type)} tone={epistemicBadge(section.epistemic_type)} />
          <strong>{section.title}</strong>
          <span className="pr-section-count">{pluralize(section.total_items, "item")}</span>
        </div>
        <ChevronDown size={16} />
      </summary>
      <div className="pr-section-body">
        {section.items.map((item) => (
          <ReportItemCard key={item.item_id} item={item} />
        ))}
        {section.notes.length > 0 && (
          <div className="pr-section-notes">
            {section.notes.map((n, i) => (
              <span key={i}>{n}</span>
            ))}
          </div>
        )}
      </div>
    </details>
  )
}

function EvidenceSectionView({ section }: { section: F8EvidenceSection }) {
  if (!section || section.total_items === 0) return null
  return (
    <div className="pr-evidence-section">
      <div className="pr-section-head">
        <strong>{section.title}</strong>
        <span className="pr-section-count">{pluralize(section.total_items, "item")}</span>
      </div>
      <div className="pr-evidence-list">
        {section.items.map((item: F8EvidenceItemSimple) => (
          <div className="pr-evidence-item" key={item.evidence_id}>
            <div className="pr-evidence-tags">
              <Tag
                text={formatLabel(item.direction)}
                tone={item.direction === "POSITIVE" ? "green" : item.direction === "NEGATIVE" ? "red" : "slate"}
              />
              <Tag text={formatLabel(item.epistemic_type)} tone="slate" />
            </div>
            <strong>{item.title}</strong>
            <p>{item.explanation}</p>
            <div className="pr-evidence-meta">
              {item.confidence && <span>Confidence: {formatConfidence(item.confidence)}</span>}
              <span>Reliability: {formatLabel(item.reliability)}</span>
              {item.observation_at && <span>Observed: {formatIso(item.observation_at)}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ConflictCard({ conflict }: { conflict: F8ConflictDetail }) {
  return (
    <div className="pr-conflict">
      <div className="pr-conflict-head">
        <AlertTriangle size={14} />
        <strong>{conflict.topic}</strong>
        {conflict.management_involved && <Tag text="Management involved" tone="red" />}
      </div>
      <p>{conflict.description}</p>
      <div className="pr-conflict-sides">
        <div className="pr-conflict-side">
          <Tag
            text={formatLabel(conflict.first_direction)}
            tone={conflict.first_direction === "POSITIVE" ? "green" : "red"}
          />
          <strong>{conflict.first_title}</strong>
          <span>{conflict.first_source}</span>
          {conflict.first_excerpt && <p>{conflict.first_excerpt}</p>}
        </div>
        <div className="pr-conflict-vs">vs</div>
        <div className="pr-conflict-side">
          <Tag
            text={formatLabel(conflict.second_direction)}
            tone={conflict.second_direction === "POSITIVE" ? "green" : "red"}
          />
          <strong>{conflict.second_title}</strong>
          <span>{conflict.second_source}</span>
          {conflict.second_excerpt && <p>{conflict.second_excerpt}</p>}
        </div>
      </div>
    </div>
  )
}

function ExecutiveOverviewView({ overview }: { overview: F8ExecutiveOverview }) {
  return (
    <div className="pr-exec">
      <div className="pr-exec-header">
        <div className="pr-exec-dir">
          <Tag
            text={formatLabel(overview.evidence_direction)}
            tone={overview.evidence_direction === "POSITIVE" ? "green" : overview.evidence_direction === "NEGATIVE" ? "red" : "slate"}
          />
          <span>Direction confidence: {formatConfidence(overview.evidence_direction_confidence)}</span>
        </div>
        <div className="pr-exec-counts">
          <span className="pr-exec-count pr-pos">{overview.positive_count} positive</span>
          <span className="pr-exec-count pr-neg">{overview.negative_count} negative</span>
          <span className="pr-exec-count pr-con">{overview.conflicting_count} conflicting</span>
          <span className="pr-exec-count">{overview.total_evidence} total</span>
        </div>
      </div>
      {overview.key_findings.length > 0 && (
        <div className="pr-exec-group">
          <strong>Key Findings</strong>
          {overview.key_findings.map((item) => (
            <ReportItemCard key={item.item_id} item={item} />
          ))}
        </div>
      )}
      {overview.what_changed.length > 0 && (
        <div className="pr-exec-group">
          <strong>What Changed</strong>
          {overview.what_changed.map((item) => (
            <ReportItemCard key={item.item_id} item={item} />
          ))}
        </div>
      )}
      {overview.hidden_insights.length > 0 && (
        <div className="pr-exec-group">
          <strong>Hidden Insights</strong>
          {overview.hidden_insights.map((item) => (
            <ReportItemCard key={item.item_id} item={item} />
          ))}
        </div>
      )}
      {overview.key_risks.length > 0 && (
        <div className="pr-exec-group">
          <strong>Key Risks</strong>
          {overview.key_risks.map((item) => (
            <ReportItemCard key={item.item_id} item={item} />
          ))}
        </div>
      )}
      {overview.cannot_assess.length > 0 && (
        <div className="pr-exec-group pr-cannot-assess">
          <strong>Cannot Assess (Insufficient Evidence)</strong>
          {overview.cannot_assess.map((note, i) => (
            <div className="pr-cannot-item" key={i}>
              <MinusCircle size={14} />
              <span>{note}</span>
            </div>
          ))}
        </div>
      )}
      {overview.uncertainties.length > 0 && (
        <div className="pr-exec-group">
          <strong>Uncertainties</strong>
          <div className="pr-uncertainties">
            {overview.uncertainties.map((u, i) => (
              <Tag key={i} text={u} tone="slate" />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ── Sub-components (Part 2: Source Health, PIT, Quality, Methodology) ── */

function SourceHealthView({ health }: { health: F8SourceHealth }) {
  return (
    <div className="pr-source-health">
      <div className="pr-sh-summary">
        <span>{health.total_sources} sources total</span>
        <span className="pr-sh-ok">{health.healthy_sources} healthy</span>
        {health.degraded_sources > 0 && (
          <span className="pr-sh-warn">{health.degraded_sources} degraded</span>
        )}
        {health.stale_sources > 0 && (
          <span className="pr-sh-warn">{health.stale_sources} stale</span>
        )}
        {health.missing_sources > 0 && (
          <span className="pr-sh-err">{health.missing_sources} missing</span>
        )}
      </div>
      {health.entries.length > 0 && (
        <div className="pr-sh-list">
          {health.entries.map((entry) => (
            <div className="pr-sh-entry" key={entry.source_id}>
              <div className="pr-sh-entry-head">
                <strong>{formatSourceName(entry.name)}</strong>
                <Tag text={formatLabel(entry.freshness_status)} tone={entry.stale ? "red" : "green"} />
                {entry.provenance_complete && <Tag text="Provenance OK" tone="green" />}
              </div>
              <div className="pr-sh-entry-meta">
                <span>{entry.evidence_count} evidence items</span>
                {entry.source_type && <span>{formatLabel(entry.source_type)}</span>}
                <span>Tier {entry.reliability_tier}</span>
              </div>
            </div>
          ))}
        </div>
      )}
      {health.provider_failures.length > 0 && (
        <div className="pr-sh-failures">
          <strong>Provider Failures</strong>
          {health.provider_failures.map((f, i) => (
            <div key={i}><XCircle size={12} /> {f}</div>
          ))}
        </div>
      )}
    </div>
  )
}

function PITIntegrityView({ pit }: { pit: F8PITIntegrity }) {
  return (
    <div className="pr-pit">
      <div className="pr-pit-row">
        <span>As-of: {formatIso(pit.as_of)}</span>
        {pit.effective_as_of && <span>Effective: {formatIso(pit.effective_as_of)}</span>}
        {pit.market_as_of && <span>Market: {formatIso(pit.market_as_of)}</span>}
      </div>
      <div className="pr-pit-row">
        <span>Evidence included: {pit.evidence_included}</span>
        <span>Future excluded: {pit.future_evidence_excluded}</span>
        <span>Sources: {pit.sources_accepted}/{pit.sources_discovered}</span>
      </div>
      <div className="pr-pit-status">
        {pit.pit_checks_passed ? (
          <><CheckCircle size={14} /> PIT checks passed</>
        ) : (
          <><AlertTriangle size={14} /> PIT checks failed</>
        )}
      </div>
    </div>
  )
}

function QualityLayerView({ quality }: { quality: F8QualityLayer }) {
  return (
    <div className="pr-quality">
      <div className="pr-ql-metrics">
        <div className="pr-ql-metric">
          <span className="pr-ql-label">Evidence coverage</span>
          <span className="pr-ql-value">{quality.evidence_coverage_pct}</span>
        </div>
        <div className="pr-ql-metric">
          <span className="pr-ql-label">Provenance coverage</span>
          <span className="pr-ql-value">{quality.provenance_coverage_pct}</span>
        </div>
        <div className="pr-ql-metric">
          <span className="pr-ql-label">Source freshness</span>
          <span className="pr-ql-value">{quality.source_freshness_pct}</span>
        </div>
        <div className="pr-ql-metric">
          <span className="pr-ql-label">PIT status</span>
          <span className="pr-ql-value">{formatLabel(quality.pit_status)}</span>
        </div>
      </div>
      {quality.unresolved_conflict_count > 0 && (
        <div className="pr-ql-issue"><AlertTriangle size={12} /> {pluralize(quality.unresolved_conflict_count, "unresolved conflict")}</div>
      )}
      {quality.critical_gap_count > 0 && (
        <div className="pr-ql-issue"><AlertTriangle size={12} /> {pluralize(quality.critical_gap_count, "critical gap")}</div>
      )}
      {quality.stale_input_count > 0 && (
        <div className="pr-ql-issue"><AlertTriangle size={12} /> {pluralize(quality.stale_input_count, "stale input")}</div>
      )}
    </div>
  )
}

function MethodologyView({ methodology }: { methodology: F8Methodology }) {
  return (
    <div className="pr-methodology">
      {methodology.methodology_summary && <p>{methodology.methodology_summary}</p>}
      {methodology.known_limitations.length > 0 && (
        <div className="pr-method-limits">
          <strong>Known Limitations</strong>
          {methodology.known_limitations.map((l, i) => (
            <div key={i}><MinusCircle size={12} /> {l}</div>
          ))}
        </div>
      )}
      {methodology.PIT_policy && (
        <div className="pr-method-field"><strong>PIT Policy:</strong> {methodology.PIT_policy}</div>
      )}
      {methodology.epistemic_disclosure && (
        <div className="pr-method-field"><strong>Epistemic Disclosure:</strong> {methodology.epistemic_disclosure}</div>
      )}
      {methodology.data_freshness_note && (
        <div className="pr-method-field"><strong>Data Freshness:</strong> {methodology.data_freshness_note}</div>
      )}
    </div>
  )
}

/* ── Main Component ─────────────────────────────────────────────── */

export default function ProfessionalReportPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)
  const [report, setReport] = useState<CompanyProfessionalReportResponse | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)

  const researchable = useMemo(() => items.filter((i) => i.research_available), [items])

  useEffect(() => {
    let cancelled = false
    fetchDiscovery()
      .then((res) => {
        if (cancelled) return
        setItems(res.results)
        setLoading(false)
      })
      .catch((err: unknown) => { if (!cancelled) { setError(err instanceof Error ? err.message : "Discovery unavailable"); setLoading(false) } })
    return () => { cancelled = true }
  }, [])

  const filteredCompanies = useMemo(() => {
    const q = query.toLowerCase()
    if (!q) return researchable
    return researchable.filter((i) =>
      i.symbol.toLowerCase().includes(q) ||
      (i.company_name ?? "").toLowerCase().includes(q) ||
      i.sector.toLowerCase().includes(q)
    )
  }, [researchable, query])

  const loadReport = useCallback(async (sym: string) => {
    setSelectedSymbol(sym)
    setReport(null)
    setReportLoading(true)
    setReportError(null)
    // Keep the selection in the URL so report links can be shared and
    // survive a page refresh.
    setSearchParams(new URLSearchParams({ company: sym }), { replace: true })
    try {
      const result = await fetchProfessionalReport(sym)
      setReport(result)
    } catch (err) {
      setReportError(
        err instanceof ApiError ? err.message :
        err instanceof Error ? err.message : "Failed to load report"
      )
    } finally {
      setReportLoading(false)
    }
  }, [setSearchParams])

  /* Deep-link support: /professional-report?company=SYMBOL (used by the
     Reports page) opens that company's report directly once the company
     list has arrived. Deferred to a task so state updates stay outside
     the synchronous effect body. */
  const deepLinkApplied = useRef(false)
  useEffect(() => {
    if (deepLinkApplied.current || loading || error || selectedSymbol) return
    const requested = searchParams.get("company")
    if (!requested) return
    if (!items.some((i) => i.symbol === requested && i.research_available)) {
      if (!loading) deepLinkApplied.current = true // unknown symbol: don't loop
      return
    }
    deepLinkApplied.current = true
    const timer = window.setTimeout(() => { void loadReport(requested) }, 0)
    return () => window.clearTimeout(timer)
  }, [searchParams, items, loading, error, selectedSymbol, loadReport])

  const r: F8ProfessionalReport | null = report?.report ?? null

  const narrativeSections: Array<{ key: keyof F8ProfessionalReport; title: string }> = [
    { key: "research_snapshot", title: "Research Snapshot" },
    { key: "business_context", title: "Business Context" },
    { key: "financial_performance", title: "Financial Performance" },
    { key: "financial_quality", title: "Financial Quality" },
    { key: "market_context", title: "Market Context" },
    { key: "business_developments", title: "Business Developments" },
    { key: "management_strategy", title: "Management & Strategy" },
    { key: "competitive_position", title: "Competitive Position" },
    { key: "innovation", title: "Innovation & R&D" },
    { key: "future_technology", title: "Future Technology" },
    { key: "industry_context", title: "Industry Context" },
    { key: "capital_allocation", title: "Capital Allocation" },
    { key: "corporate_actions", title: "Corporate Actions" },
    { key: "timeline", title: "Timeline" },
    { key: "research_gaps", title: "Research Gaps" },
  ]

  return (
    <div className="page-pr">
      <section className="page-hero">
        <h1>Professional Research Report</h1>
        <p className="page-subtitle">
          22-section canonical report assembled from evidence lineage.
          Every section is explicitly labeled by epistemic type. No scores,
          no rankings, no recommendations.
        </p>
      </section>

      {loading && (
        <div className="loading-state" role="status">
          <Activity className="spin" size={26} />
          <strong>Loading companies</strong>
        </div>
      )}

      {error && (
        <div className="empty-state error" role="alert">
          <FileSearch size={28} />
          <strong>Discovery unavailable</strong>
          <p>{error}</p>
        </div>
      )}

      {!loading && !error && (
        <div className="pr-layout">
          <div className="pr-sidebar">
            <div className="panel">
              <div className="panel-head">
                <h3>Select Company</h3>
                <span>{researchable.length} companies</span>
              </div>
              <div className="pr-search">
                <Search size={14} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Filter companies..."
                  aria-label="Filter companies"
                />
              </div>
              <div className="pr-company-list">
                {filteredCompanies.map((item) => (
                  <button
                    key={item.symbol}
                    className={`pr-company-item ${selectedSymbol === item.symbol ? "active" : ""}`}
                    onClick={() => void loadReport(item.symbol)}
                  >
                    <Building2 size={13} />
                    <div>
                      <strong>{item.symbol}</strong>
                      <small>{item.company_name ?? item.symbol}</small>
                    </div>
                  </button>
                ))}
                {filteredCompanies.length === 0 && (
                  <div className="pr-empty-list"><Search size={14} /><span>No matching companies</span></div>
                )}
              </div>
            </div>
            <div className="panel">
              <div className="panel-head"><h3>Report Principles</h3></div>
              <div className="pr-principles">
                <div className="pr-principle">
                  <span className="pr-principle-label">Evidence-first</span>
                  <span className="pr-principle-text">Every claim is backed by evidence with source provenance</span>
                </div>
                <div className="pr-principle">
                  <span className="pr-principle-label">Point-in-time</span>
                  <span className="pr-principle-text">Evidence is validated against the requested as-of date</span>
                </div>
                <div className="pr-principle">
                  <span className="pr-principle-label">No scores</span>
                  <span className="pr-principle-text">No rankings, scores, or investment recommendations</span>
                </div>
                <div className="pr-principle">
                  <span className="pr-principle-label">Transparent</span>
                  <span className="pr-principle-text">Unknown data is shown, never inferred or fabricated</span>
                </div>
              </div>
            </div>
          </div>

          <div className="pr-content">
            {!selectedSymbol && (
              <div className="empty-state">
                <FileSearch size={28} />
                <strong>Select a company</strong>
                <p>Choose a company to view its professional research report.</p>
              </div>
            )}

            {selectedSymbol && reportLoading && (
              <div className="loading-state" role="status">
                <Activity className="spin" size={26} />
                <strong>Loading report</strong>
                <span>Fetching report for {selectedSymbol}...</span>
              </div>
            )}

            {selectedSymbol && reportError && (
              <div className="empty-state error" role="alert">
                <FileSearch size={28} />
                <strong>Could not load report</strong>
                <p>{reportError}</p>
              </div>
            )}

            {selectedSymbol && r && !reportLoading && (
              <>
                {r.executive_overview && <ExecutiveOverviewView overview={r.executive_overview} />}

                {narrativeSections.map(({ key }) => {
                  const section = r[key] as F8ReportSection | null | undefined
                  if (!section || section.status === "MISSING" || section.total_items === 0) return null
                  return <ReportSection key={key} section={section} defaultOpen={key === "research_snapshot"} />
                })}

                {r.positive_evidence && r.positive_evidence.total_items > 0 && (
                  <EvidenceSectionView section={r.positive_evidence} />
                )}
                {r.negative_evidence && r.negative_evidence.total_items > 0 && (
                  <EvidenceSectionView section={r.negative_evidence} />
                )}
                {r.conflicting_evidence && r.conflicting_evidence.total_items > 0 && (
                  <EvidenceSectionView section={r.conflicting_evidence} />
                )}

                {r.conflict_details.length > 0 && (
                  <div className="pr-conflicts-section">
                    <div className="pr-section-head">
                      <AlertTriangle size={14} />
                      <strong>Evidence Conflicts ({r.conflict_details.length})</strong>
                    </div>
                    {r.conflict_details.map((c) => (
                      <ConflictCard key={c.conflict_id} conflict={c} />
                    ))}
                  </div>
                )}

                {r.source_health && <SourceHealthView health={r.source_health} />}
                {r.pit_integrity && <PITIntegrityView pit={r.pit_integrity} />}
                {r.methodology && <MethodologyView methodology={r.methodology} />}
                {r.quality_layer && <QualityLayerView quality={r.quality_layer} />}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
