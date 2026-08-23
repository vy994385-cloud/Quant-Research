/**
 * SOURCE COVERAGE — per-source freshness, item counts, and provenance
 * completeness as a compact table. Aggregate health stays at the top;
 * raw lineage records live in the provenance section (single source of
 * truth — not duplicated here).
 */

import { useMemo } from "react"
import type { CompanyResearch, SourceStatus } from "../api/types"
import { formatIso, formatLabel, formatSourceName } from "../lib/format"
import { EmptyCopy, PanelHead, Tag } from "./ui"

function SourceRow({ source }: { source: SourceStatus }) {
  return (
    <tr className={source.stale ? "source-row stale" : "source-row"}>
      <th scope="row" title={source.source_name}>
        {formatSourceName(source.source_name)}
      </th>
      <td>{formatLabel(source.source_type)}</td>
      <td className="num">{source.item_count}</td>
      <td>{source.latest_published_at ? formatIso(source.latest_published_at) : "\u2014"}</td>
      <td>
        {source.days_since_latest_published !== null
          ? `${source.days_since_latest_published}d`
          : "\u2014"}
      </td>
      <td>
        <Tag
          text={source.stale ? "Stale" : "Fresh"}
          tone={source.stale ? "red" : "green"}
        />
      </td>
      <td>
        <Tag
          text={source.provenance_completeness ? "Complete" : "Incomplete"}
          tone={source.provenance_completeness ? "green" : "amber"}
        />
      </td>
    </tr>
  )
}

export default function SourceHealthPanel({ data }: { data: CompanyResearch }) {
  const source_statuses = data.source_statuses

  const totals = useMemo(
    () => ({
      items: source_statuses.reduce((sum, s) => sum + s.item_count, 0),
      stale: source_statuses.filter((s) => s.stale).length,
    }),
    [source_statuses],
  )

  if (source_statuses.length === 0) {
    return (
      <section id="source-health" className="section-anchor">
        <PanelHead
          title="Source Coverage"
          subtitle="Per-source freshness and provenance status"
        />
        <EmptyCopy text="No source status data is available for this company." />
      </section>
    )
  }

  return (
    <section id="source-health" className="section-anchor">
      <PanelHead
        title="Source Coverage"
        subtitle={`${source_statuses.length} source${source_statuses.length !== 1 ? "s" : ""} · ${totals.items} items · ${totals.stale} stale`}
      />

      <div className="table-scroll" tabIndex={0} role="region" aria-label="Source coverage table">
        <table className="source-table">
          <caption className="visually-hidden">Per-source freshness and provenance completeness</caption>
          <thead>
            <tr>
              <th scope="col">Source</th>
              <th scope="col">Type</th>
              <th scope="col" className="num">Items</th>
              <th scope="col">Latest published</th>
              <th scope="col">Age</th>
              <th scope="col">Freshness</th>
              <th scope="col">Provenance</th>
            </tr>
          </thead>
          <tbody>
            {source_statuses.map((source) => (
              <SourceRow key={source.source_name} source={source} />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
