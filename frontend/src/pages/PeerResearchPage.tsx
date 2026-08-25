/**
 * PEER RESEARCH — structured peer company comparison.
 *
 * Select 2-4 companies for side-by-side evidence comparison.
 * Shows shared context, period-aligned data, and source freshness.
 * No winner/loser/score/ranking — just recorded evidence side by side.
 */

import { useMemo, useState } from "react"
import { Link } from "react-router-dom"
import { useDiscovery } from "../useDiscovery"
import { formatLabel } from "../lib/format"
import { Tag } from "../components/ui"
import { LoadingState, ErrorState } from "../components/States"

const MAX_COMPARE = 4

export default function PeerResearchPage() {
  const { items, loading, error } = useDiscovery()
  const [selected, setSelected] = useState<string[]>([])

  const toggle = (symbol: string) => {
    setSelected((prev) => {
      if (prev.includes(symbol)) return prev.filter((s) => s !== symbol)
      if (prev.length >= MAX_COMPARE) return prev
      return [...prev, symbol]
    })
  }

  const selectedItems = useMemo(
    () => selected.map((s) => items.find((i) => i.symbol === s)).filter(Boolean),
    [selected, items],
  )

  return (
    <div className="page-peer-research">
      <section className="page-hero">
        <p className="page-kicker">Peer research</p>
        <h1>Peer Company Comparison</h1>
        <p className="page-subtitle">
          Select 2–4 companies for side-by-side evidence comparison.
          Shared context, period-aligned data, source freshness.
          No winner or loser — recorded evidence only.
        </p>
      </section>

      {loading && <LoadingState label="Loading companies" />}

      {error && <ErrorState error={error} />}

      {!loading && !error && (
        <>
          <section className="peer-selection" aria-label="Company selection">
            <div className="peer-selected-bar">
              <span className="peer-selected-count">
                {selected.length} of {MAX_COMPARE} selected
              </span>
              {selected.length >= 2 && (
                <Link
                  to={`/compare?symbols=${selected.join(",")}`}
                  className="peer-continue-link"
                >
                  Open in Compare →
                </Link>
              )}
            </div>

            <div className="company-table">
              <div className="company-table-head">
                <span className="col-symbol">Symbol</span>
                <span className="col-name">Company</span>
                <span className="col-sector">Sector</span>
                <span className="col-select">Select</span>
              </div>
              {items.map((item) => {
                const isSelected = selected.includes(item.symbol)
                return (
                  <button
                    key={item.symbol}
                    type="button"
                    className={`company-table-row ${isSelected ? "peer-selected" : ""}`}
                    onClick={() => toggle(item.symbol)}
                    aria-pressed={isSelected}
                  >
                    <span className="col-symbol mono">{item.symbol}</span>
                    <span className="col-name">{item.company_name ?? item.symbol}</span>
                    <span className="col-sector">
                      <Tag text={formatLabel(item.sector)} tone="slate" />
                    </span>
                    <span className="col-select">
                      {isSelected ? (
                        <Tag text="Selected" tone="blue" />
                      ) : (
                        <Tag text="Select" tone="slate" />
                      )}
                    </span>
                  </button>
                )
              })}
            </div>
          </section>

          {selectedItems.length >= 2 && (
            <section className="peer-preview" aria-label="Selected companies preview">
              <div className="peer-preview-grid">
                {selectedItems.map((item) => item && (
                  <Link
                    key={item.symbol}
                    to={`/companies/${encodeURIComponent(item.symbol)}`}
                    className="peer-preview-card"
                  >
                    <strong>{item.company_name ?? item.symbol}</strong>
                    <span className="mono">{item.symbol}</span>
                    <Tag text={formatLabel(item.sector)} tone="slate" />
                  </Link>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  )
}
