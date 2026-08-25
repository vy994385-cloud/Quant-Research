/**
 * EVIDENCE EXPLORER — vertical research workflow.
 *
 *   header → search/filter bar → result summary → evidence stream → detail drawer
 *
 * Every row leads with WHAT KIND of evidence it is (epistemic state:
 * reported / derived / inferred / unknown); direction is deliberately
 * subordinate. Raw backend identifiers never appear on the primary
 * surface — they live inside the drawer's provenance section.
 * CLAIM -> EVIDENCE -> SOURCE -> RAW RECORD traceability is preserved.
 */

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  Activity,
  AlertTriangle,
  ChevronRight,
  FileSearch,
  Search,
  Shield,
} from "lucide-react"
import { fetchDiscovery, fetchEvidenceLineage, ApiError } from "../api/client"
import type {
  CompanyEvidenceResponse,
  DiscoveryItem,
  F7Claim,
  F7EvidenceItem,
} from "../api/types"
import {
  formatConfidence,
  formatEvidenceObservation,
  formatIso,
  formatLabel,
} from "../lib/format"
import { DetailDrawer } from "../components/ui"

/* ── Epistemic visual language ──────────────────────────────────────
   Reported = neutral/high-trust · Derived = teal · Inferred = steel
   Unknown = slate. Direction never outweighs epistemic class.       */

function epistemicClass(ep: string): string {
  switch (ep?.toUpperCase()) {
    case "REPORTED": return "reported"
    case "DERIVED": return "derived"
    case "INFERRED": return "inferred"
    default: return "unknown"
  }
}

function directionMark(d: string): { cls: string; label: string } | null {
  const up = d?.toUpperCase()
  if (up === "POSITIVE") return { cls: "positive", label: "Positive" }
  if (up === "NEGATIVE") return { cls: "negative", label: "Negative" }
  if (up === "NEUTRAL" || up === "MIXED") return { cls: "neutral", label: formatLabel(d) }
  return null
}

/** Observation window across the loaded stream — honest derived context. */
function observationWindow(items: F7EvidenceItem[]): string | null {
  const dates = items
    .map((e) => e.observation_at ?? e.published_at)
    .filter((d): d is string => Boolean(d))
    .sort()
  if (dates.length === 0) return null
  const first = formatIso(dates[0])
  const last = formatIso(dates[dates.length - 1])
  return first === last ? first : `${first} → ${last}`
}

/* ── Main Component ─────────────────────────────────────────────── */

