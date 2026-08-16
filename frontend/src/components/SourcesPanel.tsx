/**
 * Sources & point-in-time: provenance records, archived source lineage, the
 * explicit PIT contract, and the data-quality panel.
 */

import { Database, ShieldCheck, Clock } from "lucide-react"
import type {
  CompanyResearch,
  DataQuality,
  PointInTime,
  Provenance,
  ProvenanceRecord,
} from "../api/types"
import { formatIso } from "../lib/format"
import { EmptyCopy, PanelHead, Tag } from "./ui"

function SourcePanel({
  title,
  source,
}: {
  title: string
  source?: ProvenanceRecord
}) {
  return (
    <div className="panel source-panel">
      <h3>{title}</h3>
      {source ? (
        <>
          <div className="source-line">
            <span>Source</span>
            <strong>{source.source}</strong>
          </div>
          <div className="source-line">
            <span>Dataset</span>
            <strong>{source.dataset_id || "Not available"}</strong>
          </div>
          <div className="source-line">
            <span>Record</span>
            <strong>{source.record_id || "Not available"}</strong>
          </div>
          <div className="source-line">
            <span>Retrieved at</span>
            <strong>{source.retrieved_at ? formatIso(source.retrieved_at) : "—"}</strong>
          </div>
          <div className="source-line">
            <span>Available at</span>
            <strong>{source.available_at ? formatIso(source.available_at) : "—"}</strong>
          </div>
        </>
      ) : (
        <EmptyCopy text="Source metadata is not available." />
      )}
    </div>
  )
}

function PitRow({
  label,
  value,
  emphasized = false,
}: {
  label: string
  value: string
  emphasized?: boolean
}) {
  return (
    <div className={`pit-row ${emphasized ? "pit-row-emphasized" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function PitPanel({ pit }: { pit: PointInTime }) {
  return (
    <div className="panel pit-panel">
      <div className="panel-head">
        <h3>Point-in-time context</h3>
        <span>Explicit evidence window for this response</span>
      </div>
      <div className="pit-status">
        <ShieldCheck size={16} />
        <Tag
          text={pit.pit_checks_passed ? "PIT CHECKS PASSED" : "PIT CHECKS FAILED"}
          tone={pit.pit_checks_passed ? "green" : "red"}
        />
      </div>
      <div className="pit-grid">
        <PitRow label="As-of" value={pit.as_of} emphasized />
        <PitRow label="Effective as-of" value={pit.effective_as_of} emphasized />
        <PitRow label="Market as-of" value={pit.market_as_of ?? "—"} />
        <PitRow label="Evidence included" value={String(pit.evidence_included)} />
        <PitRow label="Acquired evidence" value={String(pit.acquired_evidence_included)} />
        <PitRow label="Future evidence excluded" value={String(pit.future_evidence_excluded)} />
        <PitRow label="Sources discovered" value={String(pit.sources_discovered)} />
        <PitRow label="Sources accepted" value={String(pit.sources_accepted)} />
        <PitRow label="Sources rejected" value={String(pit.sources_rejected)} />
      </div>
      {pit.notes.length > 0 ? (
        <div className="pit-notes">
          {pit.notes.map((note) => (
            <p key={note}>{note}</p>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function DataQualityPanel({ quality }: { quality: DataQuality }) {
  const invalidFeatures = Object.entries(quality.feature_statuses).filter(
    ([, status]) => status !== "VALID",
  )

  return (
    <div className="panel quality-panel">
      <PanelHead
        title="Data quality"
        subtitle="Validation, coverage, and feature status"
      />
      <div className="quality-list">
        <div>
          <span>Market validation status</span>
          <strong>{quality.market_validation_status}</strong>
        </div>
        <div>
          <span>Accepted market records</span>
          <strong>{quality.market_accepted_records}</strong>
        </div>
        <div>
          <span>Rejected market records</span>
          <strong>{quality.market_rejected_records}</strong>
        </div>
        <div>
          <span>Financial record count</span>
          <strong>{quality.financial_record_count}</strong>
        </div>
        <div>
          <span>Financial data missing</span>
          <strong>{quality.financial_data_missing ? "Yes" : "No"}</strong>
        </div>
        <div>
          <span>Invalid / missing features</span>
          <strong>{invalidFeatures.length}</strong>
        </div>
        <div>
          <span>PIT accepted observations</span>
          <strong>{quality.context.accepted_observations ?? 0}</strong>
        </div>
        <div>
          <span>PIT rejected observations</span>
          <strong>{quality.context.rejected_observations ?? 0}</strong>
        </div>
      </div>

      {invalidFeatures.length > 0 ? (
        <div className="feature-list">
          <strong>Non-valid features</strong>
          {invalidFeatures.map(([feature, status]) => (
            <div className="feature-row" key={feature}>
              <span>{feature}</span>
              <Tag text={status} tone={status === "MISSING" ? "amber" : "slate"} />
            </div>
          ))}
        </div>
      ) : null}

      {quality.warnings.length > 0 ? (
        <div className="warning-list">
          <strong>Warnings</strong>
          {quality.warnings.map((warning) => (
            <div className="warning-row" key={warning}>
              {warning}
            </div>
          ))}
        </div>
      ) : null}

      {quality.provider_failures.length > 0 ? (
        <div className="warning-list">
          <strong>Provider failures</strong>
          {quality.provider_failures.map((failure) => (
            <div className="warning-row" key={failure}>
              {failure}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export default function SourcesPanel({
  data,
}: {
  data: CompanyResearch
}) {
  const provenance: Provenance = data.provenance

  return (
    <section id="sources" className="section-anchor">
      <div className="source-grid">
        <SourcePanel title="Market source" source={provenance.market} />
        <SourcePanel title="Financial source" source={provenance.financials} />
        <div className="panel source-panel">
          <h3>Archived source records</h3>
          {provenance.archived_sources.length > 0 ? (
            <div className="archived-list">
              {provenance.archived_sources.map((sourceId) => (
                <div className="archived-row" key={sourceId}>
                  <Database size={13} />
                  {sourceId}
                </div>
              ))}
            </div>
          ) : (
            <EmptyCopy text="No archived source records were returned." />
          )}
        </div>
      </div>

      <div className="pit-layout">
        <PitPanel pit={data.point_in_time} />
        <DataQualityPanel quality={data.data_quality} />
      </div>

      <div className="as-of-display">
        <Clock size={14} />
        <span>
          This dashboard renders evidence exactly as reported by the API at the
          effective as-of timestamp <b>{data.point_in_time.effective_as_of}</b>.
        </span>
      </div>
    </section>
  )
}
