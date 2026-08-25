/**
 * MARKET CONTEXT — company-level market evidence inside the workspace.
 *
 * Renders only what the research payload actually carries: recorded market
 * intelligence observations, the market data validation status, and the
 * market provenance record. Cross-market context lives in the dedicated
 * Market Intelligence and Technical workspaces (linked, not duplicated).
 */

import { Link } from "react-router-dom"
import type { CompanyResearch } from "../api/types"
import { formatIso, formatLabel, formatNumber, formatSourceName } from "../lib/format"
import { DataField, EmptyCopy, PanelHead, StatusBadge } from "./ui"

export default function MarketContextPanel({ data }: { data: CompanyResearch }) {
  const market = data.intelligence.market_intelligence
  const quality = data.data_quality
  const provenance = data.provenance?.market
  const hasObservations = Boolean(market && market.observations.length > 0)

  return (
    <div className="section-anchor" id="market-context">
      <PanelHead
        title="Market"
        subtitle="Recorded market context and the state of the market data behind this research"
      />

      <div className="market-context-grid">
        <div className="market-observations">
          <h4>Market intelligence</h4>
          {hasObservations ? (
            <ul className="intel-observations">
              {market!.observations.map((observation) => (
                <li key={observation}>{observation}</li>
              ))}
            </ul>
          ) : (
            <EmptyCopy text="No market intelligence observations are currently supported by evidence for this company." />
          )}
          {market && !hasObservations && market.unknown.length > 0 && (
            <p className="limited-note">Limited coverage: {market.unknown.length} open unknown(s) in this area.</p>
          )}

          <h4>Cross-market workspaces</h4>
          <ul className="market-links">
            <li>
              <Link to="/market-intelligence">Market Intelligence</Link>
              <span>— market-wide observation registry</span>
            </li>
            <li>
              <Link to="/technical">Technical</Link>
              <span>— indicator-derived observations</span>
            </li>
          </ul>
        </div>

        <aside className="market-quality">
          <h4>Market data status</h4>
          <dl className="data-field-grid">
            <div className="data-field">
              <dt className="data-field-label">Validation</dt>
              <dd className="data-field-value">
                <StatusBadge
                  text={formatLabel(quality.market_validation_status)}
                  tone={quality.market_validation_status === "VALIDATED" ? "green" : "amber"}
                />
              </dd>
            </div>
            <DataField label="Accepted records" value={formatNumber(String(quality.market_accepted_records))} />
            <DataField label="Rejected records" value={formatNumber(String(quality.market_rejected_records))} />
            {provenance?.source && (
              <DataField label="Market source" value={formatSourceName(provenance.source)} />
            )}
            {provenance?.retrieved_at && (
              <DataField label="Retrieved" value={formatIso(provenance.retrieved_at)} />
            )}
          </dl>
          <p className="market-note">
            Missing or rejected market data is shown as-is; it is not treated as a negative
            signal about the company.
          </p>
        </aside>
      </div>
    </div>
  )
}
