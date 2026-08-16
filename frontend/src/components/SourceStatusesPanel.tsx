/**
 * Source statuses: per-source item count, categories, freshness,
 * and provenance completeness. Descriptive only.
 */

import type { SourceStatus } from "../api/types"
import { formatLabel } from "../lib/format"
import { EmptyCopy, PanelHead, Tag } from "./ui"

function SourceRow({ status }: { status: SourceStatus }) {
  return (
    <div className="panel source-row">
      <div className="source-row-head">
        <strong>{status.source_name}</strong>
        <Tag text={status.source_type} tone="slate" />
        {status.stale && <Tag text="STALE" tone="red" />}
        {status.provenance_completeness && (
          <Tag text="PROVENANCE OK" tone="green" />
        )}
      </div>

      <div className="source-row-meta">
        <span>{status.item_count} items</span>
        {status.categories.length > 0 && (
          <span>{status.categories.length} categories</span>
        )}
        {status.days_since_latest_published !== null && (
          <span>{status.days_since_latest_published}d since latest</span>
        )}
      </div>

      {status.categories.length > 0 && (
        <div className="source-categories">
          {status.categories.map((cat) => (
            <span key={cat} className="tag slate">{formatLabel(cat)}</span>
          ))}
        </div>
      )}

      {status.notes.length > 0 && (
        <div className="source-notes">
          {status.notes.map((note) => (
            <div key={note} className="note-row">{note}</div>
          ))}
        </div>
      )}
    </div>
  )
}

export default function SourceStatusesPanel({
  statuses,
}: {
  statuses: SourceStatus[]
}) {
  if (statuses.length === 0) {
    return (
      <section id="source-statuses" className="section-anchor">
        <EmptyCopy text="No source statuses are available for this company." />
      </section>
    )
  }

  const staleCount = statuses.filter((s) => s.stale).length

  return (
    <section id="source-statuses" className="section-anchor">
      <PanelHead
        title="Source statuses"
        subtitle={`${statuses.length} sources | ${staleCount} stale`}
      />

      {statuses.map((s) => (
        <SourceRow key={s.source_name} status={s} />
      ))}
    </section>
  )
}
