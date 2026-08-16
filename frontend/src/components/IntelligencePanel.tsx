/**
 * Company intelligence: per-section evidence state with status, confidence,
 * observations, and explicit unknowns.
 */

import { CircleHelp } from "lucide-react"
import type { CompanyResearch, Intelligence, IntelligenceSection } from "../api/types"
import { formatLabel } from "../lib/format"
import { EmptyCopy, Tag } from "./ui"

const SECTIONS: Array<[keyof Omit<Intelligence, "unknown_missing">, string]> = [
  ["business_quality", "Business quality"],
  ["financial_quality", "Financial quality"],
  ["transformation", "Transformation"],
  ["capital_allocation", "Capital allocation"],
  ["competitive_position", "Competitive position"],
  ["innovation", "Innovation"],
  ["future_technology", "Future technology"],
  ["customer_intelligence", "Customers"],
  ["management_intelligence", "Management"],
  ["market_intelligence", "Market intelligence"],
  ["risks_anomalies", "Risks & anomalies"],
]

function statusTone(status: string): "green" | "red" | "amber" | "slate" {
  switch (status) {
    case "SUPPORTED":
      return "green"
    case "CONTRADICTED":
      return "red"
    case "MIXED":
    case "PARTIAL":
      return "amber"
    default:
      return "slate"
  }
}

function SectionCard({
  title,
  section,
}: {
  title: string
  section: IntelligenceSection | null
}) {
  if (section === null) {
    return (
      <article className="panel intelligence-card status-unknown">
        <div className="intelligence-card-head">
          <h3>{title}</h3>
          <Tag text="NOT AVAILABLE" tone="slate" />
        </div>
        <EmptyCopy text="No intelligence was produced for this section." />
      </article>
    )
  }

  return (
    <article
      className={`panel intelligence-card status-${section.status.toLowerCase()}`}
    >
      <div className="intelligence-card-head">
        <h3>{title}</h3>
        <Tag text={section.status} tone={statusTone(section.status)} />
      </div>
      <div className="intelligence-state">
        <span>Confidence</span>
        <strong>{formatLabel(section.confidence)}</strong>
      </div>
      {section.observations.slice(0, 3).map((claim) => (
        <p className="intel-observation" key={claim}>
          {claim}
        </p>
      ))}
      <div className="intel-counts">
        <span>
          Supporting <b>{section.positive_count}</b>
        </span>
        <span>
          Contradicting <b>{section.negative_count}</b>
        </span>
      </div>
      {section.unknown.slice(0, 2).map((item) => (
        <p className="intel-unknown" key={item}>
          <CircleHelp size={13} />
          {item}
        </p>
      ))}
      {section.observations.length === 0 &&
      section.unknown.length === 0 &&
      section.positive_count === 0 &&
      section.negative_count === 0 ? (
        <EmptyCopy text="No section data was returned." />
      ) : null}
    </article>
  )
}

export default function IntelligencePanel({
  data,
}: {
  data: CompanyResearch
}) {
  const intelligence = data.intelligence
  const unknownMissing = intelligence.unknown_missing

  return (
    <section id="intelligence" className="section-anchor">
      <div className="intelligence-grid">
        {SECTIONS.map(([key, title]) => (
          <SectionCard key={key} title={title} section={intelligence[key]} />
        ))}
      </div>

      {unknownMissing.length > 0 ? (
        <div className="panel unknown-missing-panel">
          <div className="panel-head">
            <h3>Unknown / missing intelligence</h3>
            <span>Research areas with no evidence at the as-of cutoff</span>
          </div>
          <div className="warning-list">
            {unknownMissing.map((item) => (
              <div className="warning-row" key={item}>
                {item}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  )
}
