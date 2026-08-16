/**
 * Trends: financial trend signals plus the financial-trends score component.
 *
 * Trend evidence is surfaced from the FINANCIAL_TREND signal category and the
 * financial-quality intelligence section; nothing is invented here.
 */

import { TrendingUp } from "lucide-react"
import type { CompanyResearch, ContractSignal } from "../api/types"
import {
  formatConfidence,
  formatEvidenceObservation,
  formatLabel,
  formatNumber,
} from "../lib/format"
import { EmptyCopy, Tag } from "./ui"
import { signalTone } from "../lib/signal"

function isTrendSignal(signal: ContractSignal): boolean {
  return (
    signal.category === "FINANCIAL_TREND" ||
    signal.title.toLowerCase().includes("trend")
  )
}

export default function TrendsPanel({
  data,
}: {
  data: CompanyResearch
}) {
  const trendSignals = data.signals.filter(isTrendSignal)
  const financialTrendsScore = data.research_score.components.financial_trends
  const financialQuality = data.intelligence.financial_quality

  const trendObservations = (financialQuality?.observations ?? []).filter((claim) =>
    /trend|is available|reported|measurable/i.test(claim),
  )

  return (
    <section id="trends" className="section-anchor">
      <div className="panel trend-score-panel">
        <div className="trend-score-head">
          <TrendingUp size={16} />
          <div>
            <strong>Financial trends component</strong>
            <span>
              Contribution of multi-period financial trends to the research score
            </span>
          </div>
        </div>
        <strong className="trend-score-value">
          {financialTrendsScore ? formatNumber(financialTrendsScore) : "—"}
        </strong>
      </div>

      <div className="panel">
        <div className="panel-head">
          <h3>Trend signals</h3>
          <span>Point-in-time financial trend signals from the research engine</span>
        </div>
        {trendSignals.length > 0 ? (
          <div className="signal-list">
            {trendSignals.map((signal) => (
              <article className="signal-row" key={signal.signal_id}>
                <div className="signal-row-head">
                  <strong>{signal.title}</strong>
                  <span className="signal-tags">
                    <Tag text={formatLabel(signal.direction)} tone={signalTone(signal.direction)} />
                    <Tag text={signal.severity} tone="slate" />
                    <Tag text={`${formatConfidence(signal.confidence)} confidence`} tone="slate" />
                  </span>
                </div>
                <p>{signal.explanation}</p>
                <div className="signal-meta">
                  <span>Observed {formatEvidenceObservation(signal.observation_at)}</span>
                  {signal.supporting_features.length > 0 ? (
                    <span>
                      Features: {signal.supporting_features.map(formatLabel).join(", ")}
                    </span>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyCopy text="No financial trend signals were produced for this company." />
        )}
      </div>

      <div className="panel">
        <div className="panel-head">
          <h3>Financial quality context</h3>
          <span>Observations used by the financial-quality intelligence section</span>
        </div>
        {trendObservations.length > 0 ? (
          <div className="observation-list">
            {trendObservations.map((claim) => (
              <div className="observation-row" key={claim}>
                {claim}
              </div>
            ))}
          </div>
        ) : (
          <EmptyCopy text="No financial-quality observations are available." />
        )}
      </div>
    </section>
  )
}
