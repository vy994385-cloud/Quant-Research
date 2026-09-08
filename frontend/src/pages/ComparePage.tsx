/**
 * Compare page: evidence-based side-by-side comparison of companies.
 * Uses the canonical /api/v1/companies/compare endpoint — one call per
 * selection — and renders the aligned facts table without scores,
 * rankings, or recommendations.
 */

import { useCallback, useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Building2, Clock } from "lucide-react"
import {
  fetchCompare,
  fetchDiscovery,
  ApiError,
} from "../api/client"
import type { CompanyComparison, DiscoveryItem } from "../api/types"
import { LoadingState, ErrorState, EmptyState } from "../components/States"
import { formatLabel, formatIso } from "../lib/format"

const CATEGORY_ORDER = [
  "PROFILE",
  "FINANCIALS",
  "DERIVED",
  "EVENTS",
  "EVIDENCE",
  "OBSERVATIONS",
  "CONFLICTS",
  "COVERAGE",
  "SOURCES",
  "PIT",
]

export default function ComparePage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<DiscoveryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<string[]>([])
  const [comparison, setComparison] = useState<CompanyComparison | null>(null)
  const [compareLoading, setCompareLoading] = useState(false)
  const [compareError, setCompareError] = useState<string | null>(null)

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

  const runComparison = useCallback(async (symbols: string[]) => {
    if (symbols.length < 2) {
      setComparison(null)
      setCompareError(null)
      return
    }
    setCompareLoading(true)
    setCompareError(null)
    try {
      const result = await fetchCompare(symbols)
      setComparison(result)
    } catch (err) {
      setComparison(null)
      setCompareError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error ? err.message : "Comparison failed",
      )
    } finally {
      setCompareLoading(false)
    }
  }, [])

  function toggleSymbol(sym: string) {
    setSelected((prev) => {
      const next = prev.includes(sym)
        ? prev.filter((s) => s !== sym)
        : [...prev, sym]
      void runComparison(next)
      return next
    })
  }

  const selectedItems = items.filter((i) => selected.includes(i.symbol))

  const sectionRows = useMemo(() => {
    if (!comparison) return []
    return CATEGORY_ORDER
      .map((category) => ({
        category,
        rows: comparison.rows.filter((r) => r.category === category),
      }))
      .filter((section) => section.rows.length > 0)
  }, [comparison])

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

          {compareLoading && (
            <div className="loading-state" role="status" style={{ margin: "var(--space-6) 0" }}>
              <span className="spinner" aria-hidden />
              <strong>Building side-by-side comparison</strong>
            </div>
          )}

          {compareError && !compareLoading && (
            <div style={{ margin: "var(--space-6) 0" }}>
              <ErrorState error={compareError} />
            </div>
          )}

          {!compareLoading && comparison && (
            <div className="compare-grid">
              {/* Company headers */}
              <div className="compare-row compare-row-header">
                <div className="compare-label-col" />
                {comparison.companies.map((company) => (
                  <div key={company.symbol} className="compare-company-col">
                    <button
                      className="compare-company-header"
                      onClick={() => navigate(`/companies/${company.symbol}`)}
                    >
                      <Building2 size={16} />
                      <div>
                        <strong>{company.symbol}</strong>
                        <small>
                          {company.company_name ?? company.symbol}
                        </small>
                      </div>
                    </button>
                  </div>
                ))}
              </div>

              {comparison.as_of && (
                <CompareRow
                  label="As-of Date"
                  values={comparison.companies.map(() => formatIso(comparison.as_of))}
                  icon={<Clock size={13} />}
                />
              )}

              {comparison.mixed_as_of_warning && (
                <div className="compare-disclaimer">
                  <p className="compare-disclaimer-text">{comparison.mixed_as_of_warning}</p>
                </div>
              )}

              {sectionRows.map((section) => (
                <div key={section.category}>
                  <CompareSection label={`${formatLabel(section.category)} · aligned facts`} />
                  {section.rows.map((row) => (
                    <CompareRow
                      key={row.metric}
                      label={row.label}
                      values={row.cells.map((cell) =>
                        cell.available && cell.value != null
                          ? `${cell.value}${cell.unit ? ` ${cell.unit}` : ""}`
                          : "\u2014",
                      )}
                    />
                  ))}
                </div>
              ))}

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
}: {
  label: string
  values: string[]
  tone?: (string | undefined)[]
  icon?: React.ReactNode
}) {
  return (
    <div className="compare-row">
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