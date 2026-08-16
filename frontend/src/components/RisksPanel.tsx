/**
 * Risks & exceptions: contradicting evidence, narrative key risks,
 * risk/anomaly intelligence, and data-quality warnings.
 */

import { CircleHelp, TriangleAlert } from "lucide-react"
import type { CompanyResearch, ContractEvidence } from "../api/types"
import { formatTitle } from "../lib/format"
import { EmptyCopy, PanelHead, Tag } from "./ui"

function invalidFeatures(data: CompanyResearch): [string, string][] {
  return Object.entries(data.data_quality.feature_statuses).filter(
    ([, status]) => status !== "VALID",
  )
}

function RiskRow({ text }: { text: string }) {
  return (
    <div className="risk-row">
      <TriangleAlert size={16} />
      <span>{text}</span>
    </div>
  )
}

export default function RisksPanel({
  data,
}: {
  data: CompanyResearch
}) {
  const narrative = data.narrative
  const quality = data.data_quality
  const risksSection = data.intelligence.risks_anomalies
  const invalid = invalidFeatures(data)

  const riskStrings = [
    ...(risksSection?.observations ?? []),
    ...invalid.map(
      ([feature, status]) => `${formatTitle(feature)} — ${status}`,
    ),
    ...(quality.market_rejected_records > 0
      ? [
          `${quality.market_rejected_records} market record(s) were rejected during ingestion.`,
        ]
      : []),
  ]

  const hasAny =
    data.evidence.negative.length > 0 ||
    (narrative?.key_risks.length ?? 0) > 0 ||
    riskStrings.length > 0 ||
    quality.warnings.length > 0

  if (!hasAny) {
    return (
      <section id="risks" className="section-anchor">
        <div className="panel">
          <EmptyCopy text="No risk observations, contradicting evidence, or data-quality warnings were returned for this company." />
        </div>
      </section>
    )
  }

  return (
    <section id="risks" className="section-anchor">
      <div className="risk-grid">
        <div className="panel">
          <PanelHead
            title="Negative evidence & exceptions"
            subtitle="Validated adverse or anomalous observations"
          />
          <div className="risk-list">
            {data.evidence.negative.map((item: ContractEvidence) => (
              <RiskRow
                key={item.evidence_id}
                text={`${formatTitle(item.title)} — ${item.explanation}`}
              />
            ))}
            {narrative?.key_risks.map((risk) => (
              <RiskRow key={risk} text={risk} />
            ))}
            {riskStrings.map((item) => (
              <RiskRow key={item} text={item} />
            ))}
          </div>

          {risksSection && risksSection.unknown.length > 0 ? (
            <div className="unknown-section">
              <CircleHelp size={14} />
              <span>{risksSection.unknown[0]}</span>
            </div>
          ) : null}
        </div>

        <div className="panel quality-panel">
          <PanelHead
            title="Data quality warnings"
            subtitle="Point-in-time and provider validation context"
          />
          {quality.warnings.length > 0 ? (
            <div className="warning-list">
              {quality.warnings.map((warning) => (
                <div className="warning-row" key={warning}>
                  {warning}
                </div>
              ))}
            </div>
          ) : (
            <EmptyCopy text="No data-quality warnings were returned." />
          )}

          {quality.provider_failures.length > 0 ? (
            <div className="provider-failures">
              <Tag text="PROVIDER FAILURES" tone="red" />
              {quality.provider_failures.map((failure) => (
                <div className="warning-row" key={failure}>
                  {failure}
                </div>
              ))}
            </div>
          ) : null}

          <div className="quality-list">
            <div>
              <span>Market validation status</span>
              <strong>{quality.market_validation_status}</strong>
            </div>
            <div>
              <span>Accepted / rejected market records</span>
              <strong>
                {quality.market_accepted_records} / {quality.market_rejected_records}
              </strong>
            </div>
            <div>
              <span>Financial data missing</span>
              <strong>{quality.financial_data_missing ? "Yes" : "No"}</strong>
            </div>
            <div>
              <span>Invalid / missing features</span>
              <strong>{invalid.length}</strong>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
