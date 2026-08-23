/**
 * COMPANY CONTEXT BAR — single-row company identity for the workspace.
 *
 * Identity (ticker, name, sector) on the left; research-context chips
 * (evidence volume, freshness, PIT status) and point-in-time controls on
 * the right. This is not a dashboard header: it carries exactly the facts
 * needed to orient the reader before any section is read.
 */

import { useState } from "react"
import { Building2, RefreshCw, Star } from "lucide-react"
import type { CompanyResearch } from "../api/types"
import { formatIso } from "../lib/format"
import { isWatched, toggleWatch } from "../lib/localResearch"
import { StatusBadge } from "./ui"

interface CompanyHeaderProps {
  data: CompanyResearch
  asOf: string
  onAsOfChange: (value: string) => void
  onApplyAsOf: () => void
  onRefresh: () => void
  refreshing: boolean
}

export default function CompanyHeader({
  data,
  asOf,
  onAsOfChange,
  onApplyAsOf,
  onRefresh,
  refreshing,
}: CompanyHeaderProps) {
  const [showAsOf, setShowAsOf] = useState(false)
  const [watched, setWatched] = useState(() => isWatched(data.company.symbol))
  const {
    company,
    research_status,
    assessment,
    data_quality,
    point_in_time,
  } = data
  const freshness = research_status?.freshness

  function handleToggleWatch() {
    toggleWatch(company.symbol)
    setWatched(isWatched(company.symbol))
  }

  return (
    <header className="company-header-block">
      <div className="company-header">
        <div className="company-identity">
          <span className="company-icon" aria-hidden>
            <Building2 size={20} />
          </span>
          <div>
            <p className="ticker">{company.symbol}</p>
            <h1>{company.company_name ?? company.symbol}</h1>
            <div className="company-meta">
              <span>{company.sector ? company.sector : "Sector not available"}</span>
              <span aria-hidden>·</span>
              <span>Effective as of {formatIso(point_in_time.effective_as_of)}</span>
              {point_in_time.market_as_of ? (
                <>
                  <span aria-hidden>·</span>
                  <span>Market as of {formatIso(point_in_time.market_as_of)}</span>
                </>
              ) : null}
            </div>
          </div>
        </div>

        <div className="header-tags">
          <StatusBadge text={`${point_in_time.evidence_included} EVIDENCE`} tone="slate" />
          {freshness?.days_since_latest_published !== null &&
            freshness?.days_since_latest_published !== undefined && (
              <StatusBadge
                text={
                  freshness.stale
                    ? `STALE · ${freshness.days_since_latest_published}D`
                    : `UPDATED ${freshness.days_since_latest_published}D AGO`
                }
                tone={freshness.stale ? "amber" : "green"}
              />
            )}
          {assessment.research_ready ? (
            <StatusBadge text="RESEARCH READY" tone="blue" />
          ) : (
            <StatusBadge text="PARTIAL RESEARCH" tone="slate" />
          )}
          {data_quality.market_validation_status === "VALIDATED" && (
            <StatusBadge text="DATA VALIDATED" tone="green" />
          )}
          {point_in_time.pit_checks_passed ? (
            <StatusBadge text="PIT VERIFIED" tone="blue" />
          ) : (
            <StatusBadge text="PIT CHECKS FAILED" tone="red" />
          )}
          <button
            type="button"
            className={`track-button${watched ? " active" : ""}`}
            onClick={handleToggleWatch}
            aria-pressed={watched}
            aria-label={watched ? `Remove ${company.symbol} from watchlist` : `Track ${company.symbol}`}
            title={watched ? "Remove from watchlist (stored on this device)" : "Add to watchlist (stored on this device)"}
          >
            <Star size={13} fill={watched ? "currentColor" : "none"} />
            <span>{watched ? "Tracked" : "Track"}</span>
          </button>
          <button
            type="button"
            className={`refresh-button${refreshing ? " spin" : ""}`}
            onClick={onRefresh}
            disabled={refreshing}
            aria-label="Refresh research"
          >
            <RefreshCw size={13} />
            <span>Refresh</span>
          </button>
          <button
            type="button"
            className="refresh-button as-of-toggle"
            onClick={() => setShowAsOf((value) => !value)}
            aria-expanded={showAsOf}
            aria-controls="as-of-panel"
          >
            As-of…
          </button>
        </div>
      </div>

      {showAsOf && (
        <div className="as-of-bar" id="as-of-panel">
          <label htmlFor="as-of-input">Requested as-of</label>
          <input
            id="as-of-input"
            type="date"
            value={asOf}
            onChange={(event) => onAsOfChange(event.target.value)}
          />
          <button
            type="button"
            className="refresh-button"
            onClick={() => {
              if (asOf) {
                onApplyAsOf()
                setShowAsOf(false)
              }
            }}
            disabled={!asOf || refreshing}
          >
            Re-run at date
          </button>
          <p className="as-of-note">
            Rebuilds this report at the requested point in time; evidence dated after the
            cutoff is excluded.
          </p>
        </div>
      )}
    </header>
  )
}
