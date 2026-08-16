/**
 * Company identity header with research status tags, as-of selection, and
 * refresh controls.
 */

import { Building2, RefreshCw } from "lucide-react"
import type { CompanyResearch } from "../api/types"
import { formatConfidence, formatIso } from "../lib/format"
import { Tag } from "./ui"
import { signalTone } from "../lib/signal"

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
  const quality = data.data_quality
  const pit = data.point_in_time

  return (
    <section className="company-header-block">
      <div className="company-header">
        <div className="company-identity">
          <div className="company-icon">
            <Building2 size={25} />
          </div>
          <div>
            <div className="ticker">NSE:{data.company.symbol}</div>
            <h1>{data.company.company_name ?? data.company.symbol}</h1>
            <div className="company-meta">
              <span>{data.company.sector ?? "Sector not available"}</span>
              <span>Effective as of {formatIso(pit.effective_as_of)}</span>
            </div>
          </div>
        </div>
        <div className="header-tags">
          <Tag
            text={`${formatConfidence(data.assessment.confidence)} confidence`}
            tone={signalTone(data.assessment.direction)}
          />
          <Tag
            text={data.assessment.research_ready ? "RESEARCH READY" : "PARTIAL"}
            tone={data.assessment.research_ready ? "green" : "amber"}
          />
          <Tag
            text={quality.market_validation_status}
            tone={quality.market_validation_status === "VALID" ? "green" : "amber"}
          />
          <button
            className="refresh-button"
            onClick={onRefresh}
            disabled={refreshing}
            aria-label="Refresh research"
          >
            <RefreshCw className={refreshing ? "spin" : ""} size={15} />
            Refresh
          </button>
        </div>
      </div>
      <div className="as-of-bar">
        <label htmlFor="as-of-input">As-of date</label>
        <input
          id="as-of-input"
          type="date"
          value={asOf}
          onChange={(event) => onAsOfChange(event.target.value)}
          aria-label="Point-in-time as-of date"
        />
        <button
          className="refresh-button"
          onClick={onApplyAsOf}
          disabled={refreshing || !asOf}
        >
          Re-run research
        </button>
        <span className="as-of-note">
          Rebuilds this report at the requested point in time; evidence dated
          after the cutoff is excluded by the API.
        </span>
      </div>
    </section>
  )
}