export default function EvidencePage() {
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const [selectedSymbol, setSelectedSymbol] = useState<string>("")
  const [lineage, setLineage] = useState<CompanyEvidenceResponse | null>(null)
  const [lineageLoading, setLineageLoading] = useState(false)
  const [lineageError, setLineageError] = useState<string | null>(null)
  const [filterDirection, setFilterDirection] = useState("ALL")
  const [filterEpistemic, setFilterEpistemic] = useState("ALL")
  const [drawerItem, setDrawerItem] = useState<F7EvidenceItem | null>(null)

  const loadEvidence = useCallback(async (sym: string) => {
    setSelectedSymbol(sym)
    setLineage(null)
    setLineageLoading(true)
    setLineageError(null)
    setFilterDirection("ALL")
    setFilterEpistemic("ALL")
    try {
      const result = await fetchEvidenceLineage(sym)
      setLineage(result)
    } catch (err) {
      setLineageError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error ? err.message : "Failed to load evidence",
      )
    } finally {
      setLineageLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    fetchDiscovery()
      .then((res) => {
        if (!cancelled) {
          setItems(res.results)
          setLoading(false)
          const first = res.results.find((i) => i.research_available)
          if (first) void loadEvidence(first.symbol)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Discovery unavailable")
          setLoading(false)
        }
      })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const researchable = useMemo(
    () => items.filter((i) => i.research_available),
    [items],
  )



  const evidence = useMemo(
    () => lineage?.evidence_lineage?.evidence ?? [],
    [lineage],
  )
  const totalEvidence = lineage?.evidence_lineage?.total_evidence ?? 0
  const totalSources = lineage?.evidence_lineage?.total_sources ?? 0
  const pitFiltered = lineage?.evidence_lineage?.pit_filtered_count ?? 0
  const notes = lineage?.evidence_lineage?.notes ?? []
  const directionCounts = lineage?.evidence_lineage?.direction_counts ?? {}
  const epistemicCounts = useMemo(
    () => lineage?.evidence_lineage?.epistemic_type_counts ?? {},
    [lineage],
  )
  const sourceProfiles = lineage?.evidence_lineage?.source_profiles ?? []
  const claims = useMemo(
    () => lineage?.evidence_lineage?.claims ?? [],
    [lineage],
  )

  const filteredEvidence = useMemo(() => {
    let result = evidence
    if (query.trim()) {
      const q = query.trim().toLowerCase()
      result = result.filter(
        (e) =>
          e.title.toLowerCase().includes(q) ||
          e.explanation.toLowerCase().includes(q) ||
          (e.source?.name ?? "").toLowerCase().includes(q),
      )
    }
    if (filterDirection !== "ALL") {
      result = result.filter((e) => e.direction === filterDirection)
    }
    if (filterEpistemic !== "ALL") {
      result = result.filter((e) => e.epistemic_type === filterEpistemic)
    }
    return result
  }, [evidence, filterDirection, filterEpistemic, query])

  /** Claims that cite a given evidence item — shown in the drawer. */
  const relatedClaims = useMemo(() => {
    const map = new Map<string, F7Claim[]>()
    for (const claim of claims) {
      for (const id of claim.evidence_ids) {
        map.set(id, [...(map.get(id) ?? []), claim])
      }
    }
    return map
  }, [claims])

  const selectedCompany = items.find((i) => i.symbol === selectedSymbol)
  const windowLabel = observationWindow(evidence)

  if (loading || error) {
    return (
      <div className="page-evidence">
        <header className="scr-header">
          <span className="eyebrow">Evidence universe</span>
          <h1>Evidence Explorer</h1>
        </header>
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
      </div>
    )
  }

  return (
    <div className="page-evidence page-evidence--workflow">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="scr-header">
        <span className="eyebrow">Evidence universe</span>
        <h1>Evidence Explorer</h1>
        <p className="scr-subtitle">
          Search the recorded evidence universe. Every item carries its source,
          epistemic type, and point-in-time validation.
        </p>
      </header>

      {/* ── Search / filter bar ───────────────────────────────────── */}
      <section className="evx-bar scr-section" style={{ marginTop: "var(--space-5)" }} aria-label="Evidence filters">
        <div className="evx-bar-row">
          <div className="evx-search">
            <Search size={14} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search claims, explanations, sources…"
              aria-label="Search evidence"
            />
          </div>
          <div className="evx-company">
            <label className="evx-control-label" htmlFor="evx-company-select">Company</label>
            <select
              id="evx-company-select"
              className="scr-select"
              value={selectedSymbol}
              onChange={(e) => void loadEvidence(e.target.value)}
            >
              {researchable.map((item) => (
                <option key={item.symbol} value={item.symbol}>
                  {item.symbol}{item.company_name ? ` — ${item.company_name}` : ""}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="evx-bar-row">
          <SegmentedGroup
            label="Epistemic"
            value={filterEpistemic}
            onChange={setFilterEpistemic}
            options={[
              { key: "ALL", label: "All", count: totalEvidence },
              ...Object.keys(epistemicCounts).sort().map((ep) => ({
                key: ep,
                label: formatLabel(ep),
                count: epistemicCounts[ep],
              })),
            ]}
          />
          <SegmentedGroup
            label="Direction"
            value={filterDirection}
            onChange={setFilterDirection}
            options={[
              { key: "ALL", label: "All", count: totalEvidence },
              ...Object.keys(directionCounts).sort().map((dir) => ({
                key: dir,
                label: formatLabel(dir),
                count: directionCounts[dir],
              })),
            ]}
          />
        </div>
      </section>

      {/* ── Result summary ─────────────────────────────────────────── */}
      <div className="scr-context">
        <span className="scr-context-item">
          <strong>{filteredEvidence.length}</strong> of {totalEvidence} evidence items
        </span>
        <span className="scr-context-sep" />
        <span className="scr-context-item">
          <strong>{selectedSymbol || "—"}</strong> {selectedCompany?.company_name ?? ""}
        </span>
        <span className="scr-context-sep" />
        <span className="scr-context-item">
          <strong>{totalSources > 0 ? totalSources : "—"}</strong> sources
        </span>
        {windowLabel && (
          <>
            <span className="scr-context-sep" />
            <span className="scr-context-item">observed <strong>{windowLabel}</strong></span>
          </>
        )}
        {pitFiltered > 0 && (
          <>
            <span className="scr-context-sep" />
            <span className="scr-context-item evx-pit-note">
              <Shield size={11} /> {pitFiltered} excluded by point-in-time rules
            </span>
          </>
        )}
      </div>

      {/* ── Evidence stream ────────────────────────────────────────── */}
      <section className="scr-section" aria-label="Evidence stream">
        {lineageLoading && (
          <div className="loading-state" role="status">
            <Activity className="spin" size={26} />
            <strong>Loading evidence lineage</strong>
          </div>
        )}

        {lineageError && !lineageLoading && (
          <div className="empty-state error" role="alert">
            <FileSearch size={28} />
            <strong>Could not load evidence</strong>
            <p>{lineageError}</p>
          </div>
        )}

        {lineage && !lineageLoading && filteredEvidence.length === 0 && (
          <div className="empty-state">
            <Search size={24} />
            <strong>No matching evidence</strong>
            <p>{evidence.length === 0
              ? `No evidence was included for ${selectedSymbol}.`
              : "Try adjusting the filters."}</p>
          </div>
        )}

        {!lineageLoading && filteredEvidence.length > 0 && (
          <div className="evx-list">
            {filteredEvidence.map((item) => {
              const dir = directionMark(item.direction)
              return (
                <button
                  key={item.evidence_id}
                  type="button"
                  className="evx-row"
                  onClick={() => setDrawerItem(item)}
                  aria-haspopup="dialog"
                >
                  <span className="evx-date">
                    {item.observation_at ? formatEvidenceObservation(item.observation_at) : "—"}
                  </span>
                  <span className="evx-main">
                    <strong className="evx-title">{item.title}</strong>
                    <span className="evx-explanation">{item.explanation}</span>
                    <span className="evx-meta">
                      <span className={`epi-badge ${epistemicClass(item.epistemic_type)}`}>
                        {formatLabel(item.epistemic_type || "UNKNOWN")}
                      </span>
                      <span className="evx-meta-type">{formatLabel(item.evidence_type)}</span>
                      {dir && (
                        <span className={`evx-direction ${dir.cls}`}>
                          <span className="evx-direction-dot" />
                          {dir.label}
                        </span>
                      )}
                      {item.source && (
                        <span className="evx-source">{item.source.name}</span>
                      )}
                    </span>
                  </span>
                  <ChevronRight size={15} className="evx-chevron" />
                </button>
              )
            })}
          </div>
        )}
      </section>

      {/* ── Claims ─────────────────────────────────────────────────── */}
      {claims.length > 0 && !lineageLoading && lineage && (
        <details className="evx-section-collapse">
          <summary>
            Claims <span className="evx-count-chip">{claims.length}</span>
          </summary>
          <div className="evx-claims">
            {claims.map((claim) => (
              <div className="evx-claim" key={claim.claim_id}>
                <div className="evx-claim-head">
                  <span className={`epi-badge ${epistemicClass(claim.epistemic_type)}`}>
                    {formatLabel(claim.epistemic_type)}
                  </span>
                  <span className="evx-meta-type">{formatLabel(claim.category)}</span>
                </div>
                <p>{claim.text}</p>
                <div className="evx-claim-meta">
                  <span>Confidence {formatConfidence(claim.confidence)}</span>
                  <span>{formatLabel(claim.verification_status)}</span>
                  <span>{claim.evidence_ids.length} evidence item{claim.evidence_ids.length === 1 ? "" : "s"}</span>
                </div>
              </div>
            ))}
          </div>
        </details>
      )}

      {/* ── Source profiles ────────────────────────────────────────── */}
      {sourceProfiles.length > 0 && !lineageLoading && lineage && (
        <details className="evx-section-collapse">
          <summary>
            Sources <span className="evx-count-chip">{sourceProfiles.length}</span>
          </summary>
          <div className="evx-sources">
            {sourceProfiles.map((src) => (
              <div className="evx-source-row" key={src.source_id}>
                <strong>{src.name}</strong>
                <span className="evx-meta-type">{formatLabel(src.source_type)}</span>
                <span className="evx-reliability">{src.reliability_tier}</span>
                {src.domain && <span className="evx-domain">{src.domain}</span>}
              </div>
            ))}
          </div>
        </details>
      )}

      {/* ── Notes footer ───────────────────────────────────────────── */}
      {(notes.length > 0 || lineage) && !lineageLoading && lineage && (
        <footer className="evx-footnote">
          <Shield size={12} />
          <span>
            {notes.length > 0 ? notes.join(" ") : ""} Point-in-time validation keeps every
            item sourced from records available before the requested date.
          </span>
        </footer>
      )}

      {/* ── Detail drawer ──────────────────────────────────────────── */}
      <EvidenceDrawer
        item={drawerItem}
        claims={drawerItem ? relatedClaims.get(drawerItem.evidence_id) ?? [] : []}
        onClose={() => setDrawerItem(null)}
      />
    </div>
  )
}

/* ── Segmented filter group ─────────────────────────────────────── */

function SegmentedGroup({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (next: string) => void
  options: Array<{ key: string; label: string; count?: number }>
}) {
  return (
    <div className="evx-seg-group" role="group" aria-label={`Filter by ${label.toLowerCase()}`}>
      <span className="evx-control-label">{label}</span>
      <div className="seg-control seg-control--sm">
        {options.map((opt) => (
          <button
            key={opt.key}
            type="button"
            role="tab"
            aria-selected={value === opt.key}
            className={`seg-control-item${value === opt.key ? " active" : ""}`}
            onClick={() => onChange(opt.key)}
          >
            {opt.label}
            {opt.count !== undefined && (
              <span className="evx-seg-count">{opt.count}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  )
}

/* ── Detail drawer ──────────────────────────────────────────────── */

function EvidenceDrawer({
  item,
  claims,
  onClose,
}: {
  item: F7EvidenceItem | null
  claims: F7Claim[]
  onClose: () => void
}) {
  const dir = item ? directionMark(item.direction) : null
  return (
    <DetailDrawer
      open={Boolean(item)}
      onClose={onClose}
      kicker={item ? `${formatLabel(item.epistemic_type || "UNKNOWN")} · ${formatLabel(item.evidence_type)}` : undefined}
      title={item?.title}
    >
      {item && (
        <div className="evx-drawer">
          <div className="evx-drawer-badges">
            <span className={`epi-badge ${epistemicClass(item.epistemic_type)}`}>
              {formatLabel(item.epistemic_type || "UNKNOWN")}
            </span>
            {dir && (
              <span className={`evx-direction ${dir.cls}`}>
                <span className="evx-direction-dot" />
                {dir.label}
              </span>
            )}
            <span className={`status-badge ${item.verification_status === "CONFLICT" ? "amber" : "slate"}`}>
              <span className="status-badge-dot" />
              {formatLabel(item.verification_status)}
            </span>
          </div>

          <section className="evx-drawer-block">
            <span className="evx-drawer-label">Explanation</span>
            <p>{item.explanation}</p>
          </section>

          <section className="evx-drawer-block">
            <span className="evx-drawer-label">Classification</span>
            <dl className="evx-kv">
              <div><dt>Type</dt><dd>{formatLabel(item.evidence_type)}</dd></div>
              {item.category && <div><dt>Category</dt><dd>{formatLabel(item.category)}</dd></div>}
              {item.topic && <div><dt>Topic</dt><dd>{formatLabel(item.topic)}</dd></div>}
              <div><dt>Confidence</dt><dd>{formatConfidence(item.confidence)}</dd></div>
              <div><dt>Reliability</dt><dd>{formatLabel(item.reliability)}</dd></div>
              {item.derivation && <div><dt>Derivation</dt><dd>{item.derivation}</dd></div>}
            </dl>
          </section>

          <section className="evx-drawer-block">
            <span className="evx-drawer-label">Time &amp; PIT</span>
            <dl className="evx-kv">
              <div><dt>Observed</dt><dd>{item.observation_at ? formatEvidenceObservation(item.observation_at) : "—"}</dd></div>
              <div><dt>Published</dt><dd>{item.published_at ? formatIso(item.published_at) : "—"}</dd></div>
              <div><dt>Available</dt><dd>{item.available_at ? formatIso(item.available_at) : "—"}</dd></div>
              <div><dt>PIT eligibility</dt><dd>
                <span className={`status-badge ${pitTone(item)}`}>
                  <span className="status-badge-dot" />
                  {pitLabel(item)}
                </span>
              </dd></div>
            </dl>
          </section>

          <section className="evx-drawer-block">
            <span className="evx-drawer-label">Source</span>
            {item.source ? (
              <dl className="evx-kv">
                <div><dt>Name</dt><dd>{item.source.name}</dd></div>
                <div><dt>Type</dt><dd>{formatLabel(item.source.source_type)}</dd></div>
                <div><dt>Reliability tier</dt><dd>{item.source.reliability_tier}</dd></div>
              </dl>
            ) : (
              <p className="evx-drawer-empty">No source profile recorded.</p>
            )}
          </section>

          <section className="evx-drawer-block">
            <span className="evx-drawer-label">Provenance</span>
            {item.provenance_ids.length === 0 && item.source_records.length === 0 ? (
              <p className="evx-drawer-empty">No provenance chain recorded.</p>
            ) : (
              <>
                {item.source_records.map((rec, i) => (
                  <div className="evx-record" key={i}>
                    <span className="evx-record-source">{rec.source}</span>
                    {rec.dataset_id && <span className="mono">dataset {rec.dataset_id}</span>}
                    {rec.checksum && <span className="mono">checksum {rec.checksum.slice(0, 16)}…</span>}
                    {rec.available_at && <span>available {formatIso(rec.available_at)}</span>}
                  </div>
                ))}
                {item.source_ids.length > 0 && (
                  <p className="evx-ids mono">{item.source_ids.join(" · ")}</p>
                )}
                {item.provenance_ids.length > 0 && (
                  <p className="evx-ids mono">{item.provenance_ids.join(" · ")}</p>
                )}
              </>
            )}
          </section>

          {claims.length > 0 && (
            <section className="evx-drawer-block">
              <span className="evx-drawer-label">Related evidence</span>
              {claims.map((c) => (
                <p className="evx-related" key={c.claim_id}>{c.text}</p>
              ))}
            </section>
          )}

          {item.verification_status.toUpperCase() === "CONFLICT" && (
            <div className="evx-conflict-note">
              <AlertTriangle size={13} />
              <span>Conflicting verification status — treat interpretation with care.</span>
            </div>
          )}
        </div>
      )}
    </DetailDrawer>
  )

  function pitTone(i: F7EvidenceItem): string {
    const hasAvailability = Boolean(i.available_at)
    return hasAvailability ? "green" : "slate"
  }

  function pitLabel(i: F7EvidenceItem): string {
    return i.available_at ? "Eligible — availability recorded" : "Unknown availability"
  }
}
