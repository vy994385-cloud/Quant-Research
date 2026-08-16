/**
 * Research overview: headline metrics, overall assessment, research score,
 * and the evidence narrative.
 */

import {
  BarChart3,
  CircleHelp,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
} from "lucide-react"
import type { CompanyResearch } from "../api/types"
import { formatConfidence, formatLabel, formatNumber } from "../lib/format"
import { Metric, PanelHead, ScoreDonut, Tag } from "./ui"
import { signalColor, signalTone } from "../lib/signal"

function invalidFeatureCount(data: CompanyResearch): number {
  return Object.values(data.data_quality.feature_statuses).filter(
    (status) => status !== "VALID",
  ).length
}

function unknownCount(data: CompanyResearch): number {
  const quality = data.data_quality

  return (
    invalidFeatureCount(data) +
    (quality.financial_data_missing ? 1 : 0) +
    (quality.context.rejected_observations ?? 0)
  )
}

export default function OverviewPanel({
  data,
}: {
  data: CompanyResearch
}) {
  const assessment = data.assessment
  const score = data.research_score
  const narrative = data.narrative
  const evidence = data.evidence

  return (
    <>
      <section id="overview" className="section-anchor">
        <div className="metric-grid">
          <Metric
            label="Research score"
            value={formatNumber(score.total)}
            detail="Composite research context, 0–100"
            icon={<BarChart3 />}
          />
          <Metric
            label="Assessment confidence"
            value={formatConfidence(assessment.confidence)}
            detail="Confidence in the available evidence"
            icon={<ShieldCheck />}
          />
          <Metric
            label="Supporting evidence"
            value={String(evidence.positive_count)}
            detail="Validated positive observations"
            tone="positive"
            icon={<TrendingUp />}
          />
          <Metric
            label="Contradicting evidence"
            value={String(evidence.negative_count)}
            detail="Validated negative observations"
            tone="negative"
            icon={<TrendingDown />}
          />
          <Metric
            label="Unknown / missing"
            value={String(unknownCount(data))}
            detail="Neither positive nor negative"
            tone="neutral"
            icon={<CircleHelp />}
          />
        </div>

        <div className="overview-grid">
          <article className="panel conclusion-panel">
            <div className="panel-kicker">OVERALL CONCLUSION</div>
            <h2>{formatLabel(assessment.conclusion)}</h2>
            <p>{assessment.thesis}</p>
            <div className="score-line">
              <span>Research score</span>
              <strong>{formatNumber(score.total)} / 100</strong>
            </div>
            <div className="score-line">
              <span>Evidence direction</span>
              <strong>{formatLabel(assessment.direction)}</strong>
            </div>
            <div className="score-line">
              <span>Conflict detected</span>
              <strong>{assessment.conflict_detected ? "Yes" : "No"}</strong>
            </div>
          </article>

          <div className="overview-side">
            <div className="panel score-panel">
              <ScoreDonut
                value={Number(score.total)}
                color={signalColor(score.signal)}
              />
              <div className="score-components">
                {Object.entries(score.components).map(([key, value]) => (
                  <div className="score-component" key={key}>
                    <span>{formatLabel(key)}</span>
                    <strong>{formatNumber(value)}</strong>
                  </div>
                ))}
              </div>
            </div>
            <div className="panel assessment-tags">
              <Tag
                text={`Signal ${formatLabel(score.signal)}`}
                tone={signalTone(score.signal)}
              />
              <Tag
                text={`Direction ${formatLabel(assessment.direction)}`}
                tone={signalTone(assessment.direction)}
              />
            </div>
          </div>
        </div>

        <div className="panel narrative-panel">
          <PanelHead
            title="Evidence narrative"
            subtitle="How the available evidence is interpreted — a description, not a trade instruction."
          />
          {narrative ? (
            <div className="narrative-body">
              <p className="narrative-thesis">{narrative.thesis}</p>
              {narrative.strongest_evidence.length > 0 ? (
                <div className="narrative-group">
                  <strong>Strongest evidence</strong>
                  <ul>
                    {narrative.strongest_evidence.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {narrative.uncertainty.length > 0 ? (
                <div className="narrative-group">
                  <strong>Uncertainty</strong>
                  <ul>
                    {narrative.uncertainty.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {narrative.evidence_gaps.length > 0 ? (
                <div className="narrative-group">
                  <strong>Evidence gaps</strong>
                  <ul>
                    {narrative.evidence_gaps.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {narrative.what_could_change_thesis.length > 0 ? (
                <div className="narrative-group">
                  <strong>What could change this thesis</strong>
                  <ul>
                    {narrative.what_could_change_thesis.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="empty-copy">
              A narrative interpretation is not available for this response.
            </p>
          )}
        </div>
      </section>
    </>
  )
}
