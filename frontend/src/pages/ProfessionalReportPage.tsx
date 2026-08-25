/**
 * PROFESSIONAL REPORT — document reader.
 *
 * Composition:
 *   LEFT    · table of contents   sections that exist in THIS report, with
 *                                 item counts; anchor-scrolls the document
 *   CENTRE  · reading area         report masthead → executive overview →
 *                                 narrative sections (continuous prose-style
 *                                 document) → evidence appendix → conflicts
 *                                 → methodology & limitations
 *   RIGHT   · research-context rail  point-in-time integrity · quality layer ·
 *                                 source-health summary · principles
 *
 * Repetition is reduced deliberately: the executive overview renders compact
 * item references rather than repeating full evidence cards, per-direction
 * evidence moves to a collapsed appendix, and the source rail summarizes
 * healthy sources to counts while listing only degraded/stale/missing ones.
 *
 * No scores, no rankings, no recommendations.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useSearchParams } from "react-router-dom"
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  FileSearch,
  ListTree,
  MinusCircle,
  Search,
  XCircle,
} from "lucide-react"
import { ApiError, fetchDiscovery, fetchProfessionalReport } from "../api/client"
import type {
  CompanyProfessionalReportResponse,
  DiscoveryItem,
  F8ConflictDetail,
  F8EvidenceItemSimple,
  F8EvidenceSection,
  F8ExecutiveOverview,
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

function directionTone(direction: string): "green" | "red" | "slate" {
  if (direction === "POSITIVE") return "green"
  if (direction === "NEGATIVE") return "red"
  return "slate"
}

const NARRATIVE_SECTIONS: Array<{ key: keyof F8ProfessionalReport; title: string }> = [
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

function sectionId(key: string): string {
  return `pr-sec-${key.replace(/_/g, "-")}`
}

/* ── Document primitives ─────────────────────────────────────────── */

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

/** Compact reference used inside the executive overview: keeps the claim and
 *  its epistemic label without re-rendering the full evidence card. */
function ItemReference({ item }: { item: F8ReportItem }) {
  return (
    <li className="pr-item-ref">
      <Tag text={formatLabel(item.epistemic_type)} tone={epistemicBadge(item.epistemic_type)} />
      <span>{item.text}</span>
    </li>
  )
}

/** A narrative section rendered as part of the continuous document. */
function DocumentSection({
  id,
  title,
  count,
  children,
}: {
  id: string
  title: string
  count?: number
  children: React.ReactNode
}) {
  return (
    <section className="pr-doc-section" id={id}>
      <h2 className="pr-doc-title">
        {title}
        {count !== undefined && <span className="pr-section-count">{pluralize(count, "item")}</span>}
      </h2>
      {children}
    </section>
  )
}

function EvidenceAppendixSection({ section }: { section: F8EvidenceSection }) {
  if (!section || section.total_items === 0) return null
  return (
    <details className="pr-appendix-section">
      <summary>
        <strong>{section.title}</strong>
        <span className="pr-section-count">{pluralize(section.total_items, "item")}</span>
        <ChevronDown size={14} />
      </summary>
      <div className="pr-evidence-list">
        {section.items.map((item: F8EvidenceItemSimple) => (
          <div className="pr-evidence-item" key={item.evidence_id}>
            <div className="pr-evidence-tags">
              <Tag text={formatLabel(item.direction)} tone={directionTone(item.direction)} />
              <Tag text={formatLabel(item.epistemic_type)} tone="slate" />
            </div>
            <strong>{item.title}</strong>
            <p>{item.explanation}</p>
            <div className="pr-evidence-meta">
              {item.confidence && <span>Reliability: {formatConfidence(item.confidence)}</span>}
              <span>Grade: {formatLabel(item.reliability)}</span>
              {item.observation_at && <span>Observed: {formatIso(item.observation_at)}</span>}
            </div>
          </div>
        ))}
      </div>
    </details>
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
          <Tag text={formatLabel(conflict.first_direction)} tone={directionTone(conflict.first_direction)} />
          <strong>{conflict.first_title}</strong>
          <span>{conflict.first_source}</span>
          {conflict.first_excerpt && <p>{conflict.first_excerpt}</p>}
        </div>
        <div className="pr-conflict-vs">vs</div>
        <div className="pr-conflict-side">
          <Tag text={formatLabel(conflict.second_direction)} tone={directionTone(conflict.second_direction)} />
          <strong>{conflict.second_title}</strong>
          <span>{conflict.second_source}</span>
          {conflict.second_excerpt && <p>{conflict.second_excerpt}</p>}
        </div>
      </div>
    </div>
  )
}

