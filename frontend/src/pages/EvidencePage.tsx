/**
 * Evidence Lineage page: canonical evidence with full provenance traceability.
 * Fetches from the dedicated F7 evidence lineage endpoint.
 * CLAIM -> EVIDENCE -> SOURCE -> RAW RECORD where available.
 */

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  Activity,
  Building2,
  FileSearch,
  Database,
  Shield,
  ChevronDown,
  Search,
} from "lucide-react"
import { fetchDiscovery, fetchEvidenceLineage } from "../api/client"
import { ApiError } from "../api/client"
import type {
  CompanyEvidenceResponse,
  DiscoveryItem,
  F7EvidenceItem,
} from "../api/types"
import {
  formatConfidence,
  formatEvidenceObservation,
  formatIso,
  formatLabel,
  formatTitle,
  pluralize,
} from "../lib/format"
import { Tag } from "../components/ui"

/* ── Helpers ────────────────────────────────────────────────────── */

function directionTone(d: string): "green" | "red" | "slate" {
  if (d === "POSITIVE") return "green"
  if (d === "NEGATIVE") return "red"
  return "slate"
}

function epistemicBadge(ep: string): string {
  switch (ep) {
    case "REPORTED": return "REPORTED"
    case "DERIVED": return "DERIVED"
    case "INFERRED": return "INFERRED"
    default: return "UNKNOWN"
  }
}

/* ── Evidence Card ─────────────────────────────────────────────── */

function EvidenceCard({ item }: { item: F7EvidenceItem }) {
  return (
    <details className="ev-card">
      <summary>
        <div className="ev-card-head">
          <div className="ev-card-tags">
            <Tag text={formatLabel(item.direction)} tone={directionTone(item.direction)} />
            <Tag text={formatLabel(epistemicBadge(item.epistemic_type))} tone="slate" />
            {item.verification_status !== "UNVERIFIED" && (
              <Tag text={formatLabel(item.verification_status)} tone="slate" />
            )}
          </div>
          <strong>{formatTitle(item.title)}</strong>
          <p>{item.explanation}</p>
        </div>
        <ChevronDown size={16} />
      </summary>
      <div className="ev-detail">
        <div className="ev-detail-row">
          <span className="ev-detail-label">Type</span>
          <span>{formatLabel(item.evidence_type)}</span>
        </div>
        <div className="ev-detail-row">
          <span className="ev-detail-label">Category</span>
          <span>{item.category ? formatLabel(item.category) : "—"}</span>
        </div>
        <div className="ev-detail-row">
          <span className="ev-detail-label">Confidence</span>
          <span>{formatConfidence(item.confidence)}</span>
        </div>
        <div className="ev-detail-row">
          <span className="ev-detail-label">Reliability</span>
          <span>{formatLabel(item.reliability)}</span>
        </div>
        <div className="ev-detail-row">
          <span className="ev-detail-label">Observed</span>
          <span>{item.observation_at ? formatEvidenceObservation(item.observation_at) : "—"}</span>
        </div>
        {item.derivation && (
          <div className="ev-detail-row">
            <span className="ev-detail-label">Derivation</span>
            <span>{item.derivation}</span>
          </div>
        )}
        {item.source && (
          <div className="ev-detail-row">
            <span className="ev-detail-label">Source</span>
            <span>{item.source.name} ({item.source.source_type}, {item.source.reliability_tier})</span>
          </div>
        )}
        {item.source_ids.length > 0 && (
          <div className="ev-detail-row">
            <span className="ev-detail-label">Source IDs</span>
            <span className="mono">{item.source_ids.join(", ")}</span>
          </div>
        )}
        {item.provenance_ids.length > 0 && (
          <div className="ev-detail-row">
            <span className="ev-detail-label">Provenance IDs</span>
            <span className="mono">{item.provenance_ids.join(", ")}</span>
          </div>
        )}
        {item.source_records.length > 0 && (
          <div className="ev-detail-records">
            <span className="ev-detail-label">Raw Records</span>
            {item.source_records.map((rec, i) => (
              <div className="ev-record" key={i}>
                <span>{rec.source}</span>
                {rec.dataset_id && <span className="mono">dataset: {rec.dataset_id}</span>}
                {rec.checksum && <span className="mono">checksum: {rec.checksum}</span>}
                {rec.available_at && <span>Available: {formatIso(rec.available_at)}</span>}
              </div>
            ))}
          </div>
        )}
      </div>
    </details>
  )
}

/* ── Main Component ─────────────────────────────────────────────── */

