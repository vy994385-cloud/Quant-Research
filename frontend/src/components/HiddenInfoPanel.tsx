/**
 * Hidden / less-obvious information: co-occurring claims, financial
 * disclosure gaps, and reporting comparability notes. Derived
 * deterministically from recorded evidence. Descriptive only.
 */

import type { HiddenInformation, DerivedObservation } from "../api/types"
import { formatLabel } from "../lib/format"
import { EmptyCopy, PanelHead, Tag } from "./ui"

function ObservationRow({ obs }: { obs: DerivedObservation }) {
  return (
    <div className="panel hidden-obs-row">
      <div className="hidden-obs-head">
        <strong>{obs.label}</strong>
        <Tag text={formatLabel(obs.semantic_category)} tone="slate" />
      </div>
      <p className="hidden-obs-desc">{obs.description}</p>
      <div className="hidden-obs-derivation">
        <strong>Derivation:</strong> {obs.derivation}
      </div>
      <div className="hidden-obs-meta">
        {obs.source_ids.length > 0 && (
          <span>Sources: {obs.source_ids.join(", ")}</span>
        )}
        {obs.provenance_ids.length > 0 && (
          <span>Provenance: {obs.provenance_ids.join(", ")}</span>
        )}
        {obs.related_item_ids.length > 0 && (
          <span>Related: {obs.related_item_ids.join(", ")}</span>
        )}
      </div>
    </div>
  )
}

export default function HiddenInfoPanel({
  hidden,
}: {
  hidden: HiddenInformation | null
}) {
  if (hidden === null) {
    return (
      <section id="hidden-info" className="section-anchor">
        <EmptyCopy text="No hidden / less-obvious information is available for this company." />
      </section>
    )
  }

  return (
    <section id="hidden-info" className="section-anchor">
      <PanelHead
        title="Hidden / less-obvious information"
        subtitle={`${hidden.observations.length} derived observations from recorded evidence`}
      />

      {hidden.notes.length > 0 && (
        <div className="hidden-notes">
          {hidden.notes.map((note) => (
            <div key={note} className="note-row">{note}</div>
          ))}
        </div>
      )}

      {hidden.observations.map((obs) => (
        <ObservationRow key={obs.observation_id} obs={obs} />
      ))}
    </section>
  )
}
