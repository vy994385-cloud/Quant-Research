/**
 * Evidence ledger: positive, negative, and neutral evidence with expandable
 * traceability (confidence, observation time, source/provenance lineage).
 */

import type { ReactNode } from "react"
import {
  ChevronDown,
  CircleHelp,
  TrendingDown,
  TrendingUp,
} from "lucide-react"
import type { ContractEvidence, CompanyResearch } from "../api/types"
import { formatConfidence, formatEvidenceObservation, formatTitle } from "../lib/format"
import { EmptyCopy } from "./ui"

function EvidenceCard({ item }: { item: ContractEvidence }) {
  return (
    <details className="evidence-card">
      <summary>
        <div>
          <strong>{formatTitle(item.title)}</strong>
          <p>{item.explanation}</p>
        </div>
        <ChevronDown size={16} />
      </summary>
      <div className="evidence-detail">
        <span>
          Confidence <b>{formatConfidence(item.confidence)}</b>
        </span>
        <span>Reliability {item.reliability}</span>
        <span>Observed {formatEvidenceObservation(item.observation_at)}</span>
        <span>
          Source IDs:{" "}
          {item.source_ids.length > 0 ? item.source_ids.join(", ") : "Not available"}
        </span>
        <span>
          Provenance IDs:{" "}
          {item.provenance_ids.length > 0
            ? item.provenance_ids.join(", ")
            : "Not available"}
        </span>
      </div>
    </details>
  )
}

function EvidenceColumn({
  tone,
  title,
  icon,
  items,
  empty,
}: {
  tone: string
  title: string
  icon: ReactNode
  items: ContractEvidence[]
  empty: string
}) {
  return (
    <div className={`panel evidence-panel ${tone}`}>
      <div className="evidence-panel-title">
        {icon}
        <div>
          <h3>{title}</h3>
          <span>
            {items.length} item{items.length === 1 ? "" : "s"}
          </span>
        </div>
      </div>
      {items.length > 0 ? (
        items.map((item) => <EvidenceCard key={item.evidence_id} item={item} />)
      ) : (
        <EmptyCopy text={empty} />
      )}
    </div>
  )
}

export default function EvidencePanel({
  data,
}: {
  data: CompanyResearch
}) {
  const evidence = data.evidence

  return (
    <section id="evidence" className="section-anchor">
      <div className="evidence-columns">
        <EvidenceColumn
          tone="positive"
          title="Supporting evidence"
          icon={<TrendingUp size={16} />}
          items={evidence.positive}
          empty="No supporting evidence was included in this response."
        />
        <EvidenceColumn
          tone="negative"
          title="Contradicting evidence"
          icon={<TrendingDown size={16} />}
          items={evidence.negative}
          empty="No contradicting evidence was included in this response."
        />
        <EvidenceColumn
          tone="neutral"
          title="Neutral / context evidence"
          icon={<CircleHelp size={16} />}
          items={evidence.neutral}
          empty="No neutral evidence was included in this response."
        />
      </div>

      {evidence.conflict_detected ? (
        <p className="conflict-note">
          Conflicting evidence was detected and retained: the report presents
          both sides rather than reducing them to a single direction.
        </p>
      ) : null}
    </section>
  )
}
