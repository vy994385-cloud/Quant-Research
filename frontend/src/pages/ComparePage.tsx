/**
 * Compare page: evidence-based side-by-side comparison of companies.
 * Fetches actual research data for each selected company and presents
 * key research dimensions without scores, rankings, or recommendations.
 */

import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import {
  Activity,
  Building2,
  XCircle,
  Clock,
} from "lucide-react"
import { fetchDiscovery, fetchResearch } from "../api/client"
import { ApiError } from "../api/client"
import type { CompanyResearch, DiscoveryItem } from "../api/types"
import { LoadingState, ErrorState, EmptyState } from "../components/States"
import { formatConfidence, formatIso, formatLabel, pluralize } from "../lib/format"

interface CompanyData {
  symbol: string
  research: CompanyResearch | null
  loading: boolean
  error: string | null
}

export default function ComparePage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [companies, setCompanies] = useState<Map<string, CompanyData>>(new Map())

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

  const researchable = useMemo(() => items.filter((i) => i.research_available), [items])

  const fetchCompanyResearch = useCallback(async (sym: string) => {
    setCompanies((prev) => {
      const next = new Map(prev)
      next.set(sym, { symbol: sym, research: null, loading: true, error: null })
      return next
    })

    try {
      const result = await fetchResearch(sym)
      setCompanies((prev) => {
        const next = new Map(prev)
        next.set(sym, { symbol: sym, research: result, loading: false, error: null })
        return next
      })
    } catch (err) {
      const message = err instanceof ApiError
        ? err.message
        : err instanceof Error ? err.message : "Failed to load research"
      setCompanies((prev) => {
        const next = new Map(prev)
        next.set(sym, { symbol: sym, research: null, loading: false, error: message })
        return next
      })
    }
  }, [])

  function toggleSymbol(sym: string) {
    const isRemoving = selected.includes(sym)

    setSelected((prev) =>
      prev.includes(sym) ? prev.filter((s) => s !== sym) : [...prev, sym]
    )

    if (isRemoving) {
      setCompanies((map) => {
        const next = new Map(map)
        next.delete(sym)
        return next
      })
    } else {
      // Re-selecting always (re)fetches unless a request is already in
      // flight — so a previously failed load retries on re-select.
      const existing = companies.get(sym)
      if (!existing || !existing.loading) {
        void fetchCompanyResearch(sym)
      }
    }
  }

  const selectedItems = items.filter((i) => selected.includes(i.symbol))
  const companyDataList = selected
    .map((sym) => companies.get(sym))
    .filter((c): c is CompanyData => c !== undefined)

  return (
    <div className="page-compare">
      <section className="page-hero">
        <p className="page-kicker">Screen</p>
        <h1>Compare</h1>
        <p className="page-subtitle">
          Evidence-based comparison. Side-by-side factual data — no winner, no loser, no score.
          The researcher makes the judgment.
        </p>
      </section>

      {loading && (
        <LoadingState label="Loading comparison data" />
      )}

      {error && (
        <ErrorState error={error} />
      )}

      {!loading && !error && (
        <>
          <section className="compare-selection">
            <div className="panel">
              <div className="panel-head">
                <h3>Select Companies to Compare</h3>
                <span>{selected.length} selected</span>
              </div>
              <div className="compare-checkbox-grid">
                {researchable.map((item: DiscoveryItem) => (
                  <label key={item.symbol} className="compare-checkbox">
                    <input
                      type="checkbox"
                      checked={selected.includes(item.symbol)}
                      onChange={() => toggleSymbol(item.symbol)}
                    />
                    <span>
                      <strong>{item.symbol}</strong>
                      <small>{item.company_name ?? item.symbol}</small>
                    </span>
                  </label>
                ))}
              </div>
              {researchable.length === 0 && (
                <p className="compare-disclaimer-text">
                  No companies with research available yet.
                </p>
              )}
            </div>
          </section>

          {selectedItems.length < 2 && (
            <EmptyState
              title="Select at least 2 companies"
              description="Choose companies from the list above to enable comparison."
            />
          )}

          {selectedItems.length >= 2 && (
            <div className="compare-grid">
              {/* Company headers */}
              <div className="compare-row compare-row-header">
                <div className="compare-label-col" />
                {companyDataList.map((cd) => (
                  <div key={cd.symbol} className="compare-company-col">
                    <button
                      className="compare-company-header"
                      onClick={() => navigate(`/companies/${cd.symbol}`)}
                    >
                      <Building2 size={16} />
                      <div>
                        <strong>{cd.symbol}</strong>
                        <small>
                          {cd.research?.company.company_name ?? cd.symbol}
                        </small>
                      </div>
                    </button>
                  </div>
                ))}
              </div>

              {/* Loading/error row */}
              {companyDataList.some((cd) => cd.loading || cd.error) && (
                <div className="compare-row">
                  <div className="compare-label-col">
                    <span className="compare-label">Status</span>
                  </div>
                  {companyDataList.map((cd) => (
                    <div key={cd.symbol} className="compare-company-col">
                      {cd.loading ? (
                        <div className="compare-loading">
                          <Activity className="spin" size={14} />
                          <span>Loading...</span>
                        </div>
                      ) : cd.error ? (
                        <div className="compare-error">
                          <XCircle size={14} />
                          <span>{cd.error}</span>
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}

              {/* Data rows - only show when at least one company has research */}
              {companyDataList.some((cd) => cd.research) && (
                <>
                  <CompareRow
                    label="Sector"
                    values={companyDataList.map((cd) =>
                      cd.research?.company.sector ? formatLabel(cd.research.company.sector) : "—"
                    )}
                  />
                  <CompareRow
                    label="As-of Date"
                    values={companyDataList.map((cd) =>
                      cd.research ? formatIso(cd.research.point_in_time.as_of) : "—"
                    )}
                    icon={<Clock size={13} />}
                  />
                  <CompareRow
                    label="Research Ready"
                    values={companyDataList.map((cd) => {
                      const ready = cd.research?.assessment.research_ready
                      return ready === undefined ? "—" : ready ? "Yes" : "Not yet"
                    })}
                    tone={companyDataList.map((cd) =>
                      cd.research == null ? undefined : cd.research.assessment.research_ready ? "green" : undefined
                    )}
                  />
                  <CompareRow
                    label="PIT Checks"
                    values={companyDataList.map((cd) => {
                      const passed = cd.research?.point_in_time.pit_checks_passed
                      return passed === undefined ? "—" : passed ? "Passed" : "Failed"
                    })}
                    tone={companyDataList.map((cd) =>
                      cd.research?.point_in_time.pit_checks_passed ? "green" : "red"
                    )}
                  />
                  <CompareRow
                    label="Evidence Items"
                    values={companyDataList.map((cd) =>
                      cd.research
                        ? `${cd.research.point_in_time.evidence_included} included`
                        : "—"
                    )}
                  />
                  <CompareRow
                    label="Sources Accepted"
                    values={companyDataList.map((cd) =>
                      cd.research
                        ? `${cd.research.point_in_time.sources_accepted} / ${cd.research.point_in_time.sources_discovered}`
                        : "—"
                    )}
                  />

                  {/* Thesis / Assessment */}
                  <CompareSection label="Research assessment" />
                  <CompareRow
                    label="Thesis"
                    values={companyDataList.map((cd) =>
                      cd.research?.assessment.thesis ?? "—"
                    )}
                    multiline
                  />
                  <CompareRow
                    label="Direction"
                    values={companyDataList.map((cd) =>
                      cd.research?.assessment.direction
                        ? formatLabel(cd.research.assessment.direction)
                        : "—"
                    )}
                  />
                  <CompareRow
                    label="Confidence"
                    values={companyDataList.map((cd) =>
                      cd.research?.assessment.confidence
                        ? formatConfidence(cd.research.assessment.confidence)
                        : "—"
                    )}
                  />

                  {/* Intelligence sections */}
                  <CompareSection label="Intelligence sections" />
                  {(
                    [
                      ["Business Quality", "business_quality"],
                      ["Financial Quality", "financial_quality"],
                      ["Transformation", "transformation"],
                      ["Capital Allocation", "capital_allocation"],
                      ["Competitive Position", "competitive_position"],
                      ["Innovation", "innovation"],
                      ["Future Technology", "future_technology"],
                      ["Customer Intelligence", "customer_intelligence"],
                      ["Management Intelligence", "management_intelligence"],
                      ["Market Intelligence", "market_intelligence"],
                      ["Risks & Anomalies", "risks_anomalies"],
                    ] as const
                  ).map(([label, key]) => (
                    <CompareRow
                      key={key}
                      label={label}
                      values={companyDataList.map((cd) => {
                        const section = cd.research?.intelligence[key]
                        if (!section) return "No data"
                        const obsCount = pluralize(section.observations.length, "observation")
                        return section.unknown.length > 0
                          ? `${formatLabel(section.status)} (${obsCount}, ${section.unknown.length} unknown)`
                          : `${formatLabel(section.status)} (${obsCount})`
                      })}
                      tone={companyDataList.map((cd) => {
                        const section = cd.research?.intelligence[key]
                        if (!section) return undefined
                        // Supported sections read positive, mixed ones amber;
                        // unknown/absent coverage stays neutral — missing is
                        // not negative.
                        const status = section.status.toUpperCase()
                        if (status === "SUPPORTED" || status === "COVERED") return "green"
                        if (status === "MIXED" || status === "PARTIAL") return "amber"
                        return undefined
                      })}
                    />
                  ))}

                  {/* Evidence summary */}
                  <CompareSection label="Evidence summary" />
                  <CompareRow
                    label="Positive Evidence"
                    values={companyDataList.map((cd) =>
                      cd.research
                        ? `${cd.research.evidence.positive_count} item${cd.research.evidence.positive_count === 1 ? "" : "s"}`
                        : "—"
                    )}
                    tone={companyDataList.map((cd) => {
                      const pos = cd.research?.evidence.positive_count
                      return pos !== undefined && pos > 0 ? "green" : undefined
                    })}
                  />
                  <CompareRow
                    label="Negative Evidence"
                    values={companyDataList.map((cd) =>
                      cd.research
                        ? `${cd.research.evidence.negative_count} item${cd.research.evidence.negative_count === 1 ? "" : "s"}`
                        : "—"
                    )}
                    tone={companyDataList.map((cd) => {
                      const neg = cd.research?.evidence.negative_count
                      return neg !== undefined && neg > 0 ? "red" : undefined
                    })}
                  />
                  <CompareRow
                    label="Neutral Evidence"
                    values={companyDataList.map((cd) =>
                      cd.research
                        ? `${cd.research.evidence.neutral_count} item${cd.research.evidence.neutral_count === 1 ? "" : "s"}`
                        : "—"
                    )}
                  />
                  <CompareRow
                    label="Conflict Detected"
                    values={companyDataList.map((cd) =>
                      cd.research == null ? "—" : cd.research.evidence.conflict_detected ? "Yes" : "No"
                    )}
                    tone={companyDataList.map((cd) =>
                      cd.research?.evidence.conflict_detected ? "amber" : undefined
                    )}
                  />

                  {/* Data quality */}
                  <CompareSection label="Data quality" />
                  <CompareRow
                    label="Market Validation"
                    values={companyDataList.map((cd) =>
                      cd.research
                        ? formatLabel(cd.research.data_quality.market_validation_status)
                        : "—"
                    )}
                  />
                  <CompareRow
                    label="Financial Records"
                    values={companyDataList.map((cd) =>
                      cd.research
                        ? `${cd.research.data_quality.financial_record_count}`
                        : "—"
                    )}
                  />
                  <CompareRow
                    label="Provider Failures"
                    values={companyDataList.map((cd) => {
                      const pf = cd.research?.data_quality.provider_failures
                      return pf ? `${pf.length} failed` : "—"
                    })}
                    tone={companyDataList.map((cd) => {
                      const pf = cd.research?.data_quality.provider_failures
                      return pf && pf.length > 0 ? "slate" : undefined
                    })}
                  />

                  {/* Unknown / missing */}
                  <CompareSection label="Research gaps" />
                  <CompareRow
                    label="Unknown Categories"
                    values={companyDataList.map((cd) => {
                      const unknown = cd.research?.intelligence.unknown_missing
                      return unknown ? `${unknown.length} missing` : "—"
                    })}
                  />
                  <CompareRow
                    label="Unknown Observations"
                    values={companyDataList.map((cd) => {
                      if (!cd.research) return "—"
                      const intel = cd.research.intelligence
                      let total = 0
                      for (const section of [
                        intel.business_quality,
                        intel.financial_quality,
                        intel.transformation,
                        intel.capital_allocation,
                        intel.competitive_position,
                        intel.innovation,
                        intel.future_technology,
                        intel.customer_intelligence,
                        intel.management_intelligence,
                        intel.market_intelligence,
                        intel.risks_anomalies,
                      ]) {
                        if (section) total += section.unknown.length
                      }
                      return `${total} observations`
                    })}
                  />

                  {/* Narrative / thesis — the assessment Thesis row above is
                      canonical; here only risks and gaps add new detail. */}
                  {companyDataList.some((cd) => cd.research?.narrative) && (
                    <>
                      <CompareSection label="Narrative" />
                      <CompareRow
                        label="Key Risks"
                        values={companyDataList.map((cd) => {
                          const risks = cd.research?.narrative?.key_risks
                          return risks && risks.length > 0
                            ? risks.join("; ")
                            : "—"
                        })}
                        multiline
                      />
                      <CompareRow
                        label="Evidence Gaps"
                        values={companyDataList.map((cd) => {
                          const gaps = cd.research?.narrative?.evidence_gaps
                          return gaps && gaps.length > 0
                            ? gaps.join("; ")
                            : "—"
                        })}
                        multiline
                      />
                    </>
                  )}
                </>
              )}

              {/* No scores disclaimer */}
              <div className="compare-disclaimer">
                <p className="compare-disclaimer-text">
                  Factual data with evidence provenance only — no winners, losers,
                  scores, or recommendations. The researcher makes the judgment.
                </p>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

/* ── Helper components ──────────────────────────────────────────────── */

function CompareSection({ label }: { label: string }) {
  return (
    <div className="compare-row compare-row-section">
      <div className="compare-label-col">
        <span className="compare-section-label">{label}</span>
      </div>
    </div>
  )
}

function CompareRow({
  label,
  values,
  tone,
  icon,
  multiline,
}: {
  label: string
  values: string[]
  tone?: (string | undefined)[]
  icon?: React.ReactNode
  multiline?: boolean
}) {
  return (
    <div className={`compare-row ${multiline ? "compare-row-multiline" : ""}`}>
      <div className="compare-label-col">
        {icon && <span className="compare-icon">{icon}</span>}
        <span className="compare-label">{label}</span>
      </div>
      {values.map((value, i) => (
        <div key={i} className="compare-company-col">
          <span className={`compare-value ${tone?.[i] ? `compare-tone-${tone[i]}` : ""}`}>
            {value}
          </span>
        </div>
      ))}
    </div>
  )
}