/* ── Executive overview ──────────────────────────────────────────── */

function ExecutiveOverview({ overview }: { overview: F8ExecutiveOverview }) {
  const groups: Array<{ title: string; items: F8ReportItem[] }> = [
    { title: "Key findings", items: overview.key_findings },
    { title: "What changed", items: overview.what_changed },
    { title: "Hidden insights", items: overview.hidden_insights },
    { title: "Key risks", items: overview.key_risks },
  ]

  return (
    <section className="pr-doc-section pr-exec" id={sectionId("executive_overview")}>
      <h2 className="pr-doc-title">Executive Overview</h2>
      <div className="pr-exec-header">
        <div className="pr-exec-dir">
          <Tag text={`${formatLabel(overview.evidence_direction)} direction`} tone={directionTone(overview.evidence_direction)} />
          <span>Direction reliability: {formatConfidence(overview.evidence_direction_confidence)}</span>
        </div>
        <div className="pr-exec-counts">
          <span className="pr-exec-count pr-pos">{overview.positive_count} positive</span>
          <span className="pr-exec-count pr-neg">{overview.negative_count} negative</span>
          <span className="pr-exec-count pr-con">{overview.conflicting_count} conflicting</span>
          <span className="pr-exec-count">{overview.total_evidence} total</span>
        </div>
      </div>

      {groups.map(
        (group) =>
          group.items.length > 0 && (
            <div className="pr-exec-group" key={group.title}>
              <h3>{group.title}</h3>
              <ul>
                {group.items.map((item) => (
                  <ItemReference key={item.item_id} item={item} />
                ))}
              </ul>
            </div>
          ),
      )}

      {overview.cannot_assess.length > 0 && (
        <div className="pr-exec-group pr-cannot-assess">
          <h3>Cannot assess (insufficient evidence)</h3>
          {overview.cannot_assess.map((note, index) => (
            <div className="pr-cannot-item" key={index}>
              <MinusCircle size={14} />
              <span>{note}</span>
            </div>
          ))}
        </div>
      )}

      {overview.uncertainties.length > 0 && (
        <div className="pr-exec-group">
          <h3>Uncertainties</h3>
          <div className="pr-uncertainties">
            {overview.uncertainties.map((u, index) => (
              <Tag key={index} text={u} tone="slate" />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

/* ── Right-rail context blocks ───────────────────────────────────── */

function RailPIT({ pit }: { pit: F8PITIntegrity }) {
  return (
    <div className="pr-rail-block">
      <h4><CheckCircle size={13} /> Point-in-time</h4>
      <dl className="pr-rail-facts">
        <div><dt>As-of</dt><dd>{formatIso(pit.as_of)}</dd></div>
        {pit.effective_as_of && <div><dt>Effective</dt><dd>{formatIso(pit.effective_as_of)}</dd></div>}
        <div><dt>Evidence included</dt><dd>{pit.evidence_included}</dd></div>
        <div><dt>Future excluded</dt><dd>{pit.future_evidence_excluded}</dd></div>
        <div><dt>Sources accepted</dt><dd>{pit.sources_accepted}/{pit.sources_discovered}</dd></div>
      </dl>
      <p className={`pr-rail-status ${pit.pit_checks_passed ? "ok" : "bad"}`}>
        {pit.pit_checks_passed ? "PIT checks passed" : "PIT checks failed"}
      </p>
    </div>
  )
}

function RailQuality({ quality }: { quality: F8QualityLayer }) {
  return (
    <div className="pr-rail-block">
      <h4>Report quality</h4>
      <dl className="pr-rail-facts">
        <div><dt>Evidence coverage</dt><dd>{quality.evidence_coverage_pct}</dd></div>
        <div><dt>Provenance coverage</dt><dd>{quality.provenance_coverage_pct}</dd></div>
        <div><dt>Source freshness</dt><dd>{quality.source_freshness_pct}</dd></div>
        <div><dt>PIT status</dt><dd>{formatLabel(quality.pit_status)}</dd></div>
      </dl>
      {(quality.unresolved_conflict_count > 0 ||
        quality.critical_gap_count > 0 ||
        quality.stale_input_count > 0) && (
        <ul className="pr-rail-warnings">
          {quality.unresolved_conflict_count > 0 && (
            <li><AlertTriangle size={12} /> {pluralize(quality.unresolved_conflict_count, "unresolved conflict")}</li>
          )}
          {quality.critical_gap_count > 0 && (
            <li><AlertTriangle size={12} /> {pluralize(quality.critical_gap_count, "critical gap")}</li>
          )}
          {quality.stale_input_count > 0 && (
            <li><AlertTriangle size={12} /> {pluralize(quality.stale_input_count, "stale input")}</li>
          )}
        </ul>
      )}
    </div>
  )
}

/** Source health reduced to headline counts; only problem sources are listed. */
function RailSourceHealth({ health }: { health: F8SourceHealth }) {
  const problemSources = health.entries.filter(
    (entry) => entry.stale || !entry.provenance_complete || formatLabel(entry.freshness_status) !== "Healthy",
  )
  return (
    <div className="pr-rail-block">
      <h4>Source health</h4>
      <div className="pr-sh-summary">
        <span>{health.total_sources} sources</span>
        <span className="pr-sh-ok">{health.healthy_sources} healthy</span>
        {health.degraded_sources > 0 && <span className="pr-sh-warn">{health.degraded_sources} degraded</span>}
        {health.stale_sources > 0 && <span className="pr-sh-warn">{health.stale_sources} stale</span>}
        {health.missing_sources > 0 && <span className="pr-sh-err">{health.missing_sources} missing</span>}
      </div>
      {problemSources.length > 0 && (
        <ul className="pr-rail-source-list">
          {problemSources.slice(0, 6).map((entry) => (
            <li key={entry.source_id}>
              <strong>{formatSourceName(entry.name)}</strong>
              <Tag text={formatLabel(entry.freshness_status)} tone="amber" />
            </li>
          ))}
        </ul>
      )}
      {health.provider_failures.length > 0 && (
        <ul className="pr-rail-warnings">
          {health.provider_failures.map((failure, index) => (
            <li key={index}><XCircle size={12} /> {failure}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function RailPrinciples() {
  return (
    <div className="pr-rail-block pr-rail-principles">
      <h4>Report principles</h4>
      <ul>
        <li><strong>Evidence-first.</strong> Every claim carries source provenance.</li>
        <li><strong>Point-in-time.</strong> Evidence is validated against the requested as-of date.</li>
        <li><strong>No scores.</strong> No rankings or recommendations.</li>
        <li><strong>Transparent.</strong> Unknown data is shown, never inferred or fabricated.</li>
      </ul>
    </div>
  )
}

/* ── Main component ──────────────────────────────────────────────── */

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

  const researchable = useMemo(() => items.filter((item) => item.research_available), [items])

  useEffect(() => {
    let cancelled = false
    fetchDiscovery()
      .then((res) => {
        if (cancelled) return
        setItems(res.results)
        setLoading(false)
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Discovery unavailable")
          setLoading(false)
        }
      })
    return () => { cancelled = true }
  }, [])

  const filteredCompanies = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return researchable
    return researchable.filter(
      (item) =>
        item.symbol.toLowerCase().includes(q) ||
        (item.company_name ?? "").toLowerCase().includes(q),
    )
  }, [researchable, query])

  const loadReport = useCallback(
    async (sym: string) => {
      setSelectedSymbol(sym)
      setReport(null)
      setReportLoading(true)
      setReportError(null)
      // Keep the selection in the URL so report links survive refresh/share.
      setSearchParams(new URLSearchParams({ company: sym }), { replace: true })
      try {
        const result = await fetchProfessionalReport(sym)
        setReport(result)
      } catch (err) {
        setReportError(
          err instanceof ApiError
            ? err.message
            : err instanceof Error
              ? err.message
              : "Failed to load report",
        )
      } finally {
        setReportLoading(false)
      }
    },
    [setSearchParams],
  )

  /* Deep-link support: /professional-report?company=SYMBOL opens that
     company's report directly once discovery arrives. */
  const deepLinkApplied = useRef(false)
  useEffect(() => {
    if (deepLinkApplied.current || loading || error || selectedSymbol) return
    const requested = searchParams.get("company")
    if (!requested) return
    if (!items.some((item) => item.symbol === requested && item.research_available)) {
      if (!loading) deepLinkApplied.current = true // unknown symbol: don't loop
      return
    }
    deepLinkApplied.current = true
    const timer = window.setTimeout(() => { void loadReport(requested) }, 0)
    return () => window.clearTimeout(timer)
  }, [searchParams, items, loading, error, selectedSymbol, loadReport])

  const r: F8ProfessionalReport | null = report?.report ?? null

  /** TOC entries derived from what this specific report actually contains. */
  const toc = useMemo(() => {
    if (!r) return []
    const entries: Array<{ id: string; title: string; count?: number }> = []
    if (r.executive_overview) {
      entries.push({ id: sectionId("executive_overview"), title: "Executive Overview" })
    }
    for (const { key, title } of NARRATIVE_SECTIONS) {
      const section = r[key] as F8ReportSection | null | undefined
      if (section && section.status !== "MISSING" && section.total_items > 0) {
        entries.push({ id: sectionId(String(key)), title, count: section.total_items })
      }
    }
    const appendixCount =
      (r.positive_evidence?.total_items ?? 0) +
      (r.negative_evidence?.total_items ?? 0) +
      (r.conflicting_evidence?.total_items ?? 0)
    if (appendixCount > 0) {
      entries.push({ id: sectionId("evidence_appendix"), title: "Evidence Appendix", count: appendixCount })
    }
    if (r.conflict_details.length > 0) {
      entries.push({ id: sectionId("conflicts"), title: "Evidence Conflicts", count: r.conflict_details.length })
    }
    if (r.methodology) {
      entries.push({ id: sectionId("methodology"), title: "Methodology & Limitations" })
    }
    return entries
  }, [r])

  const selectedItem = items.find((item) => item.symbol === selectedSymbol)

  return (
    <div className="page-pr">
      {/* Compact company selector bar */}
      <section className="page-hero pr-hero">
        <div>
          <p className="page-kicker">Output</p>
          <h1>Professional Research Report</h1>
          <p className="page-subtitle">
            Canonical report assembled from evidence lineage, labelled by epistemic type.
            No scores, no rankings, no recommendations.
          </p>
        </div>
        {!loading && !error && (
          <div className="pr-selector">
            <Search size={14} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Find company…"
              aria-label="Filter companies"
            />
            <select
              value={selectedSymbol ?? ""}
              onChange={(event) => {
                if (event.target.value) void loadReport(event.target.value)
              }}
              aria-label="Select company report"
            >
              <option value="" disabled>
                Select company ({researchable.length})
              </option>
              {filteredCompanies.map((item) => (
                <option key={item.symbol} value={item.symbol}>
                  {item.symbol} — {item.company_name ?? item.symbol}
                </option>
              ))}
            </select>
          </div>
        )}
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
        <div className="pr-reader-layout">
          {/* ── LEFT · table of contents ─────────────────────────── */}
          {r && toc.length > 0 && (
            <aside className="pr-toc" aria-label="Report contents">
              <div className="pr-toc-head">
                <ListTree size={14} />
                <strong>Contents</strong>
              </div>
              <nav>
                <ol>
                  {toc.map((entry) => (
                    <li key={entry.id}>
                      <a href={`#${entry.id}`}>
                        <span>{entry.title}</span>
                        {entry.count !== undefined && <small>{entry.count}</small>}
                      </a>
                    </li>
                  ))}
                </ol>
              </nav>
            </aside>
          )}

          {/* ── CENTRE · reading area ────────────────────────────── */}
          <article className="pr-document">
            {!selectedSymbol && (
              <div className="empty-state">
                <FileSearch size={28} />
                <strong>Select a company</strong>
                <p>Choose a company above to open its professional research report.</p>
              </div>
            )}

            {selectedSymbol && reportLoading && (
              <div className="loading-state" role="status">
                <Activity className="spin" size={26} />
                <strong>Loading report</strong>
                <span>Fetching report for {selectedSymbol}…</span>
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
                {/* Report masthead */}
                <header className="pr-masthead">
                  <p className="mono pr-masthead-symbol">{selectedSymbol}</p>
                  <h2>{selectedItem?.company_name ?? selectedSymbol}</h2>
                  {r.pit_integrity && (
                    <p className="pr-masthead-meta">
                      Generated as of {formatIso(r.pit_integrity.as_of)}
                      {r.pit_integrity.effective_as_of &&
                        ` · effective ${formatIso(r.pit_integrity.effective_as_of)}`}
                    </p>
                  )}
                </header>

                {r.executive_overview && <ExecutiveOverview overview={r.executive_overview} />}

                {NARRATIVE_SECTIONS.map(({ key, title }) => {
                  const section = r[key] as F8ReportSection | null | undefined
                  if (!section || section.status === "MISSING" || section.total_items === 0) {
                    return null
                  }
                  return (
                    <DocumentSection
                      key={key}
                      id={sectionId(String(key))}
                      title={title}
                      count={section.total_items}
                    >
                      <div className={`pr-doc-body epistemic-${section.epistemic_type.toLowerCase()}`}>
                        {section.items.map((item) => (
                          <ReportItemCard key={item.item_id} item={item} />
                        ))}
                        {section.notes.length > 0 && (
                          <div className="pr-section-notes">
                            {section.notes.map((note, index) => (
                              <span key={index}>{note}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    </DocumentSection>
                  )
                })}

                {(r.positive_evidence?.total_items ?? 0) +
                  (r.negative_evidence?.total_items ?? 0) +
                  (r.conflicting_evidence?.total_items ?? 0) >
                  0 && (
                  <DocumentSection
                    id={sectionId("evidence_appendix")}
                    title="Evidence Appendix"
                  >
                    <p className="pr-appendix-note">
                      Per-direction evidence register. The same items are summarised above where
                      they inform each section; this appendix lists them in raw form.
                    </p>
                    <EvidenceAppendixSection section={r.positive_evidence!} />
                    <EvidenceAppendixSection section={r.negative_evidence!} />
                    <EvidenceAppendixSection section={r.conflicting_evidence!} />
                  </DocumentSection>
                )}

                {r.conflict_details.length > 0 && (
                  <DocumentSection
                    id={sectionId("conflicts")}
                    title="Evidence Conflicts"
                    count={r.conflict_details.length}
                  >
                    {r.conflict_details.map((conflict) => (
                      <ConflictCard key={conflict.conflict_id} conflict={conflict} />
                    ))}
                  </DocumentSection>
                )}

                {r.methodology && (
                  <DocumentSection id={sectionId("methodology")} title="Methodology & Limitations">
                    <div className="pr-methodology">
                      {r.methodology.methodology_summary && <p>{r.methodology.methodology_summary}</p>}
                      {r.methodology.known_limitations.length > 0 && (
                        <div className="pr-method-limits">
                          <strong>Known limitations</strong>
                          {r.methodology.known_limitations.map((limitation, index) => (
                            <div key={index}><MinusCircle size={12} /> {limitation}</div>
                          ))}
                        </div>
                      )}
                      {r.methodology.PIT_policy && (
                        <div className="pr-method-field"><strong>PIT policy:</strong> {r.methodology.PIT_policy}</div>
                      )}
                      {r.methodology.epistemic_disclosure && (
                        <div className="pr-method-field"><strong>Epistemic disclosure:</strong> {r.methodology.epistemic_disclosure}</div>
                      )}
                      {r.methodology.data_freshness_note && (
                        <div className="pr-method-field"><strong>Data freshness:</strong> {r.methodology.data_freshness_note}</div>
                      )}
                    </div>
                  </DocumentSection>
                )}
              </>
            )}
          </article>

          {/* ── RIGHT · research-context rail ────────────────────── */}
          {r && !reportLoading && (
            <aside className="pr-rail" aria-label="Research context">
              {r.pit_integrity && <RailPIT pit={r.pit_integrity} />}
              {r.quality_layer && <RailQuality quality={r.quality_layer} />}
              {r.source_health && <RailSourceHealth health={r.source_health} />}
              <RailPrinciples />
            </aside>
          )}
        </div>
      )}
    </div>
  )
}
