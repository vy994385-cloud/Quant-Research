/**
 * Evidence timeline & research status: the chronological company evidence
 * view plus freshness, coverage, and data-quality status of the research
 * itself. Descriptive only — never a trade signal.
 */

import { Clock, Database, GitCompareArrows } from "lucide-react"
import type {
  CompanyResearch,
  CompanyTimeline,
  IntelCategory,
  ResearchStatus,
  TimelineEntry,
} from "../api/types"
import { formatIso, formatLabel } from "../lib/format"
import { EmptyCopy, PanelHead, Tag } from "./ui"

function categoryTone(
  category: IntelCategory,
): "green" | "red" | "amber" | "blue" | "slate" {
  switch (category) {
    case "FINANCIAL_DISCLOSURE":
      return "blue"
    case "CORPORATE_ACTION":
      return "green"
    case "MANAGEMENT_STATEMENT":
      return "amber"
    case "REGULATORY_LEGAL":
      return "red"
    default:
      return "slate"
  }
}

function verificationTone(
  status: string,
): "green" | "red" | "amber" | "slate" {
  switch (status) {
    case "CONFIRMED":
      return "green"
    case "CONTRADICTED":
      return "red"
    case "ALLEGED":
    case "UNVERIFIED":
    case "REPORTED":
      return "amber"
    default:
      return "slate"
  }
}

function TimelineEntryRow({ entry }: { entry: TimelineEntry }) {
  return (
    <div className="timeline-row">
      <time>{entry.timeline_at ? formatIso(entry.timeline_at) : "—"}</time>
      <div>
        <div className="timeline-entry-head">
          <strong>{entry.title}</strong>
          <Tag
            text={formatLabel(entry.intel_category)}
            tone={categoryTone(entry.intel_category)}
          />
          <Tag
            text={entry.verification_status}
            tone={verificationTone(entry.verification_status)}
          />
        </div>
        {entry.description ? <p>{entry.description}</p> : null}
        <div className="timeline-meta">
          <span>{entry.source.source_name}</span>
          {entry.source.source_url ? (
            <span>{entry.source.source_url}</span>
          ) : null}
          {entry.provenance_id ? (
            <span>provenance: {entry.provenance_id}</span>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function TimelineList({ timeline }: { timeline: CompanyTimeline }) {
  if (timeline.entries.length === 0) {
    return <EmptyCopy text="No chronological evidence was knowable at the as-of cutoff." />
  }

  return (
    <div className="timeline">
      {timeline.entries.map((entry) => (
        <TimelineEntryRow key={entry.entry_id} entry={entry} />
      ))}
    </div>
  )
}

function StatusCard({
  title,
  icon,
  rows,
}: {
  title: string
  icon: React.ReactNode
  rows: Array<[string, string]>
}) {
  return (
    <div className="panel status-card">
      <PanelHead title={title} subtitle="Descriptive research state" />
      <div className="status-card-icon">{icon}</div>
      <div className="quality-list">
        {rows.map(([label, value]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </div>
  )
}

function ResearchStatusStrip({ status }: { status: ResearchStatus }) {
  const freshness = status.freshness
  const coverage = status.coverage
  const quality = status.quality

  const notes = [
    ...freshness.notes,
    ...coverage.notes,
    ...quality.notes,
    ...quality.insufficient_evidence_notes.map(
      (note) => `Insufficient evidence: ${note}`,
    ),
  ]

  return (
    <div className="timeline-status-grid">
      <StatusCard
        title="Freshness"
        icon={<Clock size={15} />}
        rows={[
          ["Latest published", freshness.latest_published_at ? formatIso(freshness.latest_published_at) : "—"],
          ["Days since published", freshness.days_since_latest_published?.toString() ?? "—"],
          ["Stale", freshness.stale ? "Yes" : "No"],
        ]}
      />
      <StatusCard
        title="Coverage"
        icon={<Database size={15} />}
        rows={[
          ["Intelligence items", String(coverage.item_count)],
          ["Categories covered", String(Object.keys(coverage.by_category).length)],
          ["Missing categories", String(coverage.missing_categories.length)],
        ]}
      />
      <StatusCard
        title="Quality"
        icon={<GitCompareArrows size={15} />}
        rows={[
          ["Conflicts", String(quality.conflict_count)],
          ["Evidence links", String(quality.evidence_link_count)],
          ["Deduplicated", String(quality.deduplicated_count)],
        ]}
      />
      {notes.length > 0 ? (
        <div className="timeline-status-notes">
          {notes.map((note) => (
            <div className="timeline-status-note" key={note}>
              {note}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export default function TimelinePanel({
  data,
}: {
  data: CompanyResearch
}) {
  const timeline = data.timeline
  const status = data.research_status

  return (
    <section id="timeline" className="section-anchor">
      {status !== null ? <ResearchStatusStrip status={status} /> : null}

      <div className="panel timeline-panel">
        <div className="panel-head">
          <h3>Company evidence timeline</h3>
          <span>
            Chronological, point-in-time evidence known at{" "}
            {timeline ? formatIso(timeline.as_of) : "the as-of cutoff"}
          </span>
        </div>

        {timeline === null || timeline.entries.length === 0 ? (
          <EmptyCopy text="No evidence timeline was returned for this company." />
        ) : (
          <>
            {timeline.counts ? (
              <div className="timeline-counts">
                {Object.entries(timeline.counts).map(([category, count]) => (
                  <Tag
                    key={category}
                    text={`${formatLabel(category)} ${count}`}
                    tone={categoryTone(category as IntelCategory)}
                  />
                ))}
              </div>
            ) : null}
            <TimelineList timeline={timeline} />
            {timeline.notes.length > 0 ? (
              <div className="warning-list">
                {timeline.notes.map((note) => (
                  <div className="warning-row" key={note}>
                    {note}
                  </div>
                ))}
              </div>
            ) : null}
          </>
        )}
      </div>
    </section>
  )
}