export default function EvidencePage() {
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState("")
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)
  const [lineage, setLineage] = useState<CompanyEvidenceResponse | null>(null)
  const [lineageLoading, setLineageLoading] = useState(false)
  const [lineageError, setLineageError] = useState<string | null>(null)
  const [filterDirection, setFilterDirection] = useState("ALL")
  const [filterEpistemic, setFilterEpistemic] = useState("ALL")

  useEffect(() => {
    let cancelled = false
    fetchDiscovery()
      .then((res) => {
        if (!cancelled) {
          setItems(res.results)
          setLoading(false)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Discovery unavailable")
          setLoading(false)
        }
      })
    return () => { cancelled = true }
  }, [])

  const researchable = useMemo(
    () => items.filter((i) => i.research_available),
    [items],
  )

  const filteredCompanies = useMemo(() => {
    const q = query.toLowerCase()
    if (!q) return researchable
    return researchable.filter(
      (i) =>
        i.symbol.toLowerCase().includes(q) ||
        (i.company_name ?? "").toLowerCase().includes(q) ||
        i.sector.toLowerCase().includes(q),
    )
  }, [researchable, query])

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

  const evidence = useMemo(
    () => lineage?.evidence_lineage?.evidence ?? [],
    [lineage],
  )
  const totalEvidence = lineage?.evidence_lineage?.total_evidence ?? 0
  const totalClaims = lineage?.evidence_lineage?.total_claims ?? 0
  const totalSources = lineage?.evidence_lineage?.total_sources ?? 0
  const pitFiltered = lineage?.evidence_lineage?.pit_filtered_count ?? 0
  const notes = lineage?.evidence_lineage?.notes ?? []
  const directionCounts = lineage?.evidence_lineage?.direction_counts ?? {}
  const epistemicCounts = useMemo(
    () => lineage?.evidence_lineage?.epistemic_type_counts ?? {},
    [lineage],
  )
  const sourceProfiles = lineage?.evidence_lineage?.source_profiles ?? []
  const claims = lineage?.evidence_lineage?.claims ?? []

  const filteredEvidence = useMemo(() => {
    let result = evidence
    if (filterDirection !== "ALL") {
      result = result.filter((e) => e.direction === filterDirection)
    }
    if (filterEpistemic !== "ALL") {
      result = result.filter((e) => e.epistemic_type === filterEpistemic)
    }
    return result
  }, [evidence, filterDirection, filterEpistemic])

  const epistemicTypes = useMemo(() => {
    return Object.keys(epistemicCounts).sort()
  }, [epistemicCounts])

  return (
    <div className="page-evidence">
      <section className="page-hero">
        <h1>Evidence Lineage</h1>
        <p className="page-subtitle">
          Canonical evidence with full provenance traceability. Every item
          carries source, epistemic type, confidence, and point-in-time validation.
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
        <div className="ev-layout">
          {/* LEFT: Company selector */}
          <div className="ev-sidebar">
            <div className="panel">
              <div className="panel-head">
                <h3>Select Company</h3>
                <span>{researchable.length} companies</span>
              </div>
              <div className="ev-search">
                <Search size={14} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Filter companies..."
                  aria-label="Filter companies"
                />
              </div>
              <div className="ev-company-list">
                {filteredCompanies.map((item) => (
                  <button
                    key={item.symbol}
                    className={`ev-company-item ${selectedSymbol === item.symbol ? "active" : ""}`}
                    onClick={() => void loadEvidence(item.symbol)}
                  >
                    <Building2 size={13} />
                    <div>
                      <strong>{item.symbol}</strong>
                      <small>{item.company_name ?? item.symbol}</small>
                    </div>
                  </button>
                ))}
                {filteredCompanies.length === 0 && (
                  <div className="ev-empty-list">
                    <Search size={14} />
                    <span>No matching companies</span>
                  </div>
                )}
              </div>
            </div>

            {/* Traceability chain */}
            <div className="panel">
              <div className="panel-head">
                <h3>Traceability Chain</h3>
              </div>
              <div className="ev-chain">
                <div className="ev-chain-step">
                  <Database size={16} />
                  <strong>Source</strong>
                  <small>Name, type, reliability</small>
                </div>
                <div className="ev-chain-arrow">→</div>
                <div className="ev-chain-step">
                  <Shield size={16} />
                  <strong>Provenance</strong>
                  <small>Dataset, record, checksum</small>
                </div>
                <div className="ev-chain-arrow">→</div>
                <div className="ev-chain-step">
                  <FileSearch size={16} />
                  <strong>Evidence</strong>
                  <small>Claim, type, direction</small>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT: Evidence content */}
          <div className="ev-content">
            {!selectedSymbol && (
              <div className="empty-state">
                <FileSearch size={28} />
                <strong>Select a company</strong>
                <p>Choose a company to view its canonical evidence lineage with full provenance.</p>
              </div>
            )}

            {selectedSymbol && lineageLoading && (
              <div className="loading-state" role="status">
                <Activity className="spin" size={26} />
                <strong>Loading evidence lineage</strong>
                <span>Fetching evidence for {selectedSymbol}...</span>
              </div>
            )}

            {selectedSymbol && lineageError && (
              <div className="empty-state error" role="alert">
                <FileSearch size={28} />
                <strong>Could not load evidence</strong>
                <p>{lineageError}</p>
              </div>
            )}

            {selectedSymbol && lineage && !lineageLoading && (
              <>
                {/* Summary stats */}
                <div className="ev-summary">
                  <div className="ev-stat">
                    <strong>{totalEvidence}</strong>
                    <span>evidence items</span>
                  </div>
                  {/* "claims" is only shown when it differs from the evidence
                      count — otherwise the twin chips read as duplicated copy. */}
                  {totalClaims !== totalEvidence && (
                    <div className="ev-stat">
                      <strong>{totalClaims}</strong>
                      <span>claims</span>
                    </div>
                  )}
                  <div className="ev-stat">
                    {/* A zero with no source profiles means this extract did
                        not report sources — show an explicit em-dash instead
                        of a misleading hard zero. */}
                    <strong>{totalSources > 0 ? totalSources : "—"}</strong>
                    <span>sources</span>
                  </div>
                  {pitFiltered > 0 && (
                    <div className="ev-stat ev-stat-warn">
                      <strong>{pitFiltered}</strong>
                      <span>PIT-filtered</span>
                    </div>
                  )}
                </div>

                {/* Direction counts */}
                {Object.keys(directionCounts).length > 0 && (
                  <div className="ev-direction-bar">
                    {Object.entries(directionCounts).map(([dir, count]) => (
                      <Tag key={dir} text={`${formatLabel(dir)}: ${count}`} tone={directionTone(dir)} />
                    ))}
                  </div>
                )}

                {/* Filters */}
                <div className="ev-filter-bar">
                  <span className="ev-filter-label">Direction:</span>
                  <button
                    className={`ev-filter-btn ${filterDirection === "ALL" ? "active" : ""}`}
                    onClick={() => setFilterDirection("ALL")}
                  >
                    All
                  </button>
                  {Object.keys(directionCounts).sort().map((dir) => (
                    <button
                      key={dir}
                      className={`ev-filter-btn ${filterDirection === dir ? "active" : ""}`}
                      onClick={() => setFilterDirection(dir)}
                    >
                      {formatLabel(dir)} ({directionCounts[dir]})
                    </button>
                  ))}

                  <span className="ev-filter-label" style={{ marginLeft: 12 }}>Epistemic:</span>
                  <button
                    className={`ev-filter-btn ${filterEpistemic === "ALL" ? "active" : ""}`}
                    onClick={() => setFilterEpistemic("ALL")}
                  >
                    All
                  </button>
                  {epistemicTypes.map((ep) => (
                    <button
                      key={ep}
                      className={`ev-filter-btn ${filterEpistemic === ep ? "active" : ""}`}
                      onClick={() => setFilterEpistemic(ep)}
                    >
                      {formatLabel(ep)} ({epistemicCounts[ep]})
                    </button>
                  ))}
                </div>

                {/* Evidence list */}
                {filteredEvidence.length === 0 ? (
                  <div className="empty-state">
                    <Search size={24} />
                    <strong>No matching evidence</strong>
                    <p>
                      {evidence.length === 0
                        ? `No evidence was included for ${selectedSymbol}.`
                        : "Try adjusting the filters."}
                    </p>
                  </div>
                ) : (
                  <div className="ev-list">
                    {filteredEvidence.map((item) => (
                      <EvidenceCard key={item.evidence_id} item={item} />
                    ))}
                  </div>
                )}

                {/* Claims */}
                {claims.length > 0 && (
                  <div className="ev-claims-section">
                    <div className="ev-section-head">
                      <Shield size={14} />
                      <strong>Claims ({claims.length})</strong>
                    </div>
                    <div className="ev-claims-list">
                      {claims.map((claim) => (
                        <div className="ev-claim" key={claim.claim_id}>
                          <div className="ev-claim-head">
                            <Tag text={formatLabel(claim.category)} tone="slate" />
                            <Tag text={formatLabel(claim.epistemic_type)} tone="slate" />
                          </div>
                          <p>{claim.text}</p>
                          <div className="ev-claim-meta">
                            <span>Confidence: {formatConfidence(claim.confidence)}</span>
                            <span>Status: {formatLabel(claim.verification_status)}</span>
                            <span>Evidence: {pluralize(claim.evidence_ids.length, "item")}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Source profiles */}
                {sourceProfiles.length > 0 && (
                  <div className="ev-sources-section">
                    <div className="ev-section-head">
                      <Database size={14} />
                      <strong>Source Profiles ({sourceProfiles.length})</strong>
                    </div>
                    <div className="ev-sources-list">
                      {sourceProfiles.map((src) => (
                        <div className="ev-source-row" key={src.source_id}>
                          <div className="ev-source-info">
                            <strong>{src.name}</strong>
                            <Tag text={formatLabel(src.source_type)} tone="slate" />
                            <Tag text={src.reliability_tier} tone="slate" />
                          </div>
                          <div className="ev-source-meta">
                            {src.domain && <span>{src.domain}</span>}
                            {src.official && <Tag text="Official" tone="green" />}
                            {src.requires_confirmation && <Tag text="Needs confirmation" tone="red" />}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Notes */}
                {notes.length > 0 && (
                  <div className="ev-notes">
                    <Shield size={13} />
                    <div>
                      {notes.map((n, i) => (
                        <span key={i}>{n}</span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Provenance note */}
                <div className="ev-provenance-note">
                  <Shield size={13} />
                  <span>
                    Every evidence item carries source IDs and provenance IDs for
                    full traceability. Point-in-time validation ensures evidence is
                    only from sources available before the requested date.
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
