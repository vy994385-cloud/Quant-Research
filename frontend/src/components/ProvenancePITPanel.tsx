/**
 * PROVENANCE & PIT — technical provenance layer.
 *
 * Point-in-time window, source lineage records, and archived source
 * references for this snapshot. This is the deep-detail section: primary
 * cards elsewhere never surface these IDs. Single home for lineage
 * records (the source coverage table does not repeat them).
 */

import type { CompanyResearch, PointInTime, Provenance, ProvenanceRecord } from "../api/types"
import { formatIso, formatPitNote, formatSourceName } from "../lib/format"
import {
  DataField,
  EmptyCopy,
  PanelHead,
  SectionDivider,
  StatusBadge,
} from "./ui"

function LineageRecord({
  title,
  record,
}: {
  title: string
  record?: ProvenanceRecord
}) {
  return (
    <div className="lineage-record">
      <h4>{title}</h4>
      {record ? (
        <div className="data-field-grid">
          <DataField label="Source" value={formatSourceName(record.source)} />
          <DataField label="Record ID" value={record.record_id ? `${record.record_id.slice(0, 12)}${record.record_id.length > 12 ? "…" : ""}` : "Not available"} mono />
          <DataField label="Retrieved" value={record.retrieved_at ? formatIso(record.retrieved_at) : "Not available"} />
          <DataField label="Available" value={record.available_at ? formatIso(record.available_at) : "Not available"} />
        </div>
      ) : (
        <EmptyCopy text="Source metadata not available." />
      )}
    </div>
  )
}

export default function ProvenancePITPanel({ data }: { data: CompanyResearch }) {
  const pit: PointInTime = data.point_in_time
  const provenance: Provenance = data.provenance

  return (
    <section id="provenance-pit" className="section-anchor">
      <PanelHead
        title="Provenance & Point-in-Time"
        subtitle="Evidence window and source lineage behind this research snapshot"
      />

      <div className="section-subgroup">
        <SectionDivider label="Point-in-time context" />
        <div className="pit-status-row">
          <StatusBadge
            text={pit.pit_checks_passed ? "PIT checks passed" : "PIT checks failed"}
            tone={pit.pit_checks_passed ? "green" : "red"}
          />
        </div>

        <dl className="pit-facts">
          <DataField label="Requested as-of" value={formatIso(pit.as_of)} />
          <DataField label="Effective as-of" value={formatIso(pit.effective_as_of)} />
          <DataField label="Market data as-of" value={pit.market_as_of ? formatIso(pit.market_as_of) : "Not available"} />
          <DataField label="Evidence included" value={`${pit.evidence_included} (${pit.acquired_evidence_included} acquired)`} />
          <DataField label="Future evidence excluded" value={String(pit.future_evidence_excluded)} />
          <DataField label="Sources accepted / discovered" value={`${pit.sources_accepted} / ${pit.sources_discovered}`} />
        </dl>

        {pit.notes.length > 0 && (
          <ul className="fin-comparability">
            {pit.notes.map((note) => (
              <li key={note}>{formatPitNote(note)}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="section-subgroup">
        <SectionDivider label="Source lineage records" />
        <div className="lineage-grid">
          <LineageRecord title="Market source record" record={provenance.market} />
          <LineageRecord title="Financial source record" record={provenance.financials} />
        </div>

        {provenance.archived_sources.length > 0 && (
          <div className="archived-block">
            <h4>Archived source records</h4>
            <p className="archived-summary">
              {provenance.archived_sources.length} archived source record{provenance.archived_sources.length !== 1 ? "s" : ""} retained for this snapshot.
            </p>
            <ul className="archived-list">
              {provenance.archived_sources.map((sourceId) => (
                <li key={sourceId} className="mono">{sourceId.length > 16 ? `${sourceId.slice(0, 16)}…` : sourceId}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  )
}
